@echo off
REM Setup script for Uma Musume Auto-Train Bot (Windows)
REM Checks system requirements and installs dependencies

echo ============================================================
echo   Uma Musume Auto-Train Bot - Setup
echo ============================================================
echo.

REM Check if Python is installed
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.10+ from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [OK] Python is installed
python --version

REM Check Python version (must be 3.11.x)
echo.
echo Checking Python version...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% NEQ 3 (
    echo [ERROR] Python 3.11.x is required. You have Python %PYTHON_VERSION%
    echo Please download Python 3.11.x from https://www.python.org/downloads/
    pause
    exit /b 1
)

if %MINOR% NEQ 11 (
    echo [ERROR] Python 3.11.x is required. You have Python %PYTHON_VERSION%
    echo Please download Python 3.11.x from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python version is compatible

REM Check Tesseract-OCR
echo.
echo Checking Tesseract-OCR...
where tesseract >nul 2>&1
if errorlevel 1 (
    echo [INFO] Tesseract-OCR not found, downloading installer...
    set "TESS_URL=https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
    set "TESS_EXE=%TEMP%\tesseract-ocr-w64-setup.exe"
    powershell -Command "Invoke-WebRequest -Uri '%TESS_URL%' -OutFile '%TESS_EXE%'" || (
        echo [ERROR] Failed to download Tesseract installer
        pause
        exit /b 1
    )
    echo [INFO] Running Tesseract installer (please wait)...
    start /wait "" "%TESS_EXE%" || (
        echo [ERROR] Tesseract installer failed
        pause
        exit /b 1
    )
)

REM Ensure Tesseract is on PATH for this session (common install path)
set "PATH=C:\Program Files\Tesseract-OCR;%PATH%"
where tesseract >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Tesseract still not found. If you installed to a custom path, add it to PATH manually.
) else (
    echo [OK] Tesseract-OCR is available
)

REM Check for Git
echo.
echo Checking Git installation...
if exist "toolkit\Git\mingw64\bin\git.exe" (
    echo [OK] Found bundled Git: toolkit\Git\mingw64\bin\git.exe
    set GIT_FOUND=1
) else if exist "toolkit\Git\cmd\git.exe" (
    echo [OK] Found bundled Git: toolkit\Git\cmd\git.exe
    set GIT_FOUND=1
) else if exist "toolkit\Git\bin\git.exe" (
    echo [OK] Found bundled Git: toolkit\Git\bin\git.exe
    set GIT_FOUND=1
) else (
    git --version >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Git not found
        echo Git is optional but recommended for auto-updates
        echo You can download Git from: https://git-scm.com/downloads
        set GIT_FOUND=0
    ) else (
        echo [OK] Found system Git
        git --version
        set GIT_FOUND=1
    )
)

REM Check if this is a git repository
if %GIT_FOUND% EQU 1 (
    if exist ".git" (
        echo [OK] This is a git repository
    ) else (
        echo [WARNING] Not a git repository
        echo Auto-update features will not work without git
    )
)

REM Check requirements.txt
echo.
echo Checking requirements.txt...
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found
    echo Please make sure you're in the correct directory
    pause
    exit /b 1
)
echo [OK] requirements.txt found

REM Run Python setup script
echo.
echo ============================================================
echo   Running Python setup script...
echo ============================================================
echo.

python setup.py
if errorlevel 1 (
    echo.
    echo [ERROR] Setup script failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo You can now run the application with:
echo   python launch_gui.py
echo.
pause

