# app/routers/books.py - גרסה מתוקנת עם אימות

from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.responses import FileResponse
from typing import List
import logging
from datetime import datetime

from ..models.books import BookInfo, BooksResponse, FolderInfo, FoldersResponse, SearchResponse
from ..services.books_service import BooksService
from ..config import BASE_BOOKS_PATH
from ..auth.dependencies import get_current_user

# הגדרת הRouter
router = APIRouter(
    prefix="/api/books",
    tags=["books-management"],
    responses={404: {"description": "משאב לא נמצא"}},
    dependencies=[Depends(get_current_user)]
)

logger = logging.getLogger(__name__)

# יצירת instance של השירות
books_service = BooksService(BASE_BOOKS_PATH)


@router.get("", response_model=BooksResponse)
async def get_all_books(current_user: dict = Depends(get_current_user)):
    """
    מחזיר את כל הספרים מכל התקיות
    נדרש אימות
    """
    try: 
        books = books_service.get_all_books()
        logger.info(f"User {current_user['username']} retrieved {len(books)} books")
        
        return BooksResponse(
            status="success",
            count=len(books),
            books=books
        )
    
    except Exception as e:
        logger.error(f"Error getting all books for user {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת רשימת הספרים"
        )

@router.get("/folder/{folder_name}", response_model=BooksResponse)
async def get_books_by_folder(
    folder_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    מחזיר ספרים מתקייה מסוימת
    נדרש אימות
    """
    try:
        books = books_service.get_books_by_folder(folder_name)
        logger.info(f"User {current_user['username']} retrieved {len(books)} books from folder {folder_name}")
        
        return BooksResponse(
            status="success",
            count=len(books),
            books=books
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="התקייה לא נמצאה"
        )
    except Exception as e:
        logger.error(f"Error getting books from folder {folder_name} for user {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת ספרים מהתקייה"
        )

@router.get("/folders", response_model=FoldersResponse)
async def get_folders(current_user: dict = Depends(get_current_user)):
    """
    מחזיר רשימת כל התקיות
    נדרש אימות
    """
    try:
        folders = books_service.get_folders()
        logger.info(f"User {current_user['username']} retrieved {len(folders)} folders")
        
        return FoldersResponse(
            status="success",
            count=len(folders),
            folders=folders
        )
    
    except Exception as e:
        logger.error(f"Error getting folders for user {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת רשימת התקיות"
        )

@router.get("/search", response_model=SearchResponse)
async def search_books(
    q: str = Query(..., description="מילת חיפוש"),
    search_in: str = Query("title", description="חיפוש ב: title, folder, all"),
    limit: int = Query(50, description="מספר תוצאות מקסימלי"),
    current_user: dict = Depends(get_current_user)
):
    """
    חיפוש ספרים לפי מילות מפתח
    נדרש אימות
    """
    try:
        if not q.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="מילת חיפוש נדרשת"
            )
        
        # החיפוש מתבצע כולו בservice
        filtered_books = books_service.search_books(q, search_in, limit)
        
        logger.info(f"User {current_user['username']} searched for '{q}' and got {len(filtered_books)} results")
        
        return SearchResponse(
            status="success",
            query=q,
            search_in=search_in,
            total_found=len(filtered_books),
            count=len(filtered_books),
            books=filtered_books
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching books for user {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בחיפוש ספרים"
        )


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="תחילת מילת חיפוש"),
    limit: int = Query(10, description="מספר הצעות מקסימלי"),
    current_user: dict = Depends(get_current_user)
):
    """
    הצעות חיפוש אוטומטי
    נדרש אימות
    """
    try:
        suggestions = books_service.get_search_suggestions(q, limit)
        
        logger.info(f"User {current_user['username']} requested search suggestions for '{q}'")
        
        return {
            "status": "success",
            "query": q,
            "suggestions": suggestions
        }
    
    except Exception as e:
        logger.error(f"Error getting search suggestions for user {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת הצעות חיפוש"
        )


@router.get("/view/{folder_name}/{filename}")
async def view_book(
    folder_name: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """
    צפייה בספר
    נדרש אימות
    """
    try:
        file_path, mimetype = books_service.get_file_info(folder_name, filename)
        
        logger.info(f"User {current_user['username']} viewing book: {folder_name}/{filename}")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=mimetype or "application/pdf",
            headers={"Content-Disposition": "inline"}
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="הקובץ לא נמצא"
        )
    except Exception as e:
        logger.error(f"Error viewing book for user {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בצפייה בקובץ"
        )


@router.get("/download/{folder_name}/{filename}")
async def download_book(
    folder_name: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """
    הורדת ספר
    נדרש אימות
    """
    try:
        file_path, mimetype = books_service.get_file_info(folder_name, filename)
        
        logger.info(f"User {current_user['username']} downloading book: {folder_name}/{filename}")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=mimetype or "application/pdf"
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="הקובץ לא נמצא"
        )
    except Exception as e:
        logger.error(f"Error downloading book for user {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בהורדת הקובץ"
        )

        
@router.get("/health")
async def health_check(current_user: dict = Depends(get_current_user)):
    """
    בדיקת בריאות - האם התקייה קיימת וניתנת לקריאה
    נדרש אימות
    """
    try:
        health_info = books_service.health_check()
        logger.info(f"User {current_user['username']} checked books health")
        return health_info
    
    except Exception as e:
        logger.error(f"Health check failed for user {current_user['username']}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now()
        }