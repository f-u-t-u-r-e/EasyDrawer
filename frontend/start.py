#!/usr/bin/env python3
"""EasyDrawer 前端启动脚本（跨平台）

自动检测环境并启动前端开发服务器。

用法:
    cd frontend
    python start.py           # 自动安装依赖并启动
    python start.py --skip    # 跳过依赖检查直接启动
"""

import platform
import subprocess
import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent
PACKAGE_JSON = FRONTEND_DIR / "package.json"
NODE_MODULES = FRONTEND_DIR / "node_modules"


def print_banner():
    print()
    print("  🎨 EasyDrawer 前端开发服务器")
    print()


def check_node():
    """检查 Node.js"""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✓ Node.js {version}")
            major = int(version.lstrip("v").split(".")[0])
            if major < 18:
                print(f"  ⚠️  建议使用 Node.js 18+，当前 {version}")
            return True
    except FileNotFoundError:
        pass

    print("  ❌ Node.js 未安装")
    print()
    print("  请先安装 Node.js 18+:")
    if platform.system() == "Windows":
        print("    https://nodejs.org/zh-cn/download/")
    else:
        print("    https://nodejs.org/ 或使用 nvm")
    sys.exit(1)


def check_package_json():
    """检查是否在正确目录"""
    if not PACKAGE_JSON.exists():
        print("  ❌ package.json 不存在")
        print(f"  请在 frontend 目录下运行此脚本")
        print(f"  当前目录: {Path.cwd()}")
        sys.exit(1)
    print("  ✓ package.json 已找到")


def install_dependencies():
    """安装依赖"""
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"

    if NODE_MODULES.exists():
        print("  ✓ node_modules 已存在")
        return

    print("\n  📦 安装前端依赖...")
    print("     这可能需要几分钟...\n")
    result = subprocess.run([npm_cmd, "install"], cwd=str(FRONTEND_DIR))
    if result.returncode != 0:
        print("\n  ❌ 依赖安装失败")
        sys.exit(1)
    print("\n  ✓ 依赖安装完成")


def start_dev_server():
    """启动开发服务器"""
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"

    print("\n  🚀 启动开发服务器...\n")
    print("  前端地址: http://localhost:3000")
    print("  按 Ctrl+C 停止服务")
    print()

    subprocess.run([npm_cmd, "run", "dev"], cwd=str(FRONTEND_DIR))


def main():
    print_banner()
    check_node()
    check_package_json()

    if "--skip" not in sys.argv:
        install_dependencies()

    start_dev_server()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  👋 开发服务器已停止")
    except Exception as e:
        print(f"\n  ❌ 错误: {e}")
        sys.exit(1)
