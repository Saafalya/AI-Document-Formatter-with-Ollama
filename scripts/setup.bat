@echo off
echo ============================================
echo  AI Document Formatter - Setup
echo ============================================
echo.

where ollama >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Ollama not found in PATH. Install from https://ollama.com
) else (
    echo [OK] Ollama found
    ollama list 2>nul | findstr /i "llama3.1:8b" >nul
    if %ERRORLEVEL% NEQ 0 (
        echo [INFO] Pulling recommended model llama3.1:8b ...
        ollama pull llama3.1:8b
    ) else (
        echo [OK] Model llama3.1:8b already installed
    )
)

echo.
echo Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Generating test files...
python test_data\create_test_files.py

echo.
echo ============================================
echo  Setup complete!
echo  Run: start.bat
echo  Or:  venv\Scripts\activate ^&^& python app.py
echo ============================================
pause
