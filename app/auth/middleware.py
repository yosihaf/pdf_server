# app/auth/middleware.py
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from .jwt_handler import verify_token

logger = logging.getLogger(__name__)

class JWTMiddleware(BaseHTTPMiddleware):
    """
    Middleware לבדיקת JWT טוקנים אוטומטית
    """
    
    def __init__(self, app, protected_paths: list = None):
        super().__init__(app)
        # נתיבים שדורשים אימות (אפשר להגדיר מה מוגן ומה לא)
        self.protected_paths = protected_paths or [
            "/api/books",
            "/api/pdf/generate",
            "/api/pdf/download",
        ]
        
        # נתיבים שלא דורשים אימות
        self.public_paths = [
            "/",
            "/health", 
            "/docs",
            "/openapi.json",
            "/api/auth/login",
            "/api/auth/register",
            "/api/books/health",  # בדיקת בריאות ציבורית
        ]

    async def dispatch(self, request: Request, call_next):
        """
        בדיקת כל בקשה שמגיעה לשרת
        """
        path = request.url.path
        method = request.method
        
        # דלג על בקשות OPTIONS (CORS)
        if method == "OPTIONS":
            return await call_next(request)
        
        # בדוק אם הנתיב ציבורי
        if self._is_public_path(path):
            logger.info(f"Public path accessed: {path}")
            return await call_next(request)
        
        # בדוק אם הנתיב דורש הגנה
        if self._is_protected_path(path):
            # בדוק טוקן
            token_valid, user_info = await self._validate_token(request)
            
            if not token_valid:
                logger.warning(f"Unauthorized access attempt to: {path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": "אין הרשאה - נדרש טוקן תקף",
                        "error_code": "UNAUTHORIZED"
                    }
                )
            
            # הוסף מידע על המשתמש לבקשה
            request.state.user = user_info
            logger.info(f"Authorized access: {user_info.get('username')} -> {path}")
        
        # המשך לטיפול הרגיל בבקשה
        response = await call_next(request)
        return response

    def _is_public_path(self, path: str) -> bool:
        """בדוק אם הנתיב ציבורי"""
        return any(path.startswith(public_path) for public_path in self.public_paths)
    
    def _is_protected_path(self, path: str) -> bool:
        """בדוק אם הנתיב מוגן"""
        return any(path.startswith(protected_path) for protected_path in self.protected_paths)
    
    async def _validate_token(self, request: Request) -> tuple[bool, dict]:
        """
        בדיקת טוקן JWT מההיידר
        מחזיר: (האם תקף, מידע על המשתמש)
        """
        try:
            # חפש טוקן בהיידר Authorization
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return False, {}
            
            # בדוק פורמט Bearer
            if not auth_header.startswith("Bearer "):
                return False, {}
            
            # חלץ את הטוקן
            token = auth_header.split(" ")[1]
            
            # אמת את הטוקן
            payload = verify_token(token)
            if not payload:
                return False, {}
            
            # החזר מידע על המשתמש
            user_info = {
                "username": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "expires": payload.get("exp")
            }
            
            return True, user_info
            
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return False, {}