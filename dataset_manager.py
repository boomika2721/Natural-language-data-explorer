import os
import re
import datetime
import sqlite3
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import create_engine, text
from config import DATASETS_DIR, DB_FILE, SQLALCHEMY_DATABASE_URI
import auth_db

def sanitize_table_name(name: str) -> str:
    """
    Sanitizes user or file string into a valid, safe SQLite table identifier.
    E.g., 'Sales Data (2026).xlsx' -> 'sales_data_2026'
    """
    clean = re.sub(r'\.[^.]+$', '', name)  # remove extension
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', clean.strip())
    clean = re.sub(r'_+', '_', clean).strip('_').lower()
    if not clean or clean[0].isdigit():
        clean = f"table_{clean}"
    return clean[:40]

def clean_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes column names: lowercase, spaces to underscores, alphanumeric only.
    Deduplicates column names if needed.
    """
    new_cols = []
    seen = {}
    for col in df.columns:
        c_str = str(col).strip()
        c_clean = re.sub(r'[^a-zA-Z0-9_]', '_', c_str)
        c_clean = re.sub(r'_+', '_', c_clean).strip('_').lower()
        if not c_clean:
            c_clean = "col"
        if c_clean in seen:
            seen[c_clean] += 1
            c_clean = f"{c_clean}_{seen[c_clean]}"
        else:
            seen[c_clean] = 0
        new_cols.append(c_clean)
    df.columns = new_cols
    return df

def save_and_import_dataset(
    file_storage,
    custom_table_name: Optional[str] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Saves an uploaded file (CSV or Excel) to datasets/, creates a SQLite table,
    and returns initial profiling and preview data with user isolation.
    """
    filename = file_storage.filename
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ('csv', 'xlsx', 'xls'):
        raise ValueError("Invalid file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.")

    raw_name = custom_table_name.strip() if custom_table_name and custom_table_name.strip() else filename
    display_name = re.sub(r'\.[^.]+$', '', raw_name).replace('_', ' ').title()
    clean_base = sanitize_table_name(raw_name)

    # Scoped table name if user_id is provided to guarantee isolation between different users
    if user_id:
        table_name = f"u{user_id}_{clean_base}"
    else:
        table_name = clean_base

    target_filename = f"{table_name}.{ext}"
    target_path = os.path.join(DATASETS_DIR, target_filename)

    # Save file to datasets folder
    file_storage.seek(0)
    file_storage.save(target_path)

    # Read dataset with pandas
    try:
        if ext == 'csv':
            try:
                df = pd.read_csv(target_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(target_path, encoding='latin1')
        else:
            df = pd.read_excel(target_path, engine='openpyxl')
    except Exception as e:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise ValueError(f"Failed to parse uploaded spreadsheet: {str(e)}")

    if df.empty:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise ValueError("The uploaded dataset contains no rows or data.")

    # Clean columns
    df = clean_dataframe_columns(df)

    # Ingest into SQLite database
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    with engine.begin() as conn:
        df.to_sql(table_name, con=conn, if_exists='replace', index=False)

    file_size_kb = round(os.path.getsize(target_path) / 1024, 1) if os.path.exists(target_path) else 0

    # Register in user_datasets table for isolation
    if user_id:
        auth_db.register_user_dataset(
            user_id=user_id,
            table_name=table_name,
            display_name=display_name,
            original_filename=filename,
            file_path=target_path,
            file_size_kb=file_size_kb,
            row_count=len(df),
            column_count=len(df.columns)
        )

    # Generate profiling & AI summary
    profile = profile_dataset(table_name, df)
    ai_summary = generate_ai_dataset_summary(table_name, df, profile)

    return {
        "success": True,
        "table_name": table_name,
        "display_name": display_name,
        "original_filename": filename,
        "saved_filename": target_filename,
        "rows": len(df),
        "columns": list(df.columns),
        "preview": df.head(15).to_dict(orient='records'),
        "profile": profile,
        "ai_summary": ai_summary
    }

def get_all_datasets(user_id: Optional[int] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves accessible datasets:
    - Default 'students' (demo dataset available to everyone)
    - User's own uploaded datasets (isolated to user_id)
    - If admin, shows all uploaded datasets across all users
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    datasets = []
    
    # 1. Always include the built-in 'students' dataset
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='students';")
        if cur.fetchone()[0] > 0:
            cur.execute("SELECT COUNT(*) FROM `students`;")
            st_count = cur.fetchone()[0]
            cur.execute("PRAGMA table_info(`students`);")
            st_cols = [c[1] for c in cur.fetchall()]
            datasets.append({
                "table_name": "students",
                "display_name": "Students Analytics (Built-in Demo)",
                "file_name": "students.xlsx",
                "row_count": st_count,
                "column_count": len(st_cols),
                "columns": st_cols,
                "file_size_kb": 28.5,
                "uploaded_date": "System Default",
                "is_default": True,
                "is_owner": True,
                "owner_name": "System"
            })
    finally:
        conn.close()

    # 2. Retrieve user datasets from user_datasets table
    if user_id:
        user_rows = auth_db.get_user_datasets(user_id=user_id, is_admin=is_admin)
        for r in user_rows:
            tbl = r["table_name"]
            # get live columns if table exists
            cols = []
            conn = sqlite3.connect(DB_FILE)
            try:
                cur = conn.cursor()
                cur.execute(f"PRAGMA table_info(`{tbl}`);")
                cols = [c[1] for c in cur.fetchall()]
            except Exception:
                pass
            finally:
                conn.close()

            datasets.append({
                "table_name": tbl,
                "display_name": r["display_name"],
                "file_name": r["original_filename"] or f"{tbl}.csv",
                "row_count": r["row_count"],
                "column_count": r["column_count"] or len(cols),
                "columns": cols,
                "file_size_kb": r["file_size_kb"],
                "uploaded_date": str(r["created_at"])[:16] if r["created_at"] else "Recently",
                "is_default": False,
                "is_owner": (r.get("user_id") == user_id or is_admin),
                "owner_name": r.get("owner_name", "You"),
                "owner_email": r.get("owner_email", "")
            })

    return datasets

def profile_dataset(table_name: str, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Generates detailed data profiling for a dataset:
    - Row count, column count, memory usage
    - Missing values per column & overall missing %
    - Duplicate rows count & %
    - Column breakdown: data types, unique values, top values, min/max for numerics
    """
    if df is None:
        conn = sqlite3.connect(DB_FILE)
        try:
            df = pd.read_sql_query(f"SELECT * FROM `{table_name}`;", conn)
        finally:
            conn.close()

    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols

    null_counts = df.isnull().sum().to_dict()
    total_nulls = sum(null_counts.values())
    null_pct = round((total_nulls / total_cells * 100), 2) if total_cells > 0 else 0.0

    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_rows / total_rows * 100), 2) if total_rows > 0 else 0.0

    columns_profile = []
    numeric_cols = []
    categorical_cols = []

    for col in df.columns:
        series = df[col]
        col_type = str(series.dtype)
        is_num = pd.api.types.is_numeric_dtype(series)
        unique_vals = int(series.nunique())
        nulls = int(null_counts.get(col, 0))

        col_meta = {
            "name": col,
            "display_name": col.replace('_', ' ').title(),
            "dtype": col_type,
            "is_numeric": is_num,
            "unique_count": unique_vals,
            "null_count": nulls,
            "null_pct": round((nulls / total_rows * 100), 1) if total_rows > 0 else 0.0
        }

        if is_num:
            numeric_cols.append(col)
            valid = series.dropna()
            if len(valid) > 0:
                col_meta["min"] = round(float(valid.min()), 2)
                col_meta["max"] = round(float(valid.max()), 2)
                col_meta["mean"] = round(float(valid.mean()), 2)
        else:
            categorical_cols.append(col)
            top_val = series.mode().iloc[0] if not series.empty and not series.mode().empty else None
            col_meta["top_value"] = str(top_val) if top_val is not None else "-"

        columns_profile.append(col_meta)

    return {
        "table_name": table_name,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "total_nulls": total_nulls,
        "null_percentage": null_pct,
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": duplicate_pct,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "columns": columns_profile
    }

def generate_ai_dataset_summary(table_name: str, df: pd.DataFrame, profile: Dict[str, Any]) -> str:
    """
    Generates a natural, intelligent summary describing the dataset's nature,
    structure, health, and prominent characteristics.
    """
    rows = profile["total_rows"]
    cols = profile["total_columns"]
    num_cnt = len(profile["numeric_columns"])
    cat_cnt = len(profile["categorical_columns"])
    null_pct = profile["null_percentage"]
    dups = profile["duplicate_rows"]

    summary_parts = []
    
    clean_name = re.sub(r'^u\d+_', '', table_name).replace('_', ' ').title()
    summary_parts.append(
        f"**{clean_name}** comprises **{rows:,} records** spanning **{cols} features** "
        f"({num_cnt} numeric metrics and {cat_cnt} categorical attributes)."
    )

    if null_pct == 0 and dups == 0:
        summary_parts.append(
            "The dataset exhibits **pristine integrity** with zero missing values (100% completeness) "
            "and no duplicate records detected."
        )
    else:
        health_notes = []
        if null_pct > 0:
            health_notes.append(f"{profile['total_nulls']:,} null entries ({null_pct}% missingness)")
        if dups > 0:
            health_notes.append(f"{dups:,} duplicate rows")
        summary_parts.append(
            f"Data quality audit identified {' and '.join(health_notes)}, requiring basic imputation or deduplication."
        )

    if num_cnt > 0:
        top_nums = profile["numeric_columns"][:3]
        metrics_desc = []
        for col in top_nums:
            c_info = next((c for c in profile["columns"] if c["name"] == col), None)
            if c_info and "mean" in c_info:
                metrics_desc.append(f"*{col}* (avg: {c_info['mean']:,}, range: [{c_info['min']} &rarr; {c_info['max']}])")
        if metrics_desc:
            summary_parts.append(f"Key statistical signals include: {'; '.join(metrics_desc)}.")

    if cat_cnt > 0:
        top_cats = profile["categorical_columns"][:3]
        cat_desc = []
        for col in top_cats:
            c_info = next((c for c in profile["columns"] if c["name"] == col), None)
            if c_info and "unique_count" in c_info:
                cat_desc.append(f"*{col}* ({c_info['unique_count']} unique categories, most frequent: '{c_info.get('top_value', '-')}')")
        if cat_desc:
            summary_parts.append(f"Primary classification dimensions include: {'; '.join(cat_desc)}.")

    summary_parts.append("The dataset is fully indexed in SQLite and ready for natural language querying, automated visualization, and predictive modeling.")
    return " ".join(summary_parts)

def rename_dataset(old_table: str, new_name_raw: str, user_id: Optional[int] = None, is_admin: bool = False) -> Dict[str, Any]:
    """
    Renames a SQLite table and its corresponding file in datasets/ with ownership validation.
    """
    if old_table == 'students':
        raise ValueError("The built-in 'students' demo table cannot be renamed.")

    if user_id and not auth_db.check_dataset_access(user_id, is_admin, old_table):
        raise PermissionError("You do not have permission to rename this dataset.")

    new_base = sanitize_table_name(new_name_raw)
    new_display = re.sub(r'\.[^.]+$', '', new_name_raw).replace('_', ' ').title()
    
    # Preserve prefix if present
    if old_table.startswith('u') and '_' in old_table:
        prefix = old_table.split('_', 1)[0]
        new_table = f"{prefix}_{new_base}"
    else:
        new_table = new_base

    if old_table == new_table:
        return {"success": True, "table_name": new_table, "message": "Name unchanged."}
        
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    with engine.begin() as conn:
        check = conn.execute(text(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=:t;"), {"t": new_table}).scalar()
        if check > 0:
            raise ValueError(f"A dataset with the name '{new_table}' already exists.")
            
        conn.execute(text(f"ALTER TABLE `{old_table}` RENAME TO `{new_table}`;"))

    # Update in user_datasets table
    if user_id:
        auth_db.rename_user_dataset_record(user_id, is_admin, old_table, new_table, new_display)

    # Rename associated file if present in datasets/
    for ext in ('.csv', '.xlsx', '.xls'):
        old_f = os.path.join(DATASETS_DIR, f"{old_table}{ext}")
        new_f = os.path.join(DATASETS_DIR, f"{new_table}{ext}")
        if os.path.exists(old_f):
            os.rename(old_f, new_f)
            break

    return {
        "success": True,
        "old_table": old_table,
        "new_table": new_table,
        "display_name": new_display,
        "message": f"Dataset successfully renamed from '{old_table}' to '{new_display}'."
    }

def delete_dataset(table_name: str, user_id: Optional[int] = None, is_admin: bool = False) -> Dict[str, Any]:
    """
    Deletes a dataset: drops SQLite table and removes file with ownership check.
    """
    if table_name == 'students':
        raise ValueError("Cannot delete built-in 'students' dataset.")

    if user_id and not auth_db.check_dataset_access(user_id, is_admin, table_name):
        raise PermissionError("You do not have permission to delete this dataset.")

    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`;"))

    # Remove from user_datasets
    if user_id:
        auth_db.delete_user_dataset_record(user_id, is_admin, table_name)

    # Remove file from disk
    deleted_file = False
    for ext in ('.csv', '.xlsx', '.xls'):
        f_path = os.path.join(DATASETS_DIR, f"{table_name}{ext}")
        if os.path.exists(f_path):
            os.remove(f_path)
            deleted_file = True

    return {
        "success": True,
        "table_name": table_name,
        "deleted_file": deleted_file,
        "message": f"Dataset '{table_name}' deleted successfully."
    }

def compare_two_datasets(table1: str, table2: str) -> Dict[str, Any]:
    """
    Compares two datasets side-by-side:
    - Dimensions: rows, columns, memory
    - Schema differences: shared columns, unique to A, unique to B
    - Missing value comparisons
    - Statistical distribution shifts on shared numeric attributes
    """
    conn = sqlite3.connect(DB_FILE)
    try:
        df1 = pd.read_sql_query(f"SELECT * FROM `{table1}`;", conn)
        df2 = pd.read_sql_query(f"SELECT * FROM `{table2}`;", conn)
    finally:
        conn.close()

    cols1 = set(df1.columns)
    cols2 = set(df2.columns)

    shared_cols = sorted(list(cols1.intersection(cols2)))
    unique_to_1 = sorted(list(cols1 - cols2))
    unique_to_2 = sorted(list(cols2 - cols1))

    # Shared numeric comparison
    shared_numeric = []
    for c in shared_cols:
        if pd.api.types.is_numeric_dtype(df1[c]) and pd.api.types.is_numeric_dtype(df2[c]):
            s1 = df1[c].dropna()
            s2 = df2[c].dropna()
            if len(s1) > 0 and len(s2) > 0:
                mean1 = round(float(s1.mean()), 2)
                mean2 = round(float(s2.mean()), 2)
                diff = round(mean2 - mean1, 2)
                pct_shift = round(((mean2 - mean1) / mean1 * 100), 1) if mean1 != 0 else 0.0
                shared_numeric.append({
                    "column": c,
                    "mean_1": mean1,
                    "mean_2": mean2,
                    "delta": diff,
                    "percentage_shift": pct_shift,
                    "min_1": round(float(s1.min()), 2),
                    "min_2": round(float(s2.min()), 2),
                    "max_1": round(float(s1.max()), 2),
                    "max_2": round(float(s2.max()), 2)
                })

    return {
        "dataset_1": {
            "name": table1,
            "rows": len(df1),
            "columns": len(df1.columns),
            "nulls": int(df1.isnull().sum().sum()),
            "duplicates": int(df1.duplicated().sum())
        },
        "dataset_2": {
            "name": table2,
            "rows": len(df2),
            "columns": len(df2.columns),
            "nulls": int(df2.isnull().sum().sum()),
            "duplicates": int(df2.duplicated().sum())
        },
        "schema_comparison": {
            "shared_columns_count": len(shared_cols),
            "shared_columns": shared_cols,
            "unique_to_1": unique_to_1,
            "unique_to_2": unique_to_2,
            "similarity_score": round((2 * len(shared_cols) / (len(cols1) + len(cols2))) * 100, 1) if (cols1 or cols2) else 0.0
        },
        "numeric_comparison": shared_numeric
    }
