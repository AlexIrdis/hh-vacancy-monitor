@echo off
title hh-vacancy-monitor
cd /d %~dp0
.venv\Scripts\python.exe monitor.py --headless
pause