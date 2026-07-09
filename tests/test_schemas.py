"""测试 schema 变更 — LLMConfig 和 QualityBreakdown.scoring_mode"""

from src.models.schemas import LLMConfig, QualityBreakdown


def test_llm_config_defaults():
    """LLMConfig 默认值应为 None"""
    config = LLMConfig()
    assert config.api_key is None
    assert config.base_url is None
    assert config.model is None


def test_llm_config_with_values():
    """LLMConfig 应正确存储配置"""
    config = LLMConfig(api_key="sk-test", base_url="https://api.example.com", model="claude-3")
    assert config.api_key == "sk-test"
    assert config.base_url == "https://api.example.com"
    assert config.model == "claude-3"


def test_quality_breakdown_default_scoring_mode():
    """QualityBreakdown 默认 scoring_mode 应为 'full'"""
    breakdown = QualityBreakdown(
        clip_similarity=80.0,
        aesthetic_score=75.0,
        technical_score=70.0,
        sharpness=85.0,
        overall=77.5,
    )
    assert breakdown.scoring_mode == "full"


def test_quality_breakdown_technical_only():
    """QualityBreakdown 应支持 technical_only 模式"""
    breakdown = QualityBreakdown(
        clip_similarity=50.0,
        aesthetic_score=50.0,
        technical_score=82.0,
        sharpness=78.0,
        overall=80.0,
        scoring_mode="technical_only",
    )
    assert breakdown.scoring_mode == "technical_only"


def test_quality_breakdown_clip_only():
    """QualityBreakdown 应支持 CLIP 可用但美学模型缺失的模式"""
    breakdown = QualityBreakdown(
        clip_similarity=78.0,
        aesthetic_score=50.0,
        technical_score=82.0,
        sharpness=80.0,
        overall=79.9,
        scoring_mode="clip_only",
    )
    assert breakdown.scoring_mode == "clip_only"
