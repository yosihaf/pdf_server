# app/auth/dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .jwt_handler import verify_token

# יצירת Bearer scheme
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency לקבלת המשתמש הנוכחי
    שימוש: @router.get("/protected", dependencies=[Depends(get_current_user)])
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="טוקן לא תקף",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "username": payload.get("sub"),
        "user_id": payload.get("user_id")
    }

async def get_current_user_optional(request: Request):
    """
    Dependency אופציונלי - מחזיר None אם אין טוקן
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = verify_token(token)
        
        if payload:
            return {
                "username": payload.get("sub"),
                "user_id": payload.get("user_id")
            }
    except:
        pass
    
    return None