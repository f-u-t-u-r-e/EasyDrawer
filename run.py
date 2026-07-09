#!/usr/bin/env python3
"""EasyDrawer 跨平台启动脚本

支持 Windows / macOS / Linux，自动检测环境并引导用户完成配置。

用法:
    python run.py              # 交互式启动（首次运行引导配置）
    python run.py --install    # 强制安装/更新依赖
    python run.py --skip-install  # 跳过依赖询问直接启动
    python run.py --frontend   # 同时启动前端（需要 Node.js）
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# 项目根目录 = run.py 所在目录
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
ENV_FILE = ROOT_DIR / ".env"
ENV_EXAMPLE = ROOT_DIR / ".env.example"
DATA_DIR = ROOT_DIR / "data"


def print_banner():
    """打印启动横幅"""
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║  🎨 EasyDrawer v0.3 — 智能生图 Agent     ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print(f"  系统: {platform.system()} {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  项目: {ROOT_DIR}")
    print()


def check_python():
    """检查 Python 版本"""
    if sys.version_info < (3, 11):
        print(f"  ❌ 需要 Python 3.11+，当前 {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")


def check_env() -> bool:
    """检查并创建 .env 配置文件

    Returns:
        bool: True 表示 API key 已配置，False 表示未配置但允许继续运行
    """
    if ENV_FILE.exists():
        # 检查是否填了 API key
        content = ENV_FILE.read_text(encoding="utf-8")
        if "your_claude_api_key_here" in content or "ANTHROPIC_API_KEY=\n" in content:
            print("  ⚠️  .env 文件存在但 ANTHROPIC_API_KEY 未填写")
            print("  ℹ️  服务器将启动，但提示词优化功能不可用")
            print(f"  📝 配置后请编辑: {ENV_FILE}")
            print()
            return False
        print("  ✓ .env 已配置")
        return True

    if not ENV_EXAMPLE.exists():
        print("  ❌ .env.example 不存在，项目文件不完整")
        sys.exit(1)

    print("  ⚠️  .env 不存在，从 .env.example 复制...")
    shutil.copy2(str(ENV_EXAMPLE), str(ENV_FILE))
    print("  ℹ️  服务器将启动，但提示词优化功能不可用")
    print(f"  📝 需要完整功能请编辑: {ENV_FILE}")
    print()
    _open_file_hint(ENV_FILE)
    return False


def _open_file_hint(filepath: Path):
    """提示用户如何打开文件"""
    system = platform.system()
    if system == "Windows":
        print(f"     运行: notepad {filepath}")
    elif system == "Darwin":
        print(f"     运行: open {filepath}")
    else:
        print(f"     运行: nano {filepath}  或  vim {filepath}")


def ensure_data_dirs():
    """确保数据目录存在"""
    dirs = [
        DATA_DIR / "prompts",
        DATA_DIR / "models",
        DATA_DIR / "outputs",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("  ✓ 数据目录就绪")


def install_dependencies():
    """安装 Python 依赖"""
    print("\n  📦 安装 Python 依赖...\n")
    cmd = [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode != 0:
        print("\n  ❌ 依赖安装失败")
        print("  💡 提示: 如果 torch 安装慢，可以先手动装 CPU 版本:")
        print("     pip install torch --index-url https://download.pytorch.org/whl/cpu")
        sys.exit(1)
    print("\n  ✓ 依赖安装完成")


def check_node():
    """检查 Node.js 是否可用"""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✓ Node.js {version}")
            return True
    except FileNotFoundError:
        pass
    print("  ⚠️  Node.js 未安装（前端需要，后端可独立运行）")
    return False


def install_frontend():
    """安装前端依赖"""
    if not FRONTEND_DIR.exists():
        print("  ⚠️  frontend 目录不存在")
        return False

    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        print("  ✓ 前端依赖已安装")
        return True

    print("\n  📦 安装前端依赖...\n")
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
    result = subprocess.run([npm_cmd, "install"], cwd=str(FRONTEND_DIR))
    if result.returncode != 0:
        print("\n  ❌ 前端依赖安装失败")
        return False
    print("\n  ✓ 前端依赖安装完成")
    return True


def start_backend():
    """启动后端服务"""
    print("\n  🚀 启动后端 API 服务...\n")
    print("  后端地址: http://localhost:8000")
    print("  API 文档: http://localhost:8000/docs")
    print("  健康检查: http://localhost:8000/health")
    print()

    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR))


def start_frontend_background():
    """后台启动前端开发服务器"""
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"

    kwargs = {}
    if platform.system() == "Windows":
        # Windows: CREATE_NEW_PROCESS_GROUP 让前端在独立窗口运行
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        **kwargs,
    )
    print("  ✓ 前端开发服务器已启动: http://localhost:3000")


def main():
    print_banner()

    # 环境检查
    print("  ── 环境检查 ──")
    check_python()
    api_configured = check_env()
    ensure_data_dirs()
    has_node = check_node()
    print()

    if not api_configured:
        print("  ⚠️  未检测到 Claude API 密钥")
        print("  ℹ️  您仍可以访问界面，但无法使用生图功能")
        print()

    # 依赖安装
    if "--install" in sys.argv:
        install_dependencies()
        if has_node:
            install_frontend()
    elif "--skip-install" not in sys.argv:
        # 检查是否已安装核心依赖
        try:
            import fastapi  # noqa: F401
            import langgraph  # noqa: F401
            print("  ✓ Python 依赖已安装")
        except ImportError:
            print("  ⚠️  检测到核心依赖未安装")
            response = input("  是否安装依赖? (Y/n): ").strip().lower()
            if response != "n":
                install_dependencies()

    # 前端
    if "--frontend" in sys.argv and has_node:
        install_frontend()
        start_frontend_background()

    # 启动后端
    start_backend()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  👋 服务已停止")
    except Exception as e:
        print(f"\n  ❌ 错误: {e}")
        sys.exit(1)
