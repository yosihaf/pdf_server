FROM python:3.9-slim

# התקנת wkhtmltopdf וספריות נדרשות
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    wget \
    fontconfig \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxrender1 \
    xfonts-75dpi \
    xfonts-base \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# התקנת פונטים עבריים
RUN apt-get update && apt-get install -y \
    fonts-liberation \
    fonts-dejavu \
    && apt-get clean

# יצירת תיקיות עבודה
WORKDIR /app
RUN mkdir -p /app/output

# התקנת ספריות Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת קוד המקור
COPY ./app /app/app

# חשיפת פורט
EXPOSE 8000

# הפעלת השרת
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]