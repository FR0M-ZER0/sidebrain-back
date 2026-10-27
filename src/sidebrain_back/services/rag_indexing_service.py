from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import tempfile
import time
import unicodedata
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from pathlib import Path
from urllib.parse import quote, urldefrag, urlsplit

from sidebrain_back.models.rag_chunk_model import RagChunkModel
from sidebrain_back.rag.rag_chunker import (
    RagChunk,
    RagChunker,
    approximate_duplicate_groups,
    deduplicate_exact,
)
from sidebrain_back.rag.rag_config import (
    RagConfig,
    RagSourceConfig,
    RagSourceType,
)
from sidebrain_back.rag.rag_document_parser import (
    RagDocumentParser,
    RagParsedDocument,
)
from sidebrain_back.rag.rag_git_connector import RagGitConnector
from sidebrain_back.rag.rag_html_parser import RagHtmlParser
from sidebrain_back.rag.rag_local_connector import RagLocalConnector
from sidebrain_back.rag.rag_sitemap_connector import RagSitemapConnector
from sidebrain_back.rag.rag_url_connector import (
    RagFetchedPage,
    RagRateLimitError,
    RagUrlConnector,
)
from sidebrain_back.repositories.rag_chunk_repository import RagChunkRepository
from sidebrain_back.repositories.rag_document_repository import (
    RagDocumentRepository,
)
from sidebrain_back.schemas.rag_schema import RagIndexingReportSchema
from sidebrain_back.services.rag_embedding_service import (
    RagEmbeddingInput,
    RagEmbeddingService,
)

logger = logging.getLogger(__name__)
_TAG_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9_+#.-]{1,40}")
_TAG_STOP_WORDS = {
    "and",
    "for",
    "from",
    "guide",
    "the",
    "tutorial",
    "with",
}


class RagIndexingService:
    def __init__(
        self,
        *,
        db,
        document_repository: RagDocumentRepository,
        chunk_repository: RagChunkRepository,
        chunker: RagChunker,
        embedding_service: RagEmbeddingService,
        config: RagConfig,
        html_parser: RagHtmlParser | None = None,
        document_parser: RagDocumentParser | None = None,
        git_connector: RagGitConnector | None = None,
        local_connector: RagLocalConnector | None = None,
        sitemap_connector: RagSitemapConnector | None = None,
        url_connector_factory=None,
    ):
        self.db = db
        self.document_repository = document_repository
        self.chunk_repository = chunk_repository
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.config = config
        self.html_parser = html_parser or RagHtmlParser()
        self.document_parser = document_parser or RagDocumentParser()
        self.git_connector = git_connector or RagGitConnector(
            timeout_seconds=config.defaults.crawler.timeout_seconds
        )
        self.local_connector = local_connector or RagLocalConnector()
        self.sitemap_connector = sitemap_connector or RagSitemapConnector()
        self.url_connector_factory = url_connector_factory or (
            lambda crawler_config: RagUrlConnector(config=crawler_config)
        )

    async def index_source(
        self, source: RagSourceConfig, *, full: bool = False
    ) -> RagIndexingReportSchema:
        started = time.monotonic()
        failures: list[str] = []
        if source.type in {RagSourceType.URL, RagSourceType.SITEMAP}:
            connector = self.url_connector_factory(
                self.config.defaults.crawler
            )
            try:
                if source.type is RagSourceType.URL:
                    (
                        documents,
                        discovered,
                        complete,
                        failures,
                    ) = await self._collect_url_source(source, connector)
                else:
                    (
                        documents,
                        discovered,
                        complete,
                        failures,
                    ) = await self._collect_sitemap_source(source, connector)
            finally:
                await connector.close()
        elif source.type is RagSourceType.GIT:
            (
                documents,
                discovered,
                complete,
                failures,
            ) = await self._collect_git_source(source)
        else:
            (
                documents,
                discovered,
                complete,
                failures,
            ) = await self._collect_local_source(source)

        report = await self.index_documents(
            source,
            documents,
            manifest_complete=complete,
            discovered_canonical_urls=discovered,
            collection_failures=failures,
            discovered_document_count=len(set(discovered)),
            force_reindex=full,
        )
        report.duration_seconds += time.monotonic() - started
        return report

    async def index_all(
        self, *, full: bool = False
    ) -> RagIndexingReportSchema:
        started = time.monotonic()
        price = self.config.defaults.embeddings.price_per_million_input_tokens
        report = RagIndexingReportSchema(
            estimated_cost=0.0 if price is not None else None
        )
        for source in self.config.sources:
            try:
                source_report = await self.index_source(source, full=full)
            except Exception as error:
                report.sources_processed += 1
                report.failures.append(
                    f"{source.name}: {type(error).__name__}"
                )
                logger.warning(
                    "RAG source indexing failed",
                    extra={
                        "source_name": source.name,
                        "error_category": type(error).__name__,
                    },
                )
                continue
            self._merge_report(report, source_report)
        report.duration_seconds = time.monotonic() - started
        return report

    @staticmethod
    def _merge_report(
        target: RagIndexingReportSchema,
        source: RagIndexingReportSchema,
    ) -> None:
        for field in (
            "sources_processed",
            "documents_found",
            "documents_processed",
            "documents_unchanged",
            "chunks_generated",
            "exact_duplicates_removed",
            "approximate_duplicates_grouped",
            "license_excluded",
        ):
            setattr(
                target,
                field,
                getattr(target, field) + getattr(source, field),
            )
        target.failures.extend(source.failures)
        target.duration_seconds += source.duration_seconds
        if source.estimated_cost is not None:
            target.estimated_cost = (
                target.estimated_cost or 0.0
            ) + source.estimated_cost

    async def _collect_url_source(
        self, source: RagSourceConfig, connector: RagUrlConnector
    ) -> tuple[list[RagParsedDocument], list[str], bool, list[str]]:
        if source.url is None:
            raise ValueError("url source requires url")
        root_url = self._normalize_url(source.url)
        source_host = urlsplit(root_url).netloc.casefold()
        max_depth = int(source.connector.get("max_depth", 4))
        max_pages = int(source.connector.get("max_pages", 10000))
        queue = [(root_url, 0)]
        visited: set[str] = set()
        documents: list[RagParsedDocument] = []
        discovered: list[str] = []
        failures: list[str] = []
        manifest_complete = True

        while queue:
            if len(visited) >= max_pages:
                manifest_complete = False
                failures.append(f"{source.name}: max_pages reached")
                break
            url, depth = queue.pop(0)
            url = self._normalize_url(url)
            if url in visited or not self._source_url_allowed(source, url):
                continue
            if urlsplit(url).netloc.casefold() != source_host:
                continue
            visited.add(url)
            discovered.append(url)
            try:
                page = await self._fetch_page(connector, url)
                if page is None:
                    manifest_complete = False
                    failures.append(f"{url}: robots_disallowed")
                    continue
                if urlsplit(page.final_url).netloc.casefold() != source_host:
                    manifest_complete = False
                    failures.append(f"{url}: redirect_outside_source_host")
                    continue
                document = self._parse_page(source, page)
            except Exception as error:
                manifest_complete = False
                failures.append(f"{url}: {type(error).__name__}")
                continue

            documents.append(document)
            discovered.append(document.canonical_url)
            if depth < max_depth:
                for link in self.html_parser.extract_links(
                    page.content, page.final_url
                ):
                    link = self._normalize_url(link)
                    if (
                        urlsplit(link).netloc.casefold() == source_host
                        and self._source_url_allowed(source, link)
                        and link not in visited
                    ):
                        queue.append((link, depth + 1))

        return (
            documents,
            list(dict.fromkeys(discovered)),
            manifest_complete,
            failures,
        )

    async def _collect_sitemap_source(
        self, source: RagSourceConfig, connector: RagUrlConnector
    ) -> tuple[list[RagParsedDocument], list[str], bool, list[str]]:
        sitemap_url = source.sitemap_url or source.url
        if sitemap_url is None:
            raise ValueError("sitemap source requires sitemap_url")
        sitemap_url = self._normalize_url(sitemap_url)
        source_host = urlsplit(sitemap_url).netloc.casefold()
        max_depth = int(source.connector.get("max_depth", 4))
        max_pages = int(source.connector.get("max_pages", 10000))
        sitemap_queue = [(sitemap_url, 0)]
        visited_sitemaps: set[str] = set()
        documents: list[RagParsedDocument] = []
        discovered: list[str] = []
        failures: list[str] = []
        manifest_complete = True

        while sitemap_queue:
            current_sitemap, depth = sitemap_queue.pop(0)
            current_sitemap = self._normalize_url(current_sitemap)
            if current_sitemap in visited_sitemaps:
                continue
            visited_sitemaps.add(current_sitemap)
            try:
                sitemap_page = await self._fetch_page(
                    connector, current_sitemap
                )
                if sitemap_page is None:
                    manifest_complete = False
                    failures.append(f"{current_sitemap}: robots_disallowed")
                    continue
                is_index = self.sitemap_connector.is_sitemap_index(
                    sitemap_page.content
                )
                locations = self.sitemap_connector.parse(sitemap_page.content)
            except Exception as error:
                manifest_complete = False
                failures.append(f"{current_sitemap}: {type(error).__name__}")
                continue

            if is_index:
                if depth >= max_depth:
                    manifest_complete = False
                    failures.append(f"{current_sitemap}: sitemap_depth_limit")
                    continue
                for location in locations:
                    location = self._normalize_url(location)
                    if urlsplit(location).netloc.casefold() == source_host:
                        sitemap_queue.append((location, depth + 1))
                continue

            for page_url in locations:
                if len(discovered) >= max_pages:
                    manifest_complete = False
                    failures.append(f"{source.name}: max_pages reached")
                    break
                page_url = self._normalize_url(page_url)
                if (
                    urlsplit(page_url).netloc.casefold() != source_host
                    or not self._source_url_allowed(source, page_url)
                ):
                    continue
                discovered.append(page_url)
                try:
                    page = await self._fetch_page(connector, page_url)
                    if page is None:
                        manifest_complete = False
                        failures.append(f"{page_url}: robots_disallowed")
                        continue
                    document = self._parse_page(source, page)
                    documents.append(document)
                    discovered.append(document.canonical_url)
                except Exception as error:
                    manifest_complete = False
                    failures.append(f"{page_url}: {type(error).__name__}")

        return (
            documents,
            list(dict.fromkeys(discovered)),
            manifest_complete,
            failures,
        )

    async def _collect_git_source(
        self, source: RagSourceConfig
    ) -> tuple[list[RagParsedDocument], list[str], bool, list[str]]:
        if source.repository_url is None:
            raise ValueError("git source requires repository_url")
        documents: list[RagParsedDocument] = []
        discovered: list[str] = []
        failures: list[str] = []
        try:
            with tempfile.TemporaryDirectory(prefix="sidebrain-rag-") as root:
                checkout = Path(root) / "source"
                await self.git_connector.clone_to(
                    source.repository_url,
                    checkout,
                    ref=source.connector.get("ref"),
                )
                version = await self.git_connector.resolve_version(checkout)
                paths = self.local_connector.list_documents(
                    checkout,
                    include_paths=source.include_paths,
                    exclude_paths=source.exclude_paths,
                )
                for path in paths:
                    relative = path.relative_to(checkout).as_posix()
                    source_url = self._git_document_url(
                        source.repository_url, version, relative
                    )
                    discovered.append(source_url)
                    try:
                        content = await asyncio.to_thread(
                            self.local_connector.read_document, path
                        )
                        documents.append(
                            self._parse_file(
                                content,
                                source_url=source_url,
                                title=path.stem,
                                version=version,
                                suffix=path.suffix,
                            )
                        )
                    except Exception as error:
                        failures.append(
                            f"{source_url}: {type(error).__name__}"
                        )
        except Exception as error:
            return [], [], False, [f"{source.name}: {type(error).__name__}"]
        return documents, discovered, True, failures

    async def _collect_local_source(
        self, source: RagSourceConfig
    ) -> tuple[list[RagParsedDocument], list[str], bool, list[str]]:
        if source.path is None:
            raise ValueError("local source requires path")
        root = await asyncio.to_thread(Path(source.path).resolve, strict=True)
        paths = self.local_connector.list_documents(
            root,
            include_paths=source.include_paths,
            exclude_paths=source.exclude_paths,
        )
        documents: list[RagParsedDocument] = []
        discovered: list[str] = []
        failures: list[str] = []
        for path in paths:
            source_url = path.resolve().as_uri()
            discovered.append(source_url)
            try:
                content = await asyncio.to_thread(
                    self.local_connector.read_document, path
                )
                documents.append(
                    self._parse_file(
                        content,
                        source_url=source_url,
                        title=path.stem,
                        version=self._file_hash(content),
                        suffix=path.suffix,
                    )
                )
            except Exception as error:
                failures.append(f"{source_url}: {type(error).__name__}")
        return documents, discovered, True, failures

    async def _fetch_page(
        self, connector: RagUrlConnector, url: str
    ) -> RagFetchedPage | None:
        try:
            return await connector.fetch_page(url)
        except RagRateLimitError as error:
            retry_after = error.retry_after_seconds
            if retry_after is None or retry_after > 60:
                raise
            await asyncio.sleep(retry_after)
            return await connector.fetch_page(url)

    def _parse_page(
        self, source: RagSourceConfig, page: RagFetchedPage
    ) -> RagParsedDocument:
        document = self.html_parser.parse(
            page.content,
            source_url=page.final_url,
            source_version=(page.etag or page.last_modified),
        )
        canonical_url = self._normalize_url(document.canonical_url)
        if not self._source_url_allowed(source, canonical_url):
            canonical_url = self._normalize_url(page.final_url)
        return RagParsedDocument(
            title=document.title,
            source_url=page.final_url,
            canonical_url=canonical_url,
            source_version=page.etag or page.last_modified,
            sections=document.sections,
        )

    def _parse_file(
        self,
        content: str,
        *,
        source_url: str,
        title: str,
        version: str,
        suffix: str,
    ) -> RagParsedDocument:
        if suffix.lower() == ".rst":
            return self.document_parser.parse_rst(
                content,
                source_url=source_url,
                title=title,
                source_version=version,
            )
        return self.document_parser.parse_markdown(
            content,
            source_url=source_url,
            title=title,
            source_version=version,
        )

    @staticmethod
    def _source_url_allowed(source: RagSourceConfig, url: str) -> bool:
        parsed = urlsplit(url)
        path = parsed.path or "/"
        for pattern in source.exclude_paths:
            if pattern.startswith("?"):
                if parsed.query:
                    return False
            elif RagIndexingService._path_matches(path, pattern):
                return False
        return any(
            RagIndexingService._path_matches(path, pattern)
            for pattern in source.include_paths
            if not pattern.startswith("?")
        )

    @staticmethod
    def _path_matches(path: str, pattern: str) -> bool:
        if fnmatchcase(path, pattern):
            return True
        if pattern.startswith("**/") and fnmatchcase(
            path.lstrip("/"), pattern[3:]
        ):
            return True
        return pattern.endswith("/**") and path.rstrip("/") == pattern[
            :-3
        ].rstrip("/")

    @staticmethod
    def _normalize_url(url: str) -> str:
        without_fragment, _fragment = urldefrag(url.strip())
        return without_fragment

    @staticmethod
    def _git_document_url(
        repository_url: str, version: str, relative_path: str
    ) -> str:
        clean_repository = repository_url.removesuffix(".git").rstrip("/")
        parsed = urlsplit(clean_repository)
        quoted_path = quote(relative_path)
        if parsed.netloc.casefold() == "github.com":
            return f"{clean_repository}/blob/{version}/{quoted_path}"
        return f"{clean_repository}@{version}:{relative_path}"

    @staticmethod
    def _file_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def document_id(source_name: str, canonical_url: str) -> str:
        value = f"{source_name}\0{canonical_url}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def document_hash(document: RagParsedDocument) -> str:
        sections = [
            (
                section.section_path,
                unicodedata.normalize(
                    "NFC",
                    section.text.replace("\r\n", "\n").replace("\r", "\n"),
                ),
            )
            for section in document.sections
        ]
        normalized = json.dumps(
            {"title": document.title, "sections": sections},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def index_documents(
        self,
        source: RagSourceConfig,
        documents: list[RagParsedDocument],
        *,
        manifest_complete: bool = True,
        discovered_canonical_urls: list[str] | None = None,
        collection_failures: list[str] | None = None,
        discovered_document_count: int | None = None,
        force_reindex: bool = False,
    ) -> RagIndexingReportSchema:
        started_at = datetime.now(UTC)
        configured_price = (
            self.config.defaults.embeddings.price_per_million_input_tokens
        )
        report = RagIndexingReportSchema(
            sources_processed=1,
            documents_found=(
                discovered_document_count
                if discovered_document_count is not None
                else len(documents)
            ),
            estimated_cost=0.0 if configured_price is not None else None,
        )
        report.failures.extend(collection_failures or [])
        present_urls = list(
            dict.fromkeys(
                discovered_canonical_urls
                if discovered_canonical_urls is not None
                else [document.canonical_url for document in documents]
            )
        )

        for document in documents:
            doc_id = self.document_id(source.name, document.canonical_url)
            try:
                await self._index_document(
                    source, document, doc_id, report, force_reindex
                )
            except Exception as error:
                await self.db.rollback()
                report.failures.append(
                    f"{document.canonical_url}: {type(error).__name__}"
                )
                logger.warning(
                    "RAG document indexing failed",
                    extra={
                        "source_name": source.name,
                        "doc_id": doc_id,
                        "error_category": type(error).__name__,
                    },
                )

        if manifest_complete:
            try:
                await self.document_repository.delete_missing_from_source(
                    source.name, present_urls
                )
                await self.chunk_repository.delete_orphan_chunks()
                await self.db.commit()
            except Exception as error:
                await self.db.rollback()
                report.failures.append(
                    f"{source.name}: reconciliation {type(error).__name__}"
                )
                logger.warning(
                    "RAG source reconciliation failed",
                    extra={
                        "source_name": source.name,
                        "error_category": type(error).__name__,
                    },
                )

        report.duration_seconds = (
            datetime.now(UTC) - started_at
        ).total_seconds()
        return report

    async def _index_document(
        self,
        source: RagSourceConfig,
        document: RagParsedDocument,
        doc_id: str,
        report: RagIndexingReportSchema,
        force_reindex: bool,
    ) -> None:
        content_hash = self.document_hash(document)
        existing = await (
            self.document_repository.get_by_source_and_canonical_url(
                source.name,
                document.canonical_url,
            )
        )
        now = datetime.now(UTC)
        if (
            existing is not None
            and existing.document_hash == content_hash
            and not force_reindex
        ):
            await self.document_repository.update(
                existing,
                source_url=document.source_url,
                title=document.title,
                source_version=document.source_version,
                updated_at=now,
            )
            chunks = await self.chunk_repository.list_chunks_by_document(
                doc_id
            )
            await self.db.commit()
            missing = self._missing_embeddings(chunks)
            if missing:
                await self._embed(missing, report)
            report.documents_unchanged += 1
            return

        chunks = self.chunker.chunk_document(
            title=document.title,
            sections=document.sections,
            attribution=self._base_attribution(source, document, doc_id),
        )
        chunks, exact_removed = deduplicate_exact(chunks)
        report.exact_duplicates_removed += exact_removed
        groups = approximate_duplicate_groups(
            chunks,
            self.config.defaults.deduplication.simhash_max_hamming_distance,
        )
        report.approximate_duplicates_grouped += sum(
            len(group) - 1 for group in groups
        )
        for group in groups:
            group_id = hashlib.sha256(
                "\0".join(sorted(chunk.chunk_id for chunk in group)).encode(
                    "utf-8"
                )
            ).hexdigest()
            for chunk in group:
                chunk.duplicate_group_id = group_id

        document_values = {
            "source_name": source.name,
            "source_url": document.source_url,
            "canonical_url": document.canonical_url,
            "title": document.title,
            "document_hash": content_hash,
            "source_version": document.source_version,
            "collected_at": now,
            "updated_at": now,
        }
        if existing is None:
            await self.document_repository.create(
                doc_id=doc_id, **document_values
            )
        else:
            doc_id = existing.doc_id
            await self.document_repository.update(existing, **document_values)
            await self.chunk_repository.delete_attributions_for_document(
                doc_id
            )

        embedding_inputs: list[RagEmbeddingInput] = []
        for chunk in chunks:
            stored_chunk = await self.chunk_repository.get_by_chunk_id(
                chunk.chunk_id
            )
            if stored_chunk is None:
                await self.chunk_repository.create_chunk(
                    chunk_id=chunk.chunk_id,
                    content_hash=chunk.content_hash,
                    text=chunk.text,
                    duplicate_fingerprint=chunk.duplicate_fingerprint,
                    duplicate_group_id=chunk.duplicate_group_id,
                )
            else:
                await self.chunk_repository.update_chunk(
                    stored_chunk,
                    duplicate_fingerprint=chunk.duplicate_fingerprint,
                    duplicate_group_id=chunk.duplicate_group_id,
                )

            external_allowed = False
            for candidate_attribution in chunk.attributions:
                values = self._attribution_values(
                    source,
                    document,
                    doc_id,
                    chunk,
                    candidate_attribution,
                )
                external_allowed |= values["external_processing_allowed"]
                current = await self.chunk_repository.get_attribution(
                    chunk_id=chunk.chunk_id,
                    doc_id=doc_id,
                    section_path=values["section_path"],
                    license=values["license"],
                )
                if current is None:
                    await self.chunk_repository.add_attribution(
                        chunk_id=chunk.chunk_id,
                        **values,
                    )
                else:
                    await self.chunk_repository.update_attribution(
                        current, **values
                    )
            if not external_allowed:
                report.license_excluded += 1
            embedding_inputs.append(
                RagEmbeddingInput(
                    chunk_id=chunk.chunk_id,
                    content_hash=chunk.content_hash,
                    text=chunk.text,
                    external_processing_allowed=external_allowed,
                )
            )

        await self.chunk_repository.delete_orphan_chunks()
        await self.db.commit()
        report.documents_processed += 1
        report.chunks_generated += len(chunks)
        if embedding_inputs:
            await self._embed(embedding_inputs, report)

    def _missing_embeddings(
        self, chunks: list[RagChunkModel]
    ) -> list[RagEmbeddingInput]:
        model = self.config.defaults.embeddings.model
        dimensions = self.config.defaults.embeddings.dimensions
        missing: list[RagEmbeddingInput] = []
        for chunk in chunks:
            current = any(
                embedding.model_id == model
                and embedding.dimensions == dimensions
                for embedding in chunk.embeddings
            )
            if current:
                continue
            external_allowed = any(
                attribution.external_processing_allowed
                for attribution in chunk.attributions
            )
            missing.append(
                RagEmbeddingInput(
                    chunk_id=chunk.chunk_id,
                    content_hash=chunk.content_hash,
                    text=chunk.text,
                    external_processing_allowed=external_allowed,
                )
            )
        return missing

    async def _embed(
        self,
        chunks: list[RagEmbeddingInput],
        report: RagIndexingReportSchema,
    ) -> None:
        _results, usage = await self.embedding_service.embed_chunks(chunks)
        if usage.estimated_cost is not None:
            report.estimated_cost = (
                report.estimated_cost or 0.0
            ) + usage.estimated_cost

    @staticmethod
    def _base_attribution(
        source: RagSourceConfig,
        document: RagParsedDocument,
        doc_id: str,
    ) -> dict:
        license_config = source.license_for("concept")
        return {
            "doc_id": doc_id,
            "source_name": source.name,
            "source_url": document.source_url,
            "title": document.title,
            "language": source.language,
            "level": source.level,
            "content_type": "concept",
            "topics": [],
            "license": license_config.license,
            "license_url": license_config.license_url,
            "external_processing_allowed": (
                license_config.external_processing_allowed
            ),
        }

    @classmethod
    def _attribution_values(
        cls,
        source: RagSourceConfig,
        document: RagParsedDocument,
        doc_id: str,
        chunk: RagChunk,
        candidate: dict,
    ) -> dict:
        content_type = cls._classify_content_type(source, chunk)
        license_config = source.license_for(content_type)
        return {
            "doc_id": doc_id,
            "section_path": candidate.get("section_path", chunk.section_path),
            "source_name": source.name,
            "source_url": document.source_url,
            "title": document.title,
            "language": source.language,
            "level": source.level,
            "content_type": content_type,
            "topics": cls._extract_topics(chunk.section_path),
            "license": license_config.license,
            "license_url": license_config.license_url,
            "external_processing_allowed": (
                license_config.external_processing_allowed
            ),
        }

    @staticmethod
    def _classify_content_type(
        source: RagSourceConfig, chunk: RagChunk
    ) -> str:
        if chunk.code_hash is not None:
            return "code_example"
        section = chunk.section_path.casefold()
        if any(
            word in section for word in ("exercise", "practice", "exercício")
        ):
            return "exercise"
        if "tutorial" in source.name:
            return "tutorial"
        if "library" in source.name or source.name.startswith("mdn-"):
            return "reference"
        return "concept"

    @staticmethod
    def _extract_topics(section_path: str) -> list[str]:
        parts = section_path.split(" > ")
        candidate = parts[-1].casefold() if parts else ""
        return sorted(
            {
                token.lower()
                for token in _TAG_PATTERN.findall(candidate)
                if token.lower() not in _TAG_STOP_WORDS
            }
        )[:8]
