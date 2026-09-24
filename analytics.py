import sqlite3
import pandas as pd
from typing import Dict, Any, List
from config import DB_FILE

def get_db_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_dashboard_analytics() -> Dict[str, Any]:
    """
    Computes summary metrics for the dashboard cards:
    - Total Students
    - Total Departments
    - Average CGPA
    - Highest CGPA
    - Lowest CGPA
    - Total Cities
    And data series for default charts.
    """
    conn = get_db_connection()
    try:
        # High level summary
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_students,
                COUNT(DISTINCT department) as total_departments,
                ROUND(AVG(cgpa), 2) as avg_cgpa,
                MAX(cgpa) as max_cgpa,
                MIN(cgpa) as min_cgpa,
                COUNT(DISTINCT city) as total_cities
            FROM students;
        """)
        summary_row = cursor.fetchone()
        
        # Department counts
        cursor.execute("""
            SELECT department, COUNT(*) as count 
            FROM students 
            GROUP BY department 
            ORDER BY count DESC;
        """)
        dept_rows = cursor.fetchall()
        dept_labels = [r["department"] for r in dept_rows]
        dept_counts = [r["count"] for r in dept_rows]
        
        # Year distribution
        cursor.execute("""
            SELECT year, COUNT(*) as count 
            FROM students 
            GROUP BY year 
            ORDER BY year ASC;
        """)
        year_rows = cursor.fetchall()
        year_labels = [f"Year {r['year']}" for r in year_rows]
        year_counts = [r["count"] for r in year_rows]
        
        # City counts (Top 8)
        cursor.execute("""
            SELECT city, COUNT(*) as count 
            FROM students 
            GROUP BY city 
            ORDER BY count DESC 
            LIMIT 8;
        """)
        city_rows = cursor.fetchall()
        city_labels = [r["city"] for r in city_rows]
        city_counts = [r["count"] for r in city_rows]
        
        # CGPA ranges distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN cgpa >= 9.0 THEN '9.0 - 10.0'
                    WHEN cgpa >= 8.0 THEN '8.0 - 8.9'
                    WHEN cgpa >= 7.0 THEN '7.0 - 7.9'
                    ELSE '< 7.0'
                END as cgpa_band,
                COUNT(*) as count
            FROM students
            GROUP BY cgpa_band
            ORDER BY min(cgpa) DESC;
        """)
        cgpa_rows = cursor.fetchall()
        cgpa_bands = [r["cgpa_band"] for r in cgpa_rows]
        cgpa_counts = [r["count"] for r in cgpa_rows]

        # Top students for highlight
        cursor.execute("""
            SELECT name, department, cgpa, city 
            FROM students 
            ORDER BY cgpa DESC 
            LIMIT 5;
        """)
        top_students = [dict(r) for r in cursor.fetchall()]

        return {
            "total_students": summary_row["total_students"] or 0,
            "total_departments": summary_row["total_departments"] or 0,
            "avg_cgpa": summary_row["avg_cgpa"] or 0.0,
            "max_cgpa": summary_row["max_cgpa"] or 0.0,
            "min_cgpa": summary_row["min_cgpa"] or 0.0,
            "total_cities": summary_row["total_cities"] or 0,
            "dept_distribution": {"labels": dept_labels, "data": dept_counts},
            "year_distribution": {"labels": year_labels, "data": year_counts},
            "city_distribution": {"labels": city_labels, "data": city_counts},
            "cgpa_distribution": {"labels": cgpa_bands, "data": cgpa_counts},
            "top_students": top_students
        }
    finally:
        conn.close()

