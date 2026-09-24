import os
import sqlite3
import datetime
from typing import Dict, Any, List, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_FILE

def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_auth_db():
    """Initializes authentication, multi-user datasets, history, and log tables."""
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # 1. Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'User',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
        """)

        # 2. User Datasets table (for isolation and tracking)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                table_name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                original_filename TEXT,
                file_path TEXT,
                file_size_kb REAL DEFAULT 0,
                row_count INTEGER DEFAULT 0,
                column_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 3. Query History table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_question TEXT NOT NULL,
                generated_sql TEXT NOT NULL,
                table_name TEXT,
                row_count INTEGER DEFAULT 0,
                confidence INTEGER DEFAULT 90,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 4. Reports table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_type TEXT NOT NULL,
                report_name TEXT NOT NULL,
                table_name TEXT,
                query_used TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 5. Login Logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT NOT NULL,
                ip_address TEXT,
                status TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Seed default Admin and Demo User accounts if not present
        cur.execute("SELECT id FROM users WHERE email = 'admin@nlde.com';")
        admin_row = cur.fetchone()
        if not admin_row:
            admin_pwd = generate_password_hash("Admin@123")
            cur.execute("""
                INSERT INTO users (full_name, email, password_hash, role, is_active, created_at)
                VALUES ('System Administrator', 'admin@nlde.com', ?, 'Admin', 1, CURRENT_TIMESTAMP);
            """, (admin_pwd,))
            print("[AUTH] Seeded default Admin: admin@nlde.com / Admin@123")

        cur.execute("SELECT id FROM users WHERE email = 'demo@nlde.com';")
        demo_row = cur.fetchone()
        if not demo_row:
            demo_pwd = generate_password_hash("Demo@123")
            cur.execute("""
                INSERT INTO users (full_name, email, password_hash, role, is_active, created_at)
                VALUES ('Demo Analyst', 'demo@nlde.com', ?, 'User', 1, CURRENT_TIMESTAMP);
            """, (demo_pwd,))
            print("[AUTH] Seeded default Demo User: demo@nlde.com / Demo@123")

        conn.commit()
    finally:
        conn.close()

# User Management Functions
def create_user(full_name: str, email: str, password: str, role: str = 'User') -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Registers a new user after validating fields and duplicate email."""
    full_name = full_name.strip()
    email = email.strip().lower()
    
    if not full_name or len(full_name) < 2:
        return False, "Full Name must be at least 2 characters long.", None
    if not email or '@' not in email or '.' not in email:
        return False, "Please provide a valid email address.", None
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    role = 'Admin' if role.strip().lower() == 'admin' else 'User'
    pwd_hash = generate_password_hash(password)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?;", (email,))
        if cur.fetchone():
            return False, f"An account with email '{email}' already exists.", None

        cur.execute("""
            INSERT INTO users (full_name, email, password_hash, role, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP);
        """, (full_name, email, pwd_hash, role))
        user_id = cur.lastrowid
        conn.commit()

        user = {
            "id": user_id,
            "full_name": full_name,
            "email": email,
            "role": role,
            "is_active": 1
        }
        return True, "User registered successfully!", user
    except Exception as e:
        return False, f"Registration failed: {str(e)}", None
    finally:
        conn.close()

