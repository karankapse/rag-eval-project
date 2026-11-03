"""Typed project settings, loaded from config.yaml, .env, and environment variables.

Precedence (highest wins): explicit kwargs > env vars > .env file > config.yaml > defaults.
That order lets CI or a one-off experiment tweak a knob (RAG_CHUNKING__SIZE=512)
without editing the committed YAML.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

# Resolve config.yaml relative to the repo, not the current working directory,
# so `pytest` from a subfolder or a script run elsewhere finds the same file.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class PathsConfig(BaseModel):
    data_dir: Path = Path("data")
    index_dir: Path = Path("indexes")
    results_dir: Path = Path("results/runs")


class ArxivConfig(BaseModel):
    search_terms: list[str] = ["retrieval-augmented generation"]
    category: str = "cs.CL"
    start_date: str = "20240101"
    max_candidates: int = Field(700, gt=0)
    target_papers: int = Field(400, gt=0)
    delay_seconds: float = Field(3.0, ge=0)


class ChunkingConfig(BaseModel):
    size: int = Field(256, gt=0, description="Tokens per chunk.")
    overlap: int = Field(32, ge=0, description="Tokens shared between neighbouring chunks.")

    @model_validator(mode="after")
    def overlap_smaller_than_size(self) -> "ChunkingConfig":
        # A chunker advances by (size - overlap) each step; if that's <= 0 it never moves forward.
        if self.overlap >= self.size:
            raise ValueError(f"overlap ({self.overlap}) must be smaller than size ({self.size})")
        return self


class Settings(BaseSettings):
    paths: PathsConfig = PathsConfig()
    arxiv: ArxivConfig = ArxivConfig()
    chunking: ChunkingConfig = ChunkingConfig()

    # Read from the conventional ANTHROPIC_API_KEY name (no RAG_ prefix).
    # SecretStr hides the value in repr/logs so it can't leak into printed configs.
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        env_nested_delimiter="__",
        env_file=PROJECT_ROOT / ".env",
        yaml_file=CONFIG_PATH,
        extra="ignore",  # .env may hold unrelated variables; don't crash on them
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Order = priority. YAML goes last so env vars can override it.
        yaml_settings = YamlConfigSettingsSource(settings_cls)
        return (init_settings, env_settings, dotenv_settings, yaml_settings)


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process; the rest of the code calls this instead of Settings()."""
    return Settings()
