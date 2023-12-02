@echo off
setlocal enabledelayedexpansion

:: Set the virtual environment name
set VENV_NAME=.venv

:: Check if the virtual environment exists
if not exist %VENV_NAME% (
    echo Virtual environment not found. Please run the setup script first.
    exit /b 1
)

:: Activate the virtual environment
call %VENV_NAME%\Scripts\activate
if !errorlevel! neq 0 (
    echo Failed to activate virtual environment.
    exit /b 1
)

:: Run the Python file located in "src/main.py"
start /B pythonw src\main.py

:: Deactivate the virtual environment
deactivate

:: Exit
exit /b 0
