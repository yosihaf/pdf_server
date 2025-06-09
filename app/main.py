from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from app.routers import pdf
from app.routers import books 
from app.routers import auth
from .config import APP_NAME, APP_VERSION, APP_DESCRIPTION, ALLOWED_ORIGINS, LOG_LEVEL, LOG_FORMAT
from app.auth.middleware import JWTMiddleware  # הוסף import

# הגדרת logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# יצירת תיקיית פלט אם לא קיימת
os.makedirs('/app/output', exist_ok=True)

app = FastAPI(
    title="אתרי מכון חכמת התורה לספר",
    description="API להמרת דפי ויקי לקובץ PDF וניהול ספרים", 
    version="1.0.0",
)


app.add_middleware(
    JWTMiddleware,
    protected_paths=[
        "/api/pdf/generate",      # הגן על יצירת PDF
        "/api/pdf/download",      # הגן על הורדות
        "/api/books/folder",      # הגן על גישה לתיקיות ספציפיות
    ]
)


# הגדרת CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # שנה ל-False
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# הוספת נתב ה-PDF
app.include_router(pdf.router)
app.include_router(books.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {
        "service": "Wiki to PDF API & Books Manager",
        "version": "1.0.0",
        "endpoints": {
            "generate_pdf": "/api/pdf/generate",
            "check_status": "/api/pdf/status/{task_id}",
            "download_pdf": "/api/pdf/download/{task_id}/{filename}",
            "books_list": "/api/books/",
            "books_folders": "/api/books/folders",
            "books_search": "/api/books/search?q=query",
            "books_health": "/api/books/health"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

# טיפול בשגיאות
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "אירעה שגיאה בשרת. נא לנסות שוב מאוחר יותר."},
    )