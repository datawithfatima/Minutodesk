@echo off
echo Iniciando MinutoDesk...

echo Verificando Ollama...
curl -s http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo   Ollama no responde en localhost:11434 - Minutito no estara disponible hasta que lo inicies.
) else (
    echo   Ollama OK.
)

start "MinutoDesk - Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload"
start "MinutoDesk - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo Backend y frontend corriendo en dos ventanas separadas.
echo Para detener todo, cierra esas dos ventanas de terminal.
