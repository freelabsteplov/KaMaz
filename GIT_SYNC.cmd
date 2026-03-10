@echo off
setlocal EnableExtensions

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

pushd "%PROJECT_DIR%"
call GIT_SNAPSHOT.cmd
if errorlevel 1 (
    popd
    exit /b 1
)

call GIT_PUSH_MAIN.cmd
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
