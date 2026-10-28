import asyncio
import hashlib
from types import SimpleNamespace

from sidebrain_back.rag.rag_chunker import RagChunk, RagSection
from sidebrain_back.rag.rag_config import load_rag_config
from sidebrain_back.rag.rag_document_parser import RagParsedDocument
from sidebrain_back.services.rag_indexing_service import RagIndexingService


class FakeDatabase:
    async def commit(self):
        return None

    async def rollback(self):
        return None


class FakeDocumentRepository:
    def __init__(self, documents=None):
        self.documents = documents or {}
        self.deleted_sources = []

    async def get_by_source_and_canonical_url(
        self, source_name, canonical_url
    ):
        return self.documents.get((source_name, canonical_url))

    async def create(self, **values):
        document = SimpleNamespace(**values)
        self.documents[(document.source_name, document.canonical_url)] = (
            document
        )
        return document

    async def update(self, document, **values):
        for key, value in values.items():
            setattr(document, key, value)
        return document

    async def delete_missing_from_source(self, source_name, present_urls):
        self.deleted_sources.append((source_name, set(present_urls)))
        stale = [
            key
            for key in self.documents
            if key[0] == source_name and key[1] not in present_urls
        ]
        for key in stale:
            del self.documents[key]
        return len(stale)


class FakeChunkRepository:
    def __init__(self, chunks=None):
        self.chunks = chunks or {}
        self.attributions = {}
        for chunk in self.chunks.values():
            for attribution in chunk.attributions:
                key = (
                    chunk.chunk_id,
                    attribution.doc_id,
                    attribution.section_path,
                    attribution.license,
                )
                self.attributions[key] = attribution
        self.deleted_documents = []
        self.orphan_prunes = 0

    async def get_by_chunk_id(self, chunk_id):
        return self.chunks.get(chunk_id)

    async def create_chunk(self, **values):
        chunk = SimpleNamespace(**values, attributions=[], embeddings=[])
        self.chunks[chunk.chunk_id] = chunk
        return chunk

    async def update_chunk(self, chunk, **values):
        for key, value in values.items():
            setattr(chunk, key, value)
        return chunk

    async def get_attribution(self, **keys):
        key = (
            keys["chunk_id"],
            keys["doc_id"],
            keys["section_path"],
            keys["license"],
        )
        return self.attributions.get(key)

    async def add_attribution(self, **values):
        attribution = SimpleNamespace(**values)
        key = (
            attribution.chunk_id,
            attribution.doc_id,
            attribution.section_path,
            attribution.license,
        )
        self.attributions[key] = attribution
        self.chunks[attribution.chunk_id].attributions.append(attribution)
        return attribution

    async def update_attribution(self, attribution, **values):
        for key, value in values.items():
            setattr(attribution, key, value)
        return attribution

    async def delete_attributions_for_document(self, doc_id):
        self.deleted_documents.append(doc_id)
        keys = [key for key in self.attributions if key[1] == doc_id]
        for key in keys:
            attribution = self.attributions.pop(key)
            self.chunks[attribution.chunk_id].attributions.remove(attribution)
        return len(keys)

    async def list_chunks_by_document(self, doc_id):
        return [
            chunk
            for chunk in self.chunks.values()
            if any(item.doc_id == doc_id for item in chunk.attributions)
        ]

    async def delete_orphan_chunks(self):
        self.orphan_prunes += 1
        stale = [
            chunk_id
            for chunk_id, chunk in self.chunks.items()
            if not chunk.attributions
        ]
        for chunk_id in stale:
            del self.chunks[chunk_id]
        return len(stale)


class FakeChunker:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = 0

    def chunk_document(self, **_kwargs):
        self.calls += 1
        for chunk in self.chunks:
            attribution = dict(_kwargs["attribution"])
            attribution["title"] = _kwargs["title"]
            attribution["section_path"] = chunk.section_path
            chunk.attributions = [attribution]
        return self.chunks


class FakeEmbeddingService:
    def __init__(self):
        self.calls = []

    async def embed_chunks(self, chunks):
        self.calls.append(chunks)
        return [], SimpleNamespace(estimated_cost=0.01)


def _document(text="Lists preserve order."):
    return RagParsedDocument(
        title="Python Tutorial",
        source_url="https://docs.example/tutorial/lists.html",
        canonical_url="https://docs.example/tutorial/lists.html",
        source_version="3.15",
        sections=[RagSection("Tutorial > Lists", text)],
    )


def _chunk(text="Lists preserve order."):
    content_hash = hashlib.sha256(text.encode()).hexdigest()
    return RagChunk(
        chunk_id=hashlib.sha256(f"1:{content_hash}".encode()).hexdigest(),
        content_hash=content_hash,
        text=(
            "Document: Python Tutorial\nSection: Tutorial > Lists\n\n" + text
        ),
        body_text=text,
        section_path="Tutorial > Lists",
        language="python",
        content_type="tutorial",
        code_language=None,
        code_hash=None,
        duplicate_fingerprint="0" * 16,
        attributions=[],
    )


def test_unchanged_document_skips_parsing_and_embedding_provider():
    source = load_rag_config().source_by_name("python-tutorial")
    document = _document()
    doc_id = RagIndexingService.document_id(
        source.name, document.canonical_url
    )
    stored_document = SimpleNamespace(
        doc_id=doc_id,
        source_name=source.name,
        canonical_url=document.canonical_url,
        document_hash=RagIndexingService.document_hash(document),
        source_version="3.15",
    )
    stored_chunk = _chunk()
    stored_chunk.attributions = [
        SimpleNamespace(
            doc_id=doc_id,
            section_path=stored_chunk.section_path,
            license="PSF-2.0",
            external_processing_allowed=True,
        )
    ]
    stored_chunk.embeddings = [
        SimpleNamespace(
            model_id="text-embedding-3-small",
            dimensions=1536,
        )
    ]
    document_repository = FakeDocumentRepository(
        {(source.name, document.canonical_url): stored_document}
    )
    chunk_repository = FakeChunkRepository(
        {stored_chunk.chunk_id: stored_chunk}
    )
    chunker = FakeChunker([])
    embedding_service = FakeEmbeddingService()
    service = RagIndexingService(
        db=FakeDatabase(),
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        chunker=chunker,
        embedding_service=embedding_service,
        config=load_rag_config(),
    )

    report = asyncio.run(service.index_documents(source, [document]))

    assert report.documents_unchanged == 1
    assert report.documents_processed == 0
    assert chunker.calls == 0
    assert embedding_service.calls == []


def test_changed_document_replaces_attributions_and_embeds_new_chunks():
    source = load_rag_config().source_by_name("python-tutorial")
    document = _document("Lists preserve order and support indexed access.")
    doc_id = RagIndexingService.document_id(
        source.name, document.canonical_url
    )
    stored_document = SimpleNamespace(
        doc_id=doc_id,
        source_name=source.name,
        canonical_url=document.canonical_url,
        document_hash="old-content-hash",
        source_version="3.14",
    )
    stale_chunk = _chunk("Older text")
    stale_chunk.attributions = [
        SimpleNamespace(
            chunk_id=stale_chunk.chunk_id,
            doc_id=doc_id,
            section_path=stale_chunk.section_path,
            license="PSF-2.0",
        )
    ]
    new_chunk = _chunk("Lists preserve order and support indexed access.")
    chunker = FakeChunker([new_chunk])
    chunk_repository = FakeChunkRepository({stale_chunk.chunk_id: stale_chunk})
    embedding_service = FakeEmbeddingService()
    service = RagIndexingService(
        db=FakeDatabase(),
        document_repository=FakeDocumentRepository(
            {(source.name, document.canonical_url): stored_document}
        ),
        chunk_repository=chunk_repository,
        chunker=chunker,
        embedding_service=embedding_service,
        config=load_rag_config(),
    )

    report = asyncio.run(service.index_documents(source, [document]))

    assert report.documents_processed == 1
    assert report.documents_unchanged == 0
    assert chunker.calls == 1
    assert chunk_repository.deleted_documents == [doc_id]
    assert stale_chunk.chunk_id not in chunk_repository.chunks
    assert new_chunk.chunk_id in chunk_repository.chunks
    assert len(embedding_service.calls) == 1


def test_source_reconciliation_requires_complete_manifest():
    source = load_rag_config().source_by_name("python-tutorial")
    document_repository = FakeDocumentRepository()
    chunk_repository = FakeChunkRepository()
    service = RagIndexingService(
        db=FakeDatabase(),
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        chunker=FakeChunker([]),
        embedding_service=FakeEmbeddingService(),
        config=load_rag_config(),
    )

    asyncio.run(service.index_documents(source, [], manifest_complete=False))
    assert document_repository.deleted_sources == []
    assert chunk_repository.orphan_prunes == 0

    asyncio.run(service.index_documents(source, [], manifest_complete=True))
    assert document_repository.deleted_sources == [(source.name, set())]
    assert chunk_repository.orphan_prunes == 1


def test_complete_manifest_removes_documents_only_from_the_selected_source():
    config = load_rag_config()
    source = config.source_by_name("python-tutorial")
    other_source = config.source_by_name("python-library")
    document_repository = FakeDocumentRepository(
        {
            (source.name, "https://docs.example/removed"): SimpleNamespace(
                source_name=source.name,
                canonical_url="https://docs.example/removed",
            ),
            (other_source.name, "https://docs.example/keep"): SimpleNamespace(
                source_name=other_source.name,
                canonical_url="https://docs.example/keep",
            ),
        }
    )
    chunk_repository = FakeChunkRepository()
    service = RagIndexingService(
        db=FakeDatabase(),
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        chunker=FakeChunker([]),
        embedding_service=FakeEmbeddingService(),
        config=config,
    )

    asyncio.run(service.index_documents(source, [], manifest_complete=True))

    assert (source.name, "https://docs.example/removed") not in (
        document_repository.documents
    )
    assert (other_source.name, "https://docs.example/keep") in (
        document_repository.documents
    )
    assert document_repository.deleted_sources == [(source.name, set())]
