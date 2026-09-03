"""Application configuration via ``pydantic-settings``.

All runtime knobs are read from the environment (and an optional ``.env``
file) so the same code runs locally, in CI, and in production without edits.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated settings loaded from the environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM ---------------------------------------------------------------
    anthropic_api_key: str = Field(
        default="", description="Anthropic API key (leave blank to read ANTHROPIC_API_KEY env)."
    )
    model: str = Field(
        default="claude-sonnet-5",
        description="Claude model id. This is a placeholder default; override with a current id.",
    )
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)

    # --- Retrieval ---------------------------------------------------------
    data_dir: Path = Field(default=Path("data/knowledge"), description="Knowledge source docs.")
    index_dir: Path = Field(default=Path(".chroma"), description="Local Chroma persistence dir.")
    collection_name: str = Field(default="acme_support")
    retrieval_k: int = Field(default=4, ge=1, le=20)

    # --- Guardrails --------------------------------------------------------
    max_input_chars: int = Field(default=4000, ge=1)

    # --- Observability / cost ---------------------------------------------
    trace_enabled: bool = Field(
        default=False, description="Emit per-request spans (latency/tokens/cost) when true."
    )
    trace_sink: str = Field(default="stderr", description="Where trace summaries go: 'stderr' or 'none'.")
    price_input_per_mtok: float = Field(
        default=3.0, ge=0.0, description="USD per 1M input tokens (set to your model's rate)."
    )
    price_output_per_mtok: float = Field(
        default=15.0, ge=0.0, description="USD per 1M output tokens (set to your model's rate)."
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, process-wide ``Settings`` instance."""
    return Settings()
