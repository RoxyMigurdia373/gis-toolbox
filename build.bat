@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
py -3.11 -m venv .venv
if not errorlevel 1 goto install
py -3.12 -m venv .venv
if not errorlevel 1 goto install
echo 未找到 Python 3.11/3.12，请先在开发机安装 64 位 Python。接收软件的同事不需要安装。
pause
exit /b 1
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\build_desktop.py
if errorlevel 1 goto failed
echo.
echo 打包完成：%CD%\dist\GISToolbox\GISToolbox.exe
echo 请拷贝整个 GISToolbox 文件夹，不要只拷贝 exe。
pause
exit /b 0
:failed
echo 打包失败，请检查上方错误信息。详见 README.md。
pause
exit /b 1
