@echo off
cd /d %~dp0

echo Iniciando Redis...
docker start redis-pdfsplit >nul 2>&1

echo Iniciando ngrok...
net start ngrok >nul 2>&1

echo Iniciando Backend...
start "PDF Split - Backend" cmd /k "cd backend && .venv\Scripts\activate && uvicorn app.main:app --port 8000 --reload"

echo Iniciando Celery Worker...
start "PDF Split - Celery" cmd /k "cd backend && .venv\Scripts\activate && celery -A app.worker worker --pool=threads --loglevel=info"

echo Iniciando Frontend...
start "PDF Split - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo =============================================
echo  Ferramenta operacional!
echo  Local:  http://localhost:5173
echo  ngrok:  http://127.0.0.1:4040
echo =============================================
