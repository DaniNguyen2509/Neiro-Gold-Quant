@echo off
chcp 65001 >nul
echo ========================================================
echo  ⚡ NEIRO-QUANT: DONG BO DU LIEU CME GOLD OPTIONS (GCZ26)
echo ========================================================
cd /d "%~dp0\.."
echo Dang khoi dong Playwright scraper...
python -m src.collector.main
echo.
echo ========================================================
echo  ✅ HOAN TAT DONG BO VA GHI DE VAO GOOGLE DRIVE!
echo ========================================================
timeout /t 5
