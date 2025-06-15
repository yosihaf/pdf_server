#!/bin/bash
# run_app.sh - קובץ להרצת האפליקציה
<<<<<<< HEAD

echo "🚀 מתחיל להריץ את האפליקציה..."

# בדיקת Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 לא מותקן"
    exit 1
fi

# יצירת תיקיות
echo "📁 יוצר תיקיות נדרשות..."
mkdir -p app/output
mkdir -p logs

# הגדרת משתני סביבה
echo "🔧 מגדיר משתני סביבה..."
export SECRET_KEY="your-super-secret-key-change-this-in-production-12345"
export DATABASE_URL="sqlite:///./app.db"
export BOOKS_PATH="./app/output"
export LOG_LEVEL="INFO"

# בדיקת wkhtmltopdf
if ! command -v wkhtmltopdf &> /dev/null; then
    echo "⚠️  wkhtmltopdf לא מותקן - PDF generation עלול לא לעבוד"
    echo "התקן עם: sudo apt-get install wkhtmltopdf"
fi

# הרצת השרת
echo "🌟 מפעיל את השרת..."
echo "📍 השרת יפעל בכתובת: http://localhost:8000"
echo "📋 תיעוד API: http://localhost:8000/docs"
echo ""
=======
source venv/Scripts/activate
>>>>>>> f1115412e3368df770d77030654bd3f7f0759d55

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload