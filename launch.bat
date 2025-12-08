@echo off
REM Launch script for Uma Musume Auto-Train Bot GUI (Windows)

echo ============================================================
echo   Uma Musume Auto-Train Bot
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.11.x from:
    echo https://www.python.org/downloads/
    echo.
    echo Or run setup.bat first to check your installation
    echo.
    pause
    exit /b 1
)

REM Check if launch_gui.py exists
if not exist "launch_gui.py" (
    echo [ERROR] launch_gui.py not found
    echo Please make sure you're in the correct directory
    echo.
    pause
    exit /b 1
)

REM Launch the GUI
echo Starting GUI...
echo.
python launch_gui.py

REM Check exit code
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error
    echo.
    pause
    exit /b 1
)

exit /b 0

