# 🚀 EasyDrawer 快速启动指南

## 前置准备

1. ✅ Python 3.11+ 已安装
2. ✅ Node.js 18+ 已安装
3. ✅ Stable Diffusion WebUI 已下载
4. ✅ Claude API Key 已获取

---

## 第一步：配置API密钥

```bash
# 进入项目目录
cd C:\Users\exexex6661\Desktop\EasyDrawer

# 复制环境变量模板
cp .env.example .env

# 编辑.env文件（使用记事本或VSCode）
notepad .env
```

**必填项**:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxx  # 你的Claude API密钥
SD_API_URL=http://localhost:7860     # SD WebUI地址
```

---

## 第二步：启动Stable Diffusion

**Windows**:
```bash
cd D:\stable-diffusion-webui  # 你的SD安装目录
.\webui-user.bat --api
```

**Mac/Linux**:
```bash
cd ~/stable-diffusion-webui
./webui.sh --api
```

等待启动完成，访问 http://localhost:7860 确认可用。

---

## 第三步：启动后端（新终端）

```bash
cd C:\Users\exexex6661\Desktop\EasyDrawer

# 安装Python依赖（首次需要）
pip install -e ".[dev]"

# 启动FastAPI服务
python run.py
```

看到以下提示表示成功：
```
✓ Stable Diffusion API 已连接
INFO:     Uvicorn running on http://0.0.0.0:8000
```

访问 http://localhost:8000/health 检查状态。

---

## 第四步：启动前端（新终端）

```bash
cd C:\Users\exexex6661\Desktop\EasyDrawer\frontend

# Windows
start.bat

# Mac/Linux
chmod +x start.sh
./start.sh
```

首次运行会自动安装依赖，等待完成。

看到以下提示表示成功：
```
  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

---

## 第五步：开始使用！

打开浏览器访问：**http://localhost:3000**

### 🎨 第一次生图

1. 在左侧输入框输入：`一只可爱的橘猫坐在窗台上`
2. 选择风格：`写实`
3. 点击 `开始生成`
4. 等待30-60秒
5. 查看右侧的3张候选图片
6. 标有⭐的是AI评分最高的
7. 点击图片放大预览，点击下载按钮保存

---

## 常见问题

### Q1: 后端启动报错 "SD API连接失败"

**解决**:
1. 确认SD WebUI已启动
2. 确认启动时带了 `--api` 参数
3. 访问 http://localhost:7860 测试

### Q2: Claude API报错

**解决**:
1. 检查`.env`中的`ANTHROPIC_API_KEY`是否正确
2. 确认API密钥有效且有余额
3. 测试命令：
```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### Q3: 前端无法连接后端

**解决**:
1. 确认后端运行在 http://localhost:8000
2. 访问 http://localhost:8000/health
3. 检查浏览器控制台错误

### Q4: 生成速度慢

**原因**: SD生成图片本身需要时间

**优化**:
1. 降低图片尺寸（768x768）
2. 减少采样步数（编辑`parameter_optimizer.py`）
3. 使用更快的采样器（Euler a）

### Q5: 生成的图片质量不好

**调整策略**:
1. 更详细的提示词描述
2. 尝试不同的风格
3. 使用高级设置添加负面提示词
4. 调整参数优化策略（见开发文档）

---

## 进阶操作

### 仅测试提示词优化（不生图）

```bash
curl -X POST "http://localhost:8000/optimize-prompt?prompt=一只猫&style=realistic"
```

### 使用Python API

```python
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            "http://localhost:8000/generate",
            json={"prompt": "一只猫", "style": "realistic"}
        )
        print(response.json())

asyncio.run(test())
```

### 查看API文档

访问：http://localhost:8000/docs

FastAPI自动生成的交互式文档。

---

## 停止服务

**后端**: Ctrl+C  
**前端**: Ctrl+C  
**SD WebUI**: 关闭终端窗口

---

## 下一步

✅ **成功生成第一张图**? 恭喜！

📚 继续学习:
- [开发文档](docs/DEVELOPMENT.md) - 了解核心算法
- [API文档](http://localhost:8000/docs) - 集成到你的项目
- [前端文档](frontend/README.md) - 定制UI

🎨 尝试不同的:
- 提示词风格
- 图片尺寸
- 负面提示词
- 参数调优

💡 **提示**: 详细的提示词 = 更好的结果！

---

**遇到问题？** 查看 [故障排查](#常见问题) 或提交Issue
