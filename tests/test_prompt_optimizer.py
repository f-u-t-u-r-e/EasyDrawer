"""测试提示词优化器

注意：本测试需要有效的 ANTHROPIC_API_KEY 和 anthropic 包，缺少任一时自动跳过。
"""

import pytest

from src.config import settings

# 检查 API key 是否可用
HAS_API_KEY = bool(
    settings.anthropic_api_key
    and settings.anthropic_api_key != "your_claude_api_key_here"
    and settings.anthropic_api_key.strip()
)

# 检查 anthropic 包是否已安装
try:
    import anthropic  # noqa: F401
    HAS_ANTHROPIC_PKG = True
except ImportError:
    HAS_ANTHROPIC_PKG = False

CAN_RUN = HAS_API_KEY and HAS_ANTHROPIC_PKG
SKIP_REASON = "需要 ANTHROPIC_API_KEY 和 anthropic 包"


@pytest.mark.asyncio
@pytest.mark.skipif(not CAN_RUN, reason=SKIP_REASON)
async def test_prompt_optimizer():
    """测试基础提示词优化（需要 API key + anthropic 包）"""
    from src.services.prompt_optimizer import PromptOptimizer
    from src.models.schemas import ImageStyle

    optimizer = PromptOptimizer()

    result = await optimizer.optimize(
        user_prompt="一只可爱的猫咪", style_hint=ImageStyle.REALISTIC
    )

    assert result.original == "一只可爱的猫咪"
    assert len(result.enhanced) > len(result.original)
    assert "cat" in result.enhanced.lower()
    assert len(result.negative) > 0
    assert result.reasoning
    print(f"\n原始: {result.original}")
    print(f"优化: {result.enhanced}")
    print(f"负面: {result.negative}")
    print(f"思路: {result.reasoning}")


@pytest.mark.asyncio
@pytest.mark.skipif(not CAN_RUN, reason=SKIP_REASON)
async def test_style_variations():
    """测试不同风格（需要 API key + anthropic 包）"""
    from src.services.prompt_optimizer import PromptOptimizer
    from src.models.schemas import ImageStyle

    optimizer = PromptOptimizer()

    styles = [ImageStyle.REALISTIC, ImageStyle.ANIME, ImageStyle.ARTISTIC]

    for style in styles:
        result = await optimizer.optimize("一个女孩在森林里", style_hint=style)
        print(f"\n风格 {style.value}:")
        print(f"  增强: {result.enhanced[:100]}...")
        assert result.style == style
