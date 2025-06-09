from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
from pathlib import Path
import mimetypes
from datetime import datetime



# מודלים של Pydantic
class BookInfo(BaseModel):
    """מידע על ספר בודד"""
    title: str
    folder: str
    size: int
    modified: datetime
    view_url: str
    download_url: str

class FolderInfo(BaseModel):
    """מידע על תקייה"""
    name: str
    file_count: int
    url: str

class BooksResponse(BaseModel):
    """תגובת רשימת ספרים"""
    status: str
    count: int
    books: List[BookInfo]

class FoldersResponse(BaseModel):
    """תגובת רשימת תקיות"""
    status: str
    count: int
    folders: List[FolderInfo]

class SearchResponse(BaseModel):
    """תגובת חיפוש"""
    status: str
    query: str
    count: int
    books: List[BookInfo]

def get_books_from_directory(directory_path: str) -> List[dict]:
    """
    מחזיר רשימת קבצים מתקייה מסוימת
    """
    books = []
    
    if not os.path.exists(directory_path):
        return books
    
    try:
        # עבור על כל התקיות בנתיב הבסיס
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            
            # אם זה תקייה
            if os.path.isdir(item_path):
                folder_name = item
                
                # חפש קבצים בתקייה
                for file in os.listdir(item_path):
                    file_path = os.path.join(item_path, file)
                    
                    # בדוק שזה קובץ ולא תקייה
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        file_info = {
                            "filename": file,
                            "folder": folder_name,
                            "full_path": file_path,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime)
                        }
                        books.append(file_info)
    
    except Exception as e:
        logger.error(f"Error reading directory {directory_path}: {e}")
    
 