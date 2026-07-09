# EasyDrawer - 智能生图 Agent

> 通过算法优化，让相同模型生成更优质的图片

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 为什么选择 EasyDrawer？

直接调用生图 API 只能得到"能用"的图。EasyDrawer 通过 **Prompt Ensemble + CLIP 评分 + Seed 精搜 + img2img 精修** 四阶段管线，自动产出精品图片。

| 传统方式 | EasyDrawer v0.3 |
|---------|-----------------|
| 手写提示词 | 3 变体 Prompt Ensemble 自动生成最优提示词 |
| 1 张碰运气 | 批量生成 → CLIP 评分 → 只返回最佳 |
| 质量不可控 | Seed 邻域搜索 + img2img 精修双重打磨 |
| 不支持多 LLM | 前端自由切换 Anthropic / OpenAI / DeepSeek / 自定义 |

## 快速开始

### 1. 启动项目

```bash
cd EasyDrawer

# 一键启动后端（自动检测环境，无需预先配置）
python run.py

# 同时启动前端
python run.py --frontend
```

### 2. 配置 LLM

打开浏览器访问 http://localhost:3000，点击右上角齿轮按钮配置 API：

- **提供商**: Anthropic / OpenAI / DeepSeek / Moonshot / 智谱 / 自定义
- **API 地址**: 支持代理、中转、内网部署
- **API Key**: 仅保存在浏览器中

无需编辑 .env，无需重启服务。

### 3. 开始生图

输入描述 → 选择风格 → 点击生成，等待 30-60 秒即可获得精修后的最佳图片。

## 工作流程

```
用户输入
  │
  ├─→ 提示词优化     3 变体 Ensemble（构图/光影/细节）
  ├─→ 参数优化       自动选择最优 Steps/CFG/Sampler
  ├─→ 批量生成       SD 4.0 / FLUX 双后端
  ├─→ CLIP 评分      批量推理，2-3x 加速
  ├─→ 质量评估       不达标自动反馈重试
  ├─→ Seed 精搜      邻域搜索更优种子
  ├─→ img2img 精修   低强度去噪，保留构图提升细节
  │
  └─→ 返回最佳结果
```

## 技术栈

**后端**
- FastAPI 0.139 — 异步高性能 API
- LangGraph 1.2 — 8 节点工作流编排
- CLIP ViT-L/14 — 批量图片质量评分
- Anthropic SDK — 结构化输出 + Prompt 缓存

**前端**
- React 18 + TypeScript + Vite 5
- TailwindCSS 4 + Lucide React

**支持的后端**
- Stable Diffusion WebUI / API
- FLUX API

## 启动选项

```bash
# 后端
python run.py                  # 交互式启动
python run.py --install        # 强制安装依赖
python run.py --skip-install   # 跳过依赖检查

# 前端（独立启动）
cd frontend
python start.py                # 跨平台 Python 启动器
# 或
start.bat                      # Windows
./start.sh                     # Linux/macOS
```

## API 接口

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/health` | 健康检查 |
| POST | `/generate` | 完整生图 |
| POST | `/generate/stream` | SSE 流式生图 |
| POST | `/optimize-prompt` | 仅优化提示词 |
| GET | `/history` | 查询生成历史 |
| GET | `/history/{id}` | 获取历史详情 |
| DELETE | `/history/{id}` | 删除历史记录 |

接口文档: http://localhost:8000/docs

## Python API 示例

```python
import httpx
import asyncio

async def generate():
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            "http://localhost:8000/generate",
            headers={"X-Anthropic-API-Key": "your-api-key"},
            json={"prompt": "一只英短蓝猫", "style": "realistic"}
        )
        data = resp.json()
        print(f"质量分: {data['best_image']['quality_score']:.1f}")

asyncio.run(generate())
```

## 项目结构

```
EasyDrawer/
├── src/
│   ├── api/main.py              # FastAPI 入口
│   ├── agent/workflow.py        # LangGraph 8 节点工作流
│   ├── services/
│   │   ├── prompt_optimizer.py  # 提示词优化 + 结构化输出
│   │   ├── parameter_optimizer.py  # 参数智能调优
│   │   ├── sd_client.py         # SD API 客户端
│   │   ├── flux_client.py       # FLUX API 客户端
│   │   ├── quality_scorer.py    # CLIP 批量评分
│   │   └── history.py           # SQLite 历史持久化
│   ├── models/schemas.py        # Pydantic 数据模型
│   └── config.py                # 配置管理
├── frontend/                    # React 前端
│   └── src/components/          # UI 组件
├── data/prompts/                # 提示词库
├── tests/                       # 测试
├── run.py                       # 跨平台启动脚本
└── pyproject.toml
```

## 系统要求

- Python 3.11+
- Node.js 18+（仅前端）
- Stable Diffusion WebUI 或 FLUX 或任意 SD API

## License

MIT
