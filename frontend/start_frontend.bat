@echo off
REM NACRE Platform - Frontend Startup Script
SETLOCAL ENABLEDELAYEDEXPANSION

echo ================================================
echo NACRE Platform - Starting Frontend
echo ================================================

REM Check if we're in the frontend directory
if not exist "package.json" (
    echo Error: Please run this script from the frontend directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo Starting Vite development server...
echo Frontend will be available at: http://localhost:5173
echo Backend API calls will be proxied to: http://127.0.0.1:8123
echo.
echo Press Ctrl+C to stop the server
echo.

npm run dev

ENDLOCAL
