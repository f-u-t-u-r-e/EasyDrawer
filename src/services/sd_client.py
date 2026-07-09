"""Stable Diffusion API 客户端 v0.3

新增：
- img2img 精修方法 — 对已有图片做低降噪二次优化
- seed 邻域生成 — 在 best_seed ± offset 范围内生成变体
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

    # ── Seed 邻域搜索 ────────────────────────────────────────

    async def generate_seed_neighbors(
        self,
        params: SDParameters,
        best_seed: int,
        offsets: list[int] | None = None,
    ) -> list[GeneratedImage]:
        """在 best_seed 附近生成变体

        SD 的 seed 空间具有局部连续性——相邻 seed 产生相似但不同的构图。
        用于在好图附近精搜更好的变体。

        Args:
            params: 生图参数
            best_seed: 最佳种子值
            offsets: 偏移列表，默认 [-2, -1, 1, 2]
        """
        if offsets is None:
            offsets = [-2, -1, 1, 2]

        images = []
        for offset in offsets:
            neighbor_seed = best_seed + offset
            if neighbor_seed < 0:
                continue
            neighbor_params = params.model_copy(update={"seed": neighbor_seed})
            try:
                result = await self.generate(neighbor_params, batch_size=1)
                images.extend(result)
            except Exception:
                # 单个 seed 失败不中断整体流程
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
