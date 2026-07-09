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


def test_bandit_ignores_one_off_high_score(monkeypatch):
    """单条高分样本不足以覆盖默认参数，避免过拟合偶然结果"""
    monkeypatch.setattr("src.services.parameter_optimizer.random.random", lambda: 0.9)
    optimizer = ParameterOptimizer()

    history = [
        {"params": {"cfg_scale": 10.0, "steps": 35}, "score": 99.0},
        {"params": {"cfg_scale": 6.0, "steps": 25}, "score": 70.0},
        {"params": {"cfg_scale": 6.0, "steps": 25}, "score": 71.0},
    ]

    params = optimizer.optimize_sd(
        prompt="portrait photo",
        negative_prompt="ugly",
        scene_type=SceneType.PORTRAIT,
        style=ImageStyle.REALISTIC,
        history=history,
    )

    assert params.cfg_scale == pytest.approx(6.0)
    assert params.steps == 25


def test_bandit_smoothly_adjusts_with_supported_history(monkeypatch):
    """有重复历史证据时，bandit 应向高分桶平滑靠拢"""
    monkeypatch.setattr("src.services.parameter_optimizer.random.random", lambda: 0.9)
    optimizer = ParameterOptimizer()

    history = [
        {"params": {"cfg_scale": 6.0, "steps": 25}, "score": 70.0},
        {"params": {"cfg_scale": 6.0, "steps": 25}, "score": 71.0},
        {"params": {"cfg_scale": 8.0, "steps": 30}, "score": 86.0},
        {"params": {"cfg_scale": 8.0, "steps": 30}, "score": 87.0},
    ]

    params = optimizer.optimize_sd(
        prompt="portrait photo",
        negative_prompt="ugly",
        scene_type=SceneType.PORTRAIT,
        style=ImageStyle.REALISTIC,
        history=history,
    )

    assert params.cfg_scale == pytest.approx(7.2)
    assert params.steps == 28
