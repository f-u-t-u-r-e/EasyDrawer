import pytest
from fastapi import HTTPException

from src.api.main import _resolve_llm_config, settings


def test_resolve_llm_config_prefers_generic_header():
    config = _resolve_llm_config(
        x_llm_api_key="new-key",
        x_anthropic_api_key="legacy-key",
        x_llm_base_url="https://api.example.com",
        x_llm_model="test-model",
    )

    assert config.api_key == "new-key"
    assert config.base_url == "https://api.example.com"
    assert config.model == "test-model"


def test_resolve_llm_config_accepts_legacy_header():
    config = _resolve_llm_config(x_anthropic_api_key="legacy-key")

    assert config.api_key == "legacy-key"


def test_resolve_llm_config_rejects_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    with pytest.raises(HTTPException) as exc:
        _resolve_llm_config()

    assert exc.value.status_code == 503
