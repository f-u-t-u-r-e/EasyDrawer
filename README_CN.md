# EasyDrawer

> 通过算法优化，让相同模型生成更优质的图片 — 无需升级模型

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md)

## 为什么选择 EasyDrawer？

直接调用生图 API 只能得到"能用"的图。EasyDrawer 通过 **Prompt Ensemble → CLIP 评分 → 变体搜索 → img2img 精修** 八阶段管线，自动产出精品图片。

| 传统方式 | EasyDrawer |
|---------|-----------------|
| 手写提示词 | 3 变体 Prompt Ensemble 自动生成最优提示词 |
| 1 张碰运气 | 批量生成 → CLIP 评分 → MMR 多样性选图 |
| 质量不可控 | CFG 变体搜索 + img2img 精修双重打磨 |
| 参数靠经验 | ε-greedy Bandit 从历史评分自动学习最优参数 |
| 反馈只调词 | 联合调参：根据薄弱维度同时调整提示词 + CFG/Steps |
| 厂商锁定 | 前端自由切换 Anthropic / OpenAI / DeepSeek / 自定义 |

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
- **API Key**: 仅保存在浏览器中，不会上传到服务器存储

无需编辑 .env，无需重启服务。

### 3. 配置 BFL FLUX

如果你希望全程调用云端 API 生图，只需要在 `.env` 写入 BFL key：

```env
IMAGE_BACKEND=flux
FLUX_API_URL=https://api.bfl.ai/v1
FLUX_API_KEY=your_bfl_api_key_here
FLUX_MODEL_ENDPOINT=flux-2-pro-preview
```

默认使用 `flux-2-pro-preview`，适合优先追求质量和新能力；如果需要固定生产快照，可以改成 `flux-2-pro`。

### 4. 开始生图

输入描述 → 选择风格 → 点击生成。EasyDrawer 会自动优化提示词，调用 BFL FLUX 生成候选图，评分后返回最佳图片。

## 工作流程

```
用户输入
  │
  ├─→ 提示词优化       3 变体 Ensemble（构图/光影/细节）
  ├─→ 参数优化         Bandit 反馈 + 场景自适应 Steps/CFG/Sampler
  ├─→ 并发生成         asyncio.gather 并发生成 3 变体
  ├─→ CLIP 评分        批量推理，prompt 长度自适应校准
  ├─→ 质量评估         联合反馈：提示词 + 参数调整建议
  ├─→ 变体搜索         固定 seed，自适应步长微调 CFG
  ├─→ img2img 精修     低强度去噪，保留构图提升细节
  ├─→ MMR 选图         质量 + 多样性加权选最佳
  │
  └─→ 返回最佳结果
```

## 质量评分体系

| 维度 | 权重 | 说明 |
|------|------|------|
| CLIP 相似度 | 40% | 图文匹配度，按 prompt 长度自适应校准 |
| 美学评分 | 30% | LAION 美学模型，sigmoid 概率映射 |
| 技术质量 | 15% | 分辨率 + 亮度 + 对比度，sigmoid 连续函数 |
| 清晰度 | 15% | 拉普拉斯方差，log 缩放连续函数 |

当 CLIP 可用但可选美学模型缺失时，自动降级为 `clip_only` 模式（CLIP 55% + 技术 20% + 清晰度 25%）。无 CLIP 模型时降级为 `technical_only` 模式（技术 50% + 清晰度 50%），下游可通过 `scoring_mode` 字段感知。

## 技术栈

**后端**
- FastAPI 0.139 — 异步高性能 API
- LangGraph 1.2 — 8 节点工作流编排
- CLIP ViT-L/14 — 批量图片质量评分
- Anthropic SDK — 结构化输出 + Prompt 缓存
- SQLite — 历史记录 + Bandit 参数统计

**前端**
- React 18 + TypeScript + Vite 6
- TailwindCSS 4 + Lucide React
- Glassmorphism 设计系统

**支持的后端**: BFL FLUX API · Stable Diffusion (WebUI / API)

## 启动选项

```bash
# 后端
python run.py                  # 交互式启动
python run.py --install        # 强制安装依赖
python run.py --skip-install   # 跳过依赖检查

# 前端（独立启动）
cd frontend
python start.py                # 跨平台 Python 启动器
start.bat                      # Windows
./start.sh                     # Linux/macOS
```

## API 接口

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/health` | 健康检查 |
| POST | `/generate` | 完整生图（支持自定义 LLM 配置） |
| POST | `/generate/stream` | SSE 流式生图 |
| POST | `/optimize-prompt` | 仅优化提示词 |
| GET | `/history` | 查询生成历史 |
| GET | `/history/{id}` | 获取历史详情 |
| DELETE | `/history/{id}` | 删除历史记录 |

自定义 LLM 请求头：`X-LLM-API-Key`、`X-LLM-Base-URL`、`X-LLM-Model`。旧版 `X-Anthropic-API-Key` 仍兼容。

接口文档: http://localhost:8000/docs

## Python API 示例

```python
import httpx
import asyncio

async def generate():
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            "http://localhost:8000/generate",
            headers={
                "X-LLM-API-Key": "your-api-key",
                "X-LLM-Model": "claude-sonnet-4-20250514",
            },
            json={"prompt": "一只英短蓝猫", "style": "realistic"}
        )
        data = resp.json()
        print(f"质量分: {data['best_image']['quality_score']:.1f}")
        print(f"生成时间: {data['generation_time']:.1f}s")
        print(f"图片数: {len(data['images'])}")

asyncio.run(generate())
```

## 项目结构

```
EasyDrawer/
├── src/
│   ├── api/main.py                  # FastAPI 入口
│   ├── agent/workflow.py            # LangGraph 8 节点工作流 + MMR 选图
│   ├── services/
│   │   ├── prompt_optimizer.py      # 提示词优化 + 结构化输出
│   │   ├── parameter_optimizer.py   # 参数优化 + ε-greedy Bandit
│   │   ├── sd_client.py             # SD API 客户端 + 自适应变体搜索
│   │   ├── flux_client.py           # FLUX API 客户端 + 自适应变体搜索
│   │   ├── quality_scorer.py        # CLIP 评分 + 连续函数 + embedding
│   │   └── history.py               # SQLite 历史 + Bandit 参数统计
│   ├── models/schemas.py            # Pydantic 模型 + LLMConfig
│   └── config.py                    # 配置管理
├── frontend/                        # React 前端 (Aurora Glass)
│   └── src/
│       ├── components/              # UI 组件
│       ├── styles/index.css         # 设计系统
│       └── types/api.ts             # TypeScript 类型
├── data/                            # 数据库 + 提示词库
├── tests/                           # 测试
├── run.py                           # 跨平台启动脚本
└── pyproject.toml
```

## 系统要求

- Python 3.11+
- Node.js 18+（仅前端）
- BFL FLUX API Key（云端生图）
- Anthropic Claude API Key（或兼容的 OpenAI 端点，用于提示词优化）
- Stable Diffusion WebUI（仅在使用 `IMAGE_BACKEND=sd` 时需要开启 `--api` 参数）

## License

MIT

