import datetime
from functools import wraps
from flask import session, request, redirect, url_for, flash, jsonify
import auth_db

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            # Check if this is an API/JSON or AJAX request
            if (
                request.path.startswith('/api/') or 
                request.is_json or 
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                'application/json' in request.headers.get('Accept', '')
            ):
                return jsonify({
                    "success": False, 
                    "error": "Authentication required. Please log in.",
                    "redirect": "/login"
                }), 401

            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login_view', next=request.url))

        # Check if user account is still active in database
        user = auth_db.get_user_by_id(user_id)
        if not user or not user.get('is_active', 1):
            session.clear()
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    "success": False,
                    "error": "Your account has been deactivated. Please contact an administrator.",
                    "redirect": "/login"
                }), 403
            flash("Your account has been deactivated. Please contact an administrator.", "danger")
            return redirect(url_for('login_view'))

        # Track session activity
        session['last_activity'] = datetime.datetime.now().isoformat()
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({"success": False, "error": "Authentication required.", "redirect": "/login"}), 401
            flash("Please log in as an administrator.", "warning")
            return redirect(url_for('login_view', next=request.url))

        role = session.get('role', 'User')
        if role != 'Admin':
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({"success": False, "error": "Access denied. Administrator privileges required."}), 403
            flash("Access denied. Administrator privileges required.", "danger")
            return redirect(url_for('index_dashboard'))

        return f(*args, **kwargs)
    return decorated_function
