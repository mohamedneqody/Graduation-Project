@echo off
chcp 65001 > nul
title فحص حالة Supabase المحلي
echo ===================================================
echo          فحص حالة Supabase والخدمات
echo ===================================================
echo.
cd /d "d:\Graduation Project\AI-COS-Pharmacy"
call npx supabase status
echo.
echo ===================================================
echo.
pause
