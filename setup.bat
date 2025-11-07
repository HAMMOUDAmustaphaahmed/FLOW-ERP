@echo off
echo ======================================
echo FlowERP Setup Script for Windows
echo ======================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
cd backend
pip install -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo Dependencies installed successfully
cd ..

REM Initialize database
echo.
echo ======================================
echo Database Initialization
echo ======================================
echo.
echo Do you want to initialize the database with sample data?
echo This will create:
echo   - Admin account (username: admin, password: Admin@123)
echo   - Sample company with 4 departments
echo   - 3 sample users
echo.

set /p SAMPLE="Initialize with sample data? (y/n): "

if /i "%SAMPLE%"=="y" (
    cd database
    echo yes | python init_db.py
    echo yes | python init_db.py
    cd ..
) else (
    set /p EMPTY="Initialize empty database? (y/n): "
    if /i "%EMPTY%"=="y" (
        cd database
        echo yes | python init_db.py
        echo no | python init_db.py
        cd ..
    )
)

echo.
echo ======================================
echo Setup Complete!
echo ======================================
echo.
echo To start the application:
echo.
echo   1. Activate virtual environment:
echo      venv\Scripts\activate
echo.
echo   2. Start the server:
echo      cd backend
echo      python app.py
echo.
echo   3. Open browser:
echo      http://localhost:5000
echo.
echo ======================================
echo.
pause