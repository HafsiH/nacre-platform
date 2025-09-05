@echo off
REM NACRE Platform - Start All Services
SETLOCAL ENABLEDELAYEDEXPANSION

echo ================================================
echo NACRE Platform - Starting All Services
echo ================================================

REM Start Backend in background
echo Starting Backend Server...
start "NACRE Backend" cmd /k "cd backend && ..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8123 --reload"

REM Wait a bit for backend to start
timeout /t 5 /nobreak > nul

REM Start Frontend in background  
echo Starting Frontend Server...
start "NACRE Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ================================================
echo Services are starting...
echo ================================================
echo Backend: http://127.0.0.1:8123
echo Frontend: http://localhost:5173
echo API Docs: http://127.0.0.1:8123/docs
echo.
echo Both services will open in separate windows.
echo Close those windows to stop the services.
echo ================================================

pause
