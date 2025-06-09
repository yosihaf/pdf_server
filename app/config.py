import os
from pathlib import Path

# הגדרות נתיבים
BASE_BOOKS_PATH = os.getenv("BOOKS_PATH", "/home/wiki/pdf_render/output")

# הגדרות אפליקציה
APP_NAME = "Wiki PDF Generator & Books Manager"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "API לייצור PDF מויקי וניהול ספרים"

# הגדרות CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080", 
    "http://127.0.0.1:3000",
    # הוסף כאן את הדומינים שלך לפרודקשן
]

# הגדרות לוגינג
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# הגדרות קבצים
ALLOWED_FILE_EXTENSIONS = [".pdf"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# הגדרות פאגינציה
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100