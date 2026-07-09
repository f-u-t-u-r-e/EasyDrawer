# EasyDrawer - AI Image Generation Agent

> Better images through algorithmic optimization — no model upgrade required

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文文档](README_CN.md)

## Why EasyDrawer?

Calling a generation API directly gives you "usable" images. EasyDrawer adds a **Prompt Ensemble → CLIP Scoring → Variant Search → img2img Refinement** pipeline that automates quality optimization.

| Raw API | EasyDrawer v0.3 |
|---------|-----------------|
| Manual prompt writing | 3-variant prompt ensemble, AI-optimized |
| One-shot luck | Batch generation → CLIP scoring → best pick |
| Unpredictable quality | CFG variant search + img2img refinement |
| Vendor lock-in | Switch LLMs on the fly: Anthropic / OpenAI / DeepSeek / custom |

## Quick Start

### 1. Launch

```bash
cd EasyDrawer

# Start backend (auto-detects environment, no config required)
python run.py

# Or start both frontend and backend
python run.py --frontend
```

### 2. Configure LLM

Open http://localhost:3000, click the gear icon in the top-right corner:

- **Provider**: Anthropic / OpenAI / DeepSeek / Moonshot / Zhipu / Custom (OpenAI-compatible)
- **API URL**: Supports proxies, relays, self-hosted endpoints
- **API Key**: Stored in browser only, never sent to the server for storage

No `.env` editing required. No restart needed.

### 3. Generate

Enter a description → pick a style → click Generate. In 30-60 seconds you get the refined best image.

## Pipeline

```
User Input
  │
  ├─→ Prompt Optimize    3-variant ensemble (composition / lighting / detail)
  ├─→ Parameter Tuning   Auto-optimal steps, CFG, sampler per scene type
  ├─→ Batch Generate     SD 4.0 / FLUX dual backends
  ├─→ CLIP Scoring       Batch inference, 2-3x speedup
  ├─→ Quality Gate       Auto-retry with feedback if score < threshold
  ├─→ Variant Search     Fixed seed, tuned CFG for better variants
  ├─→ img2img Refine     Low-denoise polish preserving structure, enhancing detail
  │
  └─→ Return best result
```

## Tech Stack

**Backend**
- FastAPI 0.139 — Async high-performance API
- LangGraph 1.2 — 8-node workflow orchestration
- CLIP ViT-L/14 — Batch image quality scoring
- Anthropic SDK — Structured output + prompt caching

**Frontend**
- React 18 + TypeScript + Vite 5
- TailwindCSS 4 + Lucide React

**Supported Backends**: Stable Diffusion (WebUI / API) · FLUX

## Run Options

```bash
# Backend
python run.py                  # Interactive start
python run.py --install        # Force install dependencies
python run.py --skip-install   # Skip dependency check

# Frontend (standalone)
cd frontend
python start.py                # Cross-platform launcher
start.bat                      # Windows
./start.sh                     # Linux/macOS
```

## API Endpoints

| Method | Path | Description |
|-----|------|------|
| GET | `/health` | Health check |
| POST | `/generate` | Full generation |
| POST | `/generate/stream` | SSE streaming generation |
| POST | `/optimize-prompt` | Prompt optimization only |
| GET | `/history` | Query generation history |
| GET | `/history/{id}` | Get history detail |
| DELETE | `/history/{id}` | Delete history record |

API docs: http://localhost:8000/docs

## Python API

```python
import httpx
import asyncio

async def generate():
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            "http://localhost:8000/generate",
            headers={"X-Anthropic-API-Key": "your-api-key"},
            json={"prompt": "a british shorthair blue cat", "style": "realistic"}
        )
        data = resp.json()
        print(f"Quality score: {data['best_image']['quality_score']:.1f}")

asyncio.run(generate())
```

## Project Structure

```
EasyDrawer/
├── src/
│   ├── api/main.py              # FastAPI entry point
│   ├── agent/workflow.py        # LangGraph 8-node workflow
│   ├── services/
│   │   ├── prompt_optimizer.py  # Prompt optimization + structured output
│   │   ├── parameter_optimizer.py  # Parameter auto-tuning
│   │   ├── sd_client.py         # SD API client
│   │   ├── flux_client.py       # FLUX API client
│   │   ├── quality_scorer.py    # CLIP batch scoring
│   │   └── history.py           # SQLite history persistence
│   ├── models/schemas.py        # Pydantic data models
│   └── config.py                # Configuration
├── frontend/                    # React frontend
│   └── src/components/          # UI components
├── data/prompts/                # Prompt libraries
├── tests/                       # Tests
├── run.py                       # Cross-platform launcher
└── pyproject.toml
```

## Requirements

- Python 3.11+
- Node.js 18+ (frontend only)
- Stable Diffusion WebUI / FLUX / or any SD-compatible API

## License

MIT
