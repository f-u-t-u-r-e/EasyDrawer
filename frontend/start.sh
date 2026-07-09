#!/bin/bash

echo "🎨 EasyDrawer 快速启动脚本"
echo ""

# 检查是否在frontend目录
if [ ! -f "package.json" ]; then
    echo "❌ 请在frontend目录下运行此脚本"
    exit 1
fi

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 首次运行，安装依赖..."
    npm install
    echo ""
fi

echo "🚀 启动开发服务器..."
echo "访问: http://localhost:3000"
echo ""
npm run dev
