# app/models/__init__.py

# ייבוא מודלים של PDF (המודלים הקיימים שלך)
from .pdf import PDFRequest, PDFResponse, PDFStatus

# ייבוא מודלים של Books (המודלים החדשים)  
from .books import BookInfo, BooksResponse, FolderInfo, FoldersResponse, SearchResponse

# רשימת כל המודלים הזמינים
__all__ = [
    # PDF models
    "PDFRequest", 
    "PDFResponse", 
    "PDFStatus",
    # Books models
    "BookInfo", 
    "BooksResponse", 
    "FolderInfo", 
    "FoldersResponse", 
    "SearchResponse"
]