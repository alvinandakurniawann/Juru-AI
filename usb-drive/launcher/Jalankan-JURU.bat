@echo off
REM Launcher EXE: tanpa Python, tanpa pip, tanpa admin.
setlocal
set ROOT=%~dp0..
if exist "%ROOT%\JURU.exe" (set EXE=%ROOT%\JURU.exe) else (
  echo [JURU] JURU.exe tidak ditemukan di %ROOT%.
  echo Jalankan dev-only\build\build-exe.bat dulu di mesin dev,
  echo lalu salin seluruh folder usb-drive ke flashdisk.
  pause
  exit /b 1
)
if "%PORT%"=="" set PORT=8787
echo [JURU] Membuka http://127.0.0.1:%PORT%/
start "" "http://127.0.0.1:%PORT%/"
echo [JURU] Backend EXE jalan di jendela ini. Tutup untuk berhenti.
"%EXE%"
echo.
echo [JURU] Backend berhenti (kode %ERRORLEVEL%).
pause
endlocal
