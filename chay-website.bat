@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Khong cai duoc thu vien. Kiem tra Python va ket noi mang.
  pause
  exit /b 1
)
for /f %%i in ('py lan_ip.py') do set "LAN_IP=%%i"
if not defined LAN_IP set "LAN_IP=127.0.0.1"
echo Dia chi de chia se trong cung Wi-Fi: http://%LAN_IP%:8000
echo Trang giao vien tren may nay: http://127.0.0.1:8000/giao-vien/dang-nhap
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000/giao-vien/dang-nhap'"
py app.py
pause
