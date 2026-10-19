from __future__ import annotations

import fnmatch
from pathlib import Path


class RagLocalConnector:
    ACCEPTED_SUFFIXES = {".md", ".markdown", ".rst"}

    @classmethod
    def list_documents(
        cls,
        root: str | Path,
        *,
        include_paths: list[str],
        exclude_paths: list[str],
    ) -> list[Path]:
        root_path = Path(root).resolve(strict=True)
        accepted: list[Path] = []
        for candidate in root_path.rglob("*"):
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if candidate.suffix.lower() not in cls.ACCEPTED_SUFFIXES:
                continue
            relative = candidate.relative_to(root_path).as_posix()
            included = any(
                cls._matches(relative, pattern) for pattern in include_paths
            )
            excluded = any(
                cls._matches(relative, pattern) for pattern in exclude_paths
            )
            if included and not excluded:
                accepted.append(candidate)
        return sorted(accepted)

    @staticmethod
    def _matches(relative: str, pattern: str) -> bool:
        if fnmatch.fnmatchcase(relative, pattern):
            return True
        return pattern.startswith("**/") and fnmatch.fnmatchcase(
            relative, pattern[3:]
        )

    @staticmethod
    def read_document(path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")
