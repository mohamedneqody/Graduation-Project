@echo off
chcp 65001 > nul
title تشغيل Supabase المحلي
echo ===================================================
echo       تشغيل Supabase المحلي (Docker)
echo ===================================================
echo.
echo جاري تشغيل الحاويات وقاعدة البيانات...
echo.
cd /d "d:\Graduation Project\AI-COS-Pharmacy"
call npx supabase start
echo.
echo ===================================================
echo  [تم بنجاح] قاعدة البيانات والخدمات تعمل الآن!
echo  لوحة التحكم (Studio): http://127.0.0.1:54323
echo  رابط قاعدة البيانات: postgresql://postgres:postgres@127.0.0.1:54322/postgres
echo ===================================================
echo.
pause
