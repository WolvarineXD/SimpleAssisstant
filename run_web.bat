@echo off
cd /d "%~dp0"
echo Starting SimpleAssisstant web UI at http://127.0.0.1:5000
py -3.12 web\app.py
