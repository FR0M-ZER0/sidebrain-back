from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from docutils import nodes
from docutils.core import publish_doctree
from markdown_it import MarkdownIt

from sidebrain_back.rag.rag_chunker import RagSection


@dataclass(frozen=True)
class RagParsedDocument:
    title: str
    source_url: str
    canonical_url: str
    source_version: str | None
    sections: list[RagSection]


class RagDocumentParser:
    def parse_markdown(
        self,
        content: str,
        *,
        source_url: str,
        title: str | None = None,
        source_version: str | None = None,
    ) -> RagParsedDocument:
        tokens = MarkdownIt("commonmark").parse(content)
        document_title = title or self._title_from_url(source_url)
        headings: list[tuple[int, str]] = []
        sections: list[RagSection] = []
        body: list[str] = []
        pending_heading = False

        def flush() -> None:
            if not body:
                return
            section_path = " > ".join(value for _, value in headings)
            sections.append(
                RagSection(
                    section_path=section_path or document_title,
                    text="\n\n".join(body).strip(),
                )
            )
            body.clear()

        for token in tokens:
            if token.type == "heading_open":
                flush()
                level = int(token.tag[1:])
                pending_heading = True
                continue
            if token.type == "inline":
                if pending_heading:
                    heading = token.content.strip()
                    if heading:
                        if len(headings) < level:
                            headings.append((level, heading))
                        else:
                            headings[:] = [
                                item for item in headings if item[0] < level
                            ]
                            headings.append((level, heading))
                        if level == 1 and title is None:
                            document_title = heading
                    pending_heading = False
                elif token.content.strip():
                    body.append(token.content.strip())
                continue
            if token.type in {"fence", "code_block"}:
                pending_heading = False
                info = token.info.strip().split(maxsplit=1)
                language = info[0] if info else ""
                code = token.content.rstrip("\r\n")
                body.append(f"```{language}\n{code}\n```")
                continue
            if token.type == "html_block" and token.content.strip():
                body.append(token.content.strip())
        flush()
        if not sections and content.strip():
            sections.append(RagSection(document_title, content.strip()))
        return RagParsedDocument(
            title=document_title,
            source_url=source_url,
            canonical_url=source_url,
            source_version=source_version,
            sections=sections,
        )

    def parse_rst(
        self,
        content: str,
        *,
        source_url: str,
        title: str | None = None,
        source_version: str | None = None,
    ) -> RagParsedDocument:
        doctree = publish_doctree(
            source=content,
            settings_overrides={
                "file_insertion_enabled": False,
                "raw_enabled": False,
                "halt_level": 6,
                "report_level": 5,
                "warning_stream": io.StringIO(),
            },
        )
        document_title = title or self._title_from_url(source_url)
        title_node = next(
            (
                child
                for child in doctree.children
                if isinstance(child, nodes.title)
            ),
            None,
        )
        if title_node is not None and title is None:
            document_title = title_node.astext().strip() or document_title
        subtitle_node = next(
            (
                child
                for child in doctree.children
                if isinstance(child, nodes.subtitle)
            ),
            None,
        )
        root_headings = [document_title]
        if subtitle_node is not None:
            root_headings.append(subtitle_node.astext().strip())

        sections: list[RagSection] = []
        root_body: list[str] = []

        def render(node: nodes.Node) -> str:
            if isinstance(node, nodes.literal_block):
                classes = node.get("classes", [])
                language = node.get("language") or next(
                    (
                        item
                        for item in classes
                        if item not in {"code", "literal"}
                    ),
                    "",
                )
                return f"```{language}\n{node.astext().rstrip()}\n```"
            if isinstance(node, nodes.paragraph):
                return node.astext().strip()
            if isinstance(node, nodes.list_item):
                return "- " + " ".join(
                    rendered
                    for child in node.children
                    if (rendered := render(child))
                )
            if isinstance(node, nodes.section):
                return ""
            return "\n".join(
                rendered for child in getattr(node, "children", [])
                if (rendered := render(child))
            )

        def walk_section(node: nodes.section, parents: list[str]) -> None:
            heading = next(
                (child.astext().strip() for child in node.children
                 if isinstance(child, nodes.title)),
                "",
            )
            path = (
                parents
                if heading.casefold() == document_title.casefold()
                else [*parents, heading]
                if heading
                else parents
            )
            body: list[str] = []
            for child in node.children:
                if isinstance(child, nodes.title):
                    continue
                if isinstance(child, nodes.section):
                    if body:
                        sections.append(
                            RagSection(
                                " > ".join(path), "\n\n".join(body).strip()
                            )
                        )
                        body.clear()
                    walk_section(child, path)
                    continue
                rendered = render(child)
                if rendered:
                    body.append(rendered)
            if body:
                sections.append(
                    RagSection(" > ".join(path), "\n\n".join(body).strip())
                )

        for child in doctree.children:
            if isinstance(child, nodes.section):
                walk_section(child, root_headings)
            elif not isinstance(child, (nodes.title, nodes.subtitle)):
                rendered = render(child)
                if rendered:
                    root_body.append(rendered)
        if root_body:
            sections.insert(
                0,
                RagSection(
                    " > ".join(root_headings),
                    "\n\n".join(root_body).strip(),
                ),
            )
        if not sections and content.strip():
            sections.append(RagSection(document_title, content.strip()))
        return RagParsedDocument(
            title=document_title,
            source_url=source_url,
            canonical_url=source_url,
            source_version=source_version,
            sections=sections,
        )

    @staticmethod
    def _title_from_url(source_url: str) -> str:
        path = PurePosixPath(urlsplit(source_url).path.rstrip("/"))
        title = path.stem or path.name or "Document"
        return title.replace("_", " ").replace("-", " ").strip().title()
