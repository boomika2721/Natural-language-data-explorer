import os
import sys
import datetime
import sqlite3
import pandas as pd
from flask import (
    Flask, render_template, request, jsonify, send_file, 
    Response, session, redirect, url_for, flash
)
from config import (
    DB_FILE, DATASET_FILE, SECRET_KEY, DEBUG, HOST, PORT,
    MAX_HISTORY_ITEMS, MAX_QUERY_RESULTS
)
import auth_db
from auth import login_required, admin_required
from excel_to_db import init_database
from query_validator import validate_sql_query
from nlp_engine import NLPEngine
from analytics import (
    get_dashboard_analytics, get_database_schema,
    check_data_quality, generate_ai_insights, get_db_connection
)
from report_generator import export_to_csv, export_to_excel, generate_pdf_report
from dataset_manager import (
    save_and_import_dataset, get_all_datasets, profile_dataset,
    rename_dataset, delete_dataset, compare_two_datasets
)
from predictive_engine import analyze_dataset_predictions

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize NLP Engine
nlp_engine = NLPEngine()

# Active dataset pointer (defaults to 'students')
active_dataset = "students"

# In-memory last query cache for exports
last_executed_query = {
    "user_query": "Show all students",
    "corrected_query": "Show all students",
    "sql_query": "SELECT * FROM students;",
    "explanation": "This query retrieves all student records from the database.",
    "confidence_score": 95,
    "language": "English",
    "table_name": "students",
    "insights": [],
    "df": pd.DataFrame()
}

def ensure_db_ready():
    """Ensures database exists, populated with student data, and auth tables ready."""
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        print("[INIT] Database file not found. Initializing database...")
        init_database(force_recreate=True)
    else:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='students';")
            exists = cur.fetchone()[0]
            if not exists:
                init_database(force_recreate=True)
        finally:
            conn.close()

    # Initialize Auth DB tables and default accounts
    auth_db.init_auth_db()

# Auto-ensure database is ready at startup
ensure_db_ready()

@app.before_request
def check_session_timeout():
    """Enforces session timeout and updates last activity timestamp."""
    # Exclude static assets
    if request.path.startswith('/static/'):
        return

    user_id = session.get('user_id')
    if user_id:
        last_act_str = session.get('last_activity')
        is_permanent = session.get('_permanent', False)
        
        # Inactivity limit: 7 days if remember_me, 30 minutes otherwise
        timeout_seconds = 7 * 86400 if is_permanent else 30 * 60
        
        if last_act_str:
            try:
                last_act = datetime.datetime.fromisoformat(last_act_str)
                idle_seconds = (datetime.datetime.now() - last_act).total_seconds()
                if idle_seconds > timeout_seconds:
                    session.clear()
                    if request.is_json or request.path.startswith('/api/'):
                        return jsonify({"success": False, "error": "Session timed out due to inactivity.", "redirect": "/login"}), 401
                    flash("Your session has expired due to inactivity. Please log in again.", "warning")
                    return redirect(url_for('login_view'))
            except Exception:
                pass
                
        session['last_activity'] = datetime.datetime.now().isoformat()

def derive_chart_data(df: pd.DataFrame, suggested_type: str = "bar") -> dict:
    """
    Analyzes DataFrame columns and shape to construct appropriate Chart.js datasets.
    Works universally across students and any dynamically uploaded table.
    """
    if df.empty:
        return {"type": "bar", "labels": [], "data": [], "title": "No Data Available"}

    cols = df.columns.tolist()
    
    # 1. Single aggregate value
    if len(df) == 1 and len(cols) == 1:
        val = df.iloc[0, 0]
        num_val = float(val) if isinstance(val, (int, float)) and pd.notnull(val) else 1
        return {
            "type": "bar",
            "labels": [cols[0].replace('_', ' ').title()],
            "data": [num_val],
            "title": cols[0].replace('_', ' ').title()
        }

    # 2. Group Count queries (e.g. department, student_count or col, count)
    count_cols = [c for c in cols if any(k in c.lower() for k in ("student_count", "count", "total_records", "total_students", "frequency"))]
    if count_cols and len(cols) >= 2:
        cnt_col = count_cols[0]
        label_col = [c for c in cols if c != cnt_col][0]
        sample_df = df.head(15)
        labels = [str(x) for x in sample_df[label_col].tolist()]
        values = [float(x) if pd.notnull(x) else 0 for x in sample_df[cnt_col].tolist()]
        chart_type = "pie" if len(labels) <= 6 else "bar"
        return {
            "type": chart_type,
            "labels": labels,
            "data": values,
            "title": f"Distribution by {label_col.replace('_', ' ').title()}"
        }

    # 3. Two columns: 1 categorical, 1 numeric
    cat_cols = df.select_dtypes(exclude=['number']).columns.tolist()
    num_cols = df.select_dtypes(include=['number']).columns.tolist()

    if cat_cols and num_cols:
        sample_df = df.head(15)
        return {
            "type": suggested_type or "bar",
            "labels": sample_df[cat_cols[0]].astype(str).tolist(),
            "data": sample_df[num_cols[0]].tolist(),
            "title": f"{num_cols[0].replace('_', ' ').title()} by {cat_cols[0].replace('_', ' ').title()}"
        }

    # 4. Filtered or Top student list with CGPA and Name
    if "cgpa" in cols and "name" in cols:
        sample_df = df.head(15)
        return {
            "type": "bar",
            "labels": sample_df["name"].tolist(),
            "data": sample_df["cgpa"].tolist(),
            "title": "CGPA Comparison (Top Results)"
        }

    # 5. Multiple numeric columns: first two
    if len(num_cols) >= 2:
        sample_df = df.head(20)
        return {
            "type": "line" if suggested_type == "line" else "bar",
            "labels": sample_df[num_cols[0]].astype(str).tolist(),
            "data": sample_df[num_cols[1]].tolist(),
            "title": f"{num_cols[1].replace('_', ' ').title()} vs {num_cols[0].replace('_', ' ').title()}"
        }

    # Fallback to row index vs first column
    first_col = cols[0]
    sample_df = df.head(15)
    return {
        "type": "bar",
        "labels": [str(x) for x in sample_df[first_col].tolist()],
        "data": [1] * len(sample_df),
        "title": "Query Results"
    }

# ==========================================
# PUBLIC LANDING & AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def home():
    """If authenticated, redirects to dashboard; otherwise renders landing page."""
    if session.get('user_id'):
        return redirect(url_for('index_dashboard'))
    return render_template('landing.html')

@app.route('/welcome')
def welcome_page():
    """Explicit landing page route."""
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def index_dashboard():
    """Renders the protected analytics dashboard page."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login_view():
    """Handles user sign in with session management and validation."""
    if request.method == 'GET' and session.get('user_id'):
        return redirect(url_for('index_dashboard'))

    next_url = request.args.get('next') or request.form.get('next') or ''

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        remember_me = request.form.get('remember_me') == 'true'
        client_ip = request.remote_addr or '127.0.0.1'

        success, user, msg = auth_db.verify_user(email, password, client_ip)
        if success and user:
            session.clear()
            session['user_id'] = user['id']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            session['role'] = user['role']
            session['last_login'] = user['last_login']
            session['last_activity'] = datetime.datetime.now().isoformat()
            
            if remember_me:
                session.permanent = True
                app.permanent_session_lifetime = datetime.timedelta(days=7)
            else:
                session.permanent = False
                app.permanent_session_lifetime = datetime.timedelta(minutes=30)

            flash(f"Welcome back, {user['full_name']}!", "success")
            
            if next_url and not next_url.startswith('/login') and not next_url.startswith('/register'):
                return redirect(next_url)
            return redirect(url_for('index_dashboard'))
        else:
            flash(msg, "danger")
            return render_template('login.html', email=email, next_url=next_url)

    return render_template('login.html', next_url=next_url)

@app.route('/register', methods=['GET', 'POST'])
def register_view():
    """Handles user and administrator account registration."""
    if session.get('user_id'):
        return redirect(url_for('index_dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'User').strip()

        if password != confirm_password:
            flash("Passwords do not match. Please verify and try again.", "danger")
            return render_template('register.html', full_name=full_name, email=email)

        success, msg, user = auth_db.create_user(full_name, email, password, role)
        if success:
            flash("Account registered successfully! You can now log in.", "success")
            return redirect(url_for('login_view'))
        else:
            flash(msg, "danger")
            return render_template('register.html', full_name=full_name, email=email)

    return render_template('register.html')

@app.route('/forgot-password', methods=['POST'])
def forgot_password_view():
    """Password reset handler."""
    email = request.form.get('reset_email', '').strip()
    new_password = request.form.get('new_password', '')
    
    success, msg = auth_db.reset_password(email, new_password)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('login_view'))

@app.route('/logout')
def logout_view():
    """Terminates user session and redirects to sign-in page."""
    session.clear()
    flash("You have been successfully signed out.", "info")
    return redirect(url_for('login_view'))

@app.route('/api/user/stats', methods=['GET'])
@login_required
def user_stats_endpoint():
    """Returns dynamic statistics for current logged in user."""
    user_id = session.get('user_id')
    stats = auth_db.get_user_stats(user_id)
    return jsonify({"success": True, "stats": stats})

# ==========================================
# PROTECTED ANALYTICS & QUERY ENDPOINTS
# ==========================================

@app.route('/analytics', methods=['GET'])
@login_required
def analytics_endpoint():
    """
    Returns dashboard analytics.
    If 'table' query param is provided and != 'students', computes universal analytics for that table.
    Enforces user dataset access permissions.
    """
    global active_dataset
    tbl = request.args.get('table', active_dataset).strip()
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')

    if not auth_db.check_dataset_access(user_id, is_admin, tbl):
        return jsonify({"success": False, "error": "Access denied to this dataset."}), 403
    
    try:
        if tbl == 'students' or not tbl:
            data = get_dashboard_analytics()
            data["active_table"] = "students"
            data["is_students"] = True
            return jsonify({"success": True, "data": data})
            
        # Universal analytics for dynamic uploaded tables
        conn = get_db_connection()
        try:
            df = pd.read_sql_query(f"SELECT * FROM `{tbl}`;", conn)
        finally:
            conn.close()

        total_rows = len(df)
        total_cols = len(df.columns)
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(exclude=['number']).columns.tolist()
        null_count = int(df.isnull().sum().sum())
        dup_count = int(df.duplicated().sum())

        # Build dynamic chart distribution
        distribution = {"labels": [], "data": []}
        if cat_cols:
            top_cat = cat_cols[0]
            val_counts = df[top_cat].value_counts().head(8)
            distribution = {
                "labels": [str(x) for x in val_counts.index],
                "data": [int(x) for x in val_counts.values],
                "dimension": top_cat
            }
        elif num_cols:
            top_num = num_cols[0]
            distribution = {
                "labels": [f"Row {i+1}" for i in range(min(10, total_rows))],
                "data": df[top_num].head(10).tolist(),
                "dimension": top_num
            }

        universal_data = {
            "active_table": tbl,
            "is_students": False,
            "total_rows": total_rows,
            "total_columns": total_cols,
            "numeric_count": len(num_cols),
            "categorical_count": len(cat_cols),
            "total_nulls": null_count,
            "duplicate_count": dup_count,
            "distribution": distribution,
            "top_records": df.head(5).to_dict(orient='records')
        }
        return jsonify({"success": True, "data": universal_data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/history', methods=['GET'])
@login_required
def history_endpoint():
    """Returns the user's isolated query history from SQLite table."""
    user_id = session.get('user_id')
    history = auth_db.get_user_query_history(user_id, limit=20)
    return jsonify({"success": True, "history": history})

@app.route('/history/<int:history_id>', methods=['DELETE'])
@login_required
def delete_history_item_endpoint(history_id):
    """Deletes a specific query history item belonging to user."""
    user_id = session.get('user_id')
    deleted = auth_db.delete_query_history_item(user_id, history_id)
    return jsonify({"success": deleted})

@app.route('/history', methods=['DELETE'])
@login_required
def clear_history_endpoint():
    """Clears all query history for current user."""
    user_id = session.get('user_id')
    auth_db.clear_user_query_history(user_id)
    return jsonify({"success": True, "message": "History cleared successfully."})

@app.route('/schema', methods=['GET'])
@login_required
def schema_endpoint():
    """Returns database schema, columns, types, and counts."""
    try:
        schema = get_database_schema()
        return jsonify({"success": True, "schema": schema})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/quality', methods=['GET'])
@login_required
def quality_endpoint():
    """Returns data quality health metrics and summary."""
    try:
        quality_data = check_data_quality()
        return jsonify({"success": True, "quality": quality_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/query', methods=['POST'])
@login_required
def query_endpoint():
    """
    Main query processing endpoint supporting both default 'students'
    and user-isolated datasets.
    """
    global last_executed_query, active_dataset
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')
    
    req_json = request.get_json(silent=True)
    if not req_json or "query" not in req_json:
        return jsonify({"success": False, "error": "Invalid request. Please provide a 'query' field."}), 400

    user_query = req_json.get("query", "").strip()
    target_table = req_json.get("table", active_dataset).strip() or "students"

    if not user_query:
        return jsonify({"success": False, "error": "Query cannot be empty. Please ask a question."}), 400

    # Verify user dataset authorization
    if not auth_db.check_dataset_access(user_id, is_admin, target_table):
        return jsonify({"success": False, "error": f"Access denied: You do not have permission to query dataset '{target_table}'."}), 403

    try:
        # Step 1: NLP to SQL Conversion with dynamic table context
        nlp_res = nlp_engine.process_query(user_query, table_name=target_table)
        sql_query = nlp_res["sql_query"]
        
        # Step 2: Read-Only Security Validation
        is_safe, safety_msg = validate_sql_query(sql_query)
        if not is_safe:
            return jsonify({
                "success": False,
                "unsafe": True,
                "error": safety_msg,
                "user_query": user_query,
                "sql_query": sql_query,
                "explanation": "Security policy violation: This query attempts destructive or unauthorized database actions."
            }), 403

        # Step 3: Execute SQL Query safely
        conn = get_db_connection()
        try:
            df = pd.read_sql_query(sql_query, conn)
        finally:
            conn.close()

        # Step 4: Generate Dynamic AI Insights
        insights = generate_ai_insights(df, user_query)

        # Step 5: Generate Chart Suggestions
        chart_data = derive_chart_data(df, nlp_res.get("chart_type", "bar"))

        # Step 6: Prepare JSON response
        records = df.to_dict(orient='records')
        columns = list(df.columns)
        
        response_payload = {
            "success": True,
            "user_query": nlp_res["user_query"],
            "corrected_query": nlp_res["corrected_query"],
            "corrections": nlp_res["corrections"],
            "language": nlp_res["language"],
            "table_name": target_table,
            "sql_query": sql_query,
            "explanation": nlp_res["explanation"],
            "confidence_score": nlp_res["confidence_score"],
            "row_count": len(records),
            "columns": columns,
            "data": records[:MAX_QUERY_RESULTS],
            "insights": insights,
            "chart": chart_data
        }

        # Step 7: Update Last Executed Query Cache for export
        last_executed_query = {
            "user_query": nlp_res["user_query"],
            "corrected_query": nlp_res["corrected_query"],
            "sql_query": sql_query,
            "explanation": nlp_res["explanation"],
            "confidence_score": nlp_res["confidence_score"],
            "language": nlp_res["language"],
            "table_name": target_table,
            "insights": insights,
            "df": df
        }

        # Step 8: Log to User-Isolated Query History Table
        auth_db.log_query_history(
            user_id=user_id,
            question=user_query,
            sql=sql_query,
            table_name=target_table,
            row_count=len(records),
            confidence=nlp_res["confidence_score"]
        )

        return jsonify(response_payload)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error executing query: {str(e)}"
        }), 500

