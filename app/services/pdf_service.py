# app/services/pdf_service.py - שירות חדש לניהול PDF עם מעקב משתמשים

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
    """שירות לניהול משימות PDF עם מעקב משתמשים"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_pdf_task(self, 
                       user_id: int, 
                       wiki_pages: List[str], 
                       book_title: str,
                       base_url: str,
                       is_public: bool = False,
                       description: str = None) -> PDFTask:
        """יצירת משימת PDF חדשה"""
        
        task_id = str(uuid.uuid4())
        
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
        
        logger.info(f"Created PDF task {task_id} for user {user_id} (public: {is_public})")
        return pdf_task
    
    def update_task_status(self, 
                          task_id: str, 
                          status: str, 
                          message: str = None,
                          filename: str = None,
                          file_path: str = None,
                          file_size: int = None) -> bool:
        """עדכון סטטוס משימה"""
        
        task = self.db.query(PDFTask).filter(PDFTask.task_id == task_id).first()
        if not task:
            return False
        
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
        logger.info(f"Updated task {task_id} status to {status}")
        return True
    
    def get_task_by_id(self, task_id: str) -> Optional[PDFTask]:
        """קבלת משימה לפי מזהה"""
        return self.db.query(PDFTask).filter(PDFTask.task_id == task_id).first()
    
    def get_user_tasks(self, user_id: int, limit: int = 50) -> List[PDFTask]:
        """קבלת כל המשימות של משתמש"""
        return (self.db.query(PDFTask)
                .filter(PDFTask.user_id == user_id)
                .order_by(PDFTask.created_at.desc())
                .limit(limit)
                .all())
    
    def get_task_with_user(self, task_id: str) -> Optional[PDFTask]:
        """קבלת משימה עם פרטי המשתמש"""
        return (self.db.query(PDFTask)
                .join(User)
                .filter(PDFTask.task_id == task_id)
                .first())
    
    def verify_task_ownership(self, task_id: str, user_id: int) -> bool:
        """בדיקה שהמשימה שייכת למשתמש"""
        task = self.get_task_by_id(task_id)
        return task and task.user_id == user_id
    
    def get_public_pdfs(self, limit: int = 50) -> List[PDFTask]:
        """קבלת כל הקבצים הציבוריים"""
        return (self.db.query(PDFTask)
                .filter(PDFTask.is_public == True)
                .filter(PDFTask.status == "completed")
                .order_by(PDFTask.created_at.desc())
                .limit(limit)
                .all())
    
    def search_public_pdfs(self, query: str, limit: int = 20) -> List[PDFTask]:
        """חיפוש בקבצים ציבוריים"""
        return (self.db.query(PDFTask)
                .filter(PDFTask.is_public == True)
                .filter(PDFTask.status == "completed")
                .filter(PDFTask.book_title.contains(query))
                .order_by(PDFTask.created_at.desc())
                .limit(limit)
                .all())
    
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
        
        logger.info(f"Updated privacy for task {task_id}: public={is_public}")
        return True
    
    def can_access_task(self, task_id: str, user_id: int = None) -> bool:
        """בדיקה אם ניתן לגשת למשימה"""
        task = self.get_task_by_id(task_id)
        if not task:
            return False
        
        # אם הקובץ ציבורי - כולם יכולים לגשת
        if task.is_public and task.status == "completed":
            return True
        
        # אם לא ציבורי - רק הבעלים יכול לגשת
        return user_id and task.user_id == user_id
        """מחיקת משימות ישנות"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        old_tasks = (self.db.query(PDFTask)
                    .filter(PDFTask.created_at < cutoff_date)
                    .all())
        
        count = len(old_tasks)
        
        for task in old_tasks:
            # מחק את הקובץ מהדיסק אם קיים
            if task.file_path and os.path.exists(task.file_path):
                try:
                    os.remove(task.file_path)
                    logger.info(f"Deleted file: {task.file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {task.file_path}: {e}")
            
            self.db.delete(task)
        
        self.db.commit()
        logger.info(f"Deleted {count} old tasks")
        return count