@echo off
setlocal
cd /d "%~dp0"
echo [1/4] Running the Python data pipeline...
python -m src.pipeline || goto :error
echo [2/4] Running automated tests...
pytest -q || goto :error
echo [3/4] Building report charts...
python -m src.make_charts || goto :error
echo [4/4] Building the interactive HTML dashboard...
python scripts\build_dashboard.py || goto :error
echo.
echo SUCCESS. Check data\processed, excel, reports\charts and dashboard\index.html.
pause
exit /b 0
:error
echo.
echo FAILED. Read the error above and check README.md for setup instructions.
pause
exit /b 1
