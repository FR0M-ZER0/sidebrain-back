import asyncio
import subprocess
from pathlib import Path

import httpx

from sidebrain_back.rag.rag_config import RagCrawlerConfig
from sidebrain_back.rag.rag_git_connector import RagGitConnector
from sidebrain_back.rag.rag_local_connector import RagLocalConnector
from sidebrain_back.rag.rag_sitemap_connector import RagSitemapConnector
from sidebrain_back.rag.rag_url_connector import (
    RagRateLimitError,
    RagUrlConnector,
)


def test_url_connector_respects_robots_rules_with_mock_http():
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nDisallow: /private\n",
            )
        return httpx.Response(
            200,
            text="<main><h1>Allowed page</h1></main>",
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = RagUrlConnector(
        client=client,
        config=RagCrawlerConfig(
            user_agent="SidebrainRAGTest/1.0",
            timeout_seconds=2,
            max_concurrency_per_host=1,
            request_interval_seconds=0,
            robots_cache_hours=24,
        ),
    )

    async def run():
        allowed = await connector.fetch_page("https://docs.example/allowed")
        disallowed = await connector.fetch_page("https://docs.example/private")
        await client.aclose()
        return allowed, disallowed

    allowed, disallowed = asyncio.run(run())

    assert allowed is not None
    assert allowed.content == "<main><h1>Allowed page</h1></main>"
    assert disallowed is None
    assert requests.count("https://docs.example/robots.txt") == 1
    assert "https://docs.example/private" not in requests


def test_url_connector_fails_closed_when_robots_is_unreachable():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="temporarily unavailable")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = RagUrlConnector(
        client=client,
        config=RagCrawlerConfig(
            user_agent="SidebrainRAGTest/1.0",
            timeout_seconds=2,
            max_concurrency_per_host=1,
            request_interval_seconds=0,
            robots_cache_hours=24,
        ),
    )

    async def run():
        page = await connector.fetch_page("https://docs.example/page")
        await client.aclose()
        return page

    assert asyncio.run(run()) is None


def test_url_connector_exposes_retry_after_for_http_429():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(429, headers={"Retry-After": "3"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = RagUrlConnector(
        client=client,
        config=RagCrawlerConfig(
            user_agent="SidebrainRAGTest/1.0",
            timeout_seconds=2,
            max_concurrency_per_host=1,
            request_interval_seconds=0,
            robots_cache_hours=24,
        ),
    )

    async def run():
        try:
            await connector.fetch_page("https://docs.example/page")
        finally:
            await client.aclose()

    try:
        asyncio.run(run())
    except RagRateLimitError as error:
        assert error.retry_after_seconds == 3
    else:
        raise AssertionError(
            "HTTP 429 must stop the crawl and expose Retry-After"
        )


def test_sitemap_connector_extracts_page_locations():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://docs.example/tutorial/</loc></url>
      <url><loc>https://docs.example/reference/</loc></url>
    </urlset>
    """

    assert RagSitemapConnector.parse(xml) == [
        "https://docs.example/tutorial/",
        "https://docs.example/reference/",
    ]


def test_local_connector_includes_markdown_and_rst_with_path_filters(
    tmp_path: Path,
):
    (tmp_path / "tutorial.md").write_text("# Tutorial", encoding="utf-8")
    (tmp_path / "reference.rst").write_text("Reference", encoding="utf-8")
    (tmp_path / "ignore.html").write_text("<h1>Ignore</h1>", encoding="utf-8")
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "secret.md").write_text(
        "secret", encoding="utf-8"
    )

    paths = RagLocalConnector.list_documents(
        tmp_path,
        include_paths=["**/*.md", "**/*.rst"],
        exclude_paths=["private/**"],
    )

    assert [path.name for path in paths] == ["reference.rst", "tutorial.md"]


def test_git_connector_shallow_clone_reads_only_accepted_docs(tmp_path: Path):
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(
        ["git", "init", str(repository)], check=True, capture_output=True
    )
    (repository / "guide.md").write_text("# Guide", encoding="utf-8")
    (repository / "manual.rst").write_text("Manual", encoding="utf-8")
    (repository / "binary.pdf").write_bytes(b"not indexed")
    subprocess.run(
        ["git", "-C", str(repository), "add", "."],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    checkout = tmp_path / "checkout"

    asyncio.run(RagGitConnector().clone_to(str(repository), checkout))
    paths = RagLocalConnector.list_documents(
        checkout,
        include_paths=["**/*.md", "**/*.rst"],
        exclude_paths=[],
    )

    assert {path.name for path in paths} == {"guide.md", "manual.rst"}
