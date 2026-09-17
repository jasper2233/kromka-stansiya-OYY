@echo off
rem ============================================================
rem  KROMKA STANSIYASI - avtomatik ishga tushirish
rem  Ishga tushirsangiz: MES serveri koteriladi va Chrome
rem  kiosk rejimida stansiya ekranini ochadi.
rem  Kompyuter yoqilganda ozi ochilishi uchun - fayl oxiriga qarang.
rem ============================================================
title Kromka stansiyasi
cd /d "%~dp0"

set "URL=http://localhost:8000"
set "PROFIL=%LOCALAPPDATA%\KromkaStansiya\chrome-profil"

rem ---------- 1. MES serveri ----------
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul
if errorlevel 1 (
  echo MES serveri ishga tushirilmoqda...
  start "" /min pythonw "%~dp0mes_server.py"
  timeout /t 3 /nobreak >nul
) else (
  echo MES serveri allaqachon ishlayapti.
)

rem ---------- 2. Chrome ----------
set "CHROME="
for %%p in (
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do if exist %%p set "CHROME=%%p"

if not defined CHROME (
  echo.
  echo   Chrome topilmadi. Google Chrome ni ornating.
  echo.
  pause
  exit /b 1
)

rem --user-data-dir: alohida profil. Pico portiga berilgan ruxsat shu yerda
rem saqlanadi, shuning uchun ruxsat FAQAT BIR MARTA soraladi.
start "" %CHROME% --kiosk --user-data-dir="%PROFIL%" --no-first-run --no-default-browser-check --noerrdialogs --disable-session-crashed-bubble --disable-background-timer-throttling "%URL%"

exit /b 0

rem ============================================================
rem  KOMPYUTER YOQILGANDA OZI ISHGA TUSHISHI UCHUN
rem    1. Win+R bosing, yozing:  shell:startup   -> Enter
rem    2. Ochilgan papkaga shu faylning YORLIGINI tashlang
rem       (fayl ustida ong tugma -> Copy, papkada -> Paste shortcut)
rem    Tekshirish: kompyuterni qayta yoqing.
rem
rem  KIOSKDAN CHIQISH:  Alt+F4
rem ============================================================
