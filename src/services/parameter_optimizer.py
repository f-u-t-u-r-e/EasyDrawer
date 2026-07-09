"""参数优化器 — 根据场景自动选择最优生图参数

2026 最佳实践：
- DPM++ 2M Karras 是社区标准采样器
- CFG Scale: 6(写实) → 7(默认) → 8-9(复杂)，不超过 10
- Steps: 20-30 是最佳性价比区间
- FLUX: guidance 3.0-4.0，steps 4(schnell)/25(pro)

v0.4 新增：
- bandit 反馈：基于历史评分自动调整 CFG/Steps（ε-greedy 策略）
- 参数调整建议：反馈循环中根据薄弱维度微调参数
"""

import logging
import random
from collections import defaultdict

from src.models.schemas import ImageStyle, SceneType, SDParameters, FLUXParameters

logger = logging.getLogger(__name__)


class ParameterOptimizer:
    """参数优化器 — 根据场景和风格自动调整参数"""

    # SD 场景参数映射
    SD_SCENE_PARAMS: dict[SceneType, dict] = {
        SceneType.PORTRAIT: {
            "steps": 25,
            "cfg_scale": 6.5,
            "sampler_name": "DPM++ 2M Karras",
        },
        SceneType.LANDSCAPE: {
            "steps": 28,
            "cfg_scale": 7.5,
            "sampler_name": "DPM++ 2M Karras",
        },
        SceneType.ARTISTIC: {
            "steps": 30,
            "cfg_scale": 8.0,
            "sampler_name": "DPM++ 2M Karras",
        },
        SceneType.PRODUCT: {
            "steps": 25,
            "cfg_scale": 7.0,
            "sampler_name": "DPM++ 2M Karras",
        },
        SceneType.ARCHITECTURE: {
            "steps": 28,
            "cfg_scale": 7.5,
            "sampler_name": "DPM++ 2M Karras",
        },
    }

    # SD 风格微调（CFG 偏移量、Steps 偏移量）
    SD_STYLE_ADJ: dict[ImageStyle, dict] = {
        ImageStyle.REALISTIC: {"cfg_scale": -0.5, "steps": 0},
        ImageStyle.ARTISTIC: {"cfg_scale": +1.0, "steps": +5},
        ImageStyle.ANIME: {"cfg_scale": +0.5, "steps": 0},
        ImageStyle.CONCEPT_ART: {"cfg_scale": +0.5, "steps": +2},
        ImageStyle.PORTRAIT: {"cfg_scale": -0.5, "steps": 0},
        ImageStyle.LANDSCAPE: {"cfg_scale": +0.5, "steps": +2},
    }

    # FLUX 场景参数映射
    FLUX_SCENE_PARAMS: dict[SceneType, dict] = {
        SceneType.PORTRAIT: {"steps": 4, "guidance": 3.0},
        SceneType.LANDSCAPE: {"steps": 4, "guidance": 3.5},
        SceneType.ARTISTIC: {"steps": 4, "guidance": 4.0},
        SceneType.PRODUCT: {"steps": 4, "guidance": 3.5},
        SceneType.ARCHITECTURE: {"steps": 4, "guidance": 3.5},
    }

    # bandit 探索率 — ε-greedy 中 ε 的值
    BANDIT_EPSILON = 0.2

    # ── bandit 反馈 ──────────────────────────────────────────

    def _bandit_adjust_cfg(
        self,
        base_cfg: float,
        history: list[dict] | None,
        min_cfg: float = 5.0,
        max_cfg: float = 10.0,
    ) -> float:
        """ε-greedy 策略调整 CFG

        Args:
            base_cfg: 基础 CFG 值（查表得出）
            history: 历史记录列表 [{params, score}, ...]
            min_cfg: CFG 下限
            max_cfg: CFG 上限

        Returns:
            调整后的 CFG 值
        """
        if not history or len(history) < 3:
            # 历史不足 3 条，无法统计，用基础值
            return base_cfg

        # ε-greedy: 有 ε 概率探索（用基础值），1-ε 概率利用（用历史最优）
        if random.random() < self.BANDIT_EPSILON:
            return base_cfg

        # 按 CFG 分桶统计平均分（桶宽 0.5）
        cfg_buckets: dict[float, list[float]] = defaultdict(list)
        for record in history:
            params = record.get("params", {})
            score = record.get("score", 0)
            cfg = params.get("cfg_scale")
            if cfg is not None:
                bucket = round(cfg * 2) / 2  # 归到 0.5 的桶
                cfg_buckets[bucket].append(score)

        if not cfg_buckets:
            return base_cfg

        # 找到历史均分最高的 CFG 桶
        best_bucket = max(
            cfg_buckets.keys(),
            key=lambda b: sum(cfg_buckets[b]) / len(cfg_buckets[b]),
        )
        best_avg = sum(cfg_buckets[best_bucket]) / len(cfg_buckets[best_bucket])

        # 计算基础 CFG 桶的历史均分
        base_bucket = round(base_cfg * 2) / 2
        base_avg = (
            sum(cfg_buckets[base_bucket]) / len(cfg_buckets[base_bucket])
            if base_bucket in cfg_buckets
            else 0
        )

        # 仅当历史最优桶明显更好（>2 分）时才调整
        if best_avg - base_avg > 2.0:
            # 向历史最优桶平滑过渡（取加权平均，避免跳变）
            adjusted = base_cfg * 0.4 + best_bucket * 0.6
            logger.info(
                "bandit 调整 CFG: %.1f → %.1f (历史最优桶 %.1f 均分 %.1f vs 基础桶均分 %.1f)",
                base_cfg, adjusted, best_bucket, best_avg, base_avg,
            )
            return max(min_cfg, min(max_cfg, adjusted))

        return base_cfg

    def _bandit_adjust_steps(
        self,
        base_steps: int,
        history: list[dict] | None,
        min_steps: int = 20,
        max_steps: int = 35,
    ) -> int:
        """ε-greedy 策略调整 Steps

        逻辑同 _bandit_adjust_cfg，按 steps 分桶统计。
        """
        if not history or len(history) < 3:
            return base_steps

        if random.random() < self.BANDIT_EPSILON:
            return base_steps

        steps_buckets: dict[int, list[float]] = defaultdict(list)
        for record in history:
            params = record.get("params", {})
            score = record.get("score", 0)
            steps = params.get("steps")
            if steps is not None:
                steps_buckets[steps].append(score)

        if not steps_buckets:
            return base_steps

        best_bucket = max(
            steps_buckets.keys(),
            key=lambda b: sum(steps_buckets[b]) / len(steps_buckets[b]),
        )
        best_avg = sum(steps_buckets[best_bucket]) / len(steps_buckets[best_bucket])

        if base_steps in steps_buckets:
            base_avg = sum(steps_buckets[base_steps]) / len(steps_buckets[base_steps])
        else:
            base_avg = 0

        if best_avg - base_avg > 2.0:
            adjusted = round(base_steps * 0.4 + best_bucket * 0.6)
            logger.info(
                "bandit 调整 Steps: %d → %d (历史最优 %d 均分 %.1f)",
                base_steps, adjusted, best_bucket, best_avg,
            )
            return max(min_steps, min(max_steps, adjusted))

        return base_steps

    # ── 参数优化主接口 ────────────────────────────────────────

    def optimize_sd(
        self,
        prompt: str,
        negative_prompt: str,
        scene_type: SceneType,
        style: ImageStyle,
        width: int = 1024,
        height: int = 1024,
        history: list[dict] | None = None,
        param_adjustment: dict | None = None,
    ) -> SDParameters:
        """生成优化后的 SD 参数

        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            scene_type: 场景类型
            style: 风格
            width: 宽度
            height: 高度
            history: 历史参数统计（bandit 反馈用）
            param_adjustment: 参数调整建议（反馈循环用）
                支持 keys: cfg_delta, steps_delta
        """
        base = self.SD_SCENE_PARAMS.get(scene_type, self.SD_SCENE_PARAMS[SceneType.ARTISTIC])
        adj = self.SD_STYLE_ADJ.get(style, {"cfg_scale": 0, "steps": 0})

        # 基础值
        final_cfg = base["cfg_scale"] + adj["cfg_scale"]
        final_steps = base["steps"] + adj["steps"]

        # bandit 反馈调整
        final_cfg = self._bandit_adjust_cfg(final_cfg, history)
        final_steps = self._bandit_adjust_steps(final_steps, history)

        # 反馈循环参数调整（优化3: 联合调参）
        if param_adjustment:
            final_cfg += param_adjustment.get("cfg_delta", 0)
            final_steps += param_adjustment.get("steps_delta", 0)

        # 限制在合法范围
        final_cfg = max(5.0, min(10.0, final_cfg))
        final_steps = max(20, min(35, final_steps))

        return SDParameters(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=final_steps,
            cfg_scale=final_cfg,
            width=width,
            height=height,
            sampler_name=base["sampler_name"],
            seed=-1,
        )

    def optimize_flux(
        self,
        prompt: str,
        scene_type: SceneType,
        width: int = 1024,
        height: int = 1024,
        history: list[dict] | None = None,
        param_adjustment: dict | None = None,
    ) -> FLUXParameters:
        """生成优化后的 FLUX 参数

        Args:
            prompt: 正向提示词
            scene_type: 场景类型
            width: 宽度
            height: 高度
            history: 历史参数统计（bandit 反馈用）
            param_adjustment: 参数调整建议（反馈循环用）
                支持 keys: guidance_delta, steps_delta
        """
        base = self.FLUX_SCENE_PARAMS.get(scene_type, self.FLUX_SCENE_PARAMS[SceneType.ARTISTIC])

        final_guidance = base["guidance"]
        final_steps = base["steps"]

        # bandit 反馈调整 guidance
        if history and len(history) >= 3:
            if random.random() >= self.BANDIT_EPSILON:
                guidance_buckets: dict[float, list[float]] = defaultdict(list)
                for record in history:
                    params = record.get("params", {})
                    score = record.get("score", 0)
                    g = params.get("guidance")
                    if g is not None:
                        bucket = round(g * 2) / 2
                        guidance_buckets[bucket].append(score)

                if guidance_buckets:
                    best_bucket = max(
                        guidance_buckets.keys(),
                        key=lambda b: sum(guidance_buckets[b]) / len(guidance_buckets[b]),
                    )
                    best_avg = sum(guidance_buckets[best_bucket]) / len(guidance_buckets[best_bucket])
                    base_bucket = round(final_guidance * 2) / 2
                    base_avg = (
                        sum(guidance_buckets[base_bucket]) / len(guidance_buckets[base_bucket])
                        if base_bucket in guidance_buckets
                        else 0
                    )
                    if best_avg - base_avg > 2.0:
                        final_guidance = final_guidance * 0.4 + best_bucket * 0.6
                        logger.info(
                            "bandit 调整 FLUX guidance: %.1f → %.1f",
                            base["guidance"], final_guidance,
                        )

        # 反馈循环参数调整
        if param_adjustment:
            final_guidance += param_adjustment.get("guidance_delta", 0)
            final_steps += param_adjustment.get("steps_delta", 0)

        final_guidance = max(0.0, min(10.0, final_guidance))
        final_steps = max(4, min(50, final_steps))

        return FLUXParameters(
            prompt=prompt,
            width=width,
            height=height,
            steps=final_steps,
            guidance=final_guidance,
            seed=-1,
        )

    def get_reasoning(self, scene_type: SceneType, style: ImageStyle, backend: str) -> str:
        """获取参数优化说明"""
        if backend == "flux":
            base = self.FLUX_SCENE_PARAMS.get(scene_type, {})
            return (
                f"FLUX模型: {scene_type.value}场景, "
                f"guidance={base.get('guidance', 3.5)}, "
                f"steps={base.get('steps', 4)}"
            )

        base = self.SD_SCENE_PARAMS.get(scene_type, {})
        adj = self.SD_STYLE_ADJ.get(style, {})
        final_cfg = base.get("cfg_scale", 7.0) + adj.get("cfg_scale", 0)
        return (
            f"SD模型: {scene_type.value}场景+{style.value}风格, "
            f"CFG={final_cfg:.1f}, "
            f"sampler={base.get('sampler_name', 'DPM++ 2M Karras')}"
        )
