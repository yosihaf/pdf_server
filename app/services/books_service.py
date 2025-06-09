import os
import mimetypes
from typing import List, Tuple
from datetime import datetime
import logging

from ..models.books import BookInfo, FolderInfo

logger = logging.getLogger(__name__)

class BooksService:
    """שירות לניהול ספרים"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.base_path = os.getenv("BOOKS_PATH", "/app/output")  # דורס את הפרמטר
    
    def _get_books_from_directory(self) -> List[dict]:
        """
        מחזיר רשימת קבצים מתקייה מסוימת
        """
        books = []
        
        if not os.path.exists(self.base_path):
            return books
        
        try:
            # עבור על כל התקיות בנתיב הבסיס
            for item in os.listdir(self.base_path):
                item_path = os.path.join(self.base_path, item)
                
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
            logger.error(f"Error reading directory {self.base_path}: {e}")
            raise
        
        return books
    
    def get_all_books(self) -> List[BookInfo]:
        """
        מחזיר את כל הספרים מכל התקיות
        """
        books = self._get_books_from_directory()
        
        # יצירת URLs לצפייה
        books_with_urls = []
        for book in books:
            book_data = BookInfo(
                title=book["filename"],
                folder=book["folder"],
                size=book["size"],
                modified=book["modified"],
                view_url=f"/api/books/view/{book['folder']}/{book['filename']}",
                download_url=f"/api/books/download/{book['folder']}/{book['filename']}"
            )
            books_with_urls.append(book_data)
        
        return books_with_urls
    
    def get_books_by_folder(self, folder_name: str) -> List[BookInfo]:
        """
        מחזיר ספרים מתקייה מסוימת
        """
        folder_path = os.path.join(self.base_path, folder_name)
        
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder {folder_name} not found")
        
        books = []
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                book_data = BookInfo(
                    title=file,
                    folder=folder_name,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    view_url=f"/api/books/view/{folder_name}/{file}",
                    download_url=f"/api/books/download/{folder_name}/{file}"
                )
                books.append(book_data)
        
        return books
    
    def get_file_info(self, folder_name: str, filename: str) -> Tuple[str, str]:
        """
        מחזיר נתיב קובץ וסוג MIME
        """
        file_path = os.path.join(self.base_path, folder_name, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {folder_name}/{filename} not found")
        
        # קבע את סוג הקובץ
        mimetype, _ = mimetypes.guess_type(file_path)
        
        return file_path, mimetype
    
    def get_folders(self) -> List[FolderInfo]:
        """
        מחזיר רשימת כל התקיות
        """
        folders = []
        
        if os.path.exists(self.base_path):
            for item in os.listdir(self.base_path):
                item_path = os.path.join(self.base_path, item)
                
                if os.path.isdir(item_path):
                    # ספור כמה קבצים יש בתקייה
                    file_count = len([f for f in os.listdir(item_path) 
                                    if os.path.isfile(os.path.join(item_path, f))])
                    
                    folder_info = FolderInfo(
                        name=item,
                        file_count=file_count,
                        url=f"/api/books/folder/{item}"
                    )
                    folders.append(folder_info)
        
        return folders
    
    def search_books(self, query: str, search_in: str = "title", limit: int = 50) -> List[BookInfo]:
        """
        חיפוש ספרים לפי מילות מפתח
        """
        if not query.strip():
            return []
        
        # קבלת כל הספרים פעם אחת
        all_books = self.get_all_books()
        
        query_words = query.lower().strip().split()
        filtered_books = []
        
        for book in all_books:
            found = False
            
            if search_in == "title" or search_in == "all":
                # חיפוש בכותרת
                title_lower = book.title.lower()
                if any(word in title_lower for word in query_words):
                    found = True
            
            if not found and (search_in == "folder" or search_in == "all"):
                # חיפוש בשם תיקיה
                folder_lower = book.folder.lower()
                if any(word in folder_lower for word in query_words):
                    found = True
            
            if found:
                filtered_books.append(book)
        
        # מיון לפי רלוונטיות
        def relevance_score(book):
            title_lower = book.title.lower()
            score = 0
            
            for word in query_words:
                if title_lower.startswith(word):
                    score += 100
                elif word in title_lower:
                    score += 50
            
            return score
        
        filtered_books.sort(key=relevance_score, reverse=True)
        return filtered_books[:limit]

    def get_search_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """
        מחזיר הצעות חיפוש אוטומטי
        """
        if len(query) < 2:
            return []
        
        all_books = self.get_all_books()
        suggestions = set()
        query_lower = query.lower()
        
        for book in all_books:
            title = book.title.lower()
            
            # הצעות מבוססות על תחילת המילים
            title_words = title.replace('.pdf', '').replace('_', ' ').split()
            
            for word in title_words:
                if word.startswith(query_lower) and len(word) > len(query):
                    suggestions.add(word)
            
            # הצעות מבוססות על כותרות שמכילות את המילה
            if query_lower in title:
                clean_title = title.replace('.pdf', '').replace('_', ' ')
                suggestions.add(clean_title)
        
        # מיון לפי אורך (קצרים ראשון)
        sorted_suggestions = sorted(list(suggestions), key=len)
        return sorted_suggestions[:limit]

   
    def health_check(self) -> dict:
        """
        בדיקת בריאות - האם התקייה קיימת וניתנת לקריאה
        """
        if os.path.exists(self.base_path) and os.access(self.base_path, os.R_OK):
            folder_count = len([item for item in os.listdir(self.base_path) 
                              if os.path.isdir(os.path.join(self.base_path, item))])
            
            return {
                "status": "healthy",
                "base_path": self.base_path,
                "folder_count": folder_count,
                "timestamp": datetime.now()
            }
        else:
            return {
                "status": "unhealthy",
                "message": "התקייה לא קיימת או לא ניתנת לקריאה",
                "base_path": self.base_path,
                "timestamp": datetime.now()
            }