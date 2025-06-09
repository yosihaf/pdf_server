from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
import uuid
import os
import logging
import urllib.parse
from ..models import PDFRequest, PDFResponse, PDFStatus
from app.pdf_generator import create_pdf_async, task_status

router = APIRouter(
    prefix="/api/pdf",
    tags=["pdf-generation"],
    responses={404: {"description": "משאב לא נמצא"}},
)

logger = logging.getLogger(__name__)

BASE_BOOKS_PATH = "/app/output"


@router.post("/generate", response_model=PDFResponse)
async def generate_pdf(request: PDFRequest, background_tasks: BackgroundTasks):
    """
    קבלת רשימת ערכי ויקי והפעלת תהליך המרה לPDF
    """
    task_id = str(uuid.uuid4())
    logger.info(f"New PDF generation task: {task_id}")
    
    # בדיקה שיש ערכים להמרה
    if not request.wiki_pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="נדרשת רשימה של לפחות ערך ויקי אחד"
        )
    
    # הפעלת המשימה ברקע
    background_tasks.add_task(
        create_pdf_async,
        task_id=task_id,
        wiki_pages=request.wiki_pages,
        book_title=request.book_title,
        base_url=request.base_url
    )
    
    # החזרת מזהה המשימה
    return PDFResponse(
        task_id=task_id,
        status="processing",
        message="המשימה החלה לרוץ, בדוק את הסטטוס באמצעות מזהה המשימה"
    )

@router.get("/status/{task_id}", response_model=PDFStatus)
async def check_status(task_id: str):
    """
    בדיקת סטטוס משימת המרה לפי מזהה
    """
    if task_id not in task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="מזהה משימה לא קיים"
        )
    
    status_data = task_status[task_id]
    return PDFStatus(
        task_id=task_id,
        status=status_data.get("status", "unknown"),
        download_url=status_data.get("download_url"),
        message=status_data.get("message", "")
    )

@router.get("/download/{task_id}/{filename}")
async def download_pdf(task_id: str, filename: str):
    """
    הורדת קובץ PDF לפי מזהה משימה ושם קובץ
    """
   
    
    # פענוח שם הקובץ מ-URL encoding
    decoded_filename = urllib.parse.unquote(filename)
    logger.info(f"Decoded filename: {decoded_filename}")
    # בניית הנתיב המלא
    file_path = os.path.join('/app/output', task_id, decoded_filename)
    print(f"Looking for file at: {file_path}")
    
    # בדיקה אם התיקייה קיימת
    dir_path = os.path.join('/app/output', task_id)
    if not os.path.exists(dir_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"התיקייה לא נמצאה: {dir_path}"
        )
    
    # בדיקה אם הקובץ קיים
    if not os.path.exists(file_path):
        # רשימת כל הקבצים בתיקייה לדיבוג
        files = os.listdir(dir_path)
        print(f"Files in directory: {files}")
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"הקובץ המבקש לא נמצא: {file_path}"
        )
    
    return FileResponse(
        path=file_path, 
        filename=decoded_filename,
        media_type="application/pdf"
    )
    
@router.get("/view/{task_id}/{filename}")
async def download_pdf(task_id: str, filename: str):
    """
    הורדת קובץ PDF לפי מזהה משימה ושם קובץ
    """
   
    
    # פענוח שם הקובץ מ-URL encoding
    decoded_filename = urllib.parse.unquote(filename)
    logger.info(f"Decoded filename: {decoded_filename}")
    # בניית הנתיב המלא
    file_path = os.path.join('/app/output', task_id, decoded_filename)
    print(f"Looking for file at: {file_path}")
    
    # בדיקה אם התיקייה קיימת
    dir_path = os.path.join('/app/output', task_id)
    if not os.path.exists(dir_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"התיקייה לא נמצאה: {dir_path}"
        )
    
    # בדיקה אם הקובץ קיים
    if not os.path.exists(file_path):
        # רשימת כל הקבצים בתיקייה לדיבוג
        files = os.listdir(dir_path)
        print(f"Files in directory: {files}")
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"הקובץ המבקש לא נמצא: {file_path}"
        )
    
    return FileResponse(
        path=file_path, 
        filename=decoded_filename,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}
    )

        