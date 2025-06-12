import smtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

# הגדרות מייל
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)

# דומיינים מורשים
ALLOWED_DOMAINS = ["@cti.org.il"]

class EmailValidator:
    """מחלקה לאימות מיילים והגבלת דומיינים"""
    
    @staticmethod
    def is_allowed_domain(email: str) -> bool:
        """בדיקה שהמייל מדומיין מורשה"""
        email_lower = email.lower()
        return any(email_lower.endswith(domain) for domain in ALLOWED_DOMAINS)
    
    @staticmethod
    def generate_verification_code() -> str:
        """יצירת קוד אימות"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @staticmethod
    def send_verification_email(email: str, code: str, username: str) -> bool:
        """שליחת מייל אימות"""
        try:
            # יצירת ההודעה
            msg = MimeMultipart()
            msg['From'] = FROM_EMAIL
            msg['To'] = email
            msg['Subject'] = "אימות הרשמה - מערכת המכלול"
            
            # תוכן המייל
            html_body = f"""
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; direction: rtl; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .code {{ font-size: 24px; font-weight: bold; color: #333; 
                            background-color: #e8f5e8; padding: 15px; text-align: center; 
                            border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; color: #666; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>ברוכים הבאים למערכת המכלול</h1>
                    </div>
                    <div class="content">
                        <p>שלום {username},</p>
                        <p>תודה על הרשמתך למערכת יצירת הספרים של המכלול.</p>
                        <p>כדי להשלים את הרשמתך, אנא הכנס את קוד האימות הבא:</p>
                        
                        <div class="code">{code}</div>
                        
                        <p><strong>חשוב:</strong> הקוד תקף למשך 15 דקות בלבד.</p>
                        <p>אם לא ביקשת להירשם, אנא התעלם ממייל זה.</p>
                    </div>
                    <div class="footer">
                        <p>צוות המכלול<br/>
                        <small>מייל זה נשלח אוטומטית, אנא אל תשיבו עליו</small></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MimeText(html_body, 'html', 'utf-8'))
            
            # שליחת המייל
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                if SMTP_USERNAME and SMTP_PASSWORD:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Verification email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False