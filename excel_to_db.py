import os
import random
import pandas as pd
import sqlite3
from sqlalchemy import create_engine, text
from config import DB_FILE, DATASET_FILE, SQLALCHEMY_DATABASE_URI

def generate_sample_students_dataset(file_path):
    """
    Generates a realistic, comprehensive dataset of 120 Indian engineering students
    with realistic Tamil Nadu locations, departments, CGPAs, and contact info.
    Saves the data as an Excel file (.xlsx).
    """
    first_names_male = [
        "Aarav", "Karthik", "Vignesh", "Kavin", "Praveen", "Surya", "Dinesh",
        "Arvind", "Sanjay", "Harish", "Saravanan", "Vijay", "Manikandan", "Gokul",
        "Balaji", "Senthil", "Ashwin", "Siddharth", "Naveen", "Manoj", "Ajith",
        "Murugan", "Suresh", "Raghavan", "Prasanna", "Madhavan", "Vimal", "Ramesh",
        "Anand", "Deepak", "Ganesh", "Gopinath", "Kamal", "Mohan", "Natarajan"
    ]
    
    first_names_female = [
        "Ananya", "Divya", "Priya", "Soundarya", "Keerthana", "Meena", "Sneha",
        "Pavithra", "Harini", "Nithya", "Kaviya", "Deepa", "Shalini", "Gayathri",
        "Swetha", "Ramya", "Abinaya", "Mythili", "Bhavani", "Janani", "Kavitha",
        "Sandhya", "Archana", "Sowmya", "Vidya", "Aishwarya", "Revathi", "Malathi",
        "Geetha", "Pooja", "Varsha", "Monika", "Dharshini", "Preethi", "Ranjani"
    ]
    
    last_names = [
        "Kumar", "Raj", "Prakash", "Nathan", "Swamy", "Sundaram", "Chandran",
        "Murthy", "Krishnan", "Mani", "Vasan", "Pandian", "Moorthy", "Sekar",
        "Babu", "Rajan", "Prasad", "Samy", "Gopal", "Rao", "Narayanan"
    ]
    
    initials = ["S.", "R.", "M.", "K.", "P.", "V.", "A.", "G.", "T.", "D."]
    
    departments = ["CSE", "IT", "ECE", "EEE", "MECH", "AIDS", "CIVIL"]
    dept_weights = [0.25, 0.22, 0.18, 0.10, 0.10, 0.10, 0.05]
    
    cities = [
        "Erode", "Chennai", "Coimbatore", "Salem", "Madurai", 
        "Tiruchirappalli", "Tirunelveli", "Vellore", "Thanjavur", "Dindigul"
    ]
    city_weights = [0.22, 0.20, 0.18, 0.12, 0.10, 0.06, 0.04, 0.03, 0.03, 0.02]
    
    years = [1, 2, 3, 4]
    year_weights = [0.22, 0.25, 0.30, 0.23]
    
    records = []
    random.seed(42)  # Deterministic seed for reproducible testing
    
    # Pre-crafted iconic student records to guarantee exact prompt test cases
    seed_students = [
        {"name": "Karthik Raj", "department": "IT", "year": 3, "cgpa": 9.72, "city": "Erode", "gender": "Male", "email": "karthik.raj@college.edu"},
        {"name": "Divya Bharathi", "department": "CSE", "year": 4, "cgpa": 9.85, "city": "Chennai", "gender": "Female", "email": "divya.b@college.edu"},
        {"name": "Vigneshwaran S", "department": "CSE", "year": 3, "cgpa": 8.92, "city": "Erode", "gender": "Male", "email": "vignesh.s@college.edu"},
        {"name": "Priya Dharshini", "department": "IT", "year": 2, "cgpa": 8.45, "city": "Coimbatore", "gender": "Female", "email": "priya.d@college.edu"},
        {"name": "Surya Prakash", "department": "ECE", "year": 3, "cgpa": 7.80, "city": "Erode", "gender": "Male", "email": "surya.p@college.edu"},
        {"name": "Soundarya R", "department": "AIDS", "year": 1, "cgpa": 9.15, "city": "Chennai", "gender": "Female", "email": "soundarya.r@college.edu"},
        {"name": "Kavin Kumar", "department": "MECH", "year": 4, "cgpa": 6.85, "city": "Salem", "gender": "Male", "email": "kavin.k@college.edu"},
        {"name": "Ananya Sri", "department": "CSE", "year": 2, "cgpa": 9.40, "city": "Chennai", "gender": "Female", "email": "ananya.sri@college.edu"},
        {"name": "Praveen R", "department": "EEE", "year": 3, "cgpa": 7.20, "city": "Erode", "gender": "Male", "email": "praveen.r@college.edu"},
        {"name": "Keerthana S", "department": "IT", "year": 4, "cgpa": 8.90, "city": "Madurai", "gender": "Female", "email": "keerthana.s@college.edu"},
        {"name": "Dinesh Kumar", "department": "CIVIL", "year": 2, "cgpa": 6.45, "city": "Tiruchirappalli", "gender": "Male", "email": "dinesh.k@college.edu"},
        {"name": "Harini Devi", "department": "CSE", "year": 3, "cgpa": 9.60, "city": "Chennai", "gender": "Female", "email": "harini.d@college.edu"},
        {"name": "Sanjay Ram", "department": "AIDS", "year": 2, "cgpa": 8.75, "city": "Coimbatore", "gender": "Male", "email": "sanjay.ram@college.edu"},
        {"name": "Sneha R", "department": "ECE", "year": 1, "cgpa": 8.10, "city": "Erode", "gender": "Female", "email": "sneha.r@college.edu"},
        {"name": "Arvind Swamy", "department": "IT", "year": 3, "cgpa": 9.35, "city": "Chennai", "gender": "Male", "email": "arvind.s@college.edu"}
    ]
    
    current_id = 1
    for s in seed_students:
        s["id"] = current_id
        records.append(s)
        current_id += 1
        
    # Generate remaining up to 120 records
    while current_id <= 120:
        gender = random.choice(["Male", "Female"])
        if gender == "Male":
            fname = random.choice(first_names_male)
        else:
            fname = random.choice(first_names_female)
            
        if random.random() < 0.6:
            full_name = f"{fname} {random.choice(last_names)}"
        else:
            full_name = f"{fname} {random.choice(initials)}"
            
        dept = random.choices(departments, weights=dept_weights)[0]
        city = random.choices(cities, weights=city_weights)[0]
        year = random.choices(years, weights=year_weights)[0]
        
        # CGPA between 6.00 and 9.85 with realistic bell-curve distribution
        cgpa_raw = random.gauss(8.15, 0.85)
        cgpa = round(max(5.80, min(9.90, cgpa_raw)), 2)
        
        clean_email_name = full_name.lower().replace(" ", ".").replace(".", "").replace("..", ".")
        email = f"{clean_email_name}{random.randint(10, 99)}@college.edu"
        
        records.append({
            "id": current_id,
            "name": full_name,
            "department": dept,
            "year": year,
            "cgpa": cgpa,
            "city": city,
            "gender": gender,
            "email": email
        })
        current_id += 1

    df = pd.DataFrame(records)
    # Ensure columns order
    df = df[["id", "name", "department", "year", "cgpa", "city", "gender", "email"]]
    
    # Save to Excel
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_excel(file_path, index=False, engine='openpyxl')
    print(f"Generated sample dataset with {len(df)} records at: {file_path}")
    return df

def init_database(force_recreate=False):
    """
    Reads data from datasets/students.xlsx and writes it into database/students.db.
    Creates schema if table doesn't exist or if force_recreate is True.
    """
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(DATASET_FILE), exist_ok=True)
    
    # Generate dataset file if missing
    if not os.path.exists(DATASET_FILE) or os.path.getsize(DATASET_FILE) == 0:
        print("Dataset not found. Generating default students.xlsx dataset...")
        df = generate_sample_students_dataset(DATASET_FILE)
    else:
        print(f"Loading existing dataset from {DATASET_FILE}...")
        df = pd.read_excel(DATASET_FILE, engine='openpyxl')
        
    # Standardize column names
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Connect to SQLite
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    
    # Create students table with explicit schema and constraints
    with engine.begin() as conn:
        if force_recreate:
            conn.execute(text("DROP TABLE IF EXISTS students;"))
            
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                year INTEGER NOT NULL,
                cgpa REAL NOT NULL,
                city TEXT NOT NULL,
                gender TEXT NOT NULL,
                email TEXT NOT NULL
            );
        """))
        
        # Check current row count
        count = conn.execute(text("SELECT COUNT(*) FROM students;")).scalar()
        if count == 0 or force_recreate:
            print("Populating SQLite 'students' table from dataset...")
            df.to_sql('students', con=conn, if_exists='replace', index=False)
            
            # Recreate indices for query performance
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_city ON students(city);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_year ON students(year);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_students_cgpa ON students(cgpa);"))
            
            final_count = conn.execute(text("SELECT COUNT(*) FROM students;")).scalar()
            print(f"Database initialized successfully with {final_count} student records.")
        else:
            print(f"Database already populated with {count} records.")

if __name__ == '__main__':
    print("=" * 60)
    print("NLDE - Database Initialization & Excel Sync")
    print("=" * 60)
    init_database(force_recreate=True)
    print("Done.")
