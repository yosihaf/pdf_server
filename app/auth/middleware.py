# החלף את app/auth/middleware.py עם הקוד הזה:

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from .jwt_handler import verify_token

logger = logging.getLogger(__name__)

class JWTMiddleware(BaseHTTPMiddleware):
    """Middleware לבדיקת JWT טוקנים אוטומטית"""
    
    def __init__(self, app, protected_paths: list = None):
        super().__init__(app)
        
        # נתיבים שדורשים אימות
        self.protected_paths = protected_paths or [
            "/api/books",
            "/api/pdf/generate",
            "/api/pdf/download",
        ]
        
        # נתיבים ציבוריים (מדויקים!)
        self.public_paths = [
            "/",
            "/health", 
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/health",
            "/api/books/health",  # רק זה ציבורי, לא כל /api/books
        ]

    async def dispatch(self, request: Request, call_next):
        """בדיקת כל בקשה שמגיעה לשרת"""
        path = request.url.path
        method = request.method
        
        # דלג על בקשות OPTIONS (CORS)
        if method == "OPTIONS":
            return await call_next(request)
        
        # בדוק אם הנתיב ציבורי (בדיקה מדויקת!)
        if self._is_public_path(path):
            logger.debug(f"Public path accessed: {path}")
            return await call_next(request)
        
        # בדוק אם הנתיב דורש הגנה
        if self._is_protected_path(path):
            # בדוק טוקן
            auth_result = await self._validate_token(request)
            
            if not auth_result["valid"]:
                logger.warning(f"Unauthorized access attempt to: {path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": "נדרש טוקן אימות תקף",
                        "error_code": "UNAUTHORIZED",
                        "message": auth_result["message"]
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # הוסף מידע על המשתמש לבקשה
            request.state.user = auth_result["user"]
            logger.info(f"Authorized access: {auth_result['user'].get('username')} -> {path}")
        
        # המשך לטיפול הרגיל בבקשה
        response = await call_next(request)
        return response

    def _is_public_path(self, path: str) -> bool:
        """בדוק אם הנתיב ציבורי - בדיקה מדויקת!"""
        # בדיקה מדויקת עבור נתיבים שלמים
        if path in self.public_paths:
            return True
        
        # בדיקה עבור נתיבים שמתחילים עם נתיב ציבורי
        public_prefixes = ["/docs", "/openapi.json", "/redoc"]
        for prefix in public_prefixes:
            if path.startswith(prefix):
                return True
                
        return False
    
    def _is_protected_path(self, path: str) -> bool:
        """בדוק אם הנתיב מוגן"""
        return any(path.startswith(protected_path) for protected_path in self.protected_paths)
    
    async def _validate_token(self, request: Request) -> dict:
        """
        בדיקת טוקן JWT מההיידר
        מחזיר: {"valid": bool, "user": dict, "message": str}
        """
        try:
            # חפש טוקן בהיידר Authorization
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return {
                    "valid": False, 
                    "user": {}, 
                    "message": "חסר כותרת Authorization"
                }
            
            # בדוק פורמט Bearer
            if not auth_header.startswith("Bearer "):
                return {
                    "valid": False, 
                    "user": {}, 
                    "message": "פורמט טוקן שגוי - נדרש Bearer token"
                }
            
            # חלץ את הטוקן
            token = auth_header.split(" ")[1]
            
            # אמת את הטוקן
            payload = verify_token(token)
            if not payload:
                return {
                    "valid": False, 
                    "user": {}, 
                    "message": "טוקן לא תקף או פג תוקף"
                }
            
            # החזר מידע על המשתמש
            user_info = {
                "username": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "expires": payload.get("exp")
            }
            
            return {
                "valid": True, 
                "user": user_info, 
                "message": "טוקן תקף"
            }
            
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return {
                "valid": False, 
                "user": {}, 
                "message": f"שגיאה בבדיקת הטוקן: {str(e)}"
            }