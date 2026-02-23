@echo off
cd /d "%~dp0"
echo NEO MAX - Loop autonomo
echo Asegurate de tener Ollama abierto (localhost:11434)
echo.
echo .env debe tener: GITHUB_TOKEN, SERPAPI_KEY
echo AdSense y afiliados los anades cuando los tengas en config.
echo.
python run_saas_loop.py
pause
