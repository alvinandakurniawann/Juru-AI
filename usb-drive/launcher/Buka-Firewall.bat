@echo off
REM Buka port JURU di firewall (klik kanan tidak perlu, otomatis minta admin).
setlocal
net session >nul 2>nul
if errorlevel 1 (
  echo Meminta izin administrator...
  powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b
)
where py >nul 2>nul && (set PY=py) || (set PY=python)
for /f "delims=" %%P in ('%PY% -c "import sys; print(sys.executable)"') do set PYEXE=%%P
if "%PYEXE%"=="" (
  echo Python tidak ditemukan.
  pause
  exit /b 1
)
netsh advfirewall firewall delete rule name="JURU" >nul 2>nul
netsh advfirewall firewall add rule name="JURU" dir=in action=allow program="%PYEXE%" enable=yes profile=private
echo.
echo Selesai. Port JURU terbuka untuk jaringan private.
echo Buka di HP: lihat alamat http://... di data\agent.log
pause
endlocal
