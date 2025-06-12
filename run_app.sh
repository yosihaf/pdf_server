#!/bin/bash
# run_app.sh - קובץ להרצת האפליקציה
source venv/Scripts/activate

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload