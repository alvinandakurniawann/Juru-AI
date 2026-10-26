@echo off
REM Launcher portable: path dinamis dari lokasi file ini, tanpa hard-code drive.
REM Backend jalan di jendela ini (foreground) agar error selalu terlihat.
setlocal
set ROOT=%~dp0..
if not exist "%ROOT%\backend\server.py" (
  echo [JURU] server.py tidak ditemukan di %ROOT%\backend.
  echo Salin seluruh folder usb-drive ke flashdisk, jangan file ini saja.
  pause
  exit /b 1
)
where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo [JURU] Python tidak ditemukan. Install Python 3.12/3.13 64-bit dulu.
  pause
  exit /b 1
)
if not exist "%ROOT%\config\.env" (
  echo [JURU] config\.env belum ada. Mode offline untuk perintah demo.
  echo Salin config\.env.example menjadi .env dan isi key untuk perintah bebas.
  echo.
)
if "%PORT%"=="" set PORT=8787
echo [JURU] Membuka http://127.0.0.1:%PORT%/
start "" "http://127.0.0.1:%PORT%/"
echo [JURU] Backend jalan di jendela ini. Tutup jendela untuk berhenti.
echo.
%PY% -u "%ROOT%\backend\server.py"
echo.
echo [JURU] Backend berhenti (kode %ERRORLEVEL%).
echo Cek log di: %ROOT%\data\agent.log
pause
endlocal
