"""参数优化器 - 根据场景自动选择最优生图参数

2026最佳实践：
- DPM++ 2M Karras 是社区标准采样器
- CFG Scale: 6(写实) → 7(默认) → 8-9(复杂)，不超过10
- Steps: 20-30 是最佳性价比区间
- FLUX: guidance 3.0-4.0，steps 4(schnell)/25(pro)
"""

from src.models.schemas import ImageStyle, SceneType, SDParameters, FLUXParameters


class ParameterOptimizer:
    """参数优化器 - 根据场景和风格自动调整参数"""

    # SD场景参数映射
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

    # SD风格微调（CFG偏移量、Steps偏移量）
    SD_STYLE_ADJ: dict[ImageStyle, dict] = {
        ImageStyle.REALISTIC: {"cfg_scale": -0.5, "steps": 0},
        ImageStyle.ARTISTIC: {"cfg_scale": +1.0, "steps": +5},
        ImageStyle.ANIME: {"cfg_scale": +0.5, "steps": 0},
        ImageStyle.CONCEPT_ART: {"cfg_scale": +0.5, "steps": +2},
        ImageStyle.PORTRAIT: {"cfg_scale": -0.5, "steps": 0},
        ImageStyle.LANDSCAPE: {"cfg_scale": +0.5, "steps": +2},
    }

    # FLUX场景参数映射
    FLUX_SCENE_PARAMS: dict[SceneType, dict] = {
        SceneType.PORTRAIT: {"steps": 4, "guidance": 3.0},
        SceneType.LANDSCAPE: {"steps": 4, "guidance": 3.5},
        SceneType.ARTISTIC: {"steps": 4, "guidance": 4.0},
        SceneType.PRODUCT: {"steps": 4, "guidance": 3.5},
        SceneType.ARCHITECTURE: {"steps": 4, "guidance": 3.5},
    }

    def optimize_sd(
        self,
        prompt: str,
        negative_prompt: str,
        scene_type: SceneType,
        style: ImageStyle,
        width: int = 1024,
        height: int = 1024,
    ) -> SDParameters:
        """生成优化后的SD参数"""
        base = self.SD_SCENE_PARAMS.get(scene_type, self.SD_SCENE_PARAMS[SceneType.ARTISTIC])
        adj = self.SD_STYLE_ADJ.get(style, {"cfg_scale": 0, "steps": 0})

        # CFG限制在5.0-10.0（2026共识：>10产生伪影）
        final_cfg = max(5.0, min(10.0, base["cfg_scale"] + adj["cfg_scale"]))
        final_steps = max(20, min(35, base["steps"] + adj["steps"]))

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
    ) -> FLUXParameters:
        """生成优化后的FLUX参数"""
        base = self.FLUX_SCENE_PARAMS.get(scene_type, self.FLUX_SCENE_PARAMS[SceneType.ARTISTIC])

        return FLUXParameters(
            prompt=prompt,
            width=width,
            height=height,
            steps=base["steps"],
            guidance=base["guidance"],
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