def verify_user(email: str, password: str, ip_address: str = '127.0.0.1') -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Verifies credentials, checks active status, records audit log, updates last login."""
    email = email.strip().lower()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?;", (email,))
        user_row = cur.fetchone()

        if not user_row:
            cur.execute("""
                INSERT INTO login_logs (user_id, email, ip_address, status, timestamp)
                VALUES (NULL, ?, ?, 'FAILED_EMAIL_NOT_FOUND', CURRENT_TIMESTAMP);
            """, (email, ip_address))
            conn.commit()
            return False, None, "Invalid email or password."

        user = dict(user_row)
        if not user.get('is_active', 1):
            cur.execute("""
                INSERT INTO login_logs (user_id, email, ip_address, status, timestamp)
                VALUES (?, ?, ?, 'FAILED_ACCOUNT_DISABLED', CURRENT_TIMESTAMP);
            """, (user['id'], email, ip_address))
            conn.commit()
            return False, None, "Your account has been disabled by an administrator."

        if not check_password_hash(user['password_hash'], password):
            cur.execute("""
                INSERT INTO login_logs (user_id, email, ip_address, status, timestamp)
                VALUES (?, ?, ?, 'FAILED_WRONG_PASSWORD', CURRENT_TIMESTAMP);
            """, (user['id'], email, ip_address))
            conn.commit()
            return False, None, "Invalid email or password."

        # Successful login
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            UPDATE users SET last_login = ? WHERE id = ?;
        """, (now_str, user['id']))
        cur.execute("""
            INSERT INTO login_logs (user_id, email, ip_address, status, timestamp)
            VALUES (?, ?, ?, 'SUCCESS', CURRENT_TIMESTAMP);
        """, (user['id'], email, ip_address))
        conn.commit()

        # Remove password hash before returning
        user.pop('password_hash', None)
        user['last_login'] = now_str
        return True, user, "Login successful."
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, full_name, email, role, is_active, created_at, last_login FROM users WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def reset_password(email: str, new_password: str) -> Tuple[bool, str]:
    email = email.strip().lower()
    if not new_password or len(new_password) < 6:
        return False, "Password must be at least 6 characters long."
        
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?;", (email,))
        if not cur.fetchone():
            return False, "No account found with this email."

        pwd_hash = generate_password_hash(new_password)
        cur.execute("UPDATE users SET password_hash = ? WHERE email = ?;", (pwd_hash, email))
        conn.commit()
        return True, "Password has been successfully updated. You can now log in."
    finally:
        conn.close()

# User Statistics for Dashboard Bar
def get_user_stats(user_id: int) -> Dict[str, Any]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT full_name, email, role, last_login, created_at FROM users WHERE id = ?;", (user_id,))
        user_row = cur.fetchone()
        if not user_row:
            return {}

        cur.execute("SELECT COUNT(*) FROM user_datasets WHERE user_id = ?;", (user_id,))
        dataset_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM reports WHERE user_id = ?;", (user_id,))
        report_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM query_history WHERE user_id = ?;", (user_id,))
        history_count = cur.fetchone()[0]

        return {
            "full_name": user_row["full_name"],
            "email": user_row["email"],
            "role": user_row["role"],
            "last_login": user_row["last_login"] or "First session",
            "created_at": user_row["created_at"],
            "dataset_count": dataset_count,
            "report_count": report_count,
            "history_count": history_count
        }
    finally:
        conn.close()

# Multi-User Dataset Tracking & Isolation
def register_user_dataset(
    user_id: int,
    table_name: str,
    display_name: str,
    original_filename: str,
    file_path: str,
    file_size_kb: float,
    row_count: int,
    column_count: int
):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO user_datasets 
            (user_id, table_name, display_name, original_filename, file_path, file_size_kb, row_count, column_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, (user_id, table_name, display_name, original_filename, file_path, file_size_kb, row_count, column_count))
        conn.commit()
    finally:
        conn.close()

def get_user_datasets(user_id: int, is_admin: bool = False) -> List[Dict[str, Any]]:
    """Returns accessible datasets: default 'students' plus user's own datasets (or all if admin)."""
    conn = get_db()
    try:
        cur = conn.cursor()
        if is_admin:
            cur.execute("""
                SELECT ud.*, u.full_name as owner_name, u.email as owner_email
                FROM user_datasets ud
                LEFT JOIN users u ON ud.user_id = u.id
                ORDER BY ud.created_at DESC;
            """)
        else:
            cur.execute("""
                SELECT ud.*, 'You' as owner_name, '' as owner_email
                FROM user_datasets ud
                WHERE ud.user_id = ?
                ORDER BY ud.created_at DESC;
            """, (user_id,))
        
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()

def check_dataset_access(user_id: int, is_admin: bool, table_name: str) -> bool:
    """Default 'students' table is readable by everyone. Custom datasets require ownership or Admin."""
    if table_name == 'students':
        return True
    if is_admin:
        return True
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM user_datasets WHERE table_name = ? AND user_id = ?;", (table_name, user_id))
        return cur.fetchone() is not None
    finally:
        conn.close()

def delete_user_dataset_record(user_id: int, is_admin: bool, table_name: str) -> bool:
    if table_name == 'students':
        return False
    conn = get_db()
    try:
        cur = conn.cursor()
        if is_admin:
            cur.execute("DELETE FROM user_datasets WHERE table_name = ?;", (table_name,))
        else:
            cur.execute("DELETE FROM user_datasets WHERE table_name = ? AND user_id = ?;", (table_name, user_id))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()

