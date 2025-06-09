#!/bin/bash
# test_auth.sh - בדיקת מערכת האימות

BASE_URL="http://localhost:8000"

echo "🧪 בודק מערכת אימות..."

# 1. בדיקת בריאות
echo "1️⃣ בודק בריאות המערכת..."
curl -s "$BASE_URL/health" | jq '.' || echo "❌ שגיאה בבדיקת בריאות"

# 2. בדיקת בריאות אימות
echo "2️⃣ בודק בריאות מערכת אימות..."
curl -s "$BASE_URL/api/auth/health" | jq '.' || echo "❌ שגיאה בבדיקת אימות"

# 3. רישום משתמש חדש
echo "3️⃣ רושם משתמש חדש..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "email": "test@example.com", 
       "password": "password123"
     }')

echo "תגובת רישום: $REGISTER_RESPONSE"

# 4. התחברות
echo "4️⃣ מתחבר למערכת..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "password": "password123"
     }')

echo "תגובת התחברות: $LOGIN_RESPONSE"

# חילוץ הטוקן
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ "$TOKEN" != "" ]; then
    echo "✅ הטוקן נוצר בהצלחה: ${TOKEN:0:20}..."
    
    # 5. בדיקת מידע משתמש
    echo "5️⃣ בודק מידע משתמש..."
    curl -s -H "Authorization: Bearer $TOKEN" \
         "$BASE_URL/api/auth/me" | jq '.'
    
    # 6. בדיקת גישה מוגנת לספרים
    echo "6️⃣ בודק גישה מוגנת לספרים..."
    curl -s -H "Authorization: Bearer $TOKEN" \
         "$BASE_URL/api/books/" | jq '.'
    
    echo "✅ כל הבדיקות הושלמו!"
else
    echo "❌ שגיאה בקבלת הטוקן"
fi