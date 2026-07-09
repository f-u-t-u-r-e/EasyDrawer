"""FastAPI 应用入口 v0.3

v0.3 新增：
- 历史记录 CRUD 端点
- 生成完成后自动保存历史
- 版本号更新到 0.3.0
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from src.config import settings
from src.models.schemas import (
    GenerationRequest,
    GenerationResponse,
    HistoryListResponse,
    ImageStyle,
    LLMConfig,
    StreamEvent,
)
from src.agent.workflow import ImageGenerationAgent
from src.services.history import HistoryService

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("easydrawer")

# 全局实例
agent: ImageGenerationAgent | None = None
history: HistoryService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global agent, history

    logger.info("EasyDrawer v0.3.0 启动中...")

    history = HistoryService()
    agent = ImageGenerationAgent(history_service=history)

    sd_ok = await agent.sd_client.check_health()
    flux_ok = await agent.flux_client.check_health()

    if sd_ok:
        logger.info("✓ Stable Diffusion API 已连接 (%s)", settings.sd_api_url)
    else:
        logger.warning("⚠ Stable Diffusion API 不可用 (%s)", settings.sd_api_url)

    if flux_ok:
        logger.info("✓ FLUX API 已配置")
    else:
        logger.info("⚠ FLUX API 未配置（可选）")

    logger.info("✓ 历史数据库已就绪")

    yield

    if agent:
        await agent.close()
    agent = None
    history = None
    logger.info("EasyDrawer 已关闭")


app = FastAPI(
    title="EasyDrawer API",
    description="智能生图 Agent — Prompt Ensemble + 变体搜索 + img2img 精修",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 基础端点 ─────────────────────────────────────────────


@app.get("/")
async def root():
    return {"service": "EasyDrawer", "version": "0.3.0", "status": "running"}


@app.get("/health")
async def health_check():
    """详细健康检查"""
    sd_ok = await agent.sd_client.check_health() if agent else False
    flux_ok = await agent.flux_client.check_health() if agent else False

    # 检查 API key 配置状态
    api_key_configured = bool(
        settings.anthropic_api_key
        and settings.anthropic_api_key != "your_claude_api_key_here"
        and settings.anthropic_api_key.strip()
    )

    return {
        "api": "healthy",
        "stable_diffusion": "healthy" if sd_ok else "unavailable",
        "flux": "configured" if flux_ok else "not_configured",
        "llm": "configured" if api_key_configured else "not_configured",
        "llm_warning": None if api_key_configured else "ANTHROPIC_API_KEY 未配置，提示词优化功能不可用",
        "default_backend": settings.image_backend,
        "quality_threshold": settings.quality_threshold,
        "max_refinement_rounds": settings.max_refinement_rounds,
    }


# ── 生成端点 ─────────────────────────────────────────────


@app.post("/generate", response_model=GenerationResponse)
async def generate_image(
    request: GenerationRequest,
    x_anthropic_api_key: str | None = Header(None, alias="X-Anthropic-API-Key"),
    x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
    x_llm_base_url: str | None = Header(None, alias="X-LLM-Base-URL"),
    x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
):
    """生成图片（一次性返回）

    支持通过 header 动态配置 LLM:
    - X-Anthropic-API-Key: API 密钥（必需）
    - X-LLM-Provider: 提供商名称（如 anthropic, openai, deepseek）
    - X-LLM-Base-URL: API 基础 URL（可选，用于代理或自定义端点）
    - X-LLM-Model: 模型名称（可选）
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    # 优先使用 header 中的配置，否则使用 .env 配置
    api_key = x_anthropic_api_key or settings.anthropic_api_key
    if not api_key or api_key == "your_claude_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="未配置 API 密钥。请在前端设置面板中配置 LLM 提供商和 API 密钥。"
        )

    try:
        # 线程安全：通过参数传递 LLM 配置，不修改全局 agent
        llm_config = LLMConfig(
            api_key=api_key,
            base_url=x_llm_base_url,
            model=x_llm_model,
        )

        response = await agent.generate(request, llm_config=llm_config)

        # 自动保存历史（异步，不阻塞事件循环）
        if history:
            try:
                await history.save_async(response)
            except Exception as e:
                logger.warning("历史保存失败（不影响返回）: %s", e)
        return response
    except Exception as e:
        logger.exception("生成失败")
        raise HTTPException(status_code=500, detail=f"生成失败: {e}")


@app.post("/generate/stream")
async def generate_image_stream(
    request: GenerationRequest,
    x_anthropic_api_key: str | None = Header(None, alias="X-Anthropic-API-Key"),
    x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
    x_llm_base_url: str | None = Header(None, alias="X-LLM-Base-URL"),
    x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
):
    """生成图片（SSE 流式返回进度）

    支持通过 header 动态配置 LLM
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    # 优先使用 header 中的配置
    api_key = x_anthropic_api_key or settings.anthropic_api_key
    if not api_key or api_key == "your_claude_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="未配置 API 密钥。请在前端设置面板中配置 LLM 提供商和 API 密钥。"
        )

    async def event_generator():
        try:
            # 线程安全：通过参数传递 LLM 配置
            llm_config = LLMConfig(
                api_key=api_key,
                base_url=x_llm_base_url,
                model=x_llm_model,
            )

            final_response = None
            async for event in agent.generate_stream(request, llm_config=llm_config):
                # 捕获最终结果用于保存历史
                if event.get("step") == "complete" and event.get("data"):
                    try:
                        final_response = GenerationResponse.model_validate(event["data"])
                    except Exception:
                        pass
                yield {"event": "progress", "data": json.dumps(event, ensure_ascii=False)}

            # 流结束后保存历史（异步）
            if final_response and history:
                try:
                    await history.save_async(final_response)
                except Exception as e:
                    logger.warning("历史保存失败: %s", e)

        except Exception as e:
            logger.exception("流式生成失败")
            error_event = StreamEvent(
                step="error", status="error", message=str(e)
            ).model_dump()
            yield {"event": "error", "data": json.dumps(error_event, ensure_ascii=False)}

    return EventSourceResponse(event_generator())


@app.post("/optimize-prompt")
async def optimize_prompt_only(
    prompt: str,
    style: str | None = None,
    x_anthropic_api_key: str | None = Header(None, alias="X-Anthropic-API-Key"),
    x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
    x_llm_base_url: str | None = Header(None, alias="X-LLM-Base-URL"),
    x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
):
    """仅优化提示词（不生成图片）

    支持通过 header 动态配置 LLM
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    # 优先使用 header 中的配置
    api_key = x_anthropic_api_key or settings.anthropic_api_key
    if not api_key or api_key == "your_claude_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="未配置 API 密钥。请在前端设置面板中配置 LLM 提供商和 API 密钥。"
        )

    try:
        # 线程安全：创建本地 optimizer，不修改全局 agent
        from src.services.prompt_optimizer import PromptOptimizer

        optimizer = PromptOptimizer(
            api_key=api_key,
            base_url=x_llm_base_url,
            model=x_llm_model,
        )

        style_enum = ImageStyle(style) if style else None
        result = await optimizer.optimize(prompt, style_hint=style_enum)

        return result
    except Exception as e:
        logger.exception("提示词优化失败")
        raise HTTPException(status_code=500, detail=f"优化失败: {e}")


# ── 历史端点 ─────────────────────────────────────────────


@app.get("/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词"),
    backend: str | None = Query(None, description="按后端过滤"),
):
    """查询生成历史"""
    if not history:
        raise HTTPException(status_code=503, detail="历史服务未初始化")

    return await history.list_async(
        page=page, page_size=page_size, search=search, backend=backend
    )


@app.get("/history/{record_id}")
async def get_history_record(record_id: str):
    """获取单条历史记录"""
    if not history:
        raise HTTPException(status_code=503, detail="历史服务未初始化")

    record = await history.get_async(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@app.delete("/history/{record_id}")
async def delete_history_record(record_id: str):
    """删除单条历史记录"""
    if not history:
        raise HTTPException(status_code=503, detail="历史服务未初始化")

    success = await history.delete_async(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"deleted": True}


# ── 入口 ─────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
