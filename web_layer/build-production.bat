@echo off
REM Production Build Script for Options Analysis WebUI
REM Compiles and minifies CSS for production deployment

echo ========================================
echo Building Production Assets
echo ========================================
echo.

echo [1/2] Compiling and minifying CSS...
call npm run build:css
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: CSS build failed!
    exit /b 1
)
echo CSS build complete!
echo.

echo [2/2] Verifying output files...
if exist "static\css\main.css" (
    echo ✓ main.css generated
) else (
    echo ✗ main.css missing!
    exit /b 1
)
echo.

echo ========================================
echo Production Build Complete!
echo ========================================
echo.
echo Output files:
echo   - static/css/main.css (minified)
echo.
echo Ready for deployment!
