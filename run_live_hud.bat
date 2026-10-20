@echo off
title Neiro-Quant Live Tactical HUD Runner (Realtime M5 Auto-Sync)
echo ==============================================================================
echo [NEIRO-QUANT] CHAY TIEN TRINH CAP NHAT DASHBOARD VA BANG GIA M5 LIEN TUC
echo Chu ky cap nhat: 15 giay (Realtime Auto-Sync)
echo Nhan Ctrl + C de dung lai.
echo ==============================================================================
python -m src.hud.html_dashboard --loop 15
pause
