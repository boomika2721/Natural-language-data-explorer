import os
import unittest
import json
from app import app
import auth_db

class TestNLDEAuthPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()
        auth_db.init_auth_db()

    def test_01_landing_page(self):
        """Unauthenticated user visits '/' should see Landing Page."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Natural Language Data Explorer", res.data)
        self.assertIn(b"Sign In", res.data)

    def test_02_dashboard_protection(self):
        """Visiting '/dashboard' without login should redirect to /login."""
        res = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

    def test_03_api_protection(self):
        """Calling API /query without login should return 401 Unauthorized JSON."""
        res = self.client.post('/query', json={"query": "Show all students"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("Authentication required", data['error'])

    def test_04_user_registration(self):
        """Register a new user and test duplicate email rejection."""
        # Clean up test user if exists
        test_email = "tester_nlp@test.com"
        conn = auth_db.get_db()
        conn.execute("DELETE FROM users WHERE email = ?;", (test_email,))
        conn.commit()
        conn.close()

        res = self.client.post('/register', data={
            "full_name": "Test Analyst",
            "email": test_email,
            "password": "Password123",
            "confirm_password": "Password123",
            "role": "User"
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        # Duplicate email test
        res_dup = self.client.post('/register', data={
            "full_name": "Test Analyst 2",
            "email": test_email,
            "password": "Password123",
            "confirm_password": "Password123",
            "role": "User"
        })
        self.assertIn(b"already exists", res_dup.data)

    def test_05_login_demo_user(self):
        """Login with demo user credentials."""
        with self.client:
            res = self.client.post('/login', data={
                "email": "demo@nlde.com",
                "password": "Demo@123"
            }, follow_redirects=False)
            self.assertEqual(res.status_code, 302)
            self.assertIn('/dashboard', res.headers['Location'])

            # Now visit dashboard
            res_dash = self.client.get('/dashboard')
            self.assertEqual(res_dash.status_code, 200)
            self.assertIn(b"Welcome back", res_dash.data)

            # Test user stats endpoint
            res_stats = self.client.get('/api/user/stats')
            self.assertEqual(res_stats.status_code, 200)
            stats_data = res_stats.get_json()
            self.assertTrue(stats_data['success'])
            self.assertEqual(stats_data['stats']['role'], 'User')

            # User cannot access admin portal
            res_admin = self.client.get('/admin', follow_redirects=False)
            self.assertEqual(res_admin.status_code, 302) # redirected away

    def test_06_admin_access(self):
        """Login as Admin and access Admin Portal & APIs."""
        with self.client:
            # Login as Admin
            res = self.client.post('/login', data={
                "email": "admin@nlde.com",
                "password": "Admin@123"
            }, follow_redirects=False)
            self.assertEqual(res.status_code, 302)

            # Access admin portal
            res_admin = self.client.get('/admin')
            self.assertEqual(res_admin.status_code, 200)
            self.assertIn(b"Admin Portal", res_admin.data)

            # Access admin overview API
            res_overview = self.client.get('/api/admin/overview')
            self.assertEqual(res_overview.status_code, 200)
            overview_data = res_overview.get_json()
            self.assertTrue(overview_data['success'])
            self.assertIn('stats', overview_data)
            self.assertIn('users', overview_data)

    def test_07_query_execution_and_history(self):
        """Execute query, verify SQL safety, and check query history logging."""
        with self.client:
            # Login
            self.client.post('/login', data={"email": "demo@nlde.com", "password": "Demo@123"})
            
            # Execute valid query
            res = self.client.post('/query', json={"query": "Show students from Chennai"})
            self.assertEqual(res.status_code, 200)
            q_data = res.get_json()
            self.assertTrue(q_data['success'])
            self.assertIn("SELECT", q_data['sql_query'])

            # Verify query history has this item
            res_hist = self.client.get('/history')
            self.assertEqual(res_hist.status_code, 200)
            h_data = res_hist.get_json()
            self.assertTrue(h_data['success'])
            self.assertTrue(len(h_data['history']) > 0)
            self.assertEqual(h_data['history'][0]['query'], "Show students from Chennai")

            # Test SQL Injection / destructive rejection
            res_bad = self.client.post('/query', json={"query": "DROP TABLE students;"})
            # Validator or engine will reject or sanitize safely
            bad_data = res_bad.get_json()
            # Must not execute destructive drop
            self.assertTrue(res_bad.status_code in (400, 403) or not bad_data.get('success', False) or bad_data.get('unsafe', False))

if __name__ == '__main__':
    unittest.main()
