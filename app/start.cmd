@echo off


echo.
echo Loading azd .env file from current environment
echo.

@echo off
for /f "tokens=1* delims==" %%a in ('azd env get-values') do (
  set "%%a=%%~b"
)

if "%errorlevel%" neq "0" (
    echo Failed to load environment varaiables from azd environment
    exit /B %errorlevel%
)

echo.
echo Restoring backend python packages
echo.
cd backend
call pip install -r requirements.txt
if "%errorlevel%" neq "0" (
    echo Failed to restore backend python packages
    exit /B %errorlevel%
)

echo.
echo Restoring frontend npm packages
echo.
cd ../frontend
call npm install
if "%errorlevel%" neq "0" (
    echo Failed to restore frontend npm packages
    exit /B %errorlevel%
)

echo.
echo Building frontend
echo.
call npm run build
if "%errorlevel%" neq "0" (
    echo Failed to build frontend
    exit /B %errorlevel%
)

echo.
echo Starting backend
echo.
cd ../backend
start http://127.0.0.1:5000
call python ./app.py
if "%errorlevel%" neq "0" (
    echo Failed to start backend
    exit /B %errorlevel%
)
