@echo off
REM Launcher aplikasi jendela (bukan tab browser). Tanpa Python di target.
setlocal
set ROOT=%~dp0..
if exist "%ROOT%\JURU-Desktop.exe" (set EXE=%ROOT%\JURU-Desktop.exe) else (
  echo [JURU] JURU-Desktop.exe tidak ditemukan di %ROOT%.
  echo Jalankan dev-only\build\build-exe.bat dulu di mesin dev,
  echo lalu salin seluruh folder usb-drive ke flashdisk.
  pause
  exit /b 1
)
if "%PORT%"=="" set PORT=8787
echo [JURU] Membuka jendela aplikasi...
"%EXE%"
echo.
echo [JURU] Aplikasi berhenti (kode %ERRORLEVEL%).
pause
endlocal
