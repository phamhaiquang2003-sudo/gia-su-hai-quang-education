@echo off
cd /d "%~dp0"

rem Keep the class data on this machine. Cloudflare only relays HTTP requests.
powershell -NoProfile -Command "try { Invoke-WebRequest 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo Website chua chay. Hay mo chay-website.bat truoc, roi thu lai.
  pause
  exit /b 1
)

if not exist tools mkdir tools
if not exist tools\cloudflared.exe (
  echo Dang tai Cloudflare Tunnel tu trang phat hanh chinh thuc...
  powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'tools\cloudflared.exe'"
  if errorlevel 1 (
    echo Khong tai duoc cloudflared. Kiem tra mang va thu lai.
    if exist tools\cloudflared.exe del tools\cloudflared.exe
    pause
    exit /b 1
  )
)

tools\cloudflared.exe --version
if errorlevel 1 (
  echo Cloudflared khong chay duoc. Hay xoa tools\cloudflared.exe va thu lai.
  pause
  exit /b 1
)

echo.
echo Sao chep dia chi https://...trycloudflare.com xuat hien ben duoi de gui cho hoc sinh.
echo Neu bi troi log, mo xem-link-tu-xa.bat de hien va sao chep link.
echo Dia chi thay doi moi lan chay; giu CUA SO NAY va cua so website mo khi hoc sinh lam bai.
echo Nhan Ctrl+C de dung lien ket tu xa.
echo.
tools\cloudflared.exe tunnel --no-autoupdate --url http://127.0.0.1:8000
pause
