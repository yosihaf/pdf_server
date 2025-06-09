# app/models.py
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

class PDFResponse(BaseModel):
    """מודל לתשובת יצירת PDF"""
    task_id: str = Field(..., 
                        description="מזהה המשימה")
    status: str = Field(..., 
                       description="סטטוס המשימה")
    message: str = Field(..., 
                        description="הודעה למשתמש")

class PDFStatus(BaseModel):
    """מודל לסטטוס יצירת PDF"""
    task_id: str = Field(..., 
                        description="מזהה המשימה") 
    status: str = Field(..., 
                       description="סטטוס המשימה")
    download_url: Optional[str] = Field(None, 
                                      description="קישור להורדת הקובץ אם מוכן")
    message: str = Field(..., 
                        description="הודעה למשתמש")