"""数据模型定义

v0.3 新增：
- PromptVariant: 提示词变体（Ensemble用）
- PromptOptimizationOutput: 结构化输出模型（替代裸JSON解析）
- HistoryRecord: 生成历史记录
- GenerationResponse 增加 prompt_variants 字段
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ImageStyle(str, Enum):
    """图片风格枚举"""

    REALISTIC = "realistic"
    ARTISTIC = "artistic"
    ANIME = "anime"
    CONCEPT_ART = "concept_art"
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class SceneType(str, Enum):
    """场景类型"""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    PRODUCT = "product"
    ARTISTIC = "artistic"
    ARCHITECTURE = "architecture"


class ImageBackend(str, Enum):
    """图片生成后端"""

    SD = "sd"
    FLUX = "flux"


class LLMConfig(BaseModel):
    """LLM 配置 — 通过请求参数传递，避免修改全局 agent（线程安全）"""

    api_key: str | None = Field(None, description="LLM API 密钥")
    base_url: str | None = Field(None, description="API 基础 URL（代理/中转/自部署）")
    model: str | None = Field(None, description="模型名称")


class GenerationRequest(BaseModel):
    """生图请求"""

    prompt: str = Field(..., description="用户输入的描述")
    style: ImageStyle | None = Field(None, description="期望风格")
    negative_prompt: str | None = Field(None, description="负面提示词")
    width: int = Field(1024, ge=512, le=2048, description="宽度")
    height: int = Field(1024, ge=512, le=2048, description="高度")
    session_id: str | None = Field(None, description="会话ID（用于多轮对话）")
    backend: ImageBackend | None = Field(None, description="指定生图后端")


# ── 提示词优化 ─────────────────────────────────────────────


class PromptVariant(BaseModel):
    """单个提示词变体"""

    enhanced: str = Field(..., description="英文正面提示词")
    negative: str = Field(..., description="英文负面提示词")
    focus: str = Field(..., description="该变体的侧重点，中文简述")


class PromptOptimizationOutput(BaseModel):
    """LLM 结构化输出 — 3 个提示词变体 + 元信息

    用 Claude tool_use 替代裸 JSON 解析，彻底消除格式错误。
    """

    scene_type: str = Field(..., description="portrait|landscape|product|artistic|architecture")
    style: str = Field(..., description="realistic|artistic|anime|concept_art|portrait|landscape")
    reasoning: str = Field(..., description="中文，简要说明整体优化思路")
    variants: list[PromptVariant] = Field(
        ...,
        description="3个提示词变体，每个侧重点不同",
        min_length=1,
        max_length=5,
    )


class OptimizedPrompt(BaseModel):
    """优化后的提示词（含多变体）"""

    original: str = Field(..., description="原始输入")
    enhanced: str = Field(..., description="主变体正面提示词")
    negative: str = Field(..., description="负面提示词")
    scene_type: SceneType = Field(..., description="场景类型")
    style: ImageStyle = Field(..., description="风格")
    reasoning: str = Field(..., description="优化思路")
    variants: list[PromptVariant] = Field(
        default_factory=list,
        description="额外提示词变体",
    )


# ── 生图参数 ─────────────────────────────────────────────


class SDParameters(BaseModel):
    """Stable Diffusion参数"""

    prompt: str
    negative_prompt: str
    steps: int = 25
    cfg_scale: float = 7.0
    width: int = 1024
    height: int = 1024
    sampler_name: str = "DPM++ 2M Karras"
    seed: int = -1
    # img2img 精修字段
    init_image: str | None = Field(None, description="img2img 输入图片 base64")
    denoising_strength: float | None = Field(None, ge=0.0, le=1.0, description="img2img 降噪强度")


class FLUXParameters(BaseModel):
    """FLUX模型参数"""

    prompt: str
    width: int = 1024
    height: int = 1024
    steps: int = 4  # Legacy FLUX endpoints may use this; FLUX.2 pro ignores it.
    guidance: float = 3.5
    seed: int = -1


# ── 质量评分 ─────────────────────────────────────────────


class QualityBreakdown(BaseModel):
    """质量评分分解"""

    clip_similarity: float = Field(..., description="CLIP文本-图片相似度 0-100")
    aesthetic_score: float = Field(..., description="美学评分 0-100")
    technical_score: float = Field(..., description="技术质量 0-100")
    sharpness: float = Field(..., description="清晰度 0-100")
    overall: float = Field(..., description="综合加权分 0-100")
    scoring_mode: str = Field(
        "full",
        description="评分模式: full=CLIP+美学+技术, clip_only=CLIP+技术, technical_only=仅技术指标",
    )


class GeneratedImage(BaseModel):
    """生成的图片"""

    image_data: str = Field(..., description="Base64编码的图片数据")
    seed: int = Field(..., description="随机种子")
    quality_score: float | None = Field(None, description="综合质量评分")
    quality_breakdown: QualityBreakdown | None = Field(None, description="评分细项")
    parameters: SDParameters | FLUXParameters = Field(..., description="生成参数")
    variant_index: int = Field(0, description="来自哪个提示词变体 (0-based)")
    is_refined: bool = Field(False, description="是否经过 img2img 精修")


# ── 响应 ─────────────────────────────────────────────


class GenerationResponse(BaseModel):
    """生图响应"""

    session_id: str
    optimized_prompt: OptimizedPrompt
    images: list[GeneratedImage]
    best_image: GeneratedImage
    generation_time: float = Field(..., description="生成耗时（秒）")
    refinement_rounds: int = Field(0, description="经过的优化轮次")
    backend_used: str = Field("sd", description="使用的生图后端")


class StreamEvent(BaseModel):
    """SSE流式事件"""

    step: str
    status: str  # "running" | "done" | "error"
    message: str
    progress: float = Field(0.0, ge=0.0, le=1.0, description="进度 0-1")
    data: dict[str, Any] | None = None


# ── 历史记录 ─────────────────────────────────────────────


class HistoryRecord(BaseModel):
    """生成历史记录"""

    id: str
    created_at: datetime
    prompt: str
    style: str | None = None
    backend: str
    best_score: float | None = None
    image_count: int
    generation_time: float
    refinement_rounds: int
    # 存储时只保留最佳图片的 base64（节省空间）
    best_image_data: str
    best_seed: int
    optimized_prompt_text: str
    quality_breakdown: QualityBreakdown | None = None


class HistoryListResponse(BaseModel):
    """历史记录列表响应"""

    records: list[HistoryRecord]
    total: int
    page: int
    page_size: int
