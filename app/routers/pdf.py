# app/routers/pdf.py - עם מעקב יוצר מלא

from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
import uuid
import os
import logging
import urllib.parse
from typing import List
from datetime import datetime

from ..models import PDFRequest, PDFResponse, PDFStatus
from ..database.connection import get_db
from ..auth.dependencies import get_current_user
from ..services.pdf_service import PDFService
from app.pdf_generator import create_pdf_async, task_status

router = APIRouter(
    prefix="/api/pdf",
    tags=["pdf-generation"],
    responses={404: {"description": "משאב לא נמצא"}},
)

logger = logging.getLogger(__name__)

# מודל תגובה מפורט למשימות המשתמש
from pydantic import BaseModel

class UserTaskDetailedResponse(BaseModel):
    task_id: str
    book_title: str
    description: str = None
    status: str
    message: str
    created_at: datetime
    completed_at: datetime = None
    filename: str = None
    file_size: int = None
    is_public: bool = False
    wiki_pages: List[str] = []
    download_url: str = None
    view_url: str = None
    public_url: str = None

class CreatorStatsResponse(BaseModel):
    username: str
    user_id: int
    total_books_created: int
    completed_books: int
    public_books: int
    success_rate: float
    member_since: datetime

@router.post("/generate", response_model=PDFResponse)
async def generate_pdf(
    request: PDFRequest, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    יצירת PDF עם שמירת פרטי היוצר
    """
    
    # בדיקה שיש ערכים להמרה
    if not request.wiki_pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="נדרשת רשימה של לפחות ערך ויקי אחד"
        )
    
    # יצירת שירות PDF
    pdf_service = PDFService(db)
    
    # יצירת משימה במסד הנתונים עם פרטי היוצר
    pdf_task = pdf_service.create_pdf_task(
        user_id=int(current_user["user_id"]),
        wiki_pages=request.wiki_pages,
        book_title=request.book_title,
        base_url=request.base_url,
        is_public=request.is_public,
        description=request.description
    )
    
    # הפעלת המשימה ברקע
    background_tasks.add_task(
        create_pdf_with_tracking,
        task_id=pdf_task.task_id,
        wiki_pages=request.wiki_pages,
        book_title=request.book_title,
        base_url=request.base_url,
        user_id=int(current_user["user_id"])
    )
    
    privacy_msg = "ציבורי" if request.is_public else "פרטי"
    logger.info(f"User {current_user['username']} created {privacy_msg} PDF task {pdf_task.task_id} - Book: {request.book_title}")
    
    # החזרת מזהה המשימה
    return PDFResponse(
        task_id=pdf_task.task_id,
        status="processing",
        message=f"המשימה החלה לרוץ - קובץ {privacy_msg}. יוצר: {current_user['username']}",
        is_public=request.is_public
    )

@router.get("/my-tasks", response_model=List[UserTaskDetailedResponse])
async def get_my_tasks(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20
):
    """
    קבלת כל המשימות של המשתמש הנוכחי עם פרטים מלאים
    """
    pdf_service = PDFService(db)
    tasks = pdf_service.get_user_tasks_detailed(int(current_user["user_id"]), limit)
    
    return [
        UserTaskDetailedResponse(
            task_id=task["task_id"],
            book_title=task["book_title"],
            description=task["description"],
            status=task["status"],
            message=task["message"] or "",
            created_at=task["created_at"],
            completed_at=task["completed_at"],
            filename=task["filename"],
            file_size=task["file_size"],
            is_public=task["is_public"],
            wiki_pages=task["wiki_pages"],
            download_url=task["download_url"],
            view_url=task["view_url"],
            public_url=task["public_url"]
        )
        for task in tasks
    ]

@router.get("/my-stats", response_model=CreatorStatsResponse)
async def get_my_creator_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    סטטיסטיקות יצירת ספרים של המשתמש הנוכחי
    """
    pdf_service = PDFService(db)
    stats = pdf_service.get_creator_stats(int(current_user["user_id"]))
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="לא נמצאו נתוני סטטיסטיקה"
        )
    
    return CreatorStatsResponse(**stats)

