# app/database/models.py - הוסף את המודל הזה

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .connection import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # קשר למשימות PDF
    pdf_tasks = relationship("PDFTask", back_populates="user")

class PDFTask(Base):
    """מודל למעקב אחר משימות PDF"""
    __tablename__ = "pdf_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)  # UUID של המשימה
    user_id = Column(Integer, ForeignKey("users.id"))  # מזהה המשתמש
    
    # פרטי המשימה
    book_title = Column(String)
    wiki_pages = Column(Text)  # JSON string של הדפים
    base_url = Column(String)
    
    # הגדרות פרטיות
    is_public = Column(Boolean, default=False)  # האם הקובץ ציבורי
    description = Column(Text)  # תיאור הקובץ (אופציונלי)
    
    # סטטוס המשימה
    status = Column(String, default="pending")  # pending, processing, completed, failed
    message = Column(Text)
    
    # פרטי הקובץ
    filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    
    # זמנים
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # קשר למשתמש
    user = relationship("User", back_populates="pdf_tasks")