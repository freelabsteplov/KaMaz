@echo off
setlocal EnableExtensions

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "PROJECT_NAME="
for %%I in ("%PROJECT_DIR%\*.uproject") do (
    if not defined PROJECT_NAME set "PROJECT_NAME=%%~nI"
)

if not defined PROJECT_NAME (
    for %%I in ("%PROJECT_DIR%") do set "PROJECT_NAME=%%~nxI"
)

for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString(\"yyyy-MM-dd_HH-mm-ss\")"') do set "STAMP=%%I"

set "BACKUP_ROOT=%USERPROFILE%\Documents\UnrealProjectBackups"
set "DEST=%BACKUP_ROOT%\%PROJECT_NAME%_%STAMP%"

if not exist "%BACKUP_ROOT%" mkdir "%BACKUP_ROOT%"
mkdir "%DEST%"

robocopy "%PROJECT_DIR%" "%DEST%" /E ^
 /XD ".vs" "Binaries" "DerivedDataCache" "Intermediate" "Saved\Autosaves" "Saved\Backup" "Saved\Cooked" "Saved\Crashes" "Saved\Logs" "Saved\MaterialStats" "Saved\StagedBuilds" ^
 /XF "*.tmp" "*.suo" "*.opensdf" "*.VC.db" >nul

set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo Backup failed. robocopy exit code: %RC%
    exit /b 1
)

echo Backup created:
echo %DEST%
exit /b 0