def rename_user_dataset_record(user_id: int, is_admin: bool, old_table: str, new_table: str, new_display: str) -> bool:
    conn = get_db()
    try:
        cur = conn.cursor()
        if is_admin:
            cur.execute("""
                UPDATE user_datasets 
                SET table_name = ?, display_name = ? 
                WHERE table_name = ?;
            """, (new_table, new_display, old_table))
        else:
            cur.execute("""
                UPDATE user_datasets 
                SET table_name = ?, display_name = ? 
                WHERE table_name = ? AND user_id = ?;
            """, (new_table, new_display, old_table, user_id))
        updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        conn.close()

# Query History Operations
def log_query_history(user_id: int, question: str, sql: str, table_name: str, row_count: int, confidence: int = 95) -> int:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO query_history (user_id, user_question, generated_sql, table_name, row_count, confidence, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, (user_id, question, sql, table_name, row_count, confidence))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def get_user_query_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_question as query, generated_sql as sql, table_name as "table", 
                   row_count, confidence, timestamp
            FROM query_history 
            WHERE user_id = ? 
            ORDER BY id DESC 
            LIMIT ?;
        """, (user_id, limit))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def delete_query_history_item(user_id: int, history_id: int) -> bool:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM query_history WHERE id = ? AND user_id = ?;", (history_id, user_id))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()

def clear_user_query_history(user_id: int) -> bool:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM query_history WHERE user_id = ?;", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

# Report Generation Tracking
def log_report_generation(user_id: int, report_type: str, report_name: str, table_name: str, query_used: str = '') -> int:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO reports (user_id, report_type, report_name, table_name, query_used, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, (user_id, report_type, report_name, table_name, query_used))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

# Admin Management Operations
def get_admin_platform_stats() -> Dict[str, Any]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users;")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users WHERE is_active = 1;")
        active_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM user_datasets;")
        custom_datasets = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM query_history;")
        total_queries = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM reports;")
        total_reports = cur.fetchone()[0]

        # Recent 10 login logs
        cur.execute("""
            SELECT id, email, ip_address, status, timestamp 
            FROM login_logs 
            ORDER BY id DESC LIMIT 10;
        """)
        recent_logs = [dict(r) for r in cur.fetchall()]

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_datasets": custom_datasets + 1, # including 'students'
            "total_queries": total_queries,
            "total_reports": total_reports,
            "recent_logs": recent_logs
        }
    finally:
        conn.close()

def get_all_users() -> List[Dict[str, Any]]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.full_name, u.email, u.role, u.is_active, u.created_at, u.last_login,
                   (SELECT COUNT(*) FROM user_datasets WHERE user_id = u.id) as dataset_count,
                   (SELECT COUNT(*) FROM query_history WHERE user_id = u.id) as query_count
            FROM users u
            ORDER BY u.id ASC;
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def toggle_user_status(user_id: int) -> Tuple[bool, str, int]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT is_active, role, email FROM users WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        if not row:
            return False, "User not found.", 0
        if row["email"] == 'admin@nlde.com':
            return False, "Primary admin account cannot be disabled.", row["is_active"]

        new_status = 0 if row["is_active"] == 1 else 1
        cur.execute("UPDATE users SET is_active = ? WHERE id = ?;", (new_status, user_id))
        conn.commit()
        msg = "Account enabled." if new_status == 1 else "Account disabled."
        return True, msg, new_status
    finally:
        conn.close()

def toggle_user_role(user_id: int) -> Tuple[bool, str, str]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT role, email FROM users WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        if not row:
            return False, "User not found.", ""
        if row["email"] == 'admin@nlde.com':
            return False, "Primary admin role cannot be changed.", row["role"]

        new_role = 'User' if row["role"] == 'Admin' else 'Admin'
        cur.execute("UPDATE users SET role = ? WHERE id = ?;", (new_role, user_id))
        conn.commit()
        return True, f"Role changed to {new_role}.", new_role
    finally:
        conn.close()

def delete_user(user_id: int) -> Tuple[bool, str]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        if not row:
            return False, "User not found."
        if row["email"] == 'admin@nlde.com':
            return False, "Primary admin account cannot be deleted."

        cur.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        conn.commit()
        return True, "User account successfully removed."
    finally:
        conn.close()
