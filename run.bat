@echo off
title BPMKeySearch - Detector de Tom, BPM e Tempo
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo   BPMKeySearch - Detector de Tom, BPM e Tempo (Spotify & YouTube)
echo ========================================================
echo.

:: Detect Python executable in PATH or standard directories
set "PYTHON_CMD="
where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    where py >nul 2>nul && set "PYTHON_CMD=py"
)
if not defined PYTHON_CMD (
    if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    )
)
if not defined PYTHON_CMD (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
        if exist "%%D\python.exe" set "PYTHON_CMD=%%D\python.exe"
    )
)
if not defined PYTHON_CMD (
    for /d %%D in ("C:\Program Files\Python*") do (
        if exist "%%D\python.exe" set "PYTHON_CMD=%%D\python.exe"
    )
)

if not defined PYTHON_CMD (
    echo [AVISO] Python nao foi detectado automaticamente neste computador!
    echo Para rodar o BPMKeySearch, instale o Python em:
    echo   https://www.python.org/downloads/
    echo.
    echo (Dica: Marque a caixa "Add Python to PATH" durante a instalacao)
    echo.
    pause
    exit /b 1
)

echo [1/2] Verificando dependencias necessarias...
"%PYTHON_CMD%" -m pip install -q -r requirements.txt

echo [2/2] Iniciando BPMKeySearch...
echo.
"%PYTHON_CMD%" app.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Ocorreu um erro ao executar o programa.
    pause
)
