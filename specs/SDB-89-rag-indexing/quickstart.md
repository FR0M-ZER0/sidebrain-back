# Quickstart de Validação — SDB-89

## Pré-requisitos

- Python 3.11, `uv`, Docker e PostgreSQL 16 com pgvector.
- `.env` com configurações existentes de PostgreSQL, Redis e Groq. `OPENAI_API_KEY` é necessária somente para indexação vetorial e consulta manual; sua ausência não deve impedir API, Celery ou gerações sem RAG.
- `config/rag_sources.yml` validado e fontes iniciais configuradas. Conectividade externa só é necessária ao indexar fontes vivas.

## Preparação local

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
```

O banco usado por integração/CI deve fornecer a extensão vector; a configuração PostgreSQL sem pgvector não atende às migrations e buscas desta feature.

## Indexação e consulta manual

```bash
uv run python -m sidebrain_back.rag.rag_cli index --source python-tutorial
uv run python -m sidebrain_back.rag.rag_cli index --all
uv run python -m sidebrain_back.rag.rag_cli query "Como funciona async/await?" --language javascript --top-k 8
```

Verificar atribuição completa na consulta (título, seção, URL e licença) e relatório de indexação. Para execução agendada, usar `index --all` via cron no diretório da aplicação, com ambiente carregado e frequência por fonte compatível com suas políticas; por exemplo, uma execução diária em janela de baixa carga.

## Reindexação completa

```bash
uv run python -m sidebrain_back.rag.rag_cli reindex --full
```

Executar após trocar modelo/dimensão ou algoritmo de chunking. Confirmar API key, fontes, dimensionamento e migration primeiro. O rebuild pode reduzir temporariamente a cobertura da busca; geração continua sem referências porque integração RAG é fail-open. Atualizar migration/schema para a nova dimensão antes de alterar a configuração.

## Avaliação reproduzível

```bash
uv run python -m sidebrain_back.rag.rag_evaluation --fixtures --k 8
uv run python -m sidebrain_back.rag.rag_evaluation --index --k 8
```

O script usa 20 consultas fixas e IDs/fontes esperados em `tests/fixtures/rag`. O modo `--fixtures` é offline, usa provider falso e valida a execução/cálculo; o modo `--index` consulta um índice previamente carregado com o modelo configurado, exige `OPENAI_API_KEY` e nunca faz crawling ao vivo. Ambos listam perguntas, resultados, hits e recall@k; o modo de índice registra modelo/dimensão para comparação. O conjunto mede recall de fontes/chunks esperados, não qualidade editorial completa.

## Validação automatizada

```bash
uv run python -m pytest tests/unit
uv run python -m pytest tests/integration
uv run python -m pytest tests/contract
uv run ruff check .
```

Os testes unitários usam HTML/Markdown/RST locais, fake HTTP, fake Groq, fake embedding provider e mocks quando não validarem operators pgvector. Testes de busca vetorial, full-text e migration usam PostgreSQL com pgvector real. Testes de integração cobrem filtros e RRF, e testes de geração provam que: Python/JavaScript com confiança suficiente recebem contexto; assuntos não relacionados não chamam embeddings/recuperação; falha RAG não muda retry, schema JSON, transação ou idempotência.

## Evidências esperadas

- A migration cria tabelas/índices e reverte sem remover a extensão `vector` previamente habilitada.
- `index --source` atualiza apenas a fonte escolhida; repetição inalterada reutiliza chunks e embeddings; remoção só afeta fonte confirmada.
- Blocos de código são armazenados integralmente; blocos além do limite de embedding continuam consultáveis por texto.
- Erros de documento aparecem no relatório e não abortam os demais documentos.
- Objetivos fora de Python/JavaScript continuam gerando como antes, sem chamada ao provider de embeddings ou ao repository de recuperação.
- O prompt recebe referências com URLs como dados de apoio não confiáveis, sem alterar schema/JSON Pydantic.
