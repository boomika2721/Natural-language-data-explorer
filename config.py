import os

# Base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Data directories
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# Ensure required directories exist
for folder in [DATABASE_DIR, DATASETS_DIR, REPORTS_DIR, UPLOADS_DIR]:
    os.makedirs(folder, exist_ok=True)

# Database configuration
DB_FILE = os.path.join(DATABASE_DIR, 'students.db')
DATASET_FILE = os.path.join(DATASETS_DIR, 'students.xlsx')

SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_FILE}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Application settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'nlde-ai-data-explorer-super-secret-key-2026')
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', 5000))

# Query limits and safety
MAX_QUERY_RESULTS = 1000
MAX_HISTORY_ITEMS = 20
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
