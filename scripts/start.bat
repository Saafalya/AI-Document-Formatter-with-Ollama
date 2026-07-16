@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting AI Document Formatter at http://localhost:5000
python app.py
