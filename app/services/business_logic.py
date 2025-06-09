# ===== app/services/business_logic.py =====
from sqlalchemy.orm import Session
from ..database.models import User
from ..auth.jwt_handler import hash_password, verify_password, create_access_token
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class AuthService:
    """שירות אימות משתמשים"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """אימות משתמש"""
        user = self.db.query(User).filter(User.username == username).first()
        
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
            
        return user
    
    def create_user(self, username: str, email: str, password: str) -> User:
        """יצירת משתמש חדש"""
        # בדיקה שהמשתמש לא קיים
        existing_user = self.db.query(User).filter(
            (User.username == username) | 
            (User.email == email)
        ).first()
        
        if existing_user:
            raise ValueError("משתמש או אימייל כבר קיימים")
        
        # יצירת משתמש חדש
        hashed_password = hash_password(password)
        
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        logger.info(f"New user created: {new_user.username}")
        return new_user
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """קבלת משתמש לפי שם משתמש"""
        return self.db.query(User).filter(User.username == username).first()
    
    def create_access_token_for_user(self, user: User) -> str:
        """יצירת טוקן גישה למשתמש"""
        token_data = {
            "sub": user.username,
            "user_id": str(user.id),
            "email": user.email
        }
        
        return create_access_token(token_data)

class BooksBusinessLogic:
    """לוגיקה עסקית לניהול ספרים"""
    
    @staticmethod
    def validate_book_access(user_id: str, book_path: str) -> bool:
        """בדיקת הרשאות גישה לספר"""
        # כאן תוכל להוסיף לוגיקה לבדיקת הרשאות
        # לדוגמה: בדיקה אם המשתמש רשאי לגשת לתיקיה מסוימת
        return True
    
    @staticmethod
    def log_book_access(user_id: str, book_title: str, action: str):
        """רישום פעולות על ספרים"""
        logger.info(f"User {user_id} performed {action} on book: {book_title}")

class PDFBusinessLogic:
    """לוגיקה עסקית ליצירת PDF"""
    
    @staticmethod
    def validate_pdf_request(user_id: str, wiki_pages: list) -> bool:
        """בדיקת תקינות בקשת PDF"""
        if not wiki_pages:
            return False
        
        # בדיקת מגבלות למשתמש
        if len(wiki_pages) > 50:  # מגבלה של 50 דפים
            return False
            
        return True
    
    @staticmethod
    def log_pdf_creation(user_id: str, task_id: str, page_count: int):
        """רישום יצירת PDF"""
        logger.info(f"User {user_id} created PDF task {task_id} with {page_count} pages")