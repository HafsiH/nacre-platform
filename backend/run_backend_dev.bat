@echo off
REM Quick dev server for NACRE backend (FastAPI)
SETLOCAL ENABLEDELAYEDEXPANSION

IF "%PORT%"=="" SET PORT=8123

REM Move to backend directory (where this script lives)
pushd %~dp0

REM Activate virtualenv if present (optional)
IF EXIST "..\venv\Scripts\activate.bat" (
  call "..\venv\Scripts\activate.bat"
)

echo Starting FastAPI on http://127.0.0.1:%PORT% (reload enabled)
python -m uvicorn app.main:app --host 127.0.0.1 --port %PORT% --reload

popd
ENDLOCAL

