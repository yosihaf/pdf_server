from pydantic import BaseModel
from typing import List
from datetime import datetime

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

class HealthResponse(BaseModel):
    """תגובת בדיקת בריאות"""
    status: str
    base_path: str
    folder_count: int
    timestamp: datetime
    message: str = None