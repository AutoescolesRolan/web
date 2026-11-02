@echo off
setlocal
chcp 65001 >nul
title Rolan Web (local)

REM ============================================================
REM   Rolan Web a l'ordinador, en mode de demostració
REM   - El pagament és simulat (no es connecta a Stripe).
REM   - Els correus no s'envien: es poden veure al panell.
REM   - Les dades es guarden en un fitxer local (rolan_web_local.db).
REM   Només cal fer doble clic. Per aturar-la, tanca la finestra «Servidor Rolan Web».
REM ============================================================

cd /d "%~dp0"
set "PUERTO=8010"

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo  No trobo Python en aquest ordinador.
    echo  Instal·la'l des de https://www.python.org/downloads/ marcant "Add python.exe to PATH"
    echo  i torna a fer doble clic en aquest fitxer.
    echo.
    pause
    exit /b
)

if not exist "venv\Scripts\activate.bat" (
    echo  Primera vegada: preparant l'entorn...
    python -m venv venv
)
call venv\Scripts\activate.bat
if not exist "venv\instalat-ok.txt" (
    echo  Instal·lant el que cal ^(només la primera vegada, tarda un parell de minuts^)...
    python -m pip install --upgrade pip >nul
    python -m pip install -r requirements-local.txt
    if errorlevel 1 (
        echo.
        echo  No s'ha pogut instal·lar tot. Fes una captura d'aquesta finestra i envia-la.
        echo.
        pause
        exit /b
    )
    echo ok> "venv\instalat-ok.txt"
)

set "ROLAN_DEMO=1"
set "DATABASE_URL=sqlite:///./rolan_web_local.db"
set "SECRET_KEY=nomes-per-provar-en-local"
set "PUBLIC_URL=http://127.0.0.1:%PUERTO%"
set "ADMIN_EMAIL=admin@local.cat"
set "ADMIN_PASSWORD=rolanlocal123"
set "STRIPE_SECRET_KEY="
set "RESEND_API_KEY="

start "Servidor Rolan Web" /min cmd /c "uvicorn app.main:app --port %PUERTO%"

echo  Esperant que la web estigui a punt...
set /a INTENTS=0
:espera
set /a INTENTS+=1
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:%PUERTO%/salut' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    if %INTENTS% LSS 40 ( timeout /t 1 >nul & goto espera )
    echo  La web no ha arrencat. Mira la finestra "Servidor Rolan Web" per veure l'error.
    pause
    exit /b
)

start "" "http://127.0.0.1:%PUERTO%/"
echo.
echo  ============================================================
echo   Web:    http://127.0.0.1:%PUERTO%/
echo   Panell: http://127.0.0.1:%PUERTO%/gestio
echo           usuari: admin@local.cat   contrasenya: rolanlocal123
echo  ============================================================
echo.
pause
