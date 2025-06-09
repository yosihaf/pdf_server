import pdfkit
import os
import tempfile
from PyPDF2 import PdfMerger
from datetime import datetime
import uuid
from urllib.parse import quote
import logging
import urllib.request
import asyncio
from typing import List, Dict, Any, Optional

# הגדרת logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# הגדרות PDFkit
PDFKIT_OPTIONS = {
    'page-size': 'A4',
    'encoding': 'UTF-8',
    'margin-top': '15mm',
    'margin-right': '20mm',
    'margin-bottom': '15mm',
    'margin-left': '20mm',
}

# מילון לשמירת סטטוס המשימות
task_status = {}

async def create_pdf_async(task_id: str, wiki_pages: List[str], 
                          book_title: str = "המכלול ערים", 
                          base_url: str = "https://dev.hamichlol.org.il/w/rest.php/v1/page") -> None:
    """יצירת PDF באופן אסינכרוני"""
    try:
        task_status[task_id] = {"status": "processing", "message": "מתחיל בהמרה..."}
        
        # הפעלת הפונקציה המקורית בתהליך נפרד
        result = await asyncio.to_thread(
            convert_urls_to_pdfs,
            task_id=task_id,
            wiki_pages=wiki_pages,
            book_title=book_title,
            base_url=base_url
        )
        
        if result:
            # עדכון הסטטוס להצלחה
            filename = f'{book_title.replace(" ", "_")}.pdf'
            download_url = f"/download/{task_id}/{filename}"
            task_status[task_id] = {
                "status": "completed", 
                "message": "ההמרה הושלמה בהצלחה",
                "download_url": download_url
            }
        else:
            # עדכון הסטטוס לכישלון
            task_status[task_id] = {
                "status": "failed", 
                "message": "אירעה שגיאה במהלך ההמרה"
            }
            
    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}")
        task_status[task_id] = {
            "status": "failed", 
            "message": f"אירעה שגיאה: {str(e)}"
        }

def create_temp_directory(task_id: str) -> str:
    """יצירת תיקייה זמנית"""
    temp_dir = os.path.join(tempfile.gettempdir(), f'pdf_task_{task_id}')
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"Created temporary directory: {temp_dir}")
    return temp_dir

def create_table_of_contents(pages: List[str], output_path: str) -> str:
    """יצירת דף תוכן עניינים"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {
                direction: rtl;
                font-family: Arial, sans-serif;
                margin: 40px;
            }
            h1 {
                text-align: center;
                font-size: 24px;
                margin-bottom: 30px;
            }
            .toc {
                margin: 20px 0;
            }
            .toc-item {
                margin: 15px 0;
                font-size: 18px;
            }
            .toc-item a {
                text-decoration: none;
                color: #333;
            }
        </style>
    </head>
    <body>
        <h1>תוכן עניינים</h1>
        <div class="toc">
    """
    
    # הוספת כל הערכים לתוכן העניינים
    for i, page in enumerate(pages):
        html_content += f'        <div class="toc-item">{i+1}. {page}</div>\n'
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    temp_html = os.path.join(os.path.dirname(output_path), f"toc_{uuid.uuid4().hex[:8]}.html")
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    pdfkit.from_file(temp_html, output_path, options={'page-size': 'A4', 'encoding': 'UTF-8'})
    os.remove(temp_html)
    
    return output_path

def convert_page_with_header(url: str, output_path: str, title: str) -> bool:
    """המרת דף עם כותרת משולבת"""
    try:
        logger.info(f"Starting conversion with embedded header for: {title}")
        
        # הורדת התוכן המקורי מהאתר
        with urllib.request.urlopen(url) as response:
            original_html = response.read().decode('utf-8')
        
        # יצירת כותרת שתהיה חלק מהדף
        header_html = f"""
        <div style="direction: rtl; text-align: center; height: 25vh; padding-top: 5%; margin-bottom: 20px;">
            <h1 style="font-size: 24px; color: #333; margin-bottom: 10px;">{title}</h1>
            <div style="font-size: 16px; color: #666;">מתוך המכלול - האנציקלופדיה העברית</div>
        </div>
        """
        
        # זיהוי תג <body> ושילוב הכותרת אחריו
        if "<body" in original_html:
            body_index = original_html.find("<body")
            closing_bracket_index = original_html.find(">", body_index)
            modified_html = original_html[:closing_bracket_index+1] + header_html + original_html[closing_bracket_index+1:]
        else:
            # אם אין תג <body>, נוסיף את הכותרת בתחילת ה-HTML
            modified_html = header_html + original_html
        
        # שמירת ה-HTML המעודכן לקובץ זמני
        temp_html = os.path.join(os.path.dirname(output_path), f"temp_{uuid.uuid4().hex[:8]}.html")
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(modified_html)
        
        # המרה ל-PDF
        pdfkit.from_file(temp_html, output_path, options=PDFKIT_OPTIONS)
        
        # מחיקת קובץ ה-HTML הזמני
        os.remove(temp_html)
        
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            logger.info(f"Successfully created PDF: {output_path} (Size: {size} bytes)")
            return True
        else:
            logger.error(f"Failed to create PDF: {output_path}")
            return False
            
    except Exception as e:
        logger.error(f"Error converting {title}: {str(e)}")
        return False