def get_database_schema() -> Dict[str, Any]:
    """
    Inspects SQLite metadata to return table details, columns, data types,
    and record counts.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r["name"] for r in cursor.fetchall()]
        
        schema_details = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            row_count = cursor.fetchone()[0]
            
            col_list = []
            for col in columns:
                col_list.append({
                    "cid": col["cid"],
                    "name": col["name"],
                    "type": col["type"],
                    "notnull": bool(col["notnull"]),
                    "dflt_value": col["dflt_value"],
                    "pk": bool(col["pk"])
                })
                
            schema_details.append({
                "table_name": table,
                "row_count": row_count,
                "column_count": len(col_list),
                "columns": col_list
            })
            
        return {"tables": schema_details}
    finally:
        conn.close()

def check_data_quality() -> Dict[str, Any]:
    """
    Performs data quality analysis on the students dataset:
    - Missing/Null values per column
    - Duplicate records
    - Invalid entries (CGPA out of range, negative year, email format)
    - Quality health score percentage
    """
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM students;", conn)
    finally:
        conn.close()
        
    total_records = len(df)
    if total_records == 0:
        return {
            "health_score": 0,
            "total_records": 0,
            "missing_values": {},
            "duplicate_records": 0,
            "invalid_cgpa": 0,
            "invalid_year": 0,
            "invalid_emails": 0,
            "summary_status": "Empty Database"
        }
        
    # Check null / missing values
    null_counts = df.isnull().sum().to_dict()
    total_nulls = sum(null_counts.values())
    
    # Check duplicate records (excluding id)
    cols_without_id = [c for c in df.columns if c != 'id']
    duplicate_records = int(df.duplicated(subset=cols_without_id).sum())
    
    # Check invalid CGPA (must be between 0.0 and 10.0)
    invalid_cgpa = int(((df['cgpa'] < 0.0) | (df['cgpa'] > 10.0)).sum())
    
    # Check invalid academic year (must be 1, 2, 3, or 4)
    invalid_year = int((~df['year'].isin([1, 2, 3, 4])).sum())
    
    # Check invalid email formatting
    email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    invalid_emails = int((~df['email'].astype(str).str.match(email_pattern)).sum())
    
    # Calculate health score: deduction per defect
    total_checks = total_records * (len(df.columns) + 3)
    defects = total_nulls + (duplicate_records * len(cols_without_id)) + invalid_cgpa + invalid_year + invalid_emails
    health_score = round(max(0.0, min(100.0, ((total_checks - defects) / total_checks) * 100)), 2)
    
    return {
        "health_score": health_score,
        "total_records": total_records,
        "missing_values": null_counts,
        "total_nulls": total_nulls,
        "duplicate_records": duplicate_records,
        "invalid_cgpa": invalid_cgpa,
        "invalid_year": invalid_year,
        "invalid_emails": invalid_emails,
        "summary_status": "Excellent" if health_score >= 95 else ("Good" if health_score >= 85 else "Needs Attention")
    }

def generate_ai_insights(df: pd.DataFrame = None, query_context: str = "") -> List[str]:
    """
    AI Insights Engine:
    Analyzes student data (or query results DataFrame) and synthesizes
    intuitive, data-driven narrative insights.
    """
    insights = []
    
    # If no custom DataFrame provided, load entire dataset
    if df is None:
        conn = get_db_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM students;", conn)
        finally:
            conn.close()
            
    if df.empty:
        return ["No student records available to derive analytical insights."]
        
    cols = df.columns.tolist()
    
    # Scalar / Single Value Insights
    if len(df) == 1 and len(cols) == 1:
        val = df.iloc[0, 0]
        col_name = cols[0].replace('_', ' ').title()
        return [f"The calculated {col_name} is {val}."]
        
    # Department group count insights
    if "department" in cols and ("student_count" in cols or "count" in cols):
        cnt_col = "student_count" if "student_count" in cols else "count"
        max_dept = df.loc[df[cnt_col].idxmax()]
        min_dept = df.loc[df[cnt_col].idxmin()]
        total = df[cnt_col].sum()
        pct = round((max_dept[cnt_col] / total) * 100, 1) if total > 0 else 0
        insights.append(f"{max_dept['department']} Department has the highest enrollment with {int(max_dept[cnt_col])} students ({pct}% of cohort).")
        insights.append(f"{min_dept['department']} Department has the lowest enrollment with {int(min_dept[cnt_col])} students.")
        return insights

    # City group count insights
    if "city" in cols and ("student_count" in cols or "count" in cols):
        cnt_col = "student_count" if "student_count" in cols else "count"
        top_city = df.loc[df[cnt_col].idxmax()]
        insights.append(f"{top_city['city']} is the top contributing city with {int(top_city[cnt_col])} enrolled students.")
        insights.append(f"Student body spans across {len(df)} different regional cities.")
        return insights
        
    # Year group count insights
    if "year" in cols and ("student_count" in cols or "count" in cols):
        cnt_col = "student_count" if "student_count" in cols else "count"
        top_yr = df.loc[df[cnt_col].idxmax()]
        insights.append(f"Most students belong to Year {int(top_yr['year'])}, comprising {int(top_yr[cnt_col])} students.")
        return insights

    # Full table / Filtered list insights
    if "cgpa" in cols:
        avg_cgpa = round(df["cgpa"].mean(), 2)
        max_cgpa = round(df["cgpa"].max(), 2)
        min_cgpa = round(df["cgpa"].min(), 2)
        
        # Max CGPA student
        if "name" in cols and "department" in cols:
            top_scorer = df.loc[df["cgpa"].idxmax()]
            insights.append(f"Highest CGPA is {max_cgpa}, achieved by {top_scorer['name']} from {top_scorer['department']} Department.")
        else:
            insights.append(f"Highest CGPA recorded is {max_cgpa}, while the lowest is {min_cgpa}.")
            
        insights.append(f"Average CGPA across the cohort stands at {avg_cgpa}.")
        
        # High performers proportion
        above_9 = (df["cgpa"] >= 9.0).sum()
        if len(df) > 0:
            above_9_pct = round((above_9 / len(df)) * 100, 1)
            insights.append(f"{above_9} students ({above_9_pct}%) have attained an elite CGPA of 9.0 or higher.")
            
    if "department" in cols and len(df) > 5:
        top_dept = df["department"].value_counts().index[0]
        top_dept_count = df["department"].value_counts().iloc[0]
        insights.append(f"{top_dept} Department represents the largest student contingent ({top_dept_count} students).")

    if "year" in cols and len(df) > 5:
        top_year = df["year"].value_counts().index[0]
        insights.append(f"The largest cohort is currently enrolled in Year {top_year}.")

    if "city" in cols and len(df) > 5:
        top_city = df["city"].value_counts().index[0]
        insights.append(f"The geographic center with highest student representation is {top_city}.")
        
    if "gender" in cols and len(df) > 5:
        gender_counts = df["gender"].value_counts()
        if "Female" in gender_counts and "Male" in gender_counts:
            fem_pct = round((gender_counts["Female"] / len(df)) * 100, 1)
            male_pct = round((gender_counts["Male"] / len(df)) * 100, 1)
            insights.append(f"Gender distribution is balanced with {male_pct}% Male and {fem_pct}% Female students.")

    # Ensure we return at least 3-4 crisp insights
    return insights[:5]

if __name__ == "__main__":
    print("Dashboard Analytics:")
    print(get_dashboard_analytics())
    print("\nDatabase Schema:")
    print(get_database_schema())
    print("\nData Quality:")
    print(check_data_quality())
    print("\nAI Insights:")
    for ins in generate_ai_insights():
        print(f" - {ins}")
