@echo off
echo Iniciando MinutoDesk...

start "MinutoDesk - Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload"
start "MinutoDesk - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo Backend y frontend corriendo en dos ventanas separadas.
echo Para detener todo, cierra esas dos ventanas de terminal.
