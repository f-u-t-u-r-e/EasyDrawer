"""应用配置"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用元信息
    app_version: str = "0.4.0"

    # LLM配置
    anthropic_api_key: str = ""  # 允许为空，启动时检查
    llm_model: str = "claude-sonnet-4-6"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000

    # 图片生成后端配置
    image_backend: str = "flux"  # "sd" | "flux"
    sd_api_url: str = "http://localhost:7860"
    sd_api_key: str | None = None
    flux_api_url: str = "https://api.bfl.ai/v1"
    flux_api_key: str | None = None
    flux_model_endpoint: str = "flux-2-pro-preview"
    flux_output_format: str = "jpeg"
    flux_safety_tolerance: int = 2
    flux_disable_pup: bool = False
    flux_poll_timeout: float = 120.0

    # 生成参数
    sd_batch_size: int = 3
    flux_batch_size: int = 3
    max_refinement_rounds: int = 2  # 反馈循环最大轮次
    quality_threshold: float = 75.0  # 低于此分数触发重新生成

    # 质量评估
    clip_model_name: str = "ViT-L-14"
    clip_pretrained: str = "openai"

    # 应用配置
    debug: bool = False
    log_level: str = "INFO"
    max_concurrent_generations: int = 3
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
