@echo off
setlocal
cd /d "%~dp0"
set "amrPython="
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 -c "import tkinter" >nul 2>nul
  if not errorlevel 1 set "amrPython=py -3"
)
if not defined amrPython (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import tkinter" >nul 2>nul
    if not errorlevel 1 set "amrPython=python"
  )
)
if not defined amrPython (
  if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" main.py %*
    if errorlevel 1 pause
    exit /b
  )
  echo Please install Python 3.10 or newer with Tcl/Tk from python.org.
  pause
  exit /b 1
)
%amrPython% main.py %*
if errorlevel 1 pause
