@echo off
rem Abre MinutoDesk a internet con un enlace temporal de Cloudflare, para que alguien
rem lo revise desde otra red (por ejemplo, el profesor). Minutito sigue corriendo en
rem esta laptop: debe quedar encendida y con esta ventana abierta mientras lo revisan.
rem Al cerrar la ventana el enlace deja de funcionar; cada vez que se abre cambia.

echo Iniciando MinutoDesk para revision remota...

curl -s http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo   Ollama no responde: Minutito no estara disponible hasta que lo inicies.
) else (
    echo   Ollama OK.
)

curl -s http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 (
    start "MinutoDesk - Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app"
)
curl -s http://localhost:5173 >nul 2>&1
if errorlevel 1 (
    start "MinutoDesk - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
)

timeout /t 8 /nobreak >nul
echo.
echo ================================================================
echo  Busca abajo la linea con https://....trycloudflare.com
echo  Ese es el enlace para compartir. Deja esta ventana abierta.
echo ================================================================
echo.
"%ProgramFiles(x86)%\cloudflared\cloudflared.exe" tunnel --protocol http2 --url http://localhost:5173
