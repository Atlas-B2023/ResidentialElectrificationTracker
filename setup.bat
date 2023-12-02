@echo off
setlocal enabledelayedexpansion

:: Prompt the user for the path to Python executable
set /p PYTHON_PATH="Enter the path to your Python 3.12 executable: "
if not exist "!PYTHON_PATH!" (
    echo Python executable not found at specified path.
    exit /b 1
)

:: Set the virtual environment name
set VENV_NAME=.venv

:: Check if the virtual environment already exists
if exist %VENV_NAME% (
    echo Virtual environment already exists.
) else (
    :: Create the virtual environment
    !PYTHON_PATH! -m venv %VENV_NAME%
    if !errorlevel! neq 0 (
        echo Failed to create virtual environment.
        exit /b 1
    )
    echo Virtual environment created.
)

:: Activate the virtual environment
call %VENV_NAME%\Scripts\activate
if !errorlevel! neq 0 (
    echo Failed to activate virtual environment.
    exit /b 1
)

:: Install PyQt5 using pip
pip install -r requirements.txt

:: Deactivate the virtual environment
deactivate

:: Exit
exit /b 0
