# EasyDrawer

> Better images through algorithmic optimization — no model upgrade required

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文文档](README_CN.md)

## Why EasyDrawer?

Calling a generation API directly gives you "usable" images. EasyDrawer adds an 8-stage **Prompt Ensemble → CLIP Scoring → Variant Search → img2img Refinement** pipeline that automates quality optimization.

| Raw API | EasyDrawer |
|---------|-----------------|
| Manual prompt writing | 3-variant prompt ensemble, AI-optimized |
| One-shot luck | Batch generation → CLIP scoring → MMR diversity selection |
| Unpredictable quality | CFG variant search + img2img refinement |
| Manual parameter tuning | ε-greedy Bandit learns optimal params from history |
| Feedback only tweaks words | Joint adjustment: prompt + CFG/Steps based on weak dimensions |
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
  ├─→ Parameter Tuning   Bandit feedback + scene-adaptive steps/CFG/sampler
  ├─→ Concurrent Gen     asyncio.gather for 3 variants in parallel
  ├─→ CLIP Scoring       Batch inference, prompt-length adaptive calibration
  ├─→ Quality Gate       Joint feedback: prompt + parameter adjustments
  ├─→ Variant Search     Fixed seed, adaptive-step CFG tuning
  ├─→ img2img Refine     Low-denoise polish preserving structure
  ├─→ MMR Selection      Quality + diversity weighted best pick
  │
  └─→ Return best result
```

## Quality Scoring System

| Dimension | Weight | Description |
|-----------|--------|-------------|
| CLIP Similarity | 40% | Text-image match, prompt-length adaptive calibration |
| Aesthetic Score | 30% | LAION aesthetic model, sigmoid probability mapping |
| Technical Quality | 15% | Resolution + brightness + contrast, sigmoid continuous |
| Sharpness | 15% | Laplacian variance, log-scaled continuous function |

When CLIP is available but the optional aesthetic predictor is missing, scoring degrades to `clip_only` mode (CLIP 55% + technical 20% + sharpness 25%). When CLIP is unavailable, it uses `technical_only` mode (technical 50% + sharpness 50%). Downstream consumers can detect this via the `scoring_mode` field.

## Tech Stack

**Backend**
- FastAPI 0.139 — Async high-performance API
- LangGraph 1.2 — 8-node workflow orchestration
- CLIP ViT-L/14 — Batch image quality scoring
- Anthropic SDK — Structured output + prompt caching
- SQLite — History persistence + Bandit parameter stats

**Frontend**
- React 18 + TypeScript + Vite 6
- TailwindCSS 4 + Lucide React
- Glassmorphism design system

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
| POST | `/generate` | Full generation (supports custom LLM config) |
| POST | `/generate/stream` | SSE streaming generation |
| POST | `/optimize-prompt` | Prompt optimization only |
| GET | `/history` | Query generation history |
| GET | `/history/{id}` | Get history detail |
| DELETE | `/history/{id}` | Delete history record |

Custom LLM headers: `X-LLM-API-Key`, `X-LLM-Base-URL`, `X-LLM-Model`. Legacy `X-Anthropic-API-Key` is still accepted.

API docs: http://localhost:8000/docs

## Python API

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
            json={"prompt": "a british shorthair blue cat", "style": "realistic"}
        )
        data = resp.json()
        print(f"Quality score: {data['best_image']['quality_score']:.1f}")
        print(f"Generation time: {data['generation_time']:.1f}s")
        print(f"Image count: {len(data['images'])}")

asyncio.run(generate())
```

## Project Structure

```
EasyDrawer/
├── src/
│   ├── api/main.py                  # FastAPI entry point
│   ├── agent/workflow.py            # LangGraph 8-node workflow + MMR selection
│   ├── services/
│   │   ├── prompt_optimizer.py      # Prompt optimization + structured output
│   │   ├── parameter_optimizer.py   # Parameter tuning + ε-greedy Bandit
│   │   ├── sd_client.py             # SD API client + adaptive variant search
│   │   ├── flux_client.py           # FLUX API client + adaptive variant search
│   │   ├── quality_scorer.py        # CLIP scoring + continuous functions + embeddings
│   │   └── history.py               # SQLite history + Bandit parameter stats
│   ├── models/schemas.py            # Pydantic models + LLMConfig
│   └── config.py                    # Configuration
├── frontend/                        # React frontend (Aurora Glass)
│   └── src/
│       ├── components/              # UI components
│       ├── styles/index.css         # Design system
│       └── types/api.ts             # TypeScript types
├── data/                            # Database + prompt libraries
├── tests/                           # Tests
├── run.py                           # Cross-platform launcher
└── pyproject.toml
```

## Requirements

- Python 3.11+
- Node.js 18+ (frontend only)
- Stable Diffusion WebUI (with `--api` flag) / FLUX / or any SD-compatible API
- Anthropic Claude API Key (or compatible OpenAI endpoint)

## License

MIT

