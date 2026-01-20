@echo off
REM Build CSS from SCSS
REM This script compiles the SCSS files to CSS

echo Building CSS from SCSS...
cd /d "%~dp0"
call npm run build:css:dev

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ CSS build successful!
    echo Output: static/css/main.css
) else (
    echo.
    echo ✗ CSS build failed!
    exit /b 1
)
