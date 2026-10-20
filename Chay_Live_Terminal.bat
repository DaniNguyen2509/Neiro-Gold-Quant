@echo off
chcp 65001 >nul
title NEIRO-QUANT TACTICAL LIVE TERMINAL
color 0A

:MENU
cls
echo ===============================================================================
echo                NEIRO-QUANT: 100%% PURE CME GOLD FUTURES TERMINAL
echo               Zero-Touch Automation ^| Zero-Leak Memory Architecture
echo ===============================================================================
echo.
echo   [1] CHAY LIVE TERMINAL REALTIME (Cap nhat 15s/lan + Tu dong don RAM)
echo   [2] DON SACH CACHE & GIAI PHONG BO NHO (Clear Workspace Cache)
echo   [3] CAP NHAT SNAPSHOT 1 LAN (Generate 1-Shot Dashboard)
echo   [4] THOAT
echo.
echo ===============================================================================
set /p opt="Nhap lua chon cua ban [1-4]: "

if "%opt%"=="1" goto RUN_LIVE
if "%opt%"=="2" goto CLEAR_CACHE
if "%opt%"=="3" goto RUN_ONCE
if "%opt%"=="4" goto EXIT_SCRIPT

echo.
echo [LOI] Lua chon khong hop le. Vui long chon tu 1 den 4.
timeout /t 2 >nul
goto MENU

:RUN_LIVE
cls
echo [KHOI TAO] Dang mo Dashboard tren trinh duyet...
start "" "exports\index.html"
echo [LIVE RUNNER] Dang kich hoat Live Runner (Chu ky: 15s)...
echo [RAM MONITOR] Bo nho duoc thu hoi lien tuc bang gc.collect(). Khong tran RAM.
echo [THONG BAO] Nhan Ctrl+C de dung terminal bat cu luc nao.
echo.
python -m src.hud.html_dashboard --loop 15
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

:EXIT_SCRIPT
cls
echo [THOAT] Dang dong Neiro-Quant Terminal...
timeout /t 1 >nul
exit /b 0
