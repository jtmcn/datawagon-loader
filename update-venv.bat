@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM DataWagon Update Script - Runtime Updates (Non-Poetry)
REM ============================================================================
REM Updates DataWagon and runtime dependencies only.
REM
REM Requirements:
REM   - Python 3.9 or higher
REM   - Git (for repository updates)
REM   - Internet connection for pip downloads
REM
REM For development with full tooling, use Poetry: make setup-poetry
REM
REM Platform notes:
REM   - Windows uses [OK]/[ERROR] prefixes vs Unix ✓/✗ symbols
REM   - This is intentional for CMD compatibility (no ANSI colors)
REM ============================================================================

REM Variables
set BRANCH=main
set VENV=.venv
set ENV_FILE=.env
set ENV_EXAMPLE=.env.example
set HAS_UPDATES=0

REM Main execution
call :main
exit /b %ERRORLEVEL%

REM ============================================================================
REM Main function
REM ============================================================================
:main
echo [INFO] DataWagon Update Script (Non-Poetry)
echo [INFO] =====================================
echo.

call :check_venv
if errorlevel 1 exit /b 1

call :check_python
if errorlevel 1 exit /b 1

call :check_env_file
if errorlevel 1 exit /b 1

call :update_git
REM update_git returns 0 if updates found, 1 if no updates, 2+ if error
if errorlevel 2 (
    echo [ERROR] Git update failed
    exit /b 1
)
if errorlevel 1 (
    set HAS_UPDATES=0
) else (
    set HAS_UPDATES=1
)

echo.

if !HAS_UPDATES! equ 1 (
    call :update_deps
    if errorlevel 1 exit /b 1
) else (
    echo [INFO] No git updates
    echo [INFO] Run '%VENV%\Scripts\pip.exe install -e . --upgrade' to update anyway
)

echo.
echo [OK] Update complete!
goto :eof

REM ============================================================================
REM Check virtual environment exists
REM ============================================================================
:check_venv
if not exist "%VENV%" (
    echo [ERROR] Virtual environment not found at %VENV%
    echo [INFO] Run setup-venv.bat first
    exit /b 1
)
echo [OK] Virtual environment found
goto :eof

REM ============================================================================
REM Check Python version
REM ============================================================================
:check_python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 is not installed
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
REM Update git repository
REM ============================================================================
:update_git
echo [INFO] Checking for git updates on %BRANCH%...

REM Verify git is installed
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git not found in PATH
    echo [INFO] Install from: https://git-scm.com/download/win
    echo [INFO] Alternatively, update manually with: %VENV%\Scripts\pip.exe install -e . --upgrade
    exit /b 2
)

REM Switch to main branch
git switch --quiet %BRANCH% 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to switch to branch %BRANCH%
    exit /b 1
)

REM Fetch updates
git fetch --quiet 2>nul
if errorlevel 1 (
    echo [WARNING] Failed to fetch from remote (continuing anyway)
)

REM Check for updates
git diff --quiet origin/%BRANCH% %BRANCH% 2>nul
if errorlevel 1 (
    echo [INFO] Updates found, pulling changes...

    REM Check for uncommitted changes
    set HAS_UNCOMMITTED=0
    git diff --quiet 2>nul
    if errorlevel 1 set HAS_UNCOMMITTED=1
    git diff --cached --quiet 2>nul
    if errorlevel 1 set HAS_UNCOMMITTED=1

    if !HAS_UNCOMMITTED! equ 1 (
        echo [WARNING] You have uncommitted changes
        echo [INFO] Git will temporarily stash them during update
        set /p CONTINUE="Continue? (y/N): "
        REM Handle empty input (user just pressed Enter)
        if not defined CONTINUE set CONTINUE=N
        if /i not "!CONTINUE!"=="y" (
            echo [INFO] Update cancelled
            exit /b 1
        )
    )

    git pull --quiet -r --autostash origin %BRANCH%
    if errorlevel 1 (
        echo [ERROR] Failed to pull from origin
        exit /b 2
    )
    echo [OK] Git repository updated
    exit /b 0
) else (
    echo [OK] Repository is up to date
    exit /b 1
)

REM ============================================================================
REM Update Python dependencies
REM ============================================================================
:update_deps
echo [INFO] Updating dependencies...

"%VENV%\Scripts\pip.exe" install --upgrade pip --quiet
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip
    exit /b 1
)

echo [INFO] Upgrading DataWagon...
"%VENV%\Scripts\pip.exe" install -e . --upgrade --quiet
if errorlevel 1 (
    echo [ERROR] Failed to upgrade DataWagon
    exit /b 1
)

echo [OK] Dependencies updated

call :verify_installation
if errorlevel 1 (
    echo [ERROR] Update completed but verification failed
    echo.
    echo [INFO] To fix: Remove virtual environment and re-run setup
    echo [INFO]   Step 1: rmdir /s /q .venv
    echo [INFO]   Step 2: setup-venv.bat
    exit /b 1
)
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

REM ============================================================================
REM Check .env file
REM ============================================================================
:check_env_file
REM Verify .env.example exists (critical repo file)
if not exist "%ENV_EXAMPLE%" (
    echo [ERROR] .env.example not found in repository
    echo [ERROR] Repository may be corrupted. Try: git fetch ^&^& git reset --hard origin/main
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
    echo [WARNING] Please edit .env with your configuration
) else (
    echo [OK] .env file exists
)
goto :eof
