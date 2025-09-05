@echo off
REM NACRE Platform Server Startup Script
SETLOCAL ENABLEDELAYEDEXPANSION

echo ================================================
echo NACRE Platform - Starting Server
echo ================================================

REM Check if we're in the backend directory
if not exist "app\main.py" (
    echo Error: Please run this script from the backend directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Set default port
IF "%PORT%"=="" SET PORT=8123

REM Move to project root and activate virtual environment
pushd ..
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "venv\Scripts\activate.bat"
) else (
    echo Warning: Virtual environment not found at venv\Scripts\activate.bat
    echo Make sure Python and required packages are installed
)

REM Go back to backend directory
cd backend

REM Check if .env file exists, if not suggest creating one
if not exist ".env" (
    echo.
    echo WARNING: .env file not found
    echo For full functionality, create a .env file with your OpenAI API key
    echo You can copy env.template to .env and update the values
    echo.
    echo The server will start but AI features may be limited without proper configuration
    echo.
    pause
)

REM Start the server
echo Starting FastAPI server on http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop the server
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port %PORT% --reload

popd
ENDLOCAL
