@echo off
chcp 65001 > nul
echo ========================================
echo   Gemini + Telegram 주식 분석 봇 시작
echo ========================================
cd /d "%~dp0"
"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe" telegram_bot.py
pause