def merge_pdfs(pdf_files: List[str], output_path: str) -> bool:
    """מיזוג קבצי PDF"""
    try:
        merger = PdfMerger()
        
        # הוספת כל הקבצים
        for pdf in pdf_files:
            logger.info(f"Adding {pdf} to merged file")
            merger.append(pdf)
        
        # שמירת הקובץ המאוחד
        merger.write(output_path)
        merger.close()
        
        logger.info(f"Successfully created merged PDF: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error merging PDFs: {str(e)}")
        return False

def create_book_cover(title: str, output_path: str) -> str:
    """יצירת דף שער ראשי לספר"""
    html_content = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                direction: rtl;
                text-align: center;
                font-family: Arial, sans-serif;
                padding-top: 30%;
                height: 100vh;
                background-color: #f9f9f9;
            }}
            .main-title {{
                font-size: 36px;
                color: #333;
                margin-bottom: 30px;
                font-weight: bold;
            }}
            .subtitle {{
                font-size: 24px;
                color: #666;
                margin-bottom: 60px;
            }}
            .publisher {{
                font-size: 18px;
                color: #888;
                margin-top: 100px;
            }}
            .date {{
                font-size: 16px;
                color: #888;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="main-title">{title}</div>
        <div class="subtitle">אוסף ערכים נבחרים</div>
        <div class="publisher">המכלול - האנציקלופדיה היהודית</div>
        <div class="date">{datetime.now().strftime("%Y %B")}</div>
    </body>
    </html>
    """
    
    temp_html = os.path.join(os.path.dirname(output_path), f"bookcover_{uuid.uuid4().hex[:8]}.html")
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    pdfkit.from_file(temp_html, output_path, options={'page-size': 'A4', 'encoding': 'UTF-8'})
    os.remove(temp_html)
    
    return output_path

def convert_urls_to_pdfs(task_id: str, wiki_pages: List[str], 
                        book_title: str = "המכלול ערים",
                        base_url: str = "https://dev.hamichlol.org.il/w/rest.php/v1/page") -> bool:
    """המרת כל ה-URLs ל-PDFs עם דף שער, תוכן עניינים וכותרות לפרקים"""
    temp_dir = create_temp_directory(task_id)
    pdf_files = []
    output_file_created = False
    
    try:
        # יצירת דף שער ראשי לספר
        cover_filename = f"book_cover_{uuid.uuid4().hex[:8]}.pdf"
        cover_path = os.path.join(temp_dir, cover_filename)
        create_book_cover(book_title, cover_path)
        pdf_files.append(cover_path)
        
        # יצירת תוכן עניינים
        toc_filename = f"toc_{uuid.uuid4().hex[:8]}.pdf"
        toc_path = os.path.join(temp_dir, toc_filename)
        create_table_of_contents(wiki_pages, toc_path)
        pdf_files.append(toc_path)
        
        # יצירת כל דפי הויקי עם כותרות
        for page in wiki_pages:
            url = f'{base_url}/{quote(page)}/html'
            output_filename = f"{page.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.pdf"
            output_path = os.path.join(temp_dir, output_filename)
            
            if convert_page_with_header(url, output_path, page):
                pdf_files.append(output_path)
        
        # מיזוג הקבצים
        if pdf_files:
            # וודא שתיקיית הפלט קיימת
            output_dir = os.path.join('/app/output', task_id)
            os.makedirs(output_dir, exist_ok=True)
            
            merged_path = os.path.join(output_dir, f'{book_title.replace(" ", "_")}.pdf')
            if merge_pdfs(pdf_files, merged_path):
                output_file_created = True
                
        return output_file_created
            
    except Exception as e:
        logger.error(f"Error during conversion process: {str(e)}")
        return False
        
    finally:
        # ניקוי קבצים זמניים
        try:
            for pdf in pdf_files:
                if os.path.exists(pdf):
                    os.remove(pdf)
                    logger.info(f"Removed temporary file: {pdf}")
            os.rmdir(temp_dir)
            logger.info(f"Removed temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")