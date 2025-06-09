# app/main.py - גרסה פשוטה שעובדת

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

# Import הנתבים
from app.routers import pdf
from app.routers import books 
from app.routers import auth
# from app.routers import admin  # נוסיף מאוחר יותר

from .database.connection import init_db

# הגדרת logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# יצירת מסד הנתונים
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

# יצירת תיקיית פלט אם לא קיימת
os.makedirs('./app/output', exist_ok=True)

app = FastAPI(
    title="אתרי מכון חכמת התורה לספר",
    description="API להמרת דפי ויקי לקובץ PDF וניהול ספרים", 
    version="1.0.0",
)

# הגדרת CORS פשוט
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# הוספת הנתבים
app.include_router(pdf.router)
app.include_router(books.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {
        "service": "Wiki to PDF API & Books Manager",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "auth_login": "/api/auth/login",
            "auth_register": "/api/auth/register",
            "auth_health": "/api/auth/health",
            "pdf_generate": "/api/pdf/generate",
            "books_list": "/api/books/",
            "books_health": "/api/books/health"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "message": "Server is running",
        "database": "connected"
    }

# טיפול בשגיאות בסיסי
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "אירעה שגיאה בשרת. נא לנסות שוב מאוחר יותר."},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)