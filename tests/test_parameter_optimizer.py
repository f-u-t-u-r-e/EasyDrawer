"""测试参数优化器"""

import pytest
from src.services.parameter_optimizer import ParameterOptimizer
from src.models.schemas import ImageStyle, SceneType


def test_parameter_optimizer_sd():
    """测试 SD 参数优化"""
    optimizer = ParameterOptimizer()

    # 测试人像场景
    params = optimizer.optimize_sd(
        prompt="a beautiful woman",
        negative_prompt="ugly",
        scene_type=SceneType.PORTRAIT,
        style=ImageStyle.REALISTIC,
    )

    assert params.steps >= 20
    assert params.cfg_scale >= 5.0
    assert params.sampler_name
    print(f"\n人像参数: steps={params.steps}, cfg={params.cfg_scale}, sampler={params.sampler_name}")

    # 测试风景场景
    params_landscape = optimizer.optimize_sd(
        prompt="mountain landscape",
        negative_prompt="ugly",
        scene_type=SceneType.LANDSCAPE,
        style=ImageStyle.REALISTIC,
    )

    print(
        f"风景参数: steps={params_landscape.steps}, cfg={params_landscape.cfg_scale}, sampler={params_landscape.sampler_name}"
    )

    # 风景场景通常需要更多步数
    assert params_landscape.steps >= params.steps


def test_parameter_optimizer_flux():
    """测试 FLUX 参数优化"""
    optimizer = ParameterOptimizer()

    params = optimizer.optimize_flux(
        prompt="a beautiful woman",
        scene_type=SceneType.PORTRAIT,
    )

    assert params.steps >= 4
    assert params.guidance > 0
    print(f"\nFLUX人像参数: steps={params.steps}, guidance={params.guidance}")
