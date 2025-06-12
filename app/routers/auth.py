from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from datetime import timedelta, datetime
import logging
from dotenv import load_dotenv
import os
import httpx  # <-- גם את זה אם אתה משתמש בו
from ..database.connection import get_db
from ..database.models import User, EmailVerification
from ..auth.jwt_handler import create_access_token, hash_password, verify_password
from ..auth.dependencies import get_current_user
from ..auth.email_validator import EmailValidator
from google_auth_oauthlib.flow import Flow
load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth", 
    tags=["authentication"],
    responses={
        401: {"description": "לא מורשה"},
        400: {"description": "בקשה שגויה"}
    }
)
print("=== STARTING SERVER ===")
print(f"GOOGLE_CLIENT_ID: {os.getenv('GOOGLE_CLIENT_ID')}")
print(f"GOOGLE_CLIENT_SECRET: {os.getenv('GOOGLE_CLIENT_SECRET')}")
print("========================")
# מודלים מעודכנים
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    
    @validator('email')
    def validate_email_domain(cls, v):
        if not EmailValidator.is_allowed_domain(v):
            raise ValueError('רק מיילים מדומיין cti.org.il מורשים להירשם')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('הסיסמה חייבת להכיל לפחות 8 תווים')
        return v

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    verification_code: str

class ResendCodeRequest(BaseModel):
    email: EmailStr


# מודלים עבור Google OAuth
class GoogleAuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

# הוספת פונקציות עזר לגוגל OAuth
def create_google_flow():
    """יצירת Google OAuth Flow"""
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")]
        }
    }
    
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=['openid', 'email', 'profile']
    )
    
    # הגדרת redirect URI
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    
    return flow
async def get_google_user_info(access_token: str):
    """קבלת פרטי משתמש מגוגל"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code == 200:
            return response.json()
        return None

# Google OAuth Endpoints
@router.post("/google")
async def google_login():
    """התחלת תהליך אימות Google OAuth"""
    try:
        if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="הגדרות Google OAuth לא מוגדרות כראוי"
            )
        
        flow = create_google_flow()
        flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        
        # יצירת URL לאימות
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account'  # מאפשר לבחור חשבון
        )
        
        logger.info("Google OAuth flow initiated")
        
        return {
            "authorization_url": authorization_url,
            "state": state,
            "message": "העבר אל הקישור לאימות Google"
        }
        
    except Exception as e:
        logger.error(f"Google OAuth initiation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה ביצירת קישור אימות Google"
        )

@router.get("/google/callback")
async def google_callback(code: str = None, state: str = None, error: str = None, db: Session = Depends(get_db)):
    """Callback endpoint לגוגל OAuth"""
    try:
        # בדיקת שגיאות מגוגל
        if error:
            logger.warning(f"Google OAuth error: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"אימות Google נכשל: {error}"
            )
        
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="לא התקבל קוד אימות מגוגל"
            )
        
        # יצירת Flow ולקבלת token
        flow = create_google_flow()
        flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        
        # החלפת הקוד ב-token
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # קבלת פרטי המשתמש מגוגל
        user_info = await get_google_user_info(credentials.token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="לא ניתן לקבל פרטי משתמש מגוגל"
            )
        
        google_email = user_info.get('email')
        google_name = user_info.get('name', '')
        google_id = user_info.get('id')
        
        # בדיקת דומיין מייל אם נדרש
        if not EmailValidator.is_allowed_domain(google_email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="רק מיילים מדומיין cti.org.il מורשים להתחבר"
            )
        
        # חיפוש משתמש קיים או יצירת חדש
        existing_user = db.query(User).filter(User.email == google_email).first()
        
        if existing_user:
            # משתמש קיים - עדכון פרטים אם נדרש
            if not existing_user.is_active:
                existing_user.is_active = True
                db.commit()
            
            user = existing_user
            logger.info(f"Existing user logged in via Google: {user.username}")
        else:
            # יצירת משתמש חדש
            # יצירת username מהשם או מהמייל
            username = google_name.replace(' ', '_') or google_email.split('@')[0]
            
            # בדיקה שה-username לא קיים
            counter = 1
            original_username = username
            while db.query(User).filter(User.username == username).first():
                username = f"{original_username}_{counter}"
                counter += 1
            
            new_user = User(
                username=username,
                email=google_email,
                hashed_password="",  # לא צריך סיסמה לאימות Google
                is_active=True,
                # תוכל להוסיף שדות נוספים כמו google_id אם יש לך במודל
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            user = new_user
            logger.info(f"New user created via Google OAuth: {user.username}")
        
        # יצירת JWT token
        token_data = {
            "sub": user.username,
            "user_id": str(user.id),
            "email": user.email
        }
        
        access_token = create_access_token(token_data)
        
        return {
            "status": "success",
            "message": "התחברות בגוגל הושלמה בהצלחה",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user.username,
                "email": user.email,
                "user_id": user.id
            },
            "auth_method": "google"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בתהליך אימות Google"
        )

@router.get("/google/user-info")
async def get_current_google_user(current_user: User = Depends(get_current_user)):
    """קבלת פרטי המשתמש הנוכחי (לאחר אימות Google או רגיל)"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at if hasattr(current_user, 'created_at') else None
    }

# endpoint עזר לבדיקת הגדרות Google
@router.get("/google/config-check")
async def check_google_config():
    """בדיקה שהגדרות Google מוגדרות כראוי - רק לפיתוח"""
    return {
        "google_client_id_set": bool(os.getenv("GOOGLE_CLIENT_ID")),
        "google_client_secret_set": bool(os.getenv("GOOGLE_CLIENT_SECRET")),
        "google_redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "status": "ready" if (os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")) else "missing_config"
    }




@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """רישום משתמש חדש עם אימות מייל"""
    try:
        # בדיקה שהמשתמש לא קיים
        existing_user = db.query(User).filter(
            (User.username == request.username) | 
            (User.email == request.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="שם משתמש או מייל כבר קיימים"
            )
        
        # בדיקת דומיין מייל
        if not EmailValidator.is_allowed_domain(request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="רק מיילים מדומיין cti.org.il מורשים להירשם"
            )
        
        # מחיקת אימותים קודמים לאותו מייל
        db.query(EmailVerification).filter(
            EmailVerification.email == request.email
        ).delete()
        
        # יצירת קוד אימות
        verification_code = EmailValidator.generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        # שמירת קוד האימות
        email_verification = EmailVerification(
            email=request.email,
            username=request.username,
            verification_code=verification_code,
            expires_at=expires_at
        )
        
        db.add(email_verification)
        db.commit()
        
        # שליחת מייל אימות
        email_sent = EmailValidator.send_verification_email(
            request.email, 
            verification_code, 
            request.username
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="שגיאה בשליחת מייל האימות"
            )
        
        # שמירת פרטי המשתמש זמנית (ללא הפעלה)
        hashed_password = hash_password(request.password)
        temp_user_data = {
            "username": request.username,
            "email": request.email,
            "hashed_password": hashed_password
        }
        
        logger.info(f"Registration initiated for {request.username} ({request.email})")
        
        return {
            "status": "verification_required",
            "message": "נשלח קוד אימות למייל שלך. הקוד תקף למשך 15 דקות.",
            "email": request.email,
            "next_step": "השתמש ב-/api/auth/verify-email כדי להשלים את הרישום"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה ברישום המשתמש"
        )

@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """אימות מייל והשלמת רישום"""
    try:
        # חיפוש קוד האימות
        verification = db.query(EmailVerification).filter(
            EmailVerification.email == request.email,
            EmailVerification.verification_code == request.verification_code,
            EmailVerification.is_verified == False
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="קוד אימות שגוי או לא קיים"
            )
        
        # בדיקת תוקף הקוד
        if datetime.utcnow() > verification.expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="קוד האימות פג תוקף. בקש קוד חדש."
            )
        
        # בדיקה שהמשתמש לא קיים כבר
        existing_user = db.query(User).filter(
            (User.username == verification.username) | 
            (User.email == verification.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="המשתמש כבר קיים במערכת"
            )
        
        # יצירת המשתמש הסופי
        new_user = User(
            username=verification.username,
            email=verification.email,
            hashed_password=hash_password("temp_password_will_be_set"),  # נדרוש הגדרת סיסמה
            is_active=True
        )
        
        db.add(new_user)
        
        # סימון האימות כמושלם
        verification.is_verified = True
        verification.verified_at = datetime.utcnow()
        
        db.commit()
        db.refresh(new_user)
        
        # יצירת טוקן גישה
        token_data = {
            "sub": new_user.username,
            "user_id": str(new_user.id),
            "email": new_user.email
        }
        
        access_token = create_access_token(token_data)
        
        logger.info(f"Email verified and user created: {new_user.username}")
        
        return {
            "status": "success",
            "message": "האימות הושלם בהצלחה! המשתמש נוצר.",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": new_user.username,
                "email": new_user.email,
                "user_id": new_user.id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה באימות המייל"
        )

@router.post("/resend-code")
async def resend_verification_code(request: ResendCodeRequest, db: Session = Depends(get_db)):
    """שליחה מחדש של קוד אימות"""
    try:
        # חיפוש האימות הקיים
        verification = db.query(EmailVerification).filter(
            EmailVerification.email == request.email,
            EmailVerification.is_verified == False
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="לא נמצא תהליך רישום בהמתנה לאימות עבור מייל זה"
            )
        
        # יצירת קוד חדש
        new_code = EmailValidator.generate_verification_code()
        verification.verification_code = new_code
        verification.created_at = datetime.utcnow()
        verification.expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        db.commit()
        
        # שליחת המייל החדש
        email_sent = EmailValidator.send_verification_email(
            request.email,
            new_code,
            verification.username
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="שגיאה בשליחת קוד האימות החדש"
            )
        
        logger.info(f"Verification code resent to {request.email}")
        
        return {
            "status": "success",
            "message": "קוד אימות חדש נשלח למייל שלך",
            "expires_in_minutes": 15
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend code error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="שגיאה בשליחת קוד אימות חדש"
        )

@router.get("/check-email-domain")
async def check_email_domain(email: str):
    """בדיקה האם מייל מדומיין מורשה - endpoint ציבורי"""
    is_allowed = EmailValidator.is_allowed_domain(email)
    
    return {
        "email": email,
        "is_allowed": is_allowed,
        "allowed_domains": EmailValidator.ALLOWED_DOMAINS,
        "message": "מייל מורשה" if is_allowed else "רק מיילים מדומיין cti.org.il מורשים"
    }