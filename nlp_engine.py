import re
import difflib
import sqlite3
from typing import Dict, Any, Tuple, List, Optional
from config import DB_FILE

# Supported departments with synonyms
DEPARTMENT_MAP = {
    "cse": "CSE",
    "computer science": "CSE",
    "computer": "CSE",
    "comp sci": "CSE",
    "cs": "CSE",
    "it": "IT",
    "information technology": "IT",
    "info tech": "IT",
    "ece": "ECE",
    "electronics": "ECE",
    "eee": "EEE",
    "electrical": "EEE",
    "mech": "MECH",
    "mechanical": "MECH",
    "aids": "AIDS",
    "ai and ds": "AIDS",
    "artificial intelligence": "AIDS",
    "ai": "AIDS",
    "civil": "CIVIL"
}

# Supported cities with synonyms
CITY_MAP = {
    "erode": "Erode",
    "chennai": "Chennai",
    "coimbatore": "Coimbatore",
    "kovai": "Coimbatore",
    "salem": "Salem",
    "madurai": "Madurai",
    "tiruchirappalli": "Tiruchirappalli",
    "trichy": "Tiruchirappalli",
    "tirunelveli": "Tirunelveli",
    "nellai": "Tirunelveli",
    "vellore": "Vellore",
    "thanjavur": "Thanjavur",
    "tanjore": "Thanjavur",
    "dindigul": "Dindigul"
}

# Tamil word translations / mappings
TAMIL_DICTIONARY = {
    # Actions & Verbs
    "காட்டு": "show",
    "காண்பி": "show",
    "பட்டியலிடு": "list",
    "தெரிவி": "display",
    "எடு": "get",
    "தேடு": "find",
    
    # Entities
    "மாணவர்கள்": "students",
    "மாணவர்களை": "students",
    "மாணவர்": "students",
    "மாணவிகள்": "female students",
    "மாணவி": "female student",
    "பையன்கள்": "male students",
    
    # Locations
    "ஈரோடு": "erode",
    "ஈரோட்டிலிருந்து": "erode",
    "ஈரோட்டில்": "erode",
    "சென்னை": "chennai",
    "சென்னையிலிருந்து": "chennai",
    "சென்னையில்": "chennai",
    "கோயம்புத்தூர்": "coimbatore",
    "கோவை": "coimbatore",
    "கோவையில்": "coimbatore",
    "சேலம்": "salem",
    "சேலத்திலிருந்து": "salem",
    "சேலத்தில்": "salem",
    "மதுரை": "madurai",
    "மதுரையிலிருந்து": "madurai",
    "மதுரையில்": "madurai",
    "திருச்சி": "tiruchirappalli",
    "திருச்சிராப்பள்ளி": "tiruchirappalli",
    "திருநெல்வேலி": "tirunelveli",
    "வேலூர்": "vellore",
    "தஞ்சாவூர்": "thanjavur",
    "திண்டுக்கல்": "dindigul",
    
    # Departments
    "கணினி": "cse",
    "கணினி அறிவியல்": "cse",
    "தகவல் தொழில்நுட்பம்": "it",
    "மின்னணுவியல்": "ece",
    "மின் மற்றும் மின்னணுவியல்": "eee",
    "இயந்திரவியல்": "mech",
    "செயற்கை நுண்ணறிவு": "aids",
    "கட்டுமான": "civil",
    
    # Aggregations & Metrics
    "சராசரி": "average",
    "சராசரியாக": "average",
    "அதிகபட்ச": "highest",
    "உயர்ந்த": "highest",
    "குறைந்தபட்ச": "lowest",
    "குறைந்த": "lowest",
    "எண்ணிக்கை": "count",
    "மொத்தம்": "total",
    "எத்தனை": "how many",
    "முதல்": "top",
    "கடைசி": "bottom",
    
    # Conditions
    "மேல்": "above",
    "அதிகமாக": "above",
    "அதிகம்": "above",
    "விட அதிகம்": "above",
    "கீழ்": "below",
    "குறைவாக": "below",
    "குறைவு": "below",
    "விட குறைவு": "below",
    
    # Groupings & Group by
    "துறைவாரியாக": "department wise",
    "துறை வாரியாக": "department wise",
    "நகரவாரியாக": "city wise",
    "நகர வாரியாக": "city wise",
    "ஆண்டுவாரியாக": "year wise",
    "வருடவாரியாக": "year wise",
    "விநியோகம்": "distribution",
    
    # Years
    "முதலாம் ஆண்டு": "1st year",
    "இரண்டாம் ஆண்டு": "2nd year",
    "மூன்றாம் ஆண்டு": "3rd year",
    "நான்காம் ஆண்டு": "4th year",
    "இறுதி ஆண்டு": "4th year",
    
    # Gender
    "ஆண்": "male",
    "பெண்": "female"
}

