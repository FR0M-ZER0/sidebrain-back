from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path


class RagGitConnectorError(RuntimeError):
    """Raised when a configured Git source cannot be read safely."""


class RagGitConnector:
    def __init__(self, timeout_seconds: float = 120):
        self.timeout_seconds = timeout_seconds

    async def clone_to(
        self,
        repository_url: str,
        target_directory: str | Path,
        *,
        ref: str | None = None,
    ) -> Path:
        target = Path(target_directory)
        await asyncio.to_thread(self._prepare_target, target)
        arguments = ["git", "clone", "--depth", "1"]
        if ref:
            arguments.extend(["--branch", ref])
        arguments.extend([repository_url, str(target)])
        await self._run(arguments, "clone")
        return target

    @staticmethod
    def _prepare_target(target: Path) -> None:
        if target.exists() and any(target.iterdir()):
            raise RagGitConnectorError("Git checkout directory is not empty")
        target.parent.mkdir(parents=True, exist_ok=True)

    async def resolve_version(self, checkout: str | Path) -> str:
        return await self._run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            "read revision",
        )

    async def _run(self, arguments: list[str], operation: str) -> str:
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                arguments,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RagGitConnectorError(
                f"Git source {operation} failed ({type(error).__name__})"
            ) from None
        if result.returncode != 0:
            raise RagGitConnectorError(f"Git source {operation} failed")
        return result.stdout.strip()
