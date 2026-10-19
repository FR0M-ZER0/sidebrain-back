from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from sidebrain_back.rag.rag_config import RagCrawlerConfig


@dataclass(frozen=True)
class RagFetchedPage:
    requested_url: str
    final_url: str
    content: str
    etag: str | None
    last_modified: str | None


class RagRateLimitError(httpx.HTTPStatusError):
    def __init__(self, response: httpx.Response):
        self.retry_after_seconds = retry_after_seconds(response)
        super().__init__(
            "source rate limit reached",
            request=response.request,
            response=response,
        )


class RagUrlConnector:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        config: RagCrawlerConfig,
    ):
        self.config = config
        self.client = client or httpx.AsyncClient(
            follow_redirects=False,
            timeout=config.timeout_seconds,
        )
        self._owns_client = client is None
        self._robots: dict[str, tuple[float, RobotFileParser | None]] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._rate_locks: dict[str, asyncio.Lock] = {}
        self._last_request_at: dict[str, float] = {}
        self._robots_fetch_locks: dict[str, asyncio.Lock] = {}

    async def fetch_page(self, url: str) -> RagFetchedPage | None:
        requested_url = url
        initial_origin = self._origin(url)
        for _ in range(5):
            if not await self._allowed_by_robots(url):
                return None
            response = await self._send(url)
            if response.status_code == 429:
                raise RagRateLimitError(response)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise httpx.HTTPStatusError(
                        "redirect lacks a location",
                        request=response.request,
                        response=response,
                    )
                target = str(response.url.join(location))
                if self._origin(target) != initial_origin:
                    return None
                url = target
                continue
            response.raise_for_status()
            return RagFetchedPage(
                requested_url=requested_url,
                final_url=str(response.url),
                content=response.text,
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
        raise httpx.TooManyRedirects(
            "too many redirects while crawling source",
            request=response.request,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _allowed_by_robots(self, url: str) -> bool:
        origin = self._origin(url)
        cached = self._robots.get(origin)
        now = time.monotonic()
        if cached is not None and cached[0] > now:
            parser = cached[1]
            return parser is not None and parser.can_fetch(
                self.config.user_agent, url
            )

        lock = self._robots_fetch_locks.setdefault(origin, asyncio.Lock())
        async with lock:
            cached = self._robots.get(origin)
            now = time.monotonic()
            if cached is not None and cached[0] > now:
                parser = cached[1]
                return parser is not None and parser.can_fetch(
                    self.config.user_agent, url
                )

            robots_url = urlunsplit(
                (*urlsplit(origin)[:2], "/robots.txt", "", "")
            )
            try:
                response = await self._send(robots_url)
            except httpx.HTTPError:
                self._robots[origin] = (now + 60, None)
                return False

            if response.status_code == 429 or response.status_code >= 500:
                self._robots[origin] = (now + 60, None)
                return False
            if 400 <= response.status_code < 500:
                # RFC 9309 treats 4xx robots files as unavailable. A 429 was
                # handled above and remains a temporary deny.
                parser = RobotFileParser(robots_url)
                parser.parse([])
            else:
                response.raise_for_status()
                parser = RobotFileParser(robots_url)
                parser.parse(response.text.splitlines())

            expires = now + self.config.robots_cache_hours * 3600
            self._robots[origin] = (expires, parser)
            return parser.can_fetch(self.config.user_agent, url)

    async def _send(self, url: str) -> httpx.Response:
        origin = self._origin(url)
        semaphore = self._semaphores.setdefault(
            origin,
            asyncio.Semaphore(self.config.max_concurrency_per_host),
        )
        async with semaphore:
            await self._wait_for_host(origin)
            return await self.client.get(
                url,
                headers={"User-Agent": self.config.user_agent},
                timeout=self.config.timeout_seconds,
                follow_redirects=False,
            )

    async def _wait_for_host(self, origin: str) -> None:
        lock = self._rate_locks.setdefault(origin, asyncio.Lock())
        async with lock:
            delay = self.config.request_interval_seconds
            cached_robots = self._robots.get(origin)
            if cached_robots is not None and cached_robots[1] is not None:
                parser = cached_robots[1]
                crawl_delay = parser.crawl_delay(self.config.user_agent)
                if crawl_delay is not None:
                    delay = max(delay, float(crawl_delay))
                request_rate = parser.request_rate(self.config.user_agent)
                if request_rate is not None and request_rate.requests > 0:
                    delay = max(
                        delay,
                        request_rate.seconds / request_rate.requests,
                    )
            last_request = self._last_request_at.get(origin)
            if last_request is not None:
                wait = (
                    delay - (time.monotonic() - last_request)
                )
                if wait > 0:
                    await asyncio.sleep(wait)
            self._last_request_at[origin] = time.monotonic()

    @staticmethod
    def _origin(url: str) -> str:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("crawler URLs must be absolute HTTP(S) URLs")
        return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value).timestamp()
        except (TypeError, ValueError, OverflowError):
            return None
        return max(0.0, retry_at - time.time())
