@echo off
title CompilerLab One-Click Launcher
cd /d "%~dp0"
echo ===================================================
echo   CompilerLab - MiniLang 5-Phase Studio
echo ===================================================
echo.
start "CompilerLab Backend (Flask)" cmd /k "cd /d "%~dp0backend" && python -m pip install -r requirements.txt && python app.py"
timeout /t 2 /nobreak >nul
start "CompilerLab Frontend (Vite)" cmd /k "cd /d "%~dp0frontend" && if not exist node_modules call npm install && call npm run dev"
timeout /t 4 /nobreak >nul
start "" "http://localhost:5173"
echo Both servers started! Browser opening at http://localhost:5173
