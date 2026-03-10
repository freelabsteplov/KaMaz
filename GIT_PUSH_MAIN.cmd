@echo off
setlocal EnableExtensions

set "GIT_EXE=C:\Program Files\Git\cmd\git.exe"
if not exist "%GIT_EXE%" set "GIT_EXE=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer\Git\cmd\git.exe"
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "REMOTE_URL=%~1"

if not exist "%GIT_EXE%" (
    echo git.exe not found.
    exit /b 1
)

pushd "%PROJECT_DIR%"

if "%REMOTE_URL%"=="" (
    echo Usage:
    echo GIT_PUSH_MAIN.cmd https://github.com/USER/REPO.git
    popd
    exit /b 1
)

"%GIT_EXE%" rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo This folder is not a git repository.
    popd
    exit /b 1
)

"%GIT_EXE%" remote get-url origin >nul 2>nul
if errorlevel 1 (
    "%GIT_EXE%" remote add origin "%REMOTE_URL%"
) else (
    "%GIT_EXE%" remote set-url origin "%REMOTE_URL%"
)

"%GIT_EXE%" push -u origin main
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
