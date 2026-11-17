# Plano de Implementação: Referências técnicas para trilhas de programação

**Branch**: `feat/sdb-89-adiciona-pipeline-rag` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Especificação de feature em `specs/SDB-89-rag-indexing/spec.md`.

## Summary

Adicionar um índice interno de documentação oficial de Python e JavaScript e uma recuperação híbrida que abastece somente os fluxos de geração de trilha e conteúdo incremental quando o roteador classificar programação em Python ou JavaScript com confiança `>= 0,80`. O desenho usa PostgreSQL/pgvector já existente, busca textual PostgreSQL, fusão RRF, embeddings OpenAI substituíveis e um CLI interno. Falhas opcionais de classificação/recuperação deixam a geração atual seguir sem referências.

A ingestão será configurada em YAML, incremental por hashes, com proveniência/licença preservadas por associação many-to-many. A reindexação completa é necessária ao trocar modelo/dimensão e pode deixar a cobertura RAG parcial enquanto executa; os fluxos de geração seguem disponíveis sem referências.

## Technical Context

**Language/Version**: Python 3.11.

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy async, Alembic, Celery, Groq existente, `pgvector` já declarado; adicionar `openai`, `tiktoken`, `PyYAML`, `beautifulsoup4`, `markdown-it-py` e `docutils`. Promover `httpx` já presente no grupo de desenvolvimento para dependência de runtime, sem duplicá-la. `argparse`, `urllib.robotparser`, XML e `asyncio` são da biblioteca padrão. Git será executado como subprocesso com argumentos separados; não é necessária dependência GitPython.

**Storage**: PostgreSQL 16 com extensão `vector` já criada pela migration existente `f6a7b8c9d0e1`. Nova migration cria tabelas e índices RAG. Dimensão padrão `vector(1536)`, HNSW com `vector_cosine_ops`, `tsvector` com GIN e índices de metadados.

**Testing**: Pytest unitário com conectores e providers falsos; integração PostgreSQL usando imagem `pgvector/pgvector:pg16` e migrations reais; testes de contrato dos fluxos de geração sem alterar schemas públicos; lint com Ruff.

**Target Platform**: workers Celery e CLI manual/cron em Linux; API FastAPI existente.

**Project Type**: serviço web existente mais ferramenta CLI interna, sem novo endpoint HTTP público.

**Performance Goals**: sem SLO de latência ou escala definido na especificação. Recuperação padrão `top_k=8`; avaliação reproduzível com 20 perguntas e `recall@k`. Crawl com concorrência e intervalo por host configuráveis. Os limites de consulta vetorial, tamanho de lote e parser serão medidos no quickstart.

**Constraints**: objetivo/tópico precisam identificar Python ou JavaScript com confiança `>= 0,80`; pré-filtro sem menção aos idiomas não chama classificador, embeddings ou recuperação. `OPENAI_API_KEY` é opcional para inicialização e fluxos sem RAG; contratos públicos e schemas gerados não mudam. Chunking alvo 400–600 tokens, overlap 10–15%, preservando blocos de código. Entradas de embedding têm limite de 8.192 tokens; conteúdo maior permanece inteiro e pesquisável lexicalmente, sem vetor. Licenças não são inferidas quando desconhecidas.

**Scale/Scope**: primeira versão limitada à documentação oficial do tutorial Python, biblioteca padrão Python e MDN Web Docs para JavaScript; novos documentos entram por configuração. O volume de conteúdo será medido na primeira indexação e não há meta de escala além dessas fontes iniciais.

## Constitution Check

*Gate antes da pesquisa e novamente após o desenho.*

| Princípio | Verificação do plano |
|---|---|
| Qualidade e coesão | Conectores, parsing, chunking, provider, recuperação e CLI terão responsabilidades separadas e interfaces substituíveis. |
| Responsabilidade única | Regras ficam em services; SQL em repositories; ORM em models; tasks somente orquestram a composição. |
| Camadas e dependências | Mantém `routers → services → repositories → models`; o CLI compõe services. `rag/` abriga adaptadores de ingestão, tokenizador, CLI e avaliação, sem acesso direto a ORM ou regras de negócio. |
| Testes e contratos | Providers externos serão falsos em unit tests; testes de integração usarão PostgreSQL com pgvector. Nenhum contrato HTTP ou schema de conteúdo gerado será alterado. |
| Evolução segura | Migration segue o head que já habilita `vector`; downgrade remove somente objetos da feature. Mudança de dimensão exige migration e reindexação total documentada. Falhas RAG são fail-open. |

**Gate**: aprovado. A subestrutura `rag/` é um pacote de adaptadores/entrypoints da feature; persistência e orquestração seguem as camadas normativas.

**Revalidação pós-design**: modelos e queries permanecem separados em models/repositories; serviços não dependem de HTTP; o CLI não acessa ORM diretamente. Migration, integração pgvector, mocks de provedores e compatibilidade dos fluxos existentes estão previstos. Gate permanece aprovado, sem desvios.

## Project Structure

### Documentação desta feature

```text
specs/SDB-89-rag-indexing/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/rag-cli.md
└── tasks.md                 # gerado na fase /speckit-tasks
```

### Código-fonte planejado

```text
config/rag_sources.yml
docs/rag/README.md
migrations/versions/ (nova revision após f6a7b8c9d0e1)
.env.example                                  # placeholder OPENAI_API_KEY opcional
pyproject.toml                                 # dependências runtime sem duplicatas
uv.lock
.github/workflows/ci.yml                      # banco de CI com pgvector
src/sidebrain_back/
├── core/constants.py                         # settings RAG e OPENAI_API_KEY opcionais
├── models/
│   ├── rag_document_model.py
│   ├── rag_chunk_model.py
│   ├── rag_chunk_attribution_model.py
│   └── rag_chunk_embedding_model.py
├── repositories/
│   ├── rag_document_repository.py
│   └── rag_chunk_repository.py
├── services/
│   ├── rag_indexing_service.py
│   ├── rag_embedding_service.py
│   ├── rag_retrieval_service.py
│   ├── rag_routing_service.py
│   └── rag_generation_context_service.py
├── schemas/rag_schema.py                      # JSON de classificação/contexto interno
├── rag/
│   ├── rag_config.py
│   ├── rag_url_connector.py
│   ├── rag_sitemap_connector.py
│   ├── rag_git_connector.py
│   ├── rag_local_connector.py
│   ├── rag_html_parser.py
│   ├── rag_document_parser.py
│   ├── rag_chunker.py
│   ├── rag_tokenizer.py
│   ├── rag_openai_embedding_provider.py
│   ├── rag_cli.py
│   └── rag_evaluation.py
├── services/generation_service.py
└── tasks/
    ├── generate_track_task.py
    └── prepare_next_step_content_task.py
tests/
├── fixtures/rag/
├── unit/test_rag_*.py
├── integration/test_rag_*.py
└── contract/test_generation_rag_compatibility.py
```

**Structure Decision**: modelos, repositories e services ficam nos diretórios normativos da aplicação e têm prefixo `rag_` nos arquivos/classes. `rag/` é uma subestrutura limitada a conectores, parsing, tokenização, configuração, CLI e avaliação. Ela não consulta models diretamente; seus resultados passam por `RagIndexingService` e `RagRetrievalService`. As tasks compõem a camada de serviço seguindo a prática atual do worker Celery.

## Complexity Tracking

Não há violações constitucionais ou desvios arquiteturais a justificar.