# Vocabulary for English spell-checking
DOMAIN_VOCABULARY = [
    "students", "student", "department", "departments", "cgpa", "city", "cities",
    "year", "years", "gender", "email", "show", "list", "display", "find", "get",
    "count", "total", "average", "avg", "mean", "highest", "maximum", "max", "top",
    "lowest", "minimum", "min", "above", "greater", "more", "below", "less", "under",
    "from", "in", "wise", "distribution", "all", "male", "female", "first", "second",
    "third", "fourth", "erode", "chennai", "coimbatore", "salem", "madurai",
    "tiruchirappalli", "tirunelveli", "vellore", "thanjavur", "dindigul",
    "cse", "it", "ece", "eee", "mech", "aids", "civil"
]

COMMON_MISSPELLINGS = {
    "studnts": "students",
    "studnt": "student",
    "stduents": "students",
    "stundents": "students",
    "depatment": "department",
    "deparment": "department",
    "dept": "department",
    "cgpaa": "cgpa",
    "cgpa's": "cgpa",
    "gpa": "cgpa",
    "erod": "erode",
    "chenai": "chennai",
    "chennay": "chennai",
    "coimbator": "coimbatore",
    "salm": "salem",
    "maduray": "madurai",
    "averge": "average",
    "avarge": "average",
    "higest": "highest",
    "heighest": "highest",
    "lowst": "lowest",
    "distribtion": "distribution",
    "cont": "count",
    "cunt": "count",
    "femail": "female",
    "femal": "female"
}

def detect_language(text_query: str) -> str:
    """
    Detects if the query contains Tamil characters (Unicode block 0B80 - 0BFF).
    """
    for ch in text_query:
        if '\u0B80' <= ch <= '\u0BFF':
            return "Tamil"
    return "English"

def translate_tamil_to_english(query: str) -> str:
    """
    Translates Tamil domain words into English keywords.
    """
    translated = query
    # Sort keys by length descending to match multi-word phrases first
    sorted_tamil = sorted(TAMIL_DICTIONARY.keys(), key=lambda x: len(x), reverse=True)
    for tam_word in sorted_tamil:
        if tam_word in translated:
            translated = translated.replace(tam_word, f" {TAMIL_DICTIONARY[tam_word]} ")
            
    # Clean up excess spaces
    translated = re.sub(r'\s+', ' ', translated).strip()
    return translated

def fuzzy_spell_correct(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Applies fuzzy spell correction to input tokens.
    Returns:
        (corrected_text, list_of_replacements)
    """
    words = re.findall(r'[A-Za-z0-9.]+', text)
    corrected_words = []
    corrections = []
    
    for word in words:
        lower_word = word.lower()
        
        # Check direct lookup first
        if lower_word in COMMON_MISSPELLINGS:
            replacement = COMMON_MISSPELLINGS[lower_word]
            corrected_words.append(replacement)
            corrections.append((word, replacement))
            continue
            
        # Check if already exact in vocabulary or is a number
        if lower_word in DOMAIN_VOCABULARY or re.match(r'^\d+(\.\d+)?$', lower_word):
            corrected_words.append(word)
            continue
            
        # Try difflib match if length >= 4
        if len(lower_word) >= 4 and not lower_word.isdigit():
            matches = difflib.get_close_matches(lower_word, DOMAIN_VOCABULARY, n=1, cutoff=0.76)
            if matches:
                replacement = matches[0]
                corrected_words.append(replacement)
                corrections.append((word, replacement))
                continue
                
        corrected_words.append(word)
        
    corrected_text = " ".join(corrected_words)
    return corrected_text, corrections

def extract_cgpa_condition(query_lower: str) -> Optional[Dict[str, Any]]:
    """
    Extracts CGPA comparisons like 'above 8', 'greater than 8.5', 'below 7', 'between 7 and 9'.
    """
    # Between X and Y
    between_match = re.search(r'(?:between|from)\s+(\d+(?:\.\d+)?)\s+(?:and|to)\s+(\d+(?:\.\d+)?)', query_lower)
    if between_match:
        val1 = float(between_match.group(1))
        val2 = float(between_match.group(2))
        low = min(val1, val2)
        high = max(val1, val2)
        return {
            "sql": f"cgpa >= {low} AND cgpa <= {high}",
            "desc": f"between {low} and {high}",
            "op": "BETWEEN",
            "values": [low, high]
        }
        
    # Greater than / above / more than / > / >=
    above_match = re.search(r'(?:above|greater than|more than|higher than|>|>=)\s*(\d+(?:\.\d+)?)', query_lower)
    if above_match:
        val = float(above_match.group(1))
        return {
            "sql": f"cgpa > {val}",
            "desc": f"greater than {val}",
            "op": ">",
            "values": [val]
        }
        
    # Below / less than / under / < / <=
    below_match = re.search(r'(?:below|less than|under|lower than|<|<=)\s*(\d+(?:\.\d+)?)', query_lower)
    if below_match:
        val = float(below_match.group(1))
        return {
            "sql": f"cgpa < {val}",
            "desc": f"less than {val}",
            "op": "<",
            "values": [val]
        }
        
    # Pattern like "8 cgpa" or "cgpa 8" with implicit above or threshold
    threshold_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cgpa|gpa)\s+(?:above|mel|greater)', query_lower)
    if threshold_match:
        val = float(threshold_match.group(1))
        return {
            "sql": f"cgpa > {val}",
            "desc": f"greater than {val}",
            "op": ">",
            "values": [val]
        }
        
    return None

def extract_year(query_lower: str) -> Optional[int]:
    """
    Extracts student academic year (1, 2, 3, or 4).
    """
    # e.g., '3rd year', '3 year', 'year 3', 'third year', 'final year'
    if re.search(r'\b(final year|4th year|fourth year|year 4)\b', query_lower):
        return 4
    if re.search(r'\b(3rd year|third year|year 3|3 year)\b', query_lower):
        return 3
    if re.search(r'\b(2nd year|second year|year 2|2 year)\b', query_lower):
        return 2
    if re.search(r'\b(1st year|first year|year 1|1 year|freshman)\b', query_lower):
        return 1
    return None

def extract_department(query_lower: str) -> Optional[str]:
    """
    Identifies if a department is mentioned in the query.
    """
    # Search for keys sorted by length descending
    for key in sorted(DEPARTMENT_MAP.keys(), key=lambda x: len(x), reverse=True):
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, query_lower):
            return DEPARTMENT_MAP[key]
    return None

def extract_city(query_lower: str) -> Optional[str]:
    """
    Identifies if a city is mentioned in the query.
    """
    for key in sorted(CITY_MAP.keys(), key=lambda x: len(x), reverse=True):
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, query_lower):
            return CITY_MAP[key]
    return None

def extract_top_n(query_lower: str) -> Optional[int]:
    """
    Extracts Top N limit if specified, e.g., 'top 10 students', 'top 5', 'top students'.
    """
    match = re.search(r'\btop\s+(\d+)\b', query_lower)
    if match:
        return int(match.group(1))
    if re.search(r'\btop\s+students\b', query_lower):
        return 5  # Default top 5
    return None

class NLPEngine:
    """
    State-of-the-art Natural Language to SQL converter with multilingual support,
    fuzzy spell correction, query explanation, and confidence scoring.
    """
    
    def process_dynamic_table_query(
        self,
        raw_query: str,
        corrected_query: str,
        language: str,
        corrections: List[Tuple[str, str]],
        table_name: str
    ) -> Dict[str, Any]:
        """
        Dynamically extracts columns, entities, groupings, and filters for any uploaded SQLite table.
        """
        conn = sqlite3.connect(DB_FILE)
        try:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info(`{table_name}`);")
            cols_info = cur.fetchall()
            cur.execute(f"SELECT COUNT(*) FROM `{table_name}`;")
            table_row_count = cur.fetchone()[0]
        except Exception:
            cols_info = []
            table_row_count = 0
        finally:
            conn.close()

        columns = [c[1] for c in cols_info]
        types_map = {c[1]: c[2].upper() for c in cols_info}
        num_cols = [c for c, t in types_map.items() if any(nt in t for nt in ('INT', 'REAL', 'FLOAT', 'DOUBLE', 'NUMERIC', 'DECIMAL'))]
        cat_cols = [c for c in columns if c not in num_cols]

        q_lower = corrected_query.lower()
        confidence = 90
        if corrections:
            confidence -= min(10, len(corrections) * 3)

        # Match columns in query text
        matched_cols = []
        for col in columns:
            clean_col = col.lower().replace('_', ' ')
            if col.lower() in q_lower or clean_col in q_lower:
                matched_cols.append(col)

        matched_num_col = next((c for c in matched_cols if c in num_cols), None)
        matched_cat_col = next((c for c in matched_cols if c in cat_cols), None)

        # 1. Total Count (How many, count, total rows, மொத்தம், எண்ணிக்கை)
        if any(w in q_lower for w in ["count", "how many", "total records", "total rows", "எண்ணிக்கை", "எத்தனை"]) and not any(w in q_lower for w in ["wise", "by ", "group"]):
            sql = f"SELECT COUNT(*) AS total_records FROM `{table_name}`;"
            explanation = f"This query counts the total records in dataset '{table_name}'."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, confidence + 5, "bar", "COUNT")

        # 2. Average / Mean (சராசரி)
        if any(w in q_lower for w in ["average", "avg", "mean", "சராசரி"]):
            target_num = matched_num_col or (num_cols[0] if num_cols else None)
            if target_num:
                sql = f"SELECT ROUND(AVG(`{target_num}`), 2) AS average_{target_num} FROM `{table_name}`;"
                explanation = f"This query computes the average of '{target_num}' in dataset '{table_name}'."
                return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, confidence + 5, "bar", "AVERAGE")

        # 3. Maximum / Highest / Top value (அதிகபட்ச, உயர்ந்த)
        if any(w in q_lower for w in ["highest", "maximum", "max", "top value", "அதிகபட்ச", "உயர்ந்த"]) and not any(w in q_lower for w in ["top 1", "top 2", "top 3", "top 4", "top 5", "top 10"]):
            target_num = matched_num_col or (num_cols[0] if num_cols else None)
            if target_num:
                sql = f"SELECT MAX(`{target_num}`) AS max_{target_num} FROM `{table_name}`;"
                explanation = f"This query retrieves the maximum '{target_num}' in dataset '{table_name}'."
                return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, confidence + 5, "bar", "MAX")

        # 4. Minimum / Lowest (குறைந்தபட்ச, குறைந்த)
        if any(w in q_lower for w in ["lowest", "minimum", "min", "குறைந்தபட்ச", "குறைந்த"]):
            target_num = matched_num_col or (num_cols[0] if num_cols else None)
            if target_num:
                sql = f"SELECT MIN(`{target_num}`) AS min_{target_num} FROM `{table_name}`;"
                explanation = f"This query retrieves the minimum '{target_num}' in dataset '{table_name}'."
                return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, confidence + 5, "bar", "MIN")

        # 5. Sum / Total metric (மொத்தம்)
        if any(w in q_lower for w in ["sum", "total", "மொத்தம்"]) and matched_num_col:
            sql = f"SELECT ROUND(SUM(`{matched_num_col}`), 2) AS total_{matched_num_col} FROM `{table_name}`;"
            explanation = f"This query sums '{matched_num_col}' across all records in '{table_name}'."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, confidence + 5, "bar", "SUM")

        # 6. Group By / Distribution (wise, by <col>, distribution, வாரியாக)
        if any(w in q_lower for w in ["wise", "distribution", "group by", "வாரியாக"]) or "by " in q_lower:
            group_col = matched_cat_col or (cat_cols[0] if cat_cols else (columns[0] if columns else None))
            if group_col:
                if matched_num_col:
                    sql = f"SELECT `{group_col}`, ROUND(SUM(`{matched_num_col}`), 2) AS total_{matched_num_col} FROM `{table_name}` GROUP BY `{group_col}` ORDER BY total_{matched_num_col} DESC LIMIT 20;"
                    explanation = f"This query groups by '{group_col}' and calculates the total '{matched_num_col}'."
                else:
                    sql = f"SELECT `{group_col}`, COUNT(*) AS record_count FROM `{table_name}` GROUP BY `{group_col}` ORDER BY record_count DESC LIMIT 20;"
                    explanation = f"This query groups records by '{group_col}' and counts the frequency of each category."
                return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, confidence + 5, "pie", "GROUP_BY")

        # 7. Top N records
        top_match = re.search(r'\btop\s+(\d+)\b', q_lower)
        if top_match:
            n = int(top_match.group(1))
            order_col = matched_num_col or (num_cols[0] if num_cols else columns[0])
            sql = f"SELECT * FROM `{table_name}` ORDER BY `{order_col}` DESC LIMIT {n};"
            explanation = f"This query retrieves the top {n} records from '{table_name}' ordered by '{order_col}' descending."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, confidence + 5, "bar", "TOP_N")

        # 8. Numeric condition filter (e.g. above X, below X, > X)
        num_cond = re.search(r'(\b\w+\b)\s*(?:above|greater than|>|>=)\s*(\d+(?:\.\d+)?)', q_lower)
        if num_cond:
            c_name = num_cond.group(1)
            val = num_cond.group(2)
            valid_c = next((c for c in num_cols if c.lower() == c_name.lower()), None)
            if valid_c:
                sql = f"SELECT * FROM `{table_name}` WHERE `{valid_c}` > {val};"
                explanation = f"This query filters records from '{table_name}' where '{valid_c}' is greater than {val}."
                return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, confidence + 5, "bar", "FILTER")

        # 9. Default Fallback for custom table
        limit_clause = " LIMIT 100" if table_row_count > 100 else ""
        sql = f"SELECT * FROM `{table_name}`{limit_clause};"
        explanation = f"This query retrieves records from the '{table_name}' dataset."
        return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, 92, "bar", "SHOW_ALL")

    def process_query(self, user_query: str, table_name: str = "students") -> Dict[str, Any]:
        """
        Main pipeline entry point:
        1. Validates input
        2. Detects language (English/Tamil)
        3. Normalizes Tamil words if needed
        4. Applies fuzzy spell correction
        5. Identifies query intent, filters, groupings, aggregations
        6. Generates safe SQLite query
        7. Generates natural language explanation
        8. Calculates confidence score and recommended visualization
        """
        raw_query = user_query.strip()
        if not raw_query:
            raise ValueError("Query cannot be empty.")
            
        language = detect_language(raw_query)
        
        # Step 2: Tamil Translation if applicable
        if language == "Tamil":
            english_working_query = translate_tamil_to_english(raw_query)
        else:
            english_working_query = raw_query
            
        # Step 3: Fuzzy spell correction
        corrected_query, corrections = fuzzy_spell_correct(english_working_query)
        q_lower = corrected_query.lower()
        
        # If user directly inputted a SQL query (SELECT or forbidden statements like DELETE, UPDATE, DROP, etc.)
        first_token_match = re.match(r'^\s*([a-zA-Z]+)', raw_query)
        if first_token_match:
            first_cmd = first_token_match.group(1).upper()
            if first_cmd in ("SELECT", "WITH", "DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE", "CREATE", "REPLACE", "ATTACH", "PRAGMA", "GRANT", "REVOKE", "EXEC", "EXECUTE"):
                return {
                    "user_query": raw_query,
                    "corrected_query": corrected_query,
                    "language": language,
                    "corrections": corrections,
                    "sql_query": raw_query if raw_query.endswith(";") else raw_query + ";",
                    "explanation": f"Direct SQL {first_cmd} statement.",
                    "confidence_score": 99,
                    "chart_type": "bar",
                    "intent": "RAW_SQL"
                }

        # If custom table specified and not 'students', process dynamically
        if table_name and table_name.lower() != "students":
            return self.process_dynamic_table_query(raw_query, corrected_query, language, corrections, table_name)
            
        # Step 4: Extract entities & filters for students table
        target_city = extract_city(q_lower)
        target_dept = extract_department(q_lower)
        target_year = extract_year(q_lower)
        cgpa_cond = extract_cgpa_condition(q_lower)
        top_n = extract_top_n(q_lower)
        
        # Gender filter
        gender = None
        if re.search(r'\b(female|girls?|women|women students)\b', q_lower):
            gender = "Female"
        elif re.search(r'\b(male|boys?|men)\b', q_lower):
            gender = "Male"
            
        confidence = 92
        if corrections:
            confidence -= min(10, len(corrections) * 3)
            
        # Initialize query components
        where_clauses = []
        explanation_clauses = []
        
        if target_city:
            where_clauses.append(f"city = '{target_city}'")
            explanation_clauses.append(f"whose city is {target_city}")
            confidence += 2
            
        if target_dept:
            where_clauses.append(f"department = '{target_dept}'")
            explanation_clauses.append(f"in the {target_dept} department")
            confidence += 2
            
        if target_year:
            where_clauses.append(f"year = {target_year}")
            explanation_clauses.append(f"in Year {target_year}")
            confidence += 2
            
        if gender:
            where_clauses.append(f"gender = '{gender}'")
            explanation_clauses.append(f"whose gender is {gender}")
            
        if cgpa_cond:
            where_clauses.append(cgpa_cond["sql"])
            explanation_clauses.append(f"with CGPA {cgpa_cond['desc']}")
            confidence += 3
            
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        where_desc = (" " + " and ".join(explanation_clauses)) if explanation_clauses else ""
        
        # Step 5: Intent Matching
        
        # Intent: Highest CGPA
        if any(w in q_lower for w in ["highest cgpa", "maximum cgpa", "max cgpa", "top cgpa"]):
            if where_clauses:
                sql = f"SELECT * FROM students{where_sql} ORDER BY cgpa DESC LIMIT 1;"
                explanation = f"This query retrieves the student with the highest CGPA{where_desc}."
            else:
                sql = "SELECT MAX(cgpa) AS highest_cgpa FROM students;"
                explanation = "This query finds the highest CGPA among all students in the database."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 5, 98), "bar", "HIGHEST_CGPA")
            
        # Intent: Lowest CGPA
        if any(w in q_lower for w in ["lowest cgpa", "minimum cgpa", "min cgpa"]):
            if where_clauses:
                sql = f"SELECT * FROM students{where_sql} ORDER BY cgpa ASC LIMIT 1;"
                explanation = f"This query retrieves the student with the lowest CGPA{where_desc}."
            else:
                sql = "SELECT MIN(cgpa) AS lowest_cgpa FROM students;"
                explanation = "This query finds the lowest CGPA among all students in the database."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 5, 98), "bar", "LOWEST_CGPA")
            
        # Intent: Average CGPA
        if any(w in q_lower for w in ["average cgpa", "avg cgpa", "mean cgpa"]):
            if where_clauses:
                sql = f"SELECT ROUND(AVG(cgpa), 2) AS average_cgpa FROM students{where_sql};"
                explanation = f"This query calculates the average CGPA for students{where_desc}."
            else:
                sql = "SELECT ROUND(AVG(cgpa), 2) AS average_cgpa FROM students;"
                explanation = "This query calculates the average CGPA across all students in the database."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 5, 98), "bar", "AVERAGE_CGPA")
            
        # Intent: Group-wise Counts / Distributions
        # Department-wise count
        if any(p in q_lower for p in ["department wise", "department-wise", "dept wise", "by department", "students department wise", "count students department"]):
            sql = "SELECT department, COUNT(*) AS student_count FROM students GROUP BY department ORDER BY student_count DESC;"
            explanation = "This query groups students by department and counts the number of enrolled students in each department."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 6, 98), "pie", "DEPT_DISTRIBUTION")
            
        # City-wise count
        if any(p in q_lower for p in ["city wise", "city-wise", "by city", "students city wise", "count students city"]):
            sql = "SELECT city, COUNT(*) AS student_count FROM students GROUP BY city ORDER BY student_count DESC;"
            explanation = "This query groups students by city and counts the number of students from each city."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 6, 98), "bar", "CITY_DISTRIBUTION")
            
        # Year-wise distribution
        if any(p in q_lower for p in ["year wise", "year-wise", "by year", "year distribution", "year-wise distribution", "count students year"]):
            sql = "SELECT year, COUNT(*) AS student_count FROM students GROUP BY year ORDER BY year ASC;"
            explanation = "This query groups students by academic year and counts the number of students in each year."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 6, 98), "doughnut", "YEAR_DISTRIBUTION")
            
        # Gender distribution
        if any(p in q_lower for p in ["gender wise", "gender-wise", "by gender", "gender distribution"]):
            sql = "SELECT gender, COUNT(*) AS student_count FROM students GROUP BY gender;"
            explanation = "This query groups students by gender and calculates the distribution."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 6, 98), "pie", "GENDER_DISTRIBUTION")
            
        # Intent: Count Students (overall or with filters)
        if any(p in q_lower for p in ["count students", "how many students", "total students", "count of students", "number of students"]) and not top_n:
            sql = f"SELECT COUNT(*) AS total_students FROM students{where_sql};"
            if where_desc:
                explanation = f"This query counts the total number of students{where_desc}."
            else:
                explanation = "This query counts the total number of students enrolled in the database."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 5, 98), "bar", "COUNT_STUDENTS")
            
        # Intent: Top N students
        if top_n is not None:
            limit_val = top_n
            sql = f"SELECT * FROM students{where_sql} ORDER BY cgpa DESC LIMIT {limit_val};"
            if where_desc:
                explanation = f"This query retrieves the top {limit_val} students{where_desc}, ordered by CGPA in descending order."
            else:
                explanation = f"This query retrieves the top {limit_val} students across all departments ordered by CGPA in descending order."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 5, 98), "bar", "TOP_N")
            
        # Intent: Filtered Student List (e.g., from Erode, above 8 CGPA, in CSE, etc.)
        if where_clauses:
            sql = f"SELECT * FROM students{where_sql} ORDER BY cgpa DESC;"
            explanation = f"This query retrieves all students{where_desc}."
            return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, min(confidence + 4, 98), "bar", "FILTERED_LIST")
            
        # Intent: Show all students (Default fallback)
        sql = "SELECT * FROM students;"
        explanation = "This query retrieves all student records from the database."
        return self._build_result(raw_query, corrected_query, language, corrections, sql, explanation, 95, "bar", "SHOW_ALL")

    def _build_result(self, raw_query: str, corrected_query: str, language: str, 
                      corrections: List[Tuple[str, str]], sql: str, 
                      explanation: str, confidence: int, chart_type: str, intent: str) -> Dict[str, Any]:
        return {
            "user_query": raw_query,
            "corrected_query": corrected_query,
            "language": language,
            "corrections": [{"original": c[0], "corrected": c[1]} for c in corrections],
            "sql_query": sql,
            "explanation": explanation,
            "confidence_score": max(70, min(99, confidence)),
            "chart_type": chart_type,
            "intent": intent
        }

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    engine = NLPEngine()
    
    # Test suite covering all core requirements
    test_queries = [
        "Show all students",
        "Show students from Erode",
        "Show students from Chennai",
        "Students with CGPA above 8",
        "Students with CGPA below 7",
        "Count students",
        "Count students department wise",
        "Average CGPA",
        "Highest CGPA",
        "Lowest CGPA",
        "Top 10 students",
        "Top students in IT",
        "Students in 3rd year",
        "Students in CSE",
        "Department-wise count",
        "City-wise count",
        "Year-wise distribution",
        # Tamil queries
        "மாணவர்களை காட்டு",
        "ஈரோட்டிலிருந்து மாணவர்களை காட்டு",
        "8 CGPA க்கு மேல் உள்ள மாணவர்கள்",
        # Fuzzy spell typos
        "studnts from erod",
        "depatment wise count",
        "averge cgpaa in cse"
    ]
    
    print("=" * 70)
    print("NLDE NLP Engine - Verification Test Suite")
    print("=" * 70)
    for q in test_queries:
        res = engine.process_query(q)
        try:
            print(f"\n[INPUT] {q}")
        except Exception:
            print(f"\n[INPUT] {repr(q)}")
        if res['corrections']:
            print(f" [TYPO FIXED] {res['corrections']}")
        print(f" [SQL]  {res['sql_query']}")
        print(f" [EXP]  {res['explanation']}")
        print(f" [CONF] {res['confidence_score']}% | [LANG] {res['language']} | [CHART] {res['chart_type']}")

