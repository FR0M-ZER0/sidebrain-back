from __future__ import annotations

from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup, NavigableString, Tag

from sidebrain_back.rag.rag_document_parser import (
    RagDocumentParser,
    RagParsedDocument,
)


class RagHtmlParser:
    _REMOVE_SELECTORS = (
        "nav",
        "header",
        "footer",
        "script",
        "style",
        "noscript",
        "aside",
        "[role='navigation']",
        ".sidebar",
        ".breadcrumbs",
        ".top-navigation",
        ".advertisement",
        ".ad-container",
    )

    def __init__(self, document_parser: RagDocumentParser | None = None):
        self.document_parser = document_parser or RagDocumentParser()

    def parse(
        self,
        html: str,
        *,
        source_url: str,
        source_version: str | None = None,
    ) -> RagParsedDocument:
        soup = BeautifulSoup(html, "html.parser")
        for selector in self._REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

        content_root = soup.find("article") or soup.find("main") or soup.body
        if content_root is None:
            content_root = soup
        heading = content_root.find("h1")
        title_element = soup.find("title")
        title = (
            heading.get_text(" ", strip=True)
            if heading is not None
            else title_element.get_text(" ", strip=True)
            if title_element is not None
            else None
        )
        markdown = "\n\n".join(
            rendered
            for child in content_root.children
            if (rendered := self._render(child))
        )
        parsed = self.document_parser.parse_markdown(
            markdown,
            source_url=source_url,
            title=title,
            source_version=source_version,
        )
        canonical = soup.find(
            "link", rel=lambda value: value and "canonical" in value
        )
        canonical_url = (
            canonical.get("href") if canonical is not None else source_url
        )
        return RagParsedDocument(
            title=parsed.title,
            source_url=source_url,
            canonical_url=canonical_url,
            source_version=source_version,
            sections=parsed.sections,
        )

    @staticmethod
    def extract_links(html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        for selector in RagHtmlParser._REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
        root = soup.find("article") or soup.find("main") or soup.body or soup
        links = set()
        for anchor in root.select("a[href]"):
            absolute, _fragment = urldefrag(urljoin(base_url, anchor["href"]))
            parsed = urlsplit(absolute)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                links.add(absolute)
        return sorted(links)

    def _render(self, node: Tag | NavigableString) -> str:
        if isinstance(node, NavigableString):
            return " ".join(str(node).split())
        if not isinstance(node, Tag):
            return ""
        name = node.name.lower()
        if name == "pre":
            code = node.find("code")
            code_node = code or node
            classes = code_node.get("class", [])
            language = next(
                (
                    value.removeprefix("language-").removeprefix("lang-")
                    for value in classes
                    if value.startswith(("language-", "lang-"))
                ),
                code_node.get("data-language", ""),
            )
            source = code_node.get_text("", strip=False).rstrip("\r\n")
            return f"```{language}\n{source}\n```"
        if name == "code":
            return f"`{node.get_text('', strip=False)}`"
        children = [
            rendered
            for child in node.children
            if (rendered := self._render(child))
        ]
        content = " ".join(children).strip()
        if not content:
            return ""
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return f"{'#' * int(name[1])} {content}"
        if name == "li":
            return f"- {content}"
        if name == "br":
            return "\n"
        if name in {"p", "div", "section", "article", "ul", "ol", "main"}:
            return "\n\n".join(children)
        if name == "a":
            href = node.get("href")
            return f"{content} ({href})" if href else content
        return content
