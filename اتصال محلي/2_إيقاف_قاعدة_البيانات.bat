@echo off
chcp 65001 > nul
title إيقاف Supabase المحلي
echo ===================================================
echo            إيقاف Supabase المحلي
echo ===================================================
echo.
echo جاري إيقاف الحاويات وتوفير موارد الجهاز...
echo.
cd /d "d:\Graduation Project\AI-COS-Pharmacy"
call npx supabase stop
echo.
echo ===================================================
echo  [تم] تم إيقاف جميع حاويات Supabase بنجاح.
echo ===================================================
echo.
pause
