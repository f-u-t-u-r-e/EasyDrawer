@echo off
echo 🎨 EasyDrawer 快速启动脚本
echo.

REM 检查是否在frontend目录
if not exist package.json (
    echo ❌ 请在frontend目录下运行此脚本
    exit /b 1
)

REM 检查node_modules
if not exist node_modules (
    echo 📦 首次运行，安装依赖...
    call npm install
    echo.
)

echo 🚀 启动开发服务器...
echo 访问: http://localhost:3000
echo.
call npm run dev
