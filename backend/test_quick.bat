@echo off
echo Testing NACRE Server...

REM Move to parent directory and activate venv
cd ..
call venv\Scripts\activate.bat

REM Go back to backend and run test
cd backend
python test_server.py

pause
