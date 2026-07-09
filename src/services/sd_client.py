"""Stable Diffusion API 客户端 v0.3

新增：
- img2img 精修方法 — 对已有图片做低降噪二次优化
- 变体搜索 — 固定 seed，微调 CFG 产生有控的质量变化
"""

import json

import httpx

from src.config import settings
from src.models.schemas import GeneratedImage, SDParameters


class StableDiffusionClient:
    """SD WebUI API 客户端"""

    def __init__(self) -> None:
        self.base_url = settings.sd_api_url.rstrip("/")
        self.api_key = settings.sd_api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建复用的 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=180.0,
                headers=headers,
            )
        return self._client

    def _parse_info(self, result: dict) -> dict:
        """解析 SD WebUI 返回的 info 字段（JSON 字符串 → dict）"""
        info_raw = result.get("info", "{}")
        if isinstance(info_raw, str):
            try:
                return json.loads(info_raw)
            except json.JSONDecodeError:
                return {}
        return info_raw if isinstance(info_raw, dict) else {}

    # ── txt2img ──────────────────────────────────────────────

    async def generate(
        self, params: SDParameters, batch_size: int = 3
    ) -> list[GeneratedImage]:
        """txt2img 批量生成"""
        payload = {
            "prompt": params.prompt,
            "negative_prompt": params.negative_prompt,
            "steps": params.steps,
            "cfg_scale": params.cfg_scale,
            "width": params.width,
            "height": params.height,
            "sampler_name": params.sampler_name,
            "seed": params.seed,
            "batch_size": batch_size,
            "n_iter": 1,
        }

        client = await self._get_client()
        response = await client.post("/sdapi/v1/txt2img", json=payload)
        response.raise_for_status()
        result = response.json()

        info = self._parse_info(result)
        all_seeds = info.get("all_seeds", [])
        base_seed = info.get("seed", -1)

        images = []
        for idx, img_b64 in enumerate(result.get("images", [])):
            seed = all_seeds[idx] if idx < len(all_seeds) else base_seed
            images.append(
                GeneratedImage(
                    image_data=img_b64,
                    seed=seed,
                    parameters=params.model_copy(update={"seed": seed}),
                )
            )
        return images

    # ── img2img 精修 ─────────────────────────────────────────

    async def img2img_refine(
        self,
        params: SDParameters,
        init_image_b64: str,
        denoising_strength: float = 0.25,
    ) -> GeneratedImage:
        """img2img 精修 — 对已生成图片做低降噪二次优化

        Args:
            params: 生图参数（prompt/negative/cfg 等）
            init_image_b64: 原始图片的 base64 数据
            denoising_strength: 降噪强度（0.15-0.35 保留构图，增强细节）

        Returns:
            精修后的 GeneratedImage
        """
        payload = {
            "init_images": [init_image_b64],
            "prompt": params.prompt,
            "negative_prompt": params.negative_prompt,
            "steps": params.steps,
            "cfg_scale": params.cfg_scale,
            "width": params.width,
            "height": params.height,
            "sampler_name": params.sampler_name,
            "seed": params.seed,
            "denoising_strength": denoising_strength,
            "batch_size": 1,
            "n_iter": 1,
        }

        client = await self._get_client()
        response = await client.post("/sdapi/v1/img2img", json=payload)
        response.raise_for_status()
        result = response.json()

        info = self._parse_info(result)
        seed = info.get("seed", params.seed)

        raw_images = result.get("images", [])
        if not raw_images:
            raise RuntimeError("img2img 未返回图片")

        return GeneratedImage(
            image_data=raw_images[0],
            seed=seed,
            parameters=params.model_copy(
                update={
                    "seed": seed,
                    "init_image": None,  # 不在参数中存储图片数据
                    "denoising_strength": denoising_strength,
                }
            ),
            is_refined=True,
        )

    # ── 变体搜索 ────────────────────────────────────────────

    async def generate_variants(
        self,
        params: SDParameters,
        cfg_offsets: list[float] | None = None,
    ) -> list[GeneratedImage]:
        """在最佳参数附近生成变体 — 固定 seed，微调 CFG

        原理：seed±1 在 SD 的 PRNG 空间中不产生相似构图（伪随机序列
        无局部连续性）。改为固定最佳 seed，微调 CFG scale 产生有控的
        质量变化：
        - 同一 seed → 同一初始噪声 → 相同构图基础
        - 不同 CFG → 对 prompt 的不同遵循度 → 细节/风格强度变化

        优化6: 自适应步长 — 根据当前 CFG 在合法区间 [5, 10] 中的位置
        动态计算偏移，避免 clamp 到边界后产生无差异变体。

        Args:
            params: 最佳图片的生图参数（seed 已固定）
            cfg_offsets: CFG 偏移列表，None 时自动计算自适应步长
        """
        if cfg_offsets is None:
            # 优化6: 自适应步长
            current_cfg = params.cfg_scale
            cfg_min, cfg_max = 5.0, 10.0
            # 计算向上下还有多少空间
            space_up = cfg_max - current_cfg
            space_down = current_cfg - cfg_min
            # 步长取空间较小方向的一半，但不超过 1.0
            step = min(0.5, min(space_up, space_down) / 2)
            if step < 0.1:
                # 空间太小，用固定小步长
                step = 0.25
            cfg_offsets = [-step, step, step * 2]
        else:
            cfg_offsets = list(cfg_offsets)

        images = []
        for offset in cfg_offsets:
            new_cfg = max(1.0, min(15.0, params.cfg_scale + offset))
            variant_params = params.model_copy(update={"cfg_scale": new_cfg})
            try:
                result = await self.generate(variant_params, batch_size=1)
                images.extend(result)
            except Exception:
                # 单个变体失败不中断整体流程
                continue
        return images

    # ── 健康检查 & 关闭 ──────────────────────────────────────

    async def check_health(self) -> bool:
        """检查 SD API 是否可用"""
        try:
            client = await self._get_client()
            response = await client.get("/sdapi/v1/sd-models")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
