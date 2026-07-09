"""FLUX 模型 API 客户端 v0.3

修复：
1. base64 import 移到文件顶部（原在函数体内）
2. 轮询增加指数退避 + 错误重试
3. 变体搜索 — 固定 seed，微调 guidance 产生有控的质量变化
"""

import asyncio
import base64
import logging

import httpx

from src.config import settings
from src.models.schemas import GeneratedImage, FLUXParameters

logger = logging.getLogger(__name__)


class FLUXClient:
    """FLUX API 客户端 — 指数退避轮询 + 错误重试"""

    def __init__(self) -> None:
        self.base_url = settings.flux_api_url.rstrip("/")
        self.api_key = settings.flux_api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建复用的 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            headers = {"X-Key": self.api_key or ""}
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=120.0,
                headers=headers,
            )
        return self._client

    async def generate(
        self, params: FLUXParameters, batch_size: int = 3
    ) -> list[GeneratedImage]:
        """批量生成图片（并发调用）"""
        tasks = [self._generate_single(params, i) for i in range(batch_size)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        images = []
        errors = []
        for r in results:
            if isinstance(r, GeneratedImage):
                images.append(r)
            elif isinstance(r, Exception):
                errors.append(str(r))

        if not images:
            error_summary = "; ".join(errors[:3])
            raise RuntimeError(f"FLUX 生成全部失败: {error_summary}")

        if errors:
            logger.warning("FLUX 部分生成失败 (%d/%d): %s", len(errors), batch_size, errors[0])

        return images

    async def _generate_single(
        self, params: FLUXParameters, idx: int, max_retries: int = 2
    ) -> GeneratedImage:
        """生成单张图片 — 带重试逻辑"""
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await self._submit_and_poll(params, idx)
            except (httpx.HTTPStatusError, httpx.ConnectError, RuntimeError) as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2.0 * (2 ** attempt)  # 2s, 4s
                    logger.warning(
                        "FLUX 生成失败 (尝试 %d/%d), %.1fs 后重试: %s",
                        attempt + 1, max_retries + 1, wait, e,
                    )
                    await asyncio.sleep(wait)

        raise RuntimeError(f"FLUX 生成失败（已重试 {max_retries} 次）: {last_error}")

    async def _submit_and_poll(
        self, params: FLUXParameters, idx: int
    ) -> GeneratedImage:
        """提交生成任务 + 指数退避轮询"""
        payload = {
            "prompt": params.prompt,
            "width": params.width,
            "height": params.height,
            "steps": params.steps,
            "guidance": params.guidance,
            "seed": params.seed if params.seed != -1 else None,
        }

        client = await self._get_client()

        # 提交生成任务
        response = await client.post("/flux-schnell", json=payload)
        response.raise_for_status()
        task_id = response.json().get("id")

        if not task_id:
            raise RuntimeError("FLUX API 未返回 task_id")

        # 指数退避轮询（初始 0.5s，最大 4s，总等待 ~90s）
        poll_interval = 0.5
        total_waited = 0.0
        max_wait = 90.0

        while total_waited < max_wait:
            await asyncio.sleep(poll_interval)
            total_waited += poll_interval

            try:
                result_resp = await client.get(f"/get_result?id={task_id}")
                result = result_resp.json()
            except (httpx.HTTPError, ValueError) as e:
                logger.debug("FLUX 轮询异常 (%.1fs): %s", total_waited, e)
                poll_interval = min(poll_interval * 1.5, 4.0)
                continue

            status = result.get("status")

            if status == "Ready":
                image_url = result["result"]["sample"]
                img_resp = await client.get(image_url)
                img_resp.raise_for_status()
                img_b64 = base64.b64encode(img_resp.content).decode()

                seed = result.get("result", {}).get("seed", idx)
                return GeneratedImage(
                    image_data=img_b64,
                    seed=seed,
                    parameters=params.model_copy(update={"seed": seed}),
                )

            if status in ("Error", "Failed"):
                error_msg = result.get("error", "未知错误")
                raise RuntimeError(f"FLUX 生成失败: {error_msg}")

            # 状态仍在处理中，增加轮询间隔
            poll_interval = min(poll_interval * 1.5, 4.0)

        raise TimeoutError(f"FLUX 生成超时 ({max_wait}s): task_id={task_id}")

    # ── 变体搜索 ────────────────────────────────────────────

    async def generate_variants(
        self,
        params: FLUXParameters,
        guidance_offsets: list[float] | None = None,
    ) -> list[GeneratedImage]:
        """在最佳参数附近生成变体 — 固定 seed，微调 guidance

        原理：seed±1 不产生相似构图（伪随机序列无局部连续性）。
        改为固定最佳 seed，微调 guidance 产生有控的质量变化：
        - 同一 seed → 相同构图基础
        - 不同 guidance → 对 prompt 的不同遵循度

        优化6: 自适应步长 — 根据当前 guidance 在合法区间 [0, 10] 中的
        位置动态计算偏移，避免 clamp 到边界后产生无差异变体。

        Args:
            params: 最佳图片的生图参数（seed 已固定）
            guidance_offsets: guidance 偏移列表，None 时自动计算自适应步长
        """
        if guidance_offsets is None:
            # 优化6: 自适应步长
            current_g = params.guidance
            g_min, g_max = 0.0, 10.0
            space_up = g_max - current_g
            space_down = current_g - g_min
            step = min(0.5, min(space_up, space_down) / 2)
            if step < 0.1:
                step = 0.25
            guidance_offsets = [-step, step, step * 2]
        else:
            guidance_offsets = list(guidance_offsets)

        tasks = []
        for offset in guidance_offsets:
            new_guidance = max(0.0, params.guidance + offset)
            variant_params = params.model_copy(update={"guidance": new_guidance})
            tasks.append(self._generate_single(variant_params, 0, max_retries=1))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, GeneratedImage)]

    # ── 健康检查 & 关闭 ──────────────────────────────────────

    async def check_health(self) -> bool:
        """检查 FLUX API 是否已配置"""
        return bool(self.api_key)

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