# ==========================================
# DYNAMIC DATASET MANAGEMENT ENDPOINTS
# ==========================================

@app.route('/datasets', methods=['GET'])
@login_required
def list_datasets_endpoint():
    """Returns accessible datasets for the logged in user (with multi-user isolation)."""
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')
    
    try:
        datasets = get_all_datasets(user_id=user_id, is_admin=is_admin)
        for d in datasets:
            d["is_active"] = (d["table_name"] == active_dataset)
        return jsonify({
            "success": True,
            "active_dataset": active_dataset,
            "datasets": datasets
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/datasets/select', methods=['POST'])
@login_required
def select_dataset_endpoint():
    """Switches the active dataset for subsequent queries and dashboards."""
    global active_dataset
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')

    req_json = request.get_json(silent=True) or {}
    target_table = req_json.get("table", "").strip()
    
    if not target_table:
        return jsonify({"success": False, "error": "Table name required."}), 400

    if not auth_db.check_dataset_access(user_id, is_admin, target_table):
        return jsonify({"success": False, "error": "Access denied to requested dataset."}), 403

    active_dataset = target_table
    return jsonify({
        "success": True,
        "active_dataset": active_dataset,
        "message": f"Active dataset switched to '{active_dataset}'."
    })

@app.route('/datasets/upload', methods=['POST'])
@login_required
def upload_dataset_endpoint():
    """
    Accepts CSV or Excel spreadsheet, creates user-isolated SQLite table,
    stores file in datasets/, and returns profiling & AI summary.
    """
    global active_dataset
    user_id = session.get('user_id')
    
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    uploaded_file = request.files['file']
    if not uploaded_file.filename:
        return jsonify({"success": False, "error": "Empty filename."}), 400

    custom_name = request.form.get('table_name', '').strip()

    try:
        result = save_and_import_dataset(uploaded_file, custom_name, user_id=user_id)
        active_dataset = result["table_name"]
        result["is_active"] = True
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/datasets/<table_name>/preview', methods=['GET'])
@login_required
def dataset_preview_endpoint(table_name):
    """Returns the top 50 rows of a dataset for preview with isolation check."""
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')

    if not auth_db.check_dataset_access(user_id, is_admin, table_name):
        return jsonify({"success": False, "error": "Access denied to preview this dataset."}), 403

    try:
        conn = get_db_connection()
        try:
            df = pd.read_sql_query(f"SELECT * FROM `{table_name}` LIMIT 50;", conn)
        finally:
            conn.close()

        return jsonify({
            "success": True,
            "table_name": table_name,
            "columns": list(df.columns),
            "rows": df.to_dict(orient='records'),
            "total_preview": len(df)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/datasets/<table_name>/profile', methods=['GET'])
@login_required
def dataset_profile_endpoint(table_name):
    """Returns comprehensive data profiling for a dataset with access check."""
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')

    if not auth_db.check_dataset_access(user_id, is_admin, table_name):
        return jsonify({"success": False, "error": "Access denied."}), 403

    try:
        profile = profile_dataset(table_name)
        return jsonify({"success": True, "profile": profile})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/datasets/<table_name>/predictive', methods=['GET'])
@login_required
def dataset_predictive_endpoint(table_name):
    """Runs predictive analytics, correlations, and regression with access check."""
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')

    if not auth_db.check_dataset_access(user_id, is_admin, table_name):
        return jsonify({"success": False, "error": "Access denied."}), 403

    try:
        conn = get_db_connection()
        try:
            df = pd.read_sql_query(f"SELECT * FROM `{table_name}`;", conn)
        finally:
            conn.close()

        predictive_data = analyze_dataset_predictions(df)
        return jsonify({"success": True, "predictive": predictive_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/datasets/<table_name>/rename', methods=['POST'])
@login_required
def dataset_rename_endpoint(table_name):
    """Renames an existing dataset with ownership validation."""
    global active_dataset
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')

    req_json = request.get_json(silent=True) or {}
    new_name = req_json.get("new_name", "").strip()
    
    if not new_name:
        return jsonify({"success": False, "error": "New name cannot be empty."}), 400

    try:
        res = rename_dataset(table_name, new_name, user_id=user_id, is_admin=is_admin)
        if active_dataset == table_name:
            active_dataset = res["new_table"]
        return jsonify(res)
    except PermissionError as pe:
        return jsonify({"success": False, "error": str(pe)}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/datasets/<table_name>', methods=['DELETE'])
@login_required
def dataset_delete_endpoint(table_name):
    """Deletes an uploaded dataset with ownership checks."""
    global active_dataset
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')
    
    if table_name == 'students':
        init_database(force_recreate=True)
        return jsonify({
            "success": True,
            "message": "Default 'students' dataset was reset to original state."
        })

    try:
        res = delete_dataset(table_name, user_id=user_id, is_admin=is_admin)
        if active_dataset == table_name:
            active_dataset = "students"
        return jsonify(res)
    except PermissionError as pe:
        return jsonify({"success": False, "error": str(pe)}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/datasets/compare', methods=['POST'])
@login_required
def dataset_compare_endpoint():
    """Compares two datasets side-by-side with permission checks."""
    user_id = session.get('user_id')
    is_admin = (session.get('role') == 'Admin')

    req_json = request.get_json(silent=True) or {}
    t1 = req_json.get("table1", "").strip()
    t2 = req_json.get("table2", "").strip()

    if not t1 or not t2:
        return jsonify({"success": False, "error": "Both 'table1' and 'table2' are required."}), 400

    if not auth_db.check_dataset_access(user_id, is_admin, t1) or not auth_db.check_dataset_access(user_id, is_admin, t2):
        return jsonify({"success": False, "error": "Access denied to one or both comparison datasets."}), 403

    try:
        comparison = compare_two_datasets(t1, t2)
        return jsonify({"success": True, "comparison": comparison})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==========================================
# EXPORT ENDPOINTS (TRACKED PER USER)
# ==========================================

@app.route('/export/csv', methods=['GET'])
@login_required
def export_csv():
    """Exports current query result as CSV and tracks in reports table."""
    user_id = session.get('user_id')
    df = last_executed_query.get("df", pd.DataFrame())
    if df.empty:
        conn = get_db_connection()
        try:
            df = pd.read_sql_query(f"SELECT * FROM `{active_dataset}`;", conn)
        finally:
            conn.close()

    csv_bytes = export_to_csv(df)
    filename = f"NLDE_{active_dataset}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Log report creation
    auth_db.log_report_generation(
        user_id=user_id,
        report_type='CSV',
        report_name=filename,
        table_name=active_dataset,
        query_used=last_executed_query.get("user_query", "")
    )

    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/export/excel', methods=['GET'])
@login_required
def export_excel():
    """Exports current query result as styled Excel file and tracks in reports."""
    user_id = session.get('user_id')
    df = last_executed_query.get("df", pd.DataFrame())
    if df.empty:
        conn = get_db_connection()
        try:
            df = pd.read_sql_query(f"SELECT * FROM `{active_dataset}`;", conn)
        finally:
            conn.close()

    excel_bytes = export_to_excel(df, report_title=f"{active_dataset.title()} Query Results")
    filename = f"NLDE_{active_dataset}_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # Log report creation
    auth_db.log_report_generation(
        user_id=user_id,
        report_type='Excel',
        report_name=filename,
        table_name=active_dataset,
        query_used=last_executed_query.get("user_query", "")
    )

    return Response(
        excel_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/export/pdf', methods=['GET'])
@login_required
def export_pdf():
    """Exports current query report as a PDF and tracks in reports."""
    user_id = session.get('user_id')
    df = last_executed_query.get("df", pd.DataFrame())
    if df.empty:
        conn = get_db_connection()
        try:
            df = pd.read_sql_query(f"SELECT * FROM `{active_dataset}`;", conn)
        finally:
            conn.close()

    pdf_bytes = generate_pdf_report(
        user_query=last_executed_query.get("user_query", f"{active_dataset.title()} Records"),
        sql_query=last_executed_query.get("sql_query", f"SELECT * FROM `{active_dataset}`;"),
        explanation=last_executed_query.get("explanation", f"{active_dataset.title()} records analysis report."),
        confidence_score=last_executed_query.get("confidence_score", 95),
        language=last_executed_query.get("language", "English"),
        insights=last_executed_query.get("insights", ["Analysis report of query results."]),
        df=df
    )
    filename = f"NLDE_{active_dataset}_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    # Log report creation
    auth_db.log_report_generation(
        user_id=user_id,
        report_type='PDF',
        report_name=filename,
        table_name=active_dataset,
        query_used=last_executed_query.get("user_query", "")
    )

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# ==========================================
# ADMIN PORTAL ENDPOINTS
# ==========================================

@app.route('/admin')
@admin_required
def admin_portal():
    """Renders the comprehensive administration portal."""
    return render_template('admin.html')

@app.route('/api/admin/overview', methods=['GET'])
@admin_required
def admin_overview_endpoint():
    """Returns platform stats, all users, and all datasets for admin view."""
    stats = auth_db.get_admin_platform_stats()
    users = auth_db.get_all_users()
    datasets = get_all_datasets(user_id=session.get('user_id'), is_admin=True)
    return jsonify({
        "success": True,
        "stats": stats,
        "users": users,
        "datasets": datasets
    })

@app.route('/api/admin/users/<int:target_user_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(target_user_id):
    """Enables or disables a user account."""
    success, msg, new_status = auth_db.toggle_user_status(target_user_id)
    return jsonify({"success": success, "message": msg, "new_status": new_status})

@app.route('/api/admin/users/<int:target_user_id>/toggle-role', methods=['POST'])
@admin_required
def admin_toggle_user_role(target_user_id):
    """Toggles user role between User and Admin."""
    success, msg, new_role = auth_db.toggle_user_role(target_user_id)
    return jsonify({"success": success, "message": msg, "new_role": new_role})

@app.route('/api/admin/users/<int:target_user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(target_user_id):
    """Removes a user account."""
    success, msg = auth_db.delete_user(target_user_id)
    return jsonify({"success": success, "message": msg})

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    if session.get('user_id'):
        return render_template('index.html'), 200
    return render_template('landing.html'), 200

@app.errorhandler(500)
def server_error(e):
    err_str = str(getattr(e, 'original_exception', e))
    return jsonify({
        "success": False, 
        "error": f"Internal server error: {err_str}"
    }), 500

if __name__ == '__main__':
    print("=" * 65)
    print(" Natural-Language Data Explorer (NLDE) v2.5")
    print(f" Multi-User Analytics Platform & Authentication Module")
    print(f" Server starting on http://{HOST}:{PORT}")
    print("=" * 65)
    app.run(host=HOST, port=PORT, debug=DEBUG)
