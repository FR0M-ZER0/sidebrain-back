from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from sidebrain_back.core.constants import Env
from sidebrain_back.enums.generation_cache_enum import (
    GenerationCacheContentTypeEnum,
)


class AIMemoryService:
    """Builds deterministic, versioned keys without retaining user identity."""

    def __init__(self, alias_repository: object | None = None):
        self.alias_repository = alias_repository

    @staticmethod
    def canonicalize_text(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("contexto textual inválido")
        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(
            char for char in normalized if not unicodedata.combining(char)
        )
        normalized = re.sub(r"\s+", " ", normalized.casefold()).strip()
        normalized = re.sub(
            r"^[^\w]+|[^\w]+$", "", normalized, flags=re.UNICODE
        )
        if not normalized:
            raise ValueError("contexto textual obrigatório")
        return normalized

    async def canonicalize_topic(self, value: str) -> str:
        topic = self.canonicalize_text(value)
        if self.alias_repository is None:
            return topic
        alias = await self.alias_repository.get_active_by_alias(topic)
        return alias.canonical_topic if alias is not None else topic

    @classmethod
    def canonicalize_json(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): cls.canonicalize_json(value[key])
                for key in sorted(value)
            }
        if isinstance(value, (list, tuple)):
            return [cls.canonicalize_json(item) for item in value]
        if isinstance(value, str):
            return cls.canonicalize_text(value)
        return value

    @classmethod
    def fingerprint(
        cls,
        *,
        content_type: GenerationCacheContentTypeEnum | str,
        canonical_context: Mapping[str, Any],
        prompt_version: str | None = None,
        provider: str = "groq",
        model: str | None = None,
        fingerprint_version: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        envelope = {
            "fingerprint_version": fingerprint_version
            or Env.AI_MEMORY_FINGERPRINT_VERSION,
            "content_type": str(content_type),
            "canonical_context": cls.canonicalize_json(canonical_context),
            "prompt_version": prompt_version or Env.GROQ_PROMPT_VERSION,
            "provider": provider,
            "model": model or Env.GROQ_MODEL,
        }
        serialized = json.dumps(
            envelope, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest(), envelope

    @classmethod
    def track_context(
        cls, goal: str, topic: str, **values: Any
    ) -> dict[str, Any]:
        return {
            "goal": cls.canonicalize_text(goal),
            "topic": cls.canonicalize_text(topic),
            **cls.canonicalize_json(values),
        }
