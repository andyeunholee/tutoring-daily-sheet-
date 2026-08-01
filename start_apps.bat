@echo off
REM Starts both tutoring apps and leaves them running in two minimised windows.
REM The http://localhost links only work while this is running, and only on
REM this PC. Close the two windows to stop the apps.

cd /d "%~dp0"

echo Starting the tutoring apps...
echo.

start "Tutoring - teacher form" /min cmd /c python -m streamlit run app.py --server.port 8501 --server.headless true
echo   [1/2] Teacher form   http://localhost:8501

start "Tutoring - review" /min cmd /c python -m streamlit run review_app.py --server.port 8502 --server.headless true
echo   [2/2] Review app     http://localhost:8502

echo.
echo Both are starting up - give them about 10 seconds.
echo Leave the two minimised windows open; closing them stops the apps.
echo.
timeout /t 8 >nul
