@echo off
echo ======================================================================
echo             Starting MemoryOS Cognitive AI Assistant
echo ======================================================================
echo.

REM Activate virtual environment if present
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Start backend server
echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "MemoryOS Backend" cmd /k "python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload"

REM Start frontend server
echo [2/2] Starting Frontend Vite Server on http://localhost:5173 ...
cd frontend
start "MemoryOS Frontend" cmd /k "npm run dev"

echo.
echo Application is running!
echo Frontend: http://localhost:5173
echo Backend API & Swagger Docs: http://127.0.0.1:8000/docs
echo ======================================================================
