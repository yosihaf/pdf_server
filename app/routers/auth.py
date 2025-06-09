from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from ..auth.jwt_handler import create_access_token, verify_password, hash_password
from ..database.connection import get_db

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/login")
async def login(username: str, password: str):
    # בדיקת משתמש במסד נתונים
    # יצירת טוקן
    token = create_access_token({"sub": username})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register")
async def register(username: str, email: str, password: str):
    # יצירת משתמש חדש
    hashed_pwd = hash_password(password)
    # שמירה במסד נתונים
    return {"message": "משתמש נוצר בהצלחה"}