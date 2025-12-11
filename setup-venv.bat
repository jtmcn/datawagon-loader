@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM DataWagon Setup Script - Runtime Installation (Non-Poetry)
REM ============================================================================
REM This script creates a standard Python virtual environment and installs
REM DataWagon with runtime dependencies ONLY (no development tools).
REM
REM Requirements:
REM   - Python 3.9 or higher
REM   - Internet connection for pip downloads
REM
REM For development with full tooling, use Poetry: make setup-poetry
REM
REM Platform notes:
REM   - Windows uses [OK]/[ERROR] prefixes vs Unix ✓/✗ symbols
REM   - This is intentional for CMD compatibility (no ANSI colors)
REM ============================================================================

REM Variables
set VENV=.venv
set ENV_FILE=.env
set ENV_EXAMPLE=.env.example

REM Main execution
call :main
exit /b %ERRORLEVEL%

REM ============================================================================
REM Main function
REM ============================================================================
:main
echo [INFO] DataWagon Setup Script (Non-Poetry)
echo [INFO] ====================================
echo.

call :check_python
if errorlevel 1 exit /b 1

call :check_env_file
if errorlevel 1 exit /b 1

call :create_venv
if errorlevel 1 exit /b 1

call :install_deps
if errorlevel 1 exit /b 1

call :verify_installation
if errorlevel 1 (
    echo [ERROR] Installation verification failed
    echo.
    echo [INFO] To fix: Remove virtual environment and re-run setup
    echo [INFO]   Step 1: rmdir /s /q .venv
    echo [INFO]   Step 2: setup-venv.bat
    exit /b 1
)

echo.
echo [OK] Setup complete!
echo.
echo [INFO] Next steps:
echo [INFO]   1. Edit .env with your configuration
echo [INFO]   2. Activate: .venv\Scripts\activate.bat
echo [INFO]   3. Run: datawagon --help
echo.
echo [INFO] Note: Runtime-only install (no dev tools).
echo [INFO] For development, use Poetry: make setup-poetry
goto :eof

REM ============================================================================
REM Check Python version
REM ============================================================================
:check_python
REM Check if Python exists
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 is not installed
    echo [INFO] Install from: https://www.python.org/downloads/
    exit /b 1
)

REM Single Python call for version check and display (optimized)
python -c "import sys; print('OK' if sys.version_info >= (3, 9) else 'FAIL'); print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" > "%TEMP%\dw_pyver.txt" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to check Python version
    del "%TEMP%\dw_pyver.txt" 2>nul
    exit /b 1
)

set /p PY_STATUS=<"%TEMP%\dw_pyver.txt"
if not "%PY_STATUS%"=="OK" (
    for /f "skip=1 tokens=*" %%V in ('type "%TEMP%\dw_pyver.txt"') do (
        echo [ERROR] Python 3.9+ required (found: Python %%V)
    )
    del "%TEMP%\dw_pyver.txt" 2>nul
    exit /b 1
)

for /f "skip=1 tokens=*" %%V in ('type "%TEMP%\dw_pyver.txt"') do (
    echo [OK] Python found: Python %%V
    del "%TEMP%\dw_pyver.txt" 2>nul
    goto :eof
)
del "%TEMP%\dw_pyver.txt" 2>nul
goto :eof

REM ============================================================================
REM Check and create .env file
REM ============================================================================
:check_env_file
REM Verify .env.example exists (critical repo file)
if not exist "%ENV_EXAMPLE%" (
    echo [ERROR] .env.example not found in repository
    echo [ERROR] Repository may be corrupted or incomplete
    echo [INFO] Try: git fetch origin ^&^& git reset --hard origin/main
    exit /b 1
)

if not exist "%ENV_FILE%" (
    echo [WARNING] .env file not found
    echo [INFO] Copying %ENV_EXAMPLE% to %ENV_FILE%
    copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
    if errorlevel 1 (
        echo [ERROR] Failed to copy .env.example to .env
        exit /b 1
    )
    echo [WARNING] Please edit .env and configure: DW_CSV_SOURCE_DIR, DW_GCS_PROJECT_ID, DW_GCS_BUCKET
) else (
    echo [OK] .env file exists
)
goto :eof

REM ============================================================================
REM Create virtual environment
REM ============================================================================
:create_venv
if exist "%VENV%" (
    echo [WARNING] Virtual environment already exists at %VENV%
    set /p RECREATE="Remove and recreate? (y/N): "
    REM Handle empty input (user just pressed Enter)
    if not defined RECREATE set RECREATE=N
    if /i not "!RECREATE!"=="y" (
        echo [INFO] Using existing virtual environment
        goto :eof
    )
    echo [INFO] Removing existing virtual environment...
    rmdir /s /q "%VENV%"
    if errorlevel 1 (
        echo [ERROR] Failed to remove existing virtual environment
        echo [INFO] Check file permissions or if files are in use
        exit /b 1
    )
)

echo [INFO] Creating virtual environment at %VENV%...
python -m venv "%VENV%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    exit /b 1
)
echo [OK] Virtual environment created
goto :eof

REM ============================================================================
REM Install dependencies
REM ============================================================================
:install_deps
echo [INFO] Upgrading pip...
"%VENV%\Scripts\pip.exe" install --upgrade pip --quiet
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip
    exit /b 1
)

echo [INFO] Installing DataWagon and runtime dependencies...
"%VENV%\Scripts\pip.exe" install -e . --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install DataWagon
    exit /b 1
)

echo [OK] Dependencies installed
goto :eof

REM ============================================================================
REM Verify installation
REM ============================================================================
:verify_installation
echo [INFO] Verifying installation...

"%VENV%\Scripts\pip.exe" show datawagon >nul 2>&1
if errorlevel 1 (
    echo [ERROR] DataWagon package not found in virtual environment
    exit /b 1
)

"%VENV%\Scripts\python.exe" -c "import datawagon" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to import datawagon module
    exit /b 1
)

"%VENV%\Scripts\datawagon.exe" --help >nul 2>&1
if errorlevel 1 (
    echo [ERROR] datawagon command exists but failed to run
    exit /b 1
)

REM Check required packages - use explicit success flag to avoid loop issues
set PKG_CHECK_FAILED=0
for %%p in (click pandas pydantic google-cloud-storage) do (
    "%VENV%\Scripts\pip.exe" show %%p >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Required package '%%p' not found
        set PKG_CHECK_FAILED=1
    )
)
if %PKG_CHECK_FAILED% equ 1 exit /b 1

echo [OK] Installation verified successfully
goto :eof
