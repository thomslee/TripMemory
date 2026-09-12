@echo off
chcp 65001 >nul
echo ========================================
echo   途迹记忆 TripMemory - 开发环境启动
echo ========================================
echo.

echo [1/2] 启动后端 (端口 8003)...
cd /d "%~dp0backend"
if not exist ".venv" (
    echo 创建虚拟环境...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
start "TripMemory Backend" cmd /k "python run.py"

echo [2/2] 启动前端 (端口 5174)...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo 安装前端依赖...
    npm install
)
start "TripMemory Frontend" cmd /k "npm run dev"

echo.
echo 启动完成！
echo 后端: http://127.0.0.1:8003
echo 前端: http://127.0.0.1:5174
echo.
pause
