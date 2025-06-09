# app/routers/public.py - נתב לקבצים ציבוריים

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import urllib.parse
import logging

from ..database.connection import get_db
from ..services.pdf_service import PDFService
from ..models.pdf import PublicPDFInfo
from ..auth.dependencies import get_current_user_optional

router = APIRouter(
    prefix="/api/public",
    tags=["public-pdfs"],
    responses={404: {"description": "משאב לא נמצא"}},
)

logger = logging.getLogger(__name__)

@router.get("/pdfs", response_model=List[PublicPDFInfo])
async def get_public_pdfs(
    db: Session = Depends(get_db),
    limit: int = Query(50, description="מספר תוצאות מקסימלי"),
    search: Optional[str] = Query(None, description="חיפוש בכותרות")
):
    """
    קבלת כל הקבצים הציבוריים - ללא צורך באימות
    """
    try:
        pdf_service = PDFService(db)
        
        if search:
            tasks = pdf_service.search_public_pdfs(search, limit)
        else:
            tasks = pdf_service.get_public_pdfs(limit)
        
        return [
            PublicPDFInfo(
                task_id=task.task_id,
                book_title=task.book_title,
                description=task.description,
                created_at=task.created_at.isoformat(),
                file_size=task.file_size,
                creator_username=task.user.username,
                view_url=f"/api/public/view/{task.task_id}/{task.filename}",
                download_url=f"/api/public/download/{task.task_id}/{task.filename}"
            )
            for task in tasks
        ]
    
    except Exception as e:
        logger.error(f"Error getting public PDFs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת הקבצים הציבוריים"
        )

@router.get("/view/{task_id}/{filename}")
async def view_public_pdf(
    task_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """
    צפייה בקובץ PDF ציבורי - ללא צורך באימות
    """
    pdf_service = PDFService(db)
    
    # בדוק שהקובץ ציבורי
    if not pdf_service.can_access_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="הקובץ אינו ציבורי או לא קיים"
        )
    
    # פענוח שם הקובץ
    decoded_filename = urllib.parse.unquote(filename)
    file_path = os.path.join('/app/output', task_id, decoded_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="הקובץ לא נמצא"
        )
    
    logger.info(f"Public view: {decoded_filename} (task: {task_id})")
    
    return FileResponse(
        path=file_path,
        filename=decoded_filename,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}
    )

@router.get("/download/{task_id}/{filename}")
async def download_public_pdf(
    task_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """
    הורדת קובץ PDF ציבורי - ללא צורך באימות
    """
    pdf_service = PDFService(db)
    
    # בדוק שהקובץ ציבורי
    if not pdf_service.can_access_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="הקובץ אינו ציבורי או לא קיים"
        )
    
    # פענוח שם הקובץ
    decoded_filename = urllib.parse.unquote(filename)
    file_path = os.path.join('/app/output', task_id, decoded_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="הקובץ לא נמצא"
        )
    
    logger.info(f"Public download: {decoded_filename} (task: {task_id})")
    
    return FileResponse(
        path=file_path,
        filename=decoded_filename,
        media_type="application/pdf"
    )

@router.get("/info/{task_id}")
async def get_public_pdf_info(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    קבלת מידע על קובץ PDF ציבורי
    """
    pdf_service = PDFService(db)
    
    task = pdf_service.get_task_with_user(task_id)
    if not task or not task.is_public or task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="קובץ ציבורי לא נמצא"
        )
    
    return {
        "task_id": task.task_id,
        "book_title": task.book_title,
        "description": task.description,
        "created_at": task.created_at.isoformat(),
        "file_size": task.file_size,
        "creator_username": task.user.username,
        "wiki_pages": task.wiki_pages,  # רשימת הדפים
        "view_url": f"/api/public/view/{task.task_id}/{task.filename}",
        "download_url": f"/api/public/download/{task.task_id}/{task.filename}"
    }