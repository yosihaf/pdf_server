from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse
from typing import List
import logging
from datetime import datetime

from ..models.books import BookInfo, BooksResponse, FolderInfo, FoldersResponse, SearchResponse
from ..services.books_service import BooksService
from ..config import BASE_BOOKS_PATH

# הגדרת הRouter
router = APIRouter(
    prefix="/api/books",
    tags=["books-management"],
    responses={404: {"description": "משאב לא נמצא"}},
)

logger = logging.getLogger(__name__)

# יצירת instance של השירות
books_service = BooksService(BASE_BOOKS_PATH)


@router.get("", response_model=BooksResponse)
async def get_all_books():
    """
    מחזיר את כל הספרים מכל התקיות
    """
    try: 
        books = books_service.get_all_books()
        logger.info(f"Retrieved {len(books)} books")
        
        return BooksResponse(
            status="success",
            count=len(books),
            books=books
        )
    
    except Exception as e:
        logger.error(f"Error getting all books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת רשימת הספרים"
        )

@router.get("/folder/{folder_name}", response_model=BooksResponse)
async def get_books_by_folder(folder_name: str):
    """
    מחזיר ספרים מתקייה מסוימת
    """
    try:
        books = books_service.get_books_by_folder(folder_name)
        logger.info(f"Retrieved {len(books)} books from folder {folder_name}")
        
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
        logger.error(f"Error getting books from folder {folder_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת ספרים מהתקייה"
        )

@router.get("/folders", response_model=FoldersResponse)
async def get_folders():
    """
    מחזיר רשימת כל התקיות
    """
    try:
        folders = books_service.get_folders()
        logger.info(f"Retrieved {len(folders)} folders")
        
        return FoldersResponse(
            status="success",
            count=len(folders),
            folders=folders
        )
    
    except Exception as e:
        logger.error(f"Error getting folders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת רשימת התקיות"
        )

@router.get("/search", response_model=SearchResponse)
async def search_books(
    q: str = Query(..., description="מילת חיפוש"),
    search_in: str = Query("title", description="חיפוש ב: title, folder, all"),
    limit: int = Query(50, description="מספר תוצאות מקסימלי")
):
    """
    חיפוש ספרים לפי מילות מפתח
    """
    try:
        if not q.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="מילת חיפוש נדרשת"
            )
        
        # החיפוש מתבצע כולו בservice
        filtered_books = books_service.search_books(q, search_in, limit)
        
        logger.info(f"Search for '{q}' returned {len(filtered_books)} results")
        
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
        logger.error(f"Error searching books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בחיפוש ספרים"
        )


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="תחילת מילת חיפוש"),
    limit: int = Query(10, description="מספר הצעות מקסימלי")
):
    """
    הצעות חיפוש אוטומטי
    """
    try:
        suggestions = books_service.get_search_suggestions(q, limit)
        
        return {
            "status": "success",
            "query": q,
            "suggestions": suggestions
        }
    
    except Exception as e:
        logger.error(f"Error getting search suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בקבלת הצעות חיפוש"
        )

        
@router.get("/health")
async def health_check():
    """
    בדיקת בריאות - האם התקייה קיימת וניתנת לקריאה
    """
    try:
        health_info = books_service.health_check()
        return health_info
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now()
        }