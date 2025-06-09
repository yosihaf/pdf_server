# app/routers/auth.py - עם ניהול זמני תוקף מתקדם

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta
import logging

from ..database.connection import get_db
from ..database.models import User
from ..auth.jwt_handler import (
    create_access_token, create_refresh_token, verify_password, 
    hash_password, get_token_expiry_info, TOKEN_EXPIRY_SETTINGS
)
from ..auth.dependencies import get_current_user

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
    remember_me: bool = False  # האם לזכור אותי (טוקן ארוך יותר)

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = None
    token_type: str
    expires_in: int  # בדקות
    expires_at: str  # זמן מדויק

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenInfo(BaseModel):
    expires_at: str
    time_left_minutes: int
    is_expired: bool

class UserInfo(BaseModel):
    username: str
    user_id: str
    email: str
    is_admin: bool = False

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """התחברות עם אפשרות לבחור זמן תוקף"""
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
        
        # קבע זמן תוקף לפי סוג המשתמש והעדפות
        if request.remember_me:
            expire_minutes = TOKEN_EXPIRY_SETTINGS.get("premium", 480)  # 8 שעות
        else:
            # בדוק אם המשתמש הוא מנהל
            is_admin = user.username in ["admin", "manager", "root"]
            expire_minutes = TOKEN_EXPIRY_SETTINGS.get(
                "admin" if is_admin else "regular_user", 30
            )
        
        # יצירת טוקן
        token_data = {
            "sub": user.username,
            "user_id": str(user.id),
            "email": user.email,
            "is_admin": is_admin
        }
        
        access_token = create_access_token(
            token_data, 
            expires_delta=timedelta(minutes=expire_minutes)
        )
        
        # יצירת refresh token אם נבקש
        refresh_token = None
        if request.remember_me:
            refresh_token = create_refresh_token(token_data)
        
        from datetime import datetime
        expires_at = (datetime.utcnow() + timedelta(minutes=expire_minutes)).isoformat()
        
        logger.info(f"Successful login for user: {user.username} (expires in {expire_minutes} minutes)")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expire_minutes,
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בהתחברות"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """חידוש טוקן באמצעות refresh token"""
    try:
        from ..auth.jwt_handler import verify_token
        
        # אמת את ה-refresh token
        payload = verify_token(request.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token לא תקף"
            )
        
        # יצור טוקן חדש
        token_data = {
            "sub": payload.get("sub"),
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "is_admin": payload.get("is_admin", False)
        }
        
        expire_minutes = TOKEN_EXPIRY_SETTINGS.get("regular_user", 30)
        access_token = create_access_token(
            token_data,
            expires_delta=timedelta(minutes=expire_minutes)
        )
        
        from datetime import datetime
        expires_at = (datetime.utcnow() + timedelta(minutes=expire_minutes)).isoformat()
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expire_minutes,
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="שגיאה בחידוש הטוקן"
        )

@router.get("/token-info", response_model=TokenInfo)
async def get_token_info(current_user: dict = Depends(get_current_user)):
    """קבלת מידע על תוקף הטוקן הנוכחי"""
    # הטוקן כבר אומת ב-dependency, אז נחזיר מידע כללי
    from fastapi import Request
    
    return TokenInfo(
        expires_at="ידוע רק מהטוקן עצמו",
        time_left_minutes=0,  # נדרש גישה ישירה לטוקן
        is_expired=False
    )

@router.post("/register")
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
        
        return {
            "status": "success",
            "message": "משתמש נוצר בהצלחה",
            "data": {
                "username": new_user.username,
                "email": new_user.email,
                "user_id": new_user.id
            }
        }
        
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
        email=current_user.get("email", ""),
        is_admin=current_user.get("is_admin", False)
    )

@router.post("/logout")
async def logout():
    """התנתקות - הטוקן יפסיק לעבוד אוטומטית"""
    return {"message": "התנתקת בהצלחה"}

@router.get("/settings")
async def get_auth_settings():
    """קבלת הגדרות זמני תוקף"""
    return {
        "token_expiry_minutes": TOKEN_EXPIRY_SETTINGS,
        "description": {
            "regular_user": "משתמש רגיל",
            "admin": "מנהל מערכת", 
            "premium": "משתמש עם 'זכור אותי'",
            "api_client": "קליינט API"
        }
    }

@router.get("/health")
async def auth_health():
    """בדיקת בריאות מערכת האימות"""
    return {
        "status": "healthy",
        "service": "authentication",
        "features": ["login", "register", "refresh_token", "token_info"],
        "default_token_expiry_minutes": TOKEN_EXPIRY_SETTINGS["regular_user"]
    }