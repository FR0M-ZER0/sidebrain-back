# Pipeline RAG

A pipeline RAG mantém referências técnicas versionadas no PostgreSQL e as
recupera durante a geração de trilhas quando o objetivo é claramente sobre
Python ou JavaScript. A recuperação combina busca vetorial e textual. Se o
roteamento, a configuração ou um serviço RAG falhar, a geração segue sem
referências.

## Requisitos e configuração

- PostgreSQL com a extensão `vector` habilitada e migrations aplicadas.
- `OPENAI_API_KEY` para indexação vetorial e consultas manuais. A chave é
  opcional para iniciar a API e gerar trilhas sem RAG.
- `GROQ_API_KEY` e `GROQ_MODEL` já configurados para o roteador de domínio.
- Fontes e licenças revisadas em `config/rag_sources.yml`.

As variáveis da feature estão no `.env`:

```dotenv
OPENAI_API_KEY=
RAG_ROUTER_CONFIDENCE_THRESHOLD=0.80
RAG_SOURCES_CONFIG=config/rag_sources.yml
```

Prepare o ambiente e aplique as migrations:

```bash
uv sync
docker compose up -d
docker compose exec postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"'
uv run alembic upgrade head
```

A migration RAG cria as tabelas e índices do índice interno; habilitar `vector`
é uma preparação do banco, como nas demais migrations que usam a extensão.

## Fontes e licenças

O arquivo `config/rag_sources.yml` declara linguagem, nível, licença, regras de
inclusão/exclusão, estratégia de versão, limites do crawler, chunking,
deduplicação e modelo de embeddings. O arquivo inclui documentação do tutorial
e biblioteca Python e documentação JavaScript do MDN.

Cada licença de conteúdo pode definir `external_processing_allowed`. Conteúdo
enviado para embeddings é processado pela OpenAI; conteúdo sem permissão,
incluindo exemplos de código com licença desconhecida por padrão, não é enviado
para processamento externo. Antes de cadastrar uma fonte, revise os termos da
fonte e classifique separadamente prosa e exemplos de código quando necessário.

Tipos de fonte aceitos: `url`, `sitemap`, `git` e `local`. Use `include_paths` e
`exclude_paths` para limitar a coleta, e forneça um `name` estável e único para
operar cada fonte pela CLI. Respeite os limites de acesso configurados para o
crawler.

## Indexação e consulta

Execute a partir da raiz do repositório, com as variáveis do `.env` carregadas:

```bash
# Indexa ou atualiza uma fonte
uv run python -m sidebrain_back.rag.rag_cli index --source python-tutorial

# Indexa/atualiza todas as fontes
uv run python -m sidebrain_back.rag.rag_cli index --all

# Consulta o índice e retorna referências com atribuição
uv run python -m sidebrain_back.rag.rag_cli query \
  "Como funciona async/await?" --language javascript --top-k 8
```

`index` é incremental: documentos inalterados reutilizam chunks e embeddings.
O comando imprime um relatório JSON por execução; falhas por documento são
reportadas sem interromper o processamento das demais fontes. A atualização
pode ser agendada externamente (por exemplo, cron) na frequência apropriada
para cada fonte.

Para reconstruir o índice:

```bash
uv run python -m sidebrain_back.rag.rag_cli reindex --full
```

`reindex --full --source <nome>` reconstrói uma fonte quando o modelo e a
dimensão permanecem os mesmos. Trocar modelo ou dimensão exige rebuild de todas
as fontes. A dimensão também precisa coincidir com a coluna vetorial da
migration; mudanças de dimensão requerem uma migration compatível antes da
indexação.

## Avaliação

```bash
# Avaliação offline com fixtures, sem API externa
uv run python -m sidebrain_back.rag.rag_cli evaluate --fixtures --k 8

# Avalia um índice já carregado; não faz crawling
uv run python -m sidebrain_back.rag.rag_cli evaluate --index --k 8
```

O conjunto reproduzível contém 20 perguntas em `tests/fixtures/rag`. O modo
offline valida a avaliação com resultados locais. `--index` gera embeddings e
consulta o índice existente, portanto requer `OPENAI_API_KEY`; ambos retornam
hits e `recall@k`. A métrica mede a recuperação das fontes/chunks esperados, não
a qualidade editorial integral das respostas.

## Integração com geração

A integração inicial e incremental só solicita contexto quando o roteador
identifica Python ou JavaScript com confiança igual ou superior a
`RAG_ROUTER_CONFIDENCE_THRESHOLD`. Assuntos fora desses domínios não chamam a
recuperação. As referências são incluídas como material não confiável com URL e
atribuição, sem alterar o schema da resposta gerada. A geração manual e a
preparação de trilhas manuais não usam RAG.

## Testes

```bash
uv run python -m pytest tests/unit
uv run python -m pytest tests/integration
uv run python -m pytest tests/contract
uv run ruff check .
```

Os testes de busca vetorial, full-text e migration precisam de PostgreSQL com a
extensão `vector`. Os demais testes usam fontes locais e providers falsos para
não depender de crawling ou chamadas pagas.
