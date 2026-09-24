import re

# Set of forbidden SQL commands and sensitive operations
FORBIDDEN_KEYWORDS = [
    "DELETE",
    "UPDATE",
    "INSERT",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "SHUTDOWN",
    "VACUUM",
    "REINDEX",
    "INTO OUTFILE",
    "INTO DUMPFILE",
    "LOAD_FILE",
    "XP_CMDSHELL"
]

def clean_sql_comment(sql: str) -> str:
    """
    Strips inline and multiline SQL comments to prevent comment-based evasions.
    """
    # Remove multi-line comments /* ... */
    sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.DOTALL)
    # Remove single-line comments -- ...
    sql = re.sub(r'--.*$', ' ', sql, flags=re.MULTILINE)
    return sql.strip()

def validate_sql_query(sql_query: str) -> tuple[bool, str]:
    """
    Validates that a SQL query is strictly read-only (SELECT) and contains no dangerous statements.
    
    Returns:
        (is_safe, message_or_error)
    """
    if not sql_query or not sql_query.strip():
        return False, "Unsafe Query Blocked: Empty query provided."

    clean_sql = clean_sql_comment(sql_query)
    
    # Check for multiple stacked statements separated by semicolons
    # Allow a single trailing semicolon, but no statement chaining
    stripped_trailing = clean_sql.rstrip(';').strip()
    if ';' in stripped_trailing:
        return False, "Unsafe Query Blocked: Multiple SQL statements or query chaining are prohibited."

    # Must start with SELECT or WITH (for CTE read queries)
    first_token_match = re.match(r'^\s*([a-zA-Z]+)', stripped_trailing, re.IGNORECASE)
    if not first_token_match:
        return False, "Unsafe Query Blocked: Invalid SQL syntax."
        
    first_token = first_token_match.group(1).upper()
    if first_token not in ("SELECT", "WITH", "EXPLAIN"):
        return False, f"Unsafe Query Blocked: Only read-only SELECT queries are allowed. '{first_token}' is prohibited."

    # Check for any forbidden keyword as a standalone word
    upper_sql = stripped_trailing.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        # Regex word boundary check to avoid false positives (e.g., 'UPDATE' vs 'LAST_UPDATED')
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, upper_sql):
            return False, f"Unsafe Query Blocked: Dangerous keyword '{keyword}' detected."

    # Block INTO clauses in SELECT (e.g., SELECT ... INTO table)
    if re.search(r'\bSELECT\b[\s\S]+\bINTO\b', upper_sql):
        return False, "Unsafe Query Blocked: SELECT INTO statement is not allowed."

    return True, "Query verified as safe read-only SQL."

if __name__ == "__main__":
    # Self-test unit assertions
    test_cases = [
        ("SELECT * FROM students;", True),
        ("SELECT department, count(*) FROM students GROUP BY department", True),
        ("DELETE FROM students WHERE id = 1;", False),
        ("SELECT * FROM students; DROP TABLE students;", False),
        ("UPDATE students SET cgpa = 10;", False),
        ("INSERT INTO students (name) VALUES ('Hacker');", False),
        ("PRAGMA table_info(students);", False),
        ("ALTER TABLE students ADD COLUMN test TEXT;", False),
        ("ATTACH DATABASE 'malicious.db' AS mal;", False),
        ("SELECT * FROM students WHERE name='Aarav' /* comment */", True)
    ]
    for q, expected in test_cases:
        is_safe, msg = validate_sql_query(q)
        print(f"[{'PASS' if is_safe == expected else 'FAIL'}] {q} -> {msg}")
