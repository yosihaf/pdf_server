# ===== app/database/connection.py =====
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
    from .models import User  # import כאן כדי למנוע circular import
    Base.metadata.create_all(bind=engine)

# ===== app/database/schemas.py =====
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_active: bool
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# ===== app/routers/auth.py - מלא =====
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from ..database.connection import get_db, init_db
from ..database.models import User
from ..auth.jwt_handler import create_access_token, verify_password, hash_password
from ..auth.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth", 
    tags=["authentication"],
    responses={
        401: {"description": "לא מורשה"},
        400: {"description": "בקשה שגויה"}
    }
)

# מודלים לבקשות
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserInfo(BaseModel):
    username: str
    user_id: str
    email: str

class AuthResponse(BaseModel):
    status: str
    message: str
    data: dict = None

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """התחברות משתמש"""
    try:
        # חיפוש המשתמש במסד הנתונים
        user = db.query(User).filter(User.username == request.username).first()
        
        if not user or not verify_password(request.password, user.hashed_password):
            logger.warning(f"Failed login attempt for username: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="שם משתמש או סיסמה שגויים",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="החשבון אינו פעיל"
            )
        
        # יצירת טוקן
        token_data = {
            "sub": user.username,
            "user_id": str(user.id),
            "email": user.email
        }
        
        access_token = create_access_token(token_data)
        
        logger.info(f"Successful login for user: {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=30 * 60  # 30 דקות
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בהתחברות"
        )

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """רישום משתמש חדש"""
    try:
        # בדיקה שהמשתמש לא קיים
        existing_user = db.query(User).filter(
            (User.username == request.username) | 
            (User.email == request.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="שם משתמש או אימייל כבר קיימים"
            )
        
        # יצירת משתמש חדש
        hashed_password = hash_password(request.password)
        
        new_user = User(
            username=request.username,
            email=request.email,
            hashed_password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {new_user.username}")
        
        return AuthResponse(
            status="success",
            message="משתמש נוצר בהצלחה",
            data={
                "username": new_user.username,
                "email": new_user.email,
                "user_id": new_user.id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה ברישום המשתמש"
        )

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """קבלת מידע על המשתמש הנוכחי"""
    return UserInfo(
        username=current_user["username"],
        user_id=current_user["user_id"],
        email=current_user.get("email", "")
    )

@router.post("/logout")
async def logout():
    """התנתקות"""
    return {"message": "התנתקת בהצלחה"}

@router.get("/health")
async def auth_health():
    """בדיקת בריאות מערכת האימות"""
    return {
        "status": "healthy",
        "service": "authentication",
        "endpoints": ["/login", "/register", "/me", "/logout"]
    }