"""测试提示词优化器"""

import pytest
from src.services.prompt_optimizer import PromptOptimizer
from src.models.schemas import ImageStyle


@pytest.mark.asyncio
async def test_prompt_optimizer():
    """测试基础提示词优化"""
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
async def test_style_variations():
    """测试不同风格"""
    optimizer = PromptOptimizer()

    styles = [ImageStyle.REALISTIC, ImageStyle.ANIME, ImageStyle.ARTISTIC]

    for style in styles:
        result = await optimizer.optimize("一个女孩在森林里", style_hint=style)
        print(f"\n风格 {style.value}:")
        print(f"  增强: {result.enhanced[:100]}...")
        assert result.style == style
