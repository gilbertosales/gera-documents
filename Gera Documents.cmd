@echo off
rem Abre o frontend web local do Gera Documents no navegador.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado. Instale o Python 3.10+ e marque "Add python.exe to PATH".
    pause
    exit /b 1
)
python -m gera_md.web
if errorlevel 1 pause
