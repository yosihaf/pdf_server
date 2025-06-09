# app/auth/jwt_handler.py - גרסה מתוקנת ומלאה

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"

# ⏰ זמן תוקף הטוקן - כרגע 30 דקות
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = None):
    """יצירת טוקן גישה עם זמן תוקף"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # ברירת מחדל - 30 דקות
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """יצירת refresh token עם תוקף ארוך יותר - 7 ימים"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "type": "refresh"  # סימון שזה refresh token
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """אימות טוקן והחזרת הנתונים"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_token_expiry_info(token: str) -> dict:
    """קבלת מידע על תוקף הטוקן"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            now = datetime.utcnow()
            time_left = exp_datetime - now
            
            return {
                "expires_at": exp_datetime.isoformat(),
                "time_left_minutes": int(time_left.total_seconds() / 60),
                "is_expired": time_left.total_seconds() <= 0
            }
    except:
        pass
    
    return {"error": "לא ניתן לפענח את הטוקן"}

# הגדרות זמן תוקף שונות לפי סוג משתמש
TOKEN_EXPIRY_SETTINGS = {
    "regular_user": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)),
    "admin": int(os.getenv("ADMIN_TOKEN_EXPIRE_MINUTES", 120)),
    "premium": int(os.getenv("PREMIUM_TOKEN_EXPIRE_MINUTES", 480)),
    "api_client": int(os.getenv("API_TOKEN_EXPIRE_MINUTES", 1440))
}