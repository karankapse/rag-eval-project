"""Tests for settings loading. These protect the contract every later module relies on."""

import pytest
import yaml
from pydantic import ValidationError

from rag.config import CONFIG_PATH, ChunkingConfig, Settings


def test_values_come_from_config_yaml():
    # Protects against: the YAML file silently not being read (we'd run on defaults
    # and our saved experiment configs would lie about what actually ran).
    raw = yaml.safe_load(CONFIG_PATH.read_text())
    settings = Settings()
    assert settings.chunking.size == raw["chunking"]["size"]
    assert settings.chunking.overlap == raw["chunking"]["overlap"]


def test_env_var_overrides_yaml(monkeypatch):
    # Protects against: CI / one-off experiments being unable to tweak a knob without editing YAML.
    monkeypatch.setenv("RAG_CHUNKING__SIZE", "512")
    assert Settings().chunking.size == 512


def test_overlap_must_be_smaller_than_size():
    # Protects against: a chunker that never advances (step = size - overlap <= 0),
    # which would loop forever.
    with pytest.raises(ValidationError):
        ChunkingConfig(size=100, overlap=100)


def test_api_key_is_hidden_in_repr(monkeypatch):
    # Protects against: the key leaking into logs or saved eval-run configs.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    settings = Settings()
    assert settings.anthropic_api_key.get_secret_value() == "sk-test-not-real"
    assert "sk-test-not-real" not in repr(settings)
