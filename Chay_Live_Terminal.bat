@echo off
chcp 65001 >nul
title NEIRO-QUANT TACTICAL TERMINAL CONTROLLER
color 0A

:MENU
cls
echo ===============================================================================
echo                NEIRO-QUANT: 100%% PURE CME GOLD FUTURES TERMINAL
echo               Zero-Touch Automation ^| Zero-Leak Memory Architecture
echo ===============================================================================
echo.
echo   [1] MO TERMINAL ONLINE 100%% (GitHub Pages Cloud - Khong can Python)
echo   [2] DONG BO DU LIEU MOI NHAT TU GITHUB CLOUD (git pull origin main)
echo   [3] CHAY LIVE TERMINAL NOI BO (Cap nhat 15s/lan + Tu dong don RAM)
echo   [4] CAO & DONG BO DU LIEU LEN CLOUD (Scrape + Build + Push Cloud)
echo   [5] DON SACH CACHE & GIAI PHONG BO NHO (Clear Cache & Flush RAM)
echo   [6] CAP NHAT SNAPSHOT 1 LAN (Generate 1-Shot Dashboard)
echo   [7] KIEM THU HE THONG TOAN DIEN (Run Pytest Suite)
echo   [8] MO THU MUC DATA DE THA FILE (Open Data Folder)
echo   [9] THOAT
echo.
echo ===============================================================================
set /p opt="Nhap lua chon cua ban [1-9]: "

if "%opt%"=="1" goto OPEN_ONLINE
if "%opt%"=="2" goto SYNC_CLOUD
if "%opt%"=="3" goto RUN_LIVE
if "%opt%"=="4" goto RUN_SCRAPER
if "%opt%"=="5" goto CLEAR_CACHE
if "%opt%"=="6" goto RUN_ONCE
if "%opt%"=="7" goto RUN_TESTS
if "%opt%"=="8" goto OPEN_DATA
if "%opt%"=="9" goto EXIT_SCRIPT

echo.
echo [LOI] Lua chon khong hop le. Vui long chon tu 1 den 9.
timeout /t 2 >nul
goto MENU

:OPEN_ONLINE
cls
echo ===============================================================================
echo [NEIRO CLOUD] Dang mo Terminal truc tuyen dong bo 100%% tren GitHub Pages...
echo Link: https://daninguyen2509.github.io/Neiro-Gold-Quant/
echo ===============================================================================
start https://daninguyen2509.github.io/Neiro-Gold-Quant/
timeout /t 3 >nul
goto MENU

:SYNC_CLOUD
cls
echo ===============================================================================
echo [GIT PULL] Dang dong bo du lieu va code moi nhat tu GitHub Cloud...
echo ===============================================================================
git pull origin main
echo.
echo [HOAN TAT] Da dong bo thanh cong voi GitHub Cloud.
pause
goto MENU

:RUN_LIVE
cls
echo [KIEM TRA DU LIEU] Dang kiem tra do tuoi cua Options Chain...
powershell -Command "$f='data/options_prices_GCZ26.csv'; $needs_scrape = $true; if (Test-Path $f) { $h = ((Get-Date) - (Get-Item $f).LastWriteTime).TotalHours; if ($h -lt 6) { $needs_scrape = $false; Write-Host ('[XAC NHAN] Du lieu Options Chain moi cap nhat (' + [math]::Round($h*60, 0) + ' phut truoc). San sang!') -ForegroundColor Green; } else { Write-Host ('[PHAT HIEN DATA CU] Options Chain da cu ' + [math]::Round($h, 1) + ' gio (tu ngay ' + (Get-Item $f).LastWriteTime.ToString('dd/MM/yyyy HH:mm') + ').') -ForegroundColor Yellow; Write-Host '=> Tu dong kich hoat Scraper dong bo chuoi Options moi nhat hom nay...' -ForegroundColor Cyan; } } else { Write-Host '[PHAT HIEN] Chua co file data/options_prices_GCZ26.csv. Tu dong cao ban dau...' -ForegroundColor Yellow; }; if ($needs_scrape) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo.
    echo ===============================================================================
    echo [AUTO-SYNC] Dang khoi chay Playwright Chromium cao chuoi Options Chain moi nhat...
    echo ===============================================================================
    python -m src.collector.scraper --output data/options_prices_GCZ26.csv
    echo [AUTO-SYNC] Da dong bo chuoi Options hom nay thanh cong!
    echo.
)
echo [KHOI TAO] Don dep cac tien trinh cu va mo Dashboard tren trinh duyet...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*html_dashboard*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
start "" "exports\index.html"
echo [LIVE RUNNER] Dang kich hoat Live Runner (Chu ky: 15s / Realtime)...
echo [RAM MONITOR] Bo nho duoc thu hoi lien tuc bang gc.collect(). Khong tran RAM.
echo [THONG BAO] Nhan Ctrl+C de dung terminal bat cu luc nao.
echo.
python -m src.hud.html_dashboard --loop 15
pause
goto MENU

:RUN_SCRAPER
cls
echo ===============================================================================
echo [SCRAPER] Dang khoi chay Playwright Chromium cao du lieu CME Options Chain...
echo ===============================================================================
echo.
python -m src.collector.scraper --output data/options_prices_GCZ26.csv
echo.
echo [DANG TAO SNAPSHOT] Dang bien dich lai Tactical Dashboard moi nhat...
python -m src.hud.html_dashboard --input data/options_prices_GCZ26.csv --output exports/latest_gold_dashboard.html exports/index.html index.html --no-mt5
echo.
echo ===============================================================================
echo [DONG BO CLOUD] Dang tu dong day du lieu va dashboard len GitHub Cloud...
echo ===============================================================================
git add data/options_prices_GCZ26.csv index.html version.json tactical_levels.json
git diff --staged --quiet || (git commit -m "chore(data): auto-sync options chain from local terminal" && git pull --rebase origin main && git push origin main)
echo.
echo [HOAN TAT] Da cap nhat va dong bo 100%% len GitHub Cloud & Trang Online!
pause
goto MENU

:CLEAR_CACHE
cls
echo [DANG DON CACHE] Dang don sach bo nho cache va rac tam thoi...
python -m src.hud.html_dashboard --clear-cache
echo.
echo [HOAN TAT] Bo nho cache he thong da duoc giai phong sach se.
pause
goto MENU

:RUN_ONCE
cls
echo [DANG TAO SNAPSHOT] Dang cap nhat dashboard tu CME Futures...
python -m src.hud.html_dashboard
echo.
echo [HOAN TAT] Da cap nhat exports\index.html thanh cong.
pause
goto MENU

:RUN_TESTS
cls
echo ===============================================================================
echo [KIEM THU] Dang chay toan bo bo kiem thu he thong (pytest)...
echo ===============================================================================
echo.
python -m pytest tests/ -v --tb=short
echo.
pause
goto MENU

:OPEN_DATA
cls
echo [THU MUC DATA] Dang mo thu muc data tren Windows Explorer...
start "" "%~dp0data"
echo.
echo [HUONG DAN] Anh chi can keo file options_prices_GCZ26.csv vua tai tha vao day (ghi de).
timeout /t 2 >nul
goto MENU

:EXIT_SCRIPT
cls
echo [THOAT] Dang dong Neiro-Quant Terminal...
timeout /t 1 >nul
exit /b 0
