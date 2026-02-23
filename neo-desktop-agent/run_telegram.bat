@echo off
cd /d "%~dp0"
echo Iniciando bot de Telegram. Asegurate de tener Ollama corriendo y telegram_bot_token en config.json
python -m telegram_bot
pause
