from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from sidebrain_back.core.constants import Env
from sidebrain_back.schemas.rag_schema import RagLanguage, RagLevel


class RagConfigError(ValueError):
    """Raised when RAG source configuration is missing or invalid."""


class RagSourceType(StrEnum):
    URL = "url"
    SITEMAP = "sitemap"
    GIT = "git"
    LOCAL = "local"


class RagCrawlerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_agent: str = Field(min_length=1)
    timeout_seconds: float = Field(gt=0, le=120)
    max_concurrency_per_host: int = Field(ge=1, le=10)
    request_interval_seconds: float = Field(ge=0, le=60)
    robots_cache_hours: int = Field(ge=1, le=24)


class RagChunkingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_tokens: int = Field(ge=1, le=8192)
    overlap_ratio: float = Field(ge=0, lt=0.5)
    tokenizer: str = Field(min_length=1)
    encoding: str = Field(min_length=1)


class RagDeduplicationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exact: bool
    approximate: bool
    simhash_bits: int = Field(ge=16, le=128)
    simhash_max_hamming_distance: int = Field(ge=0)
    require_equal_code_hash: bool = True

    @model_validator(mode="after")
    def validate_hamming_distance(self) -> RagDeduplicationConfig:
        if self.simhash_max_hamming_distance > self.simhash_bits:
            raise ValueError(
                "simhash_max_hamming_distance cannot exceed simhash_bits"
            )
        return self


class RagEmbeddingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    dimensions: int = Field(ge=1, le=2000)
    batch_size: int = Field(ge=1, le=2048)
    max_attempts: int = Field(ge=1, le=5)
    max_input_tokens: int = Field(ge=1, le=8192)
    max_batch_tokens: int = Field(ge=1, le=300000)
    price_per_million_input_tokens: float | None = Field(default=None, ge=0)


class RagDefaultsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crawler: RagCrawlerConfig
    chunking: RagChunkingConfig
    deduplication: RagDeduplicationConfig
    embeddings: RagEmbeddingConfig


class RagContentLicenseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    license: str = Field(min_length=1)
    license_url: str | None = None
    external_processing_allowed: bool = False


class RagSourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    type: RagSourceType
    url: str | None = None
    sitemap_url: str | None = None
    repository_url: str | None = None
    path: str | None = None
    language: RagLanguage
    level: RagLevel
    license: str = Field(min_length=1)
    license_url: str | None = None
    content_licenses: dict[str, RagContentLicenseConfig] = Field(
        default_factory=dict
    )
    include_paths: list[str] = Field(min_length=1)
    exclude_paths: list[str] = Field(default_factory=list)
    version_strategy: str = Field(min_length=1)
    connector: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source_location(self) -> RagSourceConfig:
        location = {
            RagSourceType.URL: self.url,
            RagSourceType.SITEMAP: self.sitemap_url or self.url,
            RagSourceType.GIT: self.repository_url,
            RagSourceType.LOCAL: self.path,
        }[self.type]
        if not location:
            raise ValueError(
                f"location is required for source type {self.type}"
            )
        if self.type in {RagSourceType.URL, RagSourceType.SITEMAP}:
            parsed = urlsplit(location)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("web sources require an absolute HTTP(S) URL")
        if self.type is RagSourceType.GIT:
            parsed = urlsplit(location)
            if parsed.scheme not in {"http", "https", "ssh", "git"}:
                raise ValueError(
                    "git source requires a supported repository URL"
                )
        return self

    def license_for(self, content_type: str) -> RagContentLicenseConfig:
        override = self.content_licenses.get(content_type)
        if override is not None:
            return override
        if content_type == "code_example":
            return RagContentLicenseConfig(
                license="unknown",
                external_processing_allowed=False,
            )
        return RagContentLicenseConfig(
            license=self.license,
            license_url=self.license_url,
            external_processing_allowed=True,
        )


class RagConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    defaults: RagDefaultsConfig
    sources: list[RagSourceConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_source_names(self) -> RagConfig:
        names = [source.name for source in self.sources]
        if len(names) != len(set(names)):
            raise ValueError("source names must be unique")
        return self

    def source_by_name(self, name: str) -> RagSourceConfig:
        for source in self.sources:
            if source.name == name:
                return source
        raise RagConfigError(f"Unknown RAG source: {name}")


def load_rag_config(path: str | Path | None = None) -> RagConfig:
    config_path = Path(path or Env.RAG_SOURCES_CONFIG)
    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RagConfigError(
            f"Unable to read RAG configuration at {config_path}"
        ) from error
    except yaml.YAMLError as error:
        raise RagConfigError("RAG configuration is not valid YAML") from error

    try:
        return RagConfig.model_validate(raw_config)
    except ValidationError as error:
        raise RagConfigError(f"Invalid RAG configuration: {error}") from error
