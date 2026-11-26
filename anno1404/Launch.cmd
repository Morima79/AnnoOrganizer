@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto check_python
where py >nul 2>&1
if errorlevel 1 goto use_python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto check_python
:use_python
where python >nul 2>&1
if errorlevel 1 goto missing_python
python -m venv .venv
if errorlevel 1 goto failed
:check_python
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 goto missing_python
".venv\Scripts\python.exe" -c "import PIL, xlsxwriter, tzdata" >nul 2>&1
if not errorlevel 1 goto run_tools
echo Installing the required Python packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run_tools
".venv\Scripts\python.exe" launch.py %*
set "annoorganizer_exit=%errorlevel%"
if "%~1"=="" pause
exit /b %annoorganizer_exit%
:missing_python
echo Please install Python 3.11 or newer, then open Launch.cmd again.
goto failed
:failed
echo ANNO - Organizer could not start. Please check the message above.
pause
exit /b 1
