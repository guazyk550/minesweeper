@echo off
chcp 65001 >nul
title Minesweeper Auto-Play  -  live log
cd /d "%~dp0"

set "PYEXE="

rem --- prefer the bundled runtime (it already has numpy / Pillow) ---
if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
    set "PYEXE=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
)
if not defined PYEXE if exist "C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
    set "PYEXE=C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
)

rem --- otherwise fall back to whatever python is on PATH ---
if not defined PYEXE (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if not defined PYEXE set "PYEXE=%%i"
    )
)

if not defined PYEXE (
    echo.
    echo   [!] Python not found.
    echo       Install Python 3 and run:  pip install numpy Pillow
    echo.
    goto done
)

"%PYEXE%" -u "%~dp0autoplay.py" %*
set "RC=%ERRORLEVEL%"

:done
echo.
echo ================================================================
if "%RC%"=="1" echo   No Minesweeper window found - open the game first.
if "%RC%"=="2" echo   Missing python packages: pip install numpy Pillow
if "%RC%"=="3" echo   Could not read the board - keep the window visible.
echo   Finished.  Press any key to exit . . .
echo ================================================================
pause >nul
