@echo off
setlocal EnableExtensions

set "GIT_EXE=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer\Git\cmd\git.exe"
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

if not exist "%GIT_EXE%" (
    echo git.exe not found:
    echo %GIT_EXE%
    exit /b 1
)

pushd "%PROJECT_DIR%"

"%GIT_EXE%" rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    "%GIT_EXE%" init
)

"%GIT_EXE%" config user.name >nul 2>nul
if errorlevel 1 (
    "%GIT_EXE%" config user.name "post"
)

"%GIT_EXE%" config user.email >nul 2>nul
if errorlevel 1 (
    "%GIT_EXE%" config user.email "post@local"
)

for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString(\"yyyy-MM-dd HH:mm:ss\")"') do set "STAMP=%%I"

"%GIT_EXE%" add .
"%GIT_EXE%" diff --cached --quiet
if not errorlevel 1 (
    echo No staged changes to commit.
    popd
    exit /b 0
)

"%GIT_EXE%" commit -m "Snapshot %STAMP%"
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
