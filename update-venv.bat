@echo off
setlocal enabledelayedexpansion

REM DataWagon Update Script - Runtime Updates (Non-Poetry)
REM Updates DataWagon and runtime dependencies only.

REM Variables
set BRANCH=main
set VENV=.venv
set ENV_FILE=.env
set ENV_EXAMPLE=.env.example
set GIT_UPDATED=0

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
if errorlevel 1 (
    REM No updates found (errorlevel 1 from update_git means no updates)
    set GIT_UPDATED=0
) else (
    REM Updates were found and pulled
    set GIT_UPDATED=1
)

echo.

if !GIT_UPDATED! equ 1 (
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

REM Check Python version using Python itself (portable and reliable)
python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.9+ required
    python -c "import sys; print(f'[ERROR] Found: Python {sys.version_info.major}.{sys.version_info.minor}')" 2>nul
    exit /b 1
)

REM Display version
python -c "import sys; print(f'[OK] Python found: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
goto :eof

REM ============================================================================
REM Update git repository
REM ============================================================================
:update_git
echo [INFO] Checking for git updates on %BRANCH%...

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
    set UNCOMMITTED=0
    git diff --quiet 2>nul
    if errorlevel 1 set UNCOMMITTED=1
    git diff --cached --quiet 2>nul
    if errorlevel 1 set UNCOMMITTED=1

    if !UNCOMMITTED! equ 1 (
        echo [WARNING] You have uncommitted changes
        echo [INFO] Git will temporarily stash them during update
        set /p CONTINUE="Continue? (y/N): "
        if /i not "!CONTINUE!"=="y" (
            echo [INFO] Update cancelled
            exit /b 0
        )
    )

    git pull --quiet -r --autostash origin %BRANCH%
    if errorlevel 1 (
        echo [ERROR] Failed to pull from origin
        exit /b 1
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
    echo [WARNING] Update completed but verification failed
    echo [INFO] May need reinstall: rmdir /s /q .venv ^&^& setup-venv.bat
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

REM Check required packages
for %%p in (click pandas pydantic google-cloud-storage) do (
    "%VENV%\Scripts\pip.exe" show %%p >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Required package '%%p' not found
        exit /b 1
    )
)

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
