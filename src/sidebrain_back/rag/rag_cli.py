from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from sidebrain_back.core.constants import RAG_VECTOR_DIMENSIONS
from sidebrain_back.core.database import async_session
from sidebrain_back.rag.rag_chunker import RagChunker
from sidebrain_back.rag.rag_config import RagConfigError, load_rag_config
from sidebrain_back.rag.rag_evaluation import (
    evaluate_retriever,
    run_fixture_evaluation,
)
from sidebrain_back.rag.rag_openai_embedding_provider import (
    RagEmbeddingConfigurationError,
    RagOpenAIEmbeddingProvider,
)
from sidebrain_back.rag.rag_tokenizer import RagTokenizer
from sidebrain_back.repositories.rag_chunk_repository import RagChunkRepository
from sidebrain_back.repositories.rag_document_repository import (
    RagDocumentRepository,
)
from sidebrain_back.services.rag_embedding_service import RagEmbeddingService
from sidebrain_back.services.rag_indexing_service import RagIndexingService
from sidebrain_back.services.rag_retrieval_service import RagRetrievalService

logger = logging.getLogger(__name__)


class RagCLIConfigurationError(ValueError):
    pass


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sidebrain-rag",
        description="Indexa e opera o índice interno de referências RAG.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    index = commands.add_parser("index", help="indexação incremental")
    selection = index.add_mutually_exclusive_group(required=True)
    selection.add_argument("--source", help="nome de uma fonte configurada")
    selection.add_argument(
        "--all", action="store_true", help="indexa todas as fontes"
    )

    reindex = commands.add_parser("reindex", help="reconstrução do índice")
    reindex.add_argument(
        "--full", action="store_true", required=True, help="rebuild completo"
    )
    reindex.add_argument(
        "--source",
        help="restringe a uma fonte quando modelo/dimensão não muda",
    )

    query = commands.add_parser("query", help="consulta o índice RAG")
    query.add_argument("query", help="texto da consulta")
    query.add_argument(
        "--language", choices=("python", "javascript"), default=None
    )
    query.add_argument(
        "--level",
        choices=("beginner", "intermediate", "advanced"),
        default=None,
    )
    query.add_argument(
        "--content-type",
        choices=(
            "concept",
            "code_example",
            "reference",
            "tutorial",
            "exercise",
        ),
        default=None,
    )
    query.add_argument("--top-k", type=_top_k, default=8)

    evaluate = commands.add_parser("evaluate", help="calcula recall@k")
    mode = evaluate.add_mutually_exclusive_group()
    mode.add_argument("--fixtures", action="store_true")
    mode.add_argument("--index", action="store_true")
    evaluate.add_argument("--k", type=_top_k, default=8)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    try:
        return asyncio.run(_run(args))
    except (RagConfigError, RagCLIConfigurationError) as error:
        print(f"rag: {error}", file=sys.stderr)
        return 2
    except RagEmbeddingConfigurationError as error:
        print(f"rag: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        logger.error(
            "RAG CLI operation failed",
            extra={"error_category": type(error).__name__},
        )
        print(
            f"rag: operation failed ({type(error).__name__})",
            file=sys.stderr,
        )
        return 3


async def _run(args: argparse.Namespace) -> int:
    config = load_rag_config()
    if args.command == "query":
        return await _run_query(args, config)
    if args.command == "evaluate":
        return await _run_evaluation(args, config)
    selected_sources = _select_sources(config, args)
    configured_dimensions = config.defaults.embeddings.dimensions
    if configured_dimensions != RAG_VECTOR_DIMENSIONS:
        raise RagCLIConfigurationError(
            "embedding dimensions do not match the migrated vector column; "
            "create a matching migration before indexing"
        )

    provider = RagOpenAIEmbeddingProvider()
    try:
        return await _run_indexing(args, config, selected_sources, provider)
    finally:
        await provider.aclose()


async def _run_indexing(args, config, selected_sources, provider) -> int:
    has_external_content = any(
        source.license_for("concept").external_processing_allowed
        or source.license_for("code_example").external_processing_allowed
        for source in selected_sources
    )
    if has_external_content:
        provider.validate_configuration()

    tokenizer = RagTokenizer(config.defaults.chunking.encoding)
    async with async_session() as db:
        document_repository = RagDocumentRepository(db)
        chunk_repository = RagChunkRepository(db)
        signatures = await chunk_repository.list_embedding_signatures()
        await db.rollback()
        desired_signature = {
            (
                config.defaults.embeddings.model,
                config.defaults.embeddings.dimensions,
            )
        }
        full_rebuild = args.command == "reindex" and args.full
        if signatures and signatures != desired_signature and not full_rebuild:
            raise RagCLIConfigurationError(
                "stored embeddings use a different model/dimension; run "
                "reindex --full for all sources"
            )
        if (
            signatures
            and signatures != desired_signature
            and full_rebuild
            and args.source
        ):
            raise RagCLIConfigurationError(
                "a model/dimension change requires reindexing every source"
            )

        embedding_service = RagEmbeddingService(
            provider=provider,
            tokenizer=tokenizer,
            repository=chunk_repository,
            config=config.defaults.embeddings,
        )
        indexing_service = RagIndexingService(
            db=db,
            document_repository=document_repository,
            chunk_repository=chunk_repository,
            chunker=RagChunker(
                tokenizer=tokenizer,
                target_tokens=config.defaults.chunking.target_tokens,
                overlap_ratio=config.defaults.chunking.overlap_ratio,
            ),
            embedding_service=embedding_service,
            config=config,
        )
        if args.command == "index":
            if args.all:
                report = await indexing_service.index_all()
            else:
                report = await indexing_service.index_source(
                    config.source_by_name(args.source)
                )
        elif args.source:
            report = await indexing_service.index_source(
                config.source_by_name(args.source), full=True
            )
        else:
            report = await indexing_service.index_all(full=True)

        if (
            full_rebuild
            and not report.failures
            and signatures != desired_signature
        ):
            await chunk_repository.delete_embeddings_not_matching(
                config.defaults.embeddings.model,
                config.defaults.embeddings.dimensions,
            )
            await db.commit()

    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False))
    return 1 if report.failures else 0


async def _run_query(args, config) -> int:
    if config.defaults.embeddings.dimensions != RAG_VECTOR_DIMENSIONS:
        raise RagCLIConfigurationError(
            "embedding dimensions do not match the migrated vector column"
        )
    provider = RagOpenAIEmbeddingProvider()
    try:
        results = await RagRetrievalService(
            session_factory=async_session,
            embedding_provider=provider,
            embedding_config=config.defaults.embeddings,
        ).retrieve(
            args.query,
            language=args.language,
            level=args.level,
            content_type=args.content_type,
            top_k=args.top_k,
        )
        print(
            json.dumps(
                [result.model_dump(mode="json") for result in results],
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        await provider.aclose()


async def _run_evaluation(args, config) -> int:
    if not args.index:
        report = await run_fixture_evaluation(k=args.k)
    else:
        if config.defaults.embeddings.dimensions != RAG_VECTOR_DIMENSIONS:
            raise RagCLIConfigurationError(
                "embedding dimensions do not match the migrated vector column"
            )
        provider = RagOpenAIEmbeddingProvider()
        try:
            provider.validate_configuration()
            service = RagRetrievalService(
                session_factory=async_session,
                embedding_provider=provider,
                embedding_config=config.defaults.embeddings,
            )
            report = await evaluate_retriever(
                service,
                k=args.k,
                model_id=config.defaults.embeddings.model,
                dimensions=config.defaults.embeddings.dimensions,
            )
        finally:
            await provider.aclose()
    print(json.dumps(report.model_dump(), ensure_ascii=False))
    return 0


def _top_k(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if not 1 <= parsed <= 50:
        raise argparse.ArgumentTypeError("must be between 1 and 50")
    return parsed


def _select_sources(config, args: argparse.Namespace):
    if args.command == "index":
        if args.all:
            return config.sources
        return [config.source_by_name(args.source)]
    if args.source:
        return [config.source_by_name(args.source)]
    return config.sources


if __name__ == "__main__":
    raise SystemExit(main())
