@echo off
title Neiro-Quant Live Tactical HUD Runner (M5 Tape Auto-Sync)
echo ==============================================================================
echo [NEIRO-QUANT] CHAY TIEN TRINH CAP NHAT DASHBOARD VA BANG GIA M5 LIEN TUC
echo Chu ky cap nhat: 300 giay (5 phut)
echo Nhan Ctrl + C de dung lai.
echo ==============================================================================
python -m src.hud.html_dashboard --loop 300
pause
