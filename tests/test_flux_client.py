import base64
import json

import httpx
import pytest

from src.config import settings
from src.models.schemas import FLUXParameters
from src.services.flux_client import FLUXClient


@pytest.mark.asyncio
async def test_flux_client_uses_bfl_polling_url(monkeypatch):
    monkeypatch.setattr(settings, "flux_api_url", "https://api.bfl.ai/v1")
    monkeypatch.setattr(settings, "flux_api_key", "bfl-test-key")
    monkeypatch.setattr(settings, "flux_model_endpoint", "flux-2-pro-preview")
    monkeypatch.setattr(settings, "flux_output_format", "jpeg")
    monkeypatch.setattr(settings, "flux_safety_tolerance", 2)
    monkeypatch.setattr(settings, "flux_disable_pup", False)
    monkeypatch.setattr(settings, "flux_poll_timeout", 3.0)

    async def instant_sleep(_seconds):
        return None

    monkeypatch.setattr("src.services.flux_client.asyncio.sleep", instant_sleep)

    seen_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            payload = json.loads(request.content)
            seen_payloads.append(payload)
            assert request.url.path == "/v1/flux-2-pro-preview"
            assert request.headers["x-key"] == "bfl-test-key"
            assert payload["prompt"] == "a cinematic product photo"
            assert payload["width"] == 1024
            assert payload["height"] == 1024
            assert payload["seed"] == 123
            assert payload["output_format"] == "jpeg"
            assert "steps" not in payload
            assert "guidance" not in payload
            return httpx.Response(
                200,
                json={
                    "id": "task-1",
                    "polling_url": "https://poll.example/task-1",
                },
            )

        if request.url.host == "poll.example":
            return httpx.Response(
                200,
                json={
                    "id": "task-1",
                    "status": "Ready",
                    "result": {
                        "sample": "https://delivery.example/image.jpeg",
                        "seed": 456,
                    },
                },
            )

        if request.url.host == "delivery.example":
            return httpx.Response(200, content=b"fake-image-bytes")

        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(
        base_url="https://api.bfl.ai/v1",
        transport=transport,
        headers={"accept": "application/json", "x-key": "bfl-test-key"},
    )
    flux = FLUXClient(client=async_client)

    try:
        image = await flux._submit_and_poll(
            FLUXParameters(
                prompt="a cinematic product photo",
                width=1024,
                height=1024,
                steps=25,
                guidance=5.0,
                seed=123,
            ),
            idx=0,
        )
    finally:
        await flux.close()

    assert seen_payloads
    assert image.seed == 456
    assert image.image_data == base64.b64encode(b"fake-image-bytes").decode()


@pytest.mark.asyncio
async def test_flux2_variant_search_skips_unsupported_guidance(monkeypatch):
    monkeypatch.setattr(settings, "flux_api_url", "https://api.bfl.ai/v1")
    monkeypatch.setattr(settings, "flux_api_key", "bfl-test-key")
    monkeypatch.setattr(settings, "flux_model_endpoint", "flux-2-pro-preview")
    monkeypatch.setattr(settings, "flux_output_format", "jpeg")
    monkeypatch.setattr(settings, "flux_safety_tolerance", 2)
    monkeypatch.setattr(settings, "flux_disable_pup", False)
    monkeypatch.setattr(settings, "flux_poll_timeout", 3.0)

    flux = FLUXClient()
    images = await flux.generate_variants(
        FLUXParameters(prompt="a clean studio portrait", seed=42),
        guidance_offsets=[-0.5, 0.5],
    )

    assert images == []
