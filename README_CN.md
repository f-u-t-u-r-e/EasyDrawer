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

| 传统方式 | EasyDrawer v0.4 |
|---------|-----------------|
| 手写提示词 | 3 变体 Prompt Ensemble 自动生成最优提示词 |
| 1 张碰运气 | 批量生成 → CLIP 评分 → MMR 多样性选图 |
| 质量不可控 | CFG 变体搜索 + img2img 精修双重打磨 |
| 参数靠经验 | ε-greedy Bandit 从历史评分自动学习最优参数 |
| 反馈只调词 | 联合调参：根据薄弱维度同时调整提示词 + CFG/Steps |
| 厂商锁定 | 前端自由切换 Anthropic / OpenAI / DeepSeek / 自定义 |

## v0.4 新特性

### 算法优化

- **MMR 多样性选图**：不再纯选最高分。当 top-2 分差 < 5 分时，计算 CLIP embedding 余弦距离，用 `MMR = 0.7×质量 + 0.3×多样性` 选图，保留 Ensemble 多样性价值
- **参数 Bandit 反馈**：系统从历史数据库读取同场景+风格的历史参数和评分，用 ε-greedy 策略（ε=0.2）自动调整 CFG/Steps。仅当历史最优桶均分高出 2+ 分时才调整，平滑过渡避免跳变
- **反馈循环联合调参**：反馈不仅调整提示词，还根据薄弱维度生成参数调整建议（sharpness 低 → +steps，CLIP 低 → +CFG），通过 `param_adjustment` 传递给参数优化器
- **CLIP 长度自适应校准**：按 prompt token 数分三档校准 CLIP 相似度区间，消除长 prompt 被系统性低估的偏差
- **连续评分函数**：分辨率/亮度/对比度/清晰度全部改用 sigmoid 连续函数，替代阶梯式阈值，消除评分跳变
- **自适应变体步长**：根据当前 CFG/guidance 在合法区间中的位置动态计算偏移，避免 clamp 到边界后产生无差异变体

### 工程改进

- **线程安全**：LLM 配置通过参数传递，每请求独立 optimizer，彻底消除并发竞态条件
- **Ensemble 并发生成**：`asyncio.gather` 替代串行循环，3 变体并发生成，约 60% 提速
- **异步数据库**：所有 SQLite 操作通过 `asyncio.to_thread` 包装，不再阻塞事件循环
- **并发控制**：`asyncio.Semaphore` 限制同时执行的生图任务数
- **错误边保护**：生成失败时自动跳转 END，不会继续执行后续评分节点

### 前端重构 — "Aurora Glass"

- 玻璃拟态（Glassmorphism）设计风格，暖色调辉光背景
- Plus Jakarta Sans + Noto Sans SC 字体
- 浮动极光动画、图片悬浮缩放、质量分解进度条
- 风格选择卡片、生图引擎切换、示例提示词

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

### 3. 开始生图

输入描述 → 选择风格 → 点击生成，等待 30-60 秒即可获得精修后的最佳图片。

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

无 CLIP 模型时自动降级为 `technical_only` 模式（技术 50% + 清晰度 50%），下游可通过 `scoring_mode` 字段感知。

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

**支持的后端**: Stable Diffusion (WebUI / API) · FLUX

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

自定义 LLM 请求头：`X-LLM-API-Key`、`X-LLM-Base-URL`、`X-LLM-Model`

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
- Stable Diffusion WebUI（需开启 `--api` 参数）/ FLUX / 或任意兼容 SD 的 API
- Anthropic Claude API Key（或兼容的 OpenAI 端点）

## License

MIT