@router.get("/status/{task_id}", response_model=PDFStatus)
async def check_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    בדיקת סטטוס משימה - רק אם המשימה שייכת למשתמש
    """
    pdf_service = PDFService(db)
    
    # בדיקה שהמשימה שייכת למשתמש
    if not pdf_service.verify_task_ownership(task_id, int(current_user["user_id"])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="אין לך הרשאה לצפות במשימה זו"
        )
    
    task = pdf_service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="מזהה משימה לא קיים"
        )
    
    download_url = None
    view_url = None
    public_url = None
    
    if task.status == "completed" and task.filename:
        download_url = f"/api/pdf/download/{task_id}/{task.filename}"
        view_url = f"/api/pdf/view/{task_id}/{task.filename}"
        
        # אם הקובץ ציבורי, הוסף URL ציבורי
        if task.is_public:
            public_url = f"/api/public/view/{task_id}/{task.filename}"
    
    return PDFStatus(
        task_id=task_id,
        status=task.status,
        download_url=download_url,
        view_url=view_url,
        public_url=public_url,
        message=task.message or "",
        is_public=task.is_public
    )

@router.get("/download/{task_id}/{filename}")
async def download_pdf(
    task_id: str, 
    filename: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    הורדת קובץ PDF - רק אם המשימה שייכת למשתמש
    """
    pdf_service = PDFService(db)
    
    # בדיקה שהמשימה שייכת למשתמש
    if not pdf_service.verify_task_ownership(task_id, int(current_user["user_id"])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="אין לך הרשאה להוריד קובץ זה"
        )
    
    # פענוח שם הקובץ מ-URL encoding
    decoded_filename = urllib.parse.unquote(filename)
    file_path = os.path.join('/app/output', task_id, decoded_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="הקובץ לא נמצא"
        )
    
    logger.info(f"User {current_user['username']} downloading their PDF: {decoded_filename} (task: {task_id})")
    
    return FileResponse(
        path=file_path, 
        filename=decoded_filename,
        media_type="application/pdf"
    )

@router.get("/view/{task_id}/{filename}")
async def view_pdf(
    task_id: str, 
    filename: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    צפייה בקובץ PDF - רק אם המשימה שייכת למשתמש
    """
    pdf_service = PDFService(db)
    
    # בדיקה שהמשימה שייכת למשתמש
    if not pdf_service.verify_task_ownership(task_id, int(current_user["user_id"])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="אין לך הרשאה לצפות בקובץ זה"
        )
    
    # פענוח שם הקובץ
    decoded_filename = urllib.parse.unquote(filename)
    file_path = os.path.join('/app/output', task_id, decoded_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="הקובץ לא נמצא"
        )
    
    logger.info(f"User {current_user['username']} viewing their PDF: {decoded_filename} (task: {task_id})")
    
    return FileResponse(
        path=file_path, 
        filename=decoded_filename,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}
    )

@router.put("/{task_id}/privacy")
async def update_privacy(
    task_id: str,
    is_public: bool,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    עדכון הגדרת פרטיות של קובץ
    """
    pdf_service = PDFService(db)
    
    success = pdf_service.update_privacy_setting(
        task_id, 
        int(current_user["user_id"]), 
        is_public
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="המשימה לא נמצאה או שאין לך הרשאה לערוך אותה"
        )
    
    privacy_status = "ציבורי" if is_public else "פרטי"
    logger.info(f"User {current_user['username']} updated task {task_id} privacy to {privacy_status}")
    
    return {
        "status": "success",
        "message": f"הקובץ עודכן ל{privacy_status}",
        "task_id": task_id,
        "is_public": is_public,
        "updated_by": current_user["username"]
    }

# פונקציה מעודכנת ליצירת PDF עם מעקב מפורט
async def create_pdf_with_tracking(
    task_id: str, 
    wiki_pages: List[str], 
    book_title: str,
    base_url: str,
    user_id: int
):
    """יצירת PDF עם עדכון במסד הנתונים וmעקב יוצר"""
    
    # קבל חיבור למסד הנתונים
    from ..database.connection import SessionLocal
    db = SessionLocal()
    
    try:
        pdf_service = PDFService(db)
        
        # עדכן סטטוס להתחלת עיבוד
        pdf_service.update_task_status(task_id, "processing", "מתחיל בהמרה...")
        
        # הפעל את הפונקציה המקורית
        result = await create_pdf_async(task_id, wiki_pages, book_title, base_url)
        
        if result:
            # חשב גודל קובץ
            filename = f'{book_title.replace(" ", "_")}.pdf'
            file_path = os.path.join('/app/output', task_id, filename)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            # עדכן הצלחה
            pdf_service.update_task_status(
                task_id, 
                "completed", 
                "ההמרה הושלמה בהצלחה",
                filename=filename,
                file_path=file_path,
                file_size=file_size
            )
            
            logger.info(f"PDF task {task_id} completed successfully for user {user_id} - Book: {book_title}")
        else:
            pdf_service.update_task_status(task_id, "failed", "אירעה שגיאה במהלך ההמרה")
            
    except Exception as e:
        logger.error(f"Error in PDF task {task_id} for user {user_id}: {str(e)}")
        if 'pdf_service' in locals():
            pdf_service.update_task_status(task_id, "failed", f"אירעה שגיאה: {str(e)}")
        
    finally:
        db.close()