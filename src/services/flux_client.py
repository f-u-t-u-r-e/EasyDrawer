"""BFL FLUX API client.

The current BFL API is asynchronous: submit a generation request, poll the
returned polling_url, then download the signed delivery URL before it expires.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import httpx

from src.config import settings
from src.models.schemas import FLUXParameters, GeneratedImage

logger = logging.getLogger(__name__)


class FLUXClient:
    """Client for BFL-hosted FLUX endpoints."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = settings.flux_api_url.rstrip("/")
        self.api_key = settings.flux_api_key
        self.model_endpoint = settings.flux_model_endpoint.strip("/")
        self.output_format = settings.flux_output_format
        self.safety_tolerance = settings.flux_safety_tolerance
        self.disable_pup = settings.flux_disable_pup
        self.poll_timeout = settings.flux_poll_timeout
        self._client: httpx.AsyncClient | None = client

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a reusable HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "accept": "application/json",
                "x-key": self.api_key or "",
            }
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=120.0,
                headers=headers,
            )
        return self._client

    def _endpoint_path(self) -> str:
        return f"/{self.model_endpoint}"

    def _supports_guidance(self) -> bool:
        """Only legacy/non-FLUX.2 endpoints expose steps/guidance controls."""
        return not self.model_endpoint.startswith("flux-2-")

    def _build_payload(self, params: FLUXParameters) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": params.prompt,
            "width": params.width,
            "height": params.height,
            "safety_tolerance": self.safety_tolerance,
            "output_format": self.output_format,
        }

        if params.seed != -1:
            payload["seed"] = params.seed

        if self.disable_pup:
            payload["disable_pup"] = True

        if self._supports_guidance():
            payload["steps"] = params.steps
            payload["guidance"] = params.guidance

        return payload

    async def generate(
        self, params: FLUXParameters, batch_size: int = 3
    ) -> list[GeneratedImage]:
        """Generate a batch of images concurrently."""
        tasks = [self._generate_single(params, i) for i in range(batch_size)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        images: list[GeneratedImage] = []
        errors: list[str] = []
        for result in results:
            if isinstance(result, GeneratedImage):
                images.append(result)
            elif isinstance(result, Exception):
                errors.append(str(result))

        if not images:
            error_summary = "; ".join(errors[:3])
            raise RuntimeError(f"FLUX generation failed: {error_summary}")

        if errors:
            logger.warning(
                "FLUX partial generation failure (%d/%d): %s",
                len(errors),
                batch_size,
                errors[0],
            )

        return images

    async def _generate_single(
        self, params: FLUXParameters, idx: int, max_retries: int = 2
    ) -> GeneratedImage:
        """Generate one image with retry around transient API errors."""
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await self._submit_and_poll(params, idx)
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout, RuntimeError) as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2.0 * (2**attempt)
                    logger.warning(
                        "FLUX generation failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        wait,
                        e,
                    )
                    await asyncio.sleep(wait)

        raise RuntimeError(f"FLUX generation failed after retries: {last_error}")

    async def _submit_and_poll(
        self, params: FLUXParameters, idx: int
    ) -> GeneratedImage:
        """Submit a BFL task, poll until ready, then download the signed image URL."""
        if not self.api_key:
            raise RuntimeError("FLUX API key is not configured")

        payload = self._build_payload(params)
        client = await self._get_client()

        response = await client.post(self._endpoint_path(), json=payload)
        response.raise_for_status()
        submitted = response.json()

        task_id = submitted.get("id")
        polling_url = submitted.get("polling_url")
        if not task_id:
            raise RuntimeError("FLUX API did not return a task id")

        poll_interval = 0.5
        total_waited = 0.0

        while total_waited < self.poll_timeout:
            await asyncio.sleep(poll_interval)
            total_waited += poll_interval

            try:
                if polling_url:
                    result_resp = await client.get(polling_url)
                else:
                    result_resp = await client.get("/get_result", params={"id": task_id})
                result_resp.raise_for_status()
                result = result_resp.json()
            except (httpx.HTTPError, ValueError) as e:
                logger.debug("FLUX polling error after %.1fs: %s", total_waited, e)
                poll_interval = min(poll_interval * 1.5, 4.0)
                continue

            status = result.get("status")

            if status == "Ready":
                sample_url = result.get("result", {}).get("sample")
                if not sample_url:
                    raise RuntimeError("FLUX result is ready but missing result.sample")

                img_resp = await client.get(sample_url)
                img_resp.raise_for_status()
                img_b64 = base64.b64encode(img_resp.content).decode()

                seed = result.get("result", {}).get("seed")
                if seed is None:
                    seed = params.seed if params.seed != -1 else idx

                return GeneratedImage(
                    image_data=img_b64,
                    seed=seed,
                    parameters=params.model_copy(update={"seed": seed}),
                )

            if status in (
                "Error",
                "Failed",
                "Task not found",
                "Request Moderated",
                "Content Moderated",
            ):
                error_msg = result.get("error") or result.get("details") or result
                raise RuntimeError(f"FLUX generation failed: {error_msg}")

            poll_interval = min(poll_interval * 1.5, 4.0)

        raise TimeoutError(f"FLUX generation timed out ({self.poll_timeout}s): task_id={task_id}")

    async def generate_variants(
        self,
        params: FLUXParameters,
        guidance_offsets: list[float] | None = None,
    ) -> list[GeneratedImage]:
        """Generate variants near the best image when the endpoint supports guidance."""
        if not self._supports_guidance():
            logger.info(
                "Skipping FLUX variant search: %s does not expose guidance controls",
                self.model_endpoint,
            )
            return []

        if guidance_offsets is None:
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

    async def check_health(self) -> bool:
        """The BFL endpoint is usable when an API key is present."""
        return bool(self.api_key)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
