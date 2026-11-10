@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
python -X utf8 -m src %*
set "result=%errorlevel%"
popd
exit /b %result%
