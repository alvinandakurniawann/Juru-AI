@echo off
REM Build JURU.exe (butuh Python + pip di MESIN BUILD saja, target bebas Python).
setlocal
set HERE=%~dp0
set USB=%HERE%..\..\usb-drive
where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% "%HERE%build-exe.py"
if errorlevel 1 (
  echo [BUILD] gagal. Cek log di atas.
  pause
  exit /b 1
)
echo [BUILD] selesai. Hasil: %USB%\JURU.exe
pause
endlocal
