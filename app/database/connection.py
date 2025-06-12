# app/database/connection.py - עבור SQLAlchemy 1.4.53

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

# הגדרת מסד נתונים (SQLite לפיתוח)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency לקבלת session של מסד נתונים"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """יצירת הטבלאות"""
    from .models import User, PDFTask, EmailVerification  # import כאן כדי למנוע circular import
    Base.metadata.create_all(bind=engine)