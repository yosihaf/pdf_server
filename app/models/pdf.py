# app/models/pdf.py - מודלים מעודכנים

from pydantic import BaseModel, Field
from typing import List, Optional

class PDFRequest(BaseModel):
    """מודל לבקשת יצירת PDF"""
    wiki_pages: List[str] = Field(..., 
                                  description="רשימת ערכי ויקי להמרה")
    book_title: Optional[str] = Field("המכלול ערים", 
                                     description="כותרת הספר")
    base_url: Optional[str] = Field("https://dev.hamichlol.org.il/w/rest.php/v1/page", 
                                   description="כתובת בסיס לערכי הויקי")
    is_public: Optional[bool] = Field(False, 
                                     description="האם הקובץ ציבורי לצפייה")
    description: Optional[str] = Field(None, 
                                      description="תיאור הקובץ")

class PDFResponse(BaseModel):
    """מודל לתשובת יצירת PDF"""
    task_id: str = Field(..., 
                        description="מזהה המשימה")
    status: str = Field(..., 
                       description="סטטוס המשימה")
    message: str = Field(..., 
                        description="הודעה למשתמש")
    is_public: bool = Field(...,
                           description="האם הקובץ ציבורי")

class PDFStatus(BaseModel):
    """מודל לסטטוס יצירת PDF"""
    task_id: str = Field(..., 
                        description="מזהה המשימה") 
    status: str = Field(..., 
                       description="סטטוס המשימה")
    download_url: Optional[str] = Field(None, 
                                      description="קישור להורדת הקובץ אם מוכן")
    view_url: Optional[str] = Field(None,
                                   description="קישור לצפייה בקובץ")
    public_url: Optional[str] = Field(None,
                                     description="קישור ציבורי לקובץ (אם ציבורי)")
    message: str = Field(..., 
                        description="הודעה למשתמש")
    is_public: bool = Field(...,
                           description="האם הקובץ ציבורי")

class PublicPDFInfo(BaseModel):
    """מידע על קובץ PDF ציבורי"""
    task_id: str
    book_title: str
    description: Optional[str]
    created_at: str
    file_size: Optional[int]
    creator_username: str
    view_url: str
    download_url: str