# app/services/pdf_service.py - עם מעקב יוצר מלא

from sqlalchemy.orm import Session
from ..database.models import PDFTask, User
from ..database.connection import get_db
from typing import List, Optional
import json
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PDFService:
    """שירות לניהול משימות PDF עם מעקב יוצרים"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_pdf_task(self, 
                       user_id: int, 
                       wiki_pages: List[str], 
                       book_title: str,
                       base_url: str,
                       is_public: bool = False,
                       description: str = None) -> PDFTask:
        """יצירת משימת PDF חדשה עם שמירת יוצר"""
        
        task_id = str(uuid.uuid4())
        
        # קבלת פרטי היוצר
        creator = self.db.query(User).filter(User.id == user_id).first()
        if not creator:
            raise ValueError(f"User with ID {user_id} not found")
        
        # יצירת רשומה במסד הנתונים
        pdf_task = PDFTask(
            task_id=task_id,
            user_id=user_id,
            book_title=book_title,
            wiki_pages=json.dumps(wiki_pages, ensure_ascii=False),
            base_url=base_url,
            is_public=is_public,
            description=description,
            status="pending",
            message="המשימה נוצרה ומחכה להתחלה"
        )
        
        self.db.add(pdf_task)
        self.db.commit()
        self.db.refresh(pdf_task)
        
        logger.info(f"Created PDF task {task_id} for user {creator.username} (ID: {user_id}, public: {is_public})")
        return pdf_task
    
    def get_task_with_creator(self, task_id: str) -> Optional[dict]:
        """קבלת משימה עם פרטי היוצר"""
        task = (self.db.query(PDFTask)
                .join(User)
                .filter(PDFTask.task_id == task_id)
                .first())
        
        if not task:
            return None
        
        return {
            "task": task,
            "creator": {
                "id": task.user.id,
                "username": task.user.username,
                "email": task.user.email,
                "created_at": task.user.created_at
            }
        }
    
    def get_public_pdfs_with_creators(self, limit: int = 50) -> List[dict]:
        """קבלת כל הקבצים הציבוריים עם פרטי היוצרים"""
        tasks = (self.db.query(PDFTask)
                .join(User)
                .filter(PDFTask.is_public == True)
                .filter(PDFTask.status == "completed")
                .order_by(PDFTask.created_at.desc())
                .limit(limit)
                .all())
        
        result = []
        for task in tasks:
            result.append({
                "task_id": task.task_id,
                "book_title": task.book_title,
                "description": task.description,
                "created_at": task.created_at,
                "file_size": task.file_size,
                "filename": task.filename,
                "creator": {
                    "username": task.user.username,
                    "user_id": task.user.id
                },
                "wiki_pages": json.loads(task.wiki_pages) if task.wiki_pages else [],
                "view_url": f"/api/public/view/{task.task_id}/{task.filename}",
                "download_url": f"/api/public/download/{task.task_id}/{task.filename}"
            })
        
        return result
    
    def search_public_pdfs_with_creators(self, query: str, limit: int = 20) -> List[dict]:
        """חיפוש בקבצים ציבוריים עם פרטי יוצרים"""
        tasks = (self.db.query(PDFTask)
                .join(User)
                .filter(PDFTask.is_public == True)
                .filter(PDFTask.status == "completed")
                .filter(
                    (PDFTask.book_title.contains(query)) |
                    (PDFTask.description.contains(query)) |
                    (User.username.contains(query))
                )
                .order_by(PDFTask.created_at.desc())
                .limit(limit)
                .all())
        
        result = []
        for task in tasks:
            result.append({
                "task_id": task.task_id,
                "book_title": task.book_title,
                "description": task.description,
                "created_at": task.created_at,
                "file_size": task.file_size,
                "filename": task.filename,
                "creator": {
                    "username": task.user.username,
                    "user_id": task.user.id
                },
                "view_url": f"/api/public/view/{task.task_id}/{task.filename}",
                "download_url": f"/api/public/download/{task.task_id}/{task.filename}"
            })
        
        return result
    
    def get_user_tasks_detailed(self, user_id: int, limit: int = 50) -> List[dict]:
        """קבלת כל המשימות של משתמש עם פרטים מלאים"""
        tasks = (self.db.query(PDFTask)
                .join(User)
                .filter(PDFTask.user_id == user_id)
                .order_by(PDFTask.created_at.desc())
                .limit(limit)
                .all())
        
        result = []
        for task in tasks:
            result.append({
                "task_id": task.task_id,
                "book_title": task.book_title,
                "description": task.description,
                "status": task.status,
                "message": task.message,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "filename": task.filename,
                "file_size": task.file_size,
                "is_public": task.is_public,
                "wiki_pages": json.loads(task.wiki_pages) if task.wiki_pages else [],
                "download_url": f"/api/pdf/download/{task.task_id}/{task.filename}" if task.filename else None,
                "view_url": f"/api/pdf/view/{task.task_id}/{task.filename}" if task.filename else None,
                "public_url": f"/api/public/view/{task.task_id}/{task.filename}" if task.is_public and task.filename else None
            })
        
        return result
    
    def get_creator_stats(self, user_id: int) -> dict:
        """סטטיסטיקות יצירת ספרים למשתמש"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}
        
        total_tasks = self.db.query(PDFTask).filter(PDFTask.user_id == user_id).count()
        completed_tasks = self.db.query(PDFTask).filter(
            PDFTask.user_id == user_id,
            PDFTask.status == "completed"
        ).count()
        public_tasks = self.db.query(PDFTask).filter(
            PDFTask.user_id == user_id,
            PDFTask.is_public == True,
            PDFTask.status == "completed"
        ).count()
        
        return {
            "username": user.username,
            "user_id": user_id,
            "total_books_created": total_tasks,
            "completed_books": completed_tasks,
            "public_books": public_tasks,
            "success_rate": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
            "member_since": user.created_at
        }
    
    def update_task_status(self, 
                          task_id: str, 
                          status: str, 
                          message: str = None,
                          filename: str = None,
                          file_path: str = None,
                          file_size: int = None) -> bool:
        """עדכון סטטוס משימה עם logging מפורט"""
        
        task = self.db.query(PDFTask).filter(PDFTask.task_id == task_id).first()
        if not task:
            return False
        
        # קבל את שם היוצר לlogging
        creator = self.db.query(User).filter(User.id == task.user_id).first()
        creator_name = creator.username if creator else f"UserID:{task.user_id}"
        
        task.status = status
        if message:
            task.message = message
        if filename:
            task.filename = filename
        if file_path:
            task.file_path = file_path
        if file_size:
            task.file_size = file_size
        
        # עדכון זמנים
        if status == "processing":
            task.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            task.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Updated task {task_id} status to '{status}' for user {creator_name} (book: {task.book_title})")
        return True
    
    def verify_task_ownership(self, task_id: str, user_id: int) -> bool:
        """בדיקה שהמשימה שייכת למשתמש"""
        task = self.db.query(PDFTask).filter(PDFTask.task_id == task_id).first()
        return task and task.user_id == user_id
    
    def can_access_task(self, task_id: str, user_id: int = None) -> bool:
        """בדיקה אם ניתן לגשת למשימה"""
        task = self.db.query(PDFTask).filter(PDFTask.task_id == task_id).first()
        if not task:
            return False
        
        # אם הקובץ ציבורי - כולם יכולים לגשת
        if task.is_public and task.status == "completed":
            return True
        
        # אם לא ציבורי - רק הבעלים יכול לגשת
        return user_id and task.user_id == user_id
    
    def get_task_by_id(self, task_id: str) -> Optional[PDFTask]:
        """קבלת משימה לפי מזהה"""
        return self.db.query(PDFTask).filter(PDFTask.task_id == task_id).first()
    
    def update_privacy_setting(self, task_id: str, user_id: int, is_public: bool) -> bool:
        """עדכון הגדרת פרטיות של קובץ"""
        task = self.db.query(PDFTask).filter(
            PDFTask.task_id == task_id,
            PDFTask.user_id == user_id
        ).first()
        
        if not task:
            return False
        
        task.is_public = is_public
        self.db.commit()
        
        # קבל שם יוצר לlogging
        creator = self.db.query(User).filter(User.id == user_id).first()
        creator_name = creator.username if creator else f"UserID:{user_id}"
        
        logger.info(f"Updated privacy for task {task_id} by {creator_name}: public={is_public} (book: {task.book_title})")
        return True