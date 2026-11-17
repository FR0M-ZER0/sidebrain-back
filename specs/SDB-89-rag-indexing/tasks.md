---

description: "Lista de tarefas de implementação da pipeline RAG para SDB-89"
---

# Tasks: Referências técnicas para trilhas de programação

**Input**: Artefatos de design em `specs/SDB-89-rag-indexing/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/rag-cli.md` e `quickstart.md`.

**Tests**: Incluídos porque a especificação pede cobertura unitária, integração PostgreSQL/pgvector, compatibilidade de geração, fallback e avaliação local reproduzível.

**Organization**: Fases compartilhadas seguidas por uma fase por user story na ordem de prioridade da especificação. A recuperação real é entregue depois da indexação; a integração final nos workers ocorre quando os serviços concretos estiverem disponíveis.

## Formato de checklist

Cada tarefa usa `- [ ] TNNN [P?] [USn?] descrição com caminho de arquivo`. `[P]` indica trabalho paralelo sem dependência em arquivo ou tarefa incompleta. Fases Setup, Foundational e Polish não recebem label de story.

## Phase 1: Setup (infraestrutura compartilhada)

**Objetivo**: habilitar dependências, configuração opcional e banco de desenvolvimento/CI compatível com pgvector.

- [X] T001 [P] Declarar `openai`, `tiktoken`, `PyYAML`, `beautifulsoup4`, `markdown-it-py` e `docutils` como dependências runtime; promover `httpx>=0.28.1` do grupo dev sem duplicá-lo e atualizar `uv.lock` em `pyproject.toml` e `uv.lock`.
- [X] T002 [P] Adicionar configuração opcional de `OPENAI_API_KEY`, threshold e caminho do YAML em `src/sidebrain_back/core/constants.py`, com placeholder sem segredo real em `.env.example`; manter modelo/dimensões no bloco `defaults.embeddings` de `config/rag_sources.yml` (T003).
- [X] T003 [P] Criar `config/rag_sources.yml` com `python-tutorial`, `python-library` e `mdn-javascript`, incluindo tipo, idioma, nível, licença/URL e override por tipo de conteúdo, inclusão/exclusão, versão, profundidade, User-Agent/contato, limites por host, chunking e preços configuráveis.
- [X] T004 [P] Configurar o banco da CI e a fixture de integração para `pgvector/pgvector:pg16` e habilitação da extensão no setup de teste em `.github/workflows/ci.yml` e `tests/conftest.py`.

---

## Phase 2: Foundational (pré-requisitos bloqueantes)

**Objetivo**: definir os contratos internos, persistência e configuração compartilhados pelas quatro stories.

**Checkpoint**: nenhuma story começa antes de settings, schema/config, models, migration e repositories base estarem disponíveis.

- [X] T005 [P] Definir schemas Pydantic internos `RagClassificationSchema`, `RagReferenceSchema` e resultados de ingestão/recuperação em `src/sidebrain_back/schemas/rag_schema.py`, sem adicioná-los a schemas públicos de request/response.
- [X] T006 [P] Escrever teste de migration que valide as tabelas/índices RAG no PostgreSQL com pgvector e que o downgrade da feature não remova `vector` em `tests/integration/test_rag_migration.py`.
- [X] T007 [P] Escrever testes de validação de fontes e parâmetros globais (tipos `url|sitemap|git|local`, idioma, nível, regras de inclusão/exclusão e configuração de licenças) em `tests/unit/test_rag_config.py`.
- [X] T008 [P] Criar `RagDocumentModel`, `RagChunkModel`, `RagChunkAttributionModel` e `RagChunkEmbeddingModel`, registrando-os em `src/sidebrain_back/models/rag_document_model.py`, `src/sidebrain_back/models/rag_chunk_model.py`, `src/sidebrain_back/models/rag_chunk_attribution_model.py`, `src/sidebrain_back/models/rag_chunk_embedding_model.py`, `src/sidebrain_back/models/__init__.py` e `migrations/env.py`. Preservar os domínios `language=python|javascript`, `level=beginner|intermediate|advanced`, `content_type=concept|code_example|reference|tutorial|exercise`, licença desconhecida explícita e dimensão inicial `VECTOR(1536)`.
- [X] T009 Criar migration revision `a1b2c3d4e5f6` encadeada após `f6a7b8c9d0e1` em `migrations/versions/a1b2c3d4e5f6_cria_indice_rag.py`, com tabelas/constraints, HNSW `vector_cosine_ops`, GIN para `tsvector` e tags e índices de `language`, `level` e `content_type`; reutilizar a extensão existente sem removê-la no downgrade.
- [X] T010 Implementar loader/validador Pydantic do YAML e compatibilidade de settings em `src/sidebrain_back/rag/rag_config.py`, fazendo os testes de `tests/unit/test_rag_config.py` passarem sem exigir `OPENAI_API_KEY` ao iniciar a aplicação.
- [X] T011 Implementar persistência base de documentos, chunks, atribuições e cache de embedding em `src/sidebrain_back/repositories/rag_document_repository.py` e `src/sidebrain_back/repositories/rag_chunk_repository.py`, com limpeza de chunk somente quando não houver atribuição de origem restante.

---

## Phase 3: User Story 1 — Gerar conteúdo de programação com referências confiáveis (Priority: P1)

**Objetivo**: incluir referências fornecidas por uma dependência RAG substituível nos prompts da geração inicial e incremental sem alterar respostas ou schemas de conteúdo.

**Teste independente**: usar roteador e recuperação falsos para confirmar que o prompt inicial e o incremental recebem texto, fonte e URL para Python/JavaScript, mantendo validação Pydantic e JSON existentes.

### Testes da User Story 1

- [X] T012 [P] [US1] Testar injeção de referências no prompt de geração inicial, precedência das instruções e preservação do JSON validado em `tests/unit/test_generation_rag_context.py`.
- [X] T013 [P] [US1] Testar que a etapa usa `goal/topic` original da solicitação vinculada e que trilha manual ou sem contexto persistido recebe `reference_context=None` em `tests/unit/test_prepare_next_step_rag_context.py`.
- [X] T014 [P] [US1] Verificar que schemas públicos de geração e contratos HTTP não ganham campos RAG em `tests/contract/test_generation_rag_compatibility.py`.

### Implementação da User Story 1

- [X] T015 [US1] Implementar `RagGenerationContextService` injetável que combina decisão do roteador e recuperação, retorna atribuições com título/URL, exclui do prompt conteúdo com `external_processing_allowed=false` e captura falhas RAG sem propagar erro para geração em `src/sidebrain_back/services/rag_generation_context_service.py`.
- [X] T016 [US1] Adicionar bloco de referências claramente delimitado como material não confiável/de apoio ao prompt, sem alterar schema de saída, em `src/sidebrain_back/services/generation_service.py`.
- [X] T017 [US1] Permitir injetar o serviço de contexto RAG em `_run_generation`, chamá-lo com `goal/topic` antes de `GenerationService` e passar referências sem alterar serialização/idempotência/retries em `src/sidebrain_back/tasks/generate_track_task.py`; a composição concreta do worker fica em T044.
- [X] T018 [P] [US1] Adicionar leitura interna de `goal`, `topic` e nível originais pelo `trk_generation_request_id` em `src/sidebrain_back/repositories/generation_request_repository.py`, sem expor esses dados em request/response novo.
- [X] T019 [US1] Permitir injetar contexto RAG na task incremental, obtê-lo usando solicitação original fora do lock/transação de escrita e depois readquirir lock/revalidar antes de chamar `StepContentGenerator` e persistir atomicamente em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`; a composição concreta do worker fica em T044.

**Checkpoint**: geração inicial e incremental aceitam referências injetadas; com provider falso podem ser demonstradas sem internet, e as trilhas manuais continuam sem RAG.

---

## Phase 4: User Story 2 — Preservar geração de assuntos sem suporte RAG (Priority: P1)

**Objetivo**: restringir o RAG a objetivos claramente de programação Python/JavaScript, falhando de forma conservadora e fail-open.

**Teste independente**: simular Python, JavaScript, menção incidental, assunto alheio, confidence abaixo de `0,80`, Groq indisponível e JSON inválido; provar que cenários negativos não chamam embeddings/recuperação e que a geração prossegue sem referências.

### Testes da User Story 2

- [X] T020 [P] [US2] Testar classificação positiva de Python/JavaScript, threshold `>= 0,80`, resposta ambígua e menção incidental usando Groq falso em `tests/unit/test_rag_routing_service.py`.
- [X] T021 [P] [US2] Testar pré-filtro sem chamada ao classificador para assunto sem menção aos idiomas, ausência de chamadas a embeddings/repository quando `use_rag=False` e fail-open para falhas do roteador/recuperação em `tests/unit/test_rag_generation_fallback.py`.

### Implementação da User Story 2

- [X] T022 [US2] Implementar pré-filtro determinístico, classificação Groq com JSON validado por `RagClassificationSchema` e política `confidence >= 0,80` em `src/sidebrain_back/services/rag_routing_service.py`; contextos sem palavra/alias de Python/JavaScript retornam `language=None` sem chamar provider.
- [X] T023 [US2] Implementar fallback determinístico que só retorna idioma/confidence `0,80` para menção ao idioma combinada a intenção explícita de programação, e garantir logs sem segredos e fail-open que não dispare retries indevidos em `src/sidebrain_back/services/rag_routing_service.py` e `src/sidebrain_back/services/rag_generation_context_service.py`.

**Checkpoint**: inglês para viagens, menções incidentais, contexto ausente e falhas de provider permanecem nos fluxos existentes sem embeddings ou busca RAG.

---

## Phase 5: User Story 3 — Manter referências atribuídas e atualizadas (Priority: P1)

**Objetivo**: coletar fontes configuradas, preservar documentos/código/licenças e atualizar incrementalmente sem interromper outras fontes.

**Teste independente**: usar HTML/Markdown/RST locais, repositório Git falso/local e provider de embeddings falso; exercitar documentos novos, inalterados, modificados, removidos, duplicados e com falha.

### Testes da User Story 3

- [X] T024 [P] [US3] Testar chunking por seções, prefixo documento/seção, overlap, normalização que não reindenta código e bloco de código maior que o alvo sem split em `tests/unit/test_rag_chunker.py`.
- [X] T025 [P] [US3] Testar parsing HTML/Markdown/RST, remoção de navegação, preservação de código/language e conectores com respostas HTTP/robots/sitemap locais em `tests/unit/test_rag_parsers.py` e `tests/unit/test_rag_connectors.py`.
- [X] T026 [P] [US3] Testar lotes, ordem das respostas, retry/backoff limitado, `Retry-After`, cache `content_hash+model+dimension`, custo configurável e ausência de chamada quando credencial faltar em `tests/unit/test_rag_embedding_service.py`.
- [X] T027 [P] [US3] Testar deduplicação exata/aproximada com atribuições preservadas e atualização incremental que mantém inalterados e só remove obsoletos da fonte confirmada em `tests/unit/test_rag_indexing_service.py`.

### Implementação da User Story 3

- [X] T028 [US3] Implementar interface `RagTokenizer`, contagem `cl100k_base`, chunker por headings/seções e deduplicação exata/SimHash configurável em `src/sidebrain_back/rag/rag_tokenizer.py` e `src/sidebrain_back/rag/rag_chunker.py`; não dividir código e manter blocos acima de 8192 tokens sem embedding.
- [X] T029 [P] [US3] Implementar extração estrutural HTML e parser Markdown/RST com títulos, seção, code fences e linguagem detectada, sem executar código ou diretivas/includes locais, em `src/sidebrain_back/rag/rag_html_parser.py` e `src/sidebrain_back/rag/rag_document_parser.py`.
- [X] T030 [P] [US3] Implementar conectores URL e sitemap com timeout, User-Agent/contato, cache robots até 24h, fail-closed em rede/5xx, respeito a 429/Retry-After e concorrência/intervalo por host em `src/sidebrain_back/rag/rag_url_connector.py` e `src/sidebrain_back/rag/rag_sitemap_connector.py`.
- [X] T031 [P] [US3] Implementar conectores Git (clone raso, SHA como versão, subprocess sem shell) e local (somente arquivos incluídos Markdown/RST) em `src/sidebrain_back/rag/rag_git_connector.py` e `src/sidebrain_back/rag/rag_local_connector.py`.
- [X] T032 [P] [US3] Implementar provider assíncrono OpenAI sob demanda e `RagEmbeddingService` com batches limitados por 8192 tokens/input e orçamento agregado, no máximo três tentativas, cache por hash/modelo/dimensão, preço sem valor hardcoded e bloqueio de envio quando `external_processing_allowed=false` em `src/sidebrain_back/rag/rag_openai_embedding_provider.py` e `src/sidebrain_back/services/rag_embedding_service.py`.
- [X] T033 [US3] Orquestrar manifesto por fonte, normalização, hash documental/chunk, atribuições, deduplicação, cache, remoção após enumeração bem-sucedida e relatório de documentos/chunks/falhas/duração/custo em `src/sidebrain_back/services/rag_indexing_service.py`.
- [X] T034 [US3] Testar argumentos válidos/inválidos em `tests/unit/test_rag_cli.py` e implementar comandos `index --source|--all` e `reindex --full [--source]`, validação antes de rebuild, rejeição de escopo parcial ao mudar modelo/dimensão e códigos de saída/relatório em `src/sidebrain_back/rag/rag_cli.py`.
- [X] T035 [P] [US3] Executar indexação de fixtures locais com sessão PostgreSQL e provider falso, validando isolamento de falhas e remoção restrita à fonte em `tests/integration/test_rag_indexing.py`.

**Checkpoint**: documentação e exemplos são indexáveis sem serviços externos nos testes; reexecução inalterada reutiliza vetores, e falhas por documento não interrompem fontes restantes.

---

## Phase 6: User Story 4 — Consultar e avaliar a recuperação (Priority: P2)

**Objetivo**: disponibilizar recuperação híbrida filtrada, CLI de consulta e avaliação offline com 20 perguntas.

**Teste independente**: carregar documentos/chunks locais no PostgreSQL pgvector, consultar com filtros, conferir fusão RRF e executar recall@k sem crawling, Groq ou OpenAI.

### Testes e fixtures da User Story 4

- [X] T036 [US4] Criar fixtures locais Python/JavaScript em níveis variados e 20 perguntas com `chunk_id`/fonte/seção esperados em `tests/fixtures/rag/evaluation_documents/` e `tests/fixtures/rag/evaluation_queries.jsonl`.
- [X] T037 [P] [US4] Testar filtros aplicados aos dois ramos, mapeamento `pro→advanced`, agrupamento de proveniência e RRF com ranks controlados em `tests/unit/test_rag_retrieval_service.py`.
- [X] T038 [P] [US4] Testar busca vetorial, full-text GIN, filtros e consulta híbrida com PostgreSQL/pgvector real em `tests/integration/test_rag_retrieval_postgres.py`.
- [X] T039 [P] [US4] Testar cálculo de recall@k e execução offline das 20 perguntas usando os dados de `tests/fixtures/rag/` em `tests/unit/test_rag_evaluation.py`.

### Implementação da User Story 4

- [X] T040 [US4] Implementar consultas vetorial e textual no `RagChunkRepository`, aplicando os mesmos filtros, candidato vetorial HNSW cosine e candidato lexical GIN/`ts_rank_cd` (sem chamá-lo de BM25), mesclando ranks por RRF `k=60` em `src/sidebrain_back/repositories/rag_chunk_repository.py`.
- [X] T041 [US4] Implementar `RagRetrievalService.retrieve(query, language, level, content_type, top_k=8)`, gerando embedding antes da sessão SQL, mapeando `pro`, preservando atribuições/metadados de processamento externo para a CLI e deixando reranker desativado em `src/sidebrain_back/services/rag_retrieval_service.py`.
- [X] T042 [US4] Completar subcomando `query` com filtros, `top_k` 1–50 e impressão de texto/fonte/título/seção/metadados conforme `contracts/rag-cli.md` em `src/sidebrain_back/rag/rag_cli.py`.
- [X] T043 [US4] Implementar script/subcomando `evaluate` com modo offline de fixtures e modo de índice previamente carregado; calcular recall@k, registrar modelo/dimensão no modo real, nunca fazer crawling e usar provider falso no modo offline em `src/sidebrain_back/rag/rag_evaluation.py` e `src/sidebrain_back/rag/rag_cli.py`.

**Checkpoint**: a recuperação retorna referências filtradas com origem/licença e a avaliação é reproduzível sem crawling vivo.

---

## Phase 7: Polish & integração transversal

**Objetivo**: ligar providers concretos aos workers, demonstrar fluxos completos e documentar operação.

- [X] T044 Compor `RagRoutingService`, `RagRetrievalService` e `RagGenerationContextService` nas tasks inicial/incremental, mantendo criação manual fora do caminho RAG, em `src/sidebrain_back/tasks/generate_track_task.py` e `src/sidebrain_back/tasks/prepare_next_step_content_task.py`.
- [X] T045 Testar geração inicial e incremental com/sem RAG, falha de classificação/recuperação, JSON Pydantic e persistência/idempotência preservados usando providers falsos em `tests/integration/test_generation_rag_flow.py`.
- [X] T046 [P] Documentar instalação, env opcional, fontes/escopos/licenças, cron, CLI, avaliação, limites de código/licença desconhecida e impacto/requisitos de full reindex em `docs/rag/README.md`; registrar a subestrutura de domínio em `docs/architecture.md` e linkar o guia em `README.md`.
- [X] T047 Executar `uv run pytest`, `uv run ruff check .` e os cenários de `specs/SDB-89-rag-indexing/quickstart.md`; corrigir falhas de migration, CI pgvector ou contratos antes da conclusão.

---

## Dependências e ordem de execução

### Dependências entre fases

- **Setup (Phase 1)**: independente; T001–T004 podem ser iniciadas em paralelo.
- **Foundational (Phase 2)**: depende de Setup e bloqueia todas as stories. T006/T007/T008 são paralelas após Setup; migration depende de models e banco pgvector; repositories dependem de models/migration.
- **US1 (Phase 3)**: depende da fundação. Usa roteador/recuperação falsos para testar a integração de prompt sem esperar a implementação do índice.
- **US2 (Phase 4)**: depende da interface de contexto criada em US1; define classificação conservadora e fail-open.
- **US3 (Phase 5)**: depende da fundação; implementa os dados e embeddings que alimentam a recuperação. Pode ser desenvolvida em paralelo com US1/US2 após a fundação, respeitando os arquivos compartilhados.
- **US4 (Phase 6)**: depende dos models/repositories e do provider de embedding/cache de US3 para validação operacional completa. Os testes SQL podem começar com fixtures e provider falso.
- **Polish (Phase 7)**: T044 depende dos serviços concretos de US2/US4; T045 valida fluxos completos; documentação e validação final encerram a entrega.

### Dependências entre user stories

| Story | Pode iniciar após | Dependência de entrega integrada |
|---|---|---|
| US1 (P1) | Foundational | Integração de prompt é testável com fake; contexto real depende de US2, US3 e US4, finalizado em T044. |
| US2 (P1) | Foundational + interface de US1 | US1 para uso do roteador no contexto de geração. |
| US3 (P1) | Foundational | Independente dos prompts; fornece índice para US4. |
| US4 (P2) | Foundational; provider real de US3 para operação | US3 para a jornada completa `index → query`; geração consome a recuperação em T044. |

### Grafo resumido

```text
Setup → Foundational → US1 → US2
                    ├→ US3 → US4
                    └───────────────┐
US1 + US2 + US3 + US4 ──────────────→ Polish (T044–T047)
```

### Oportunidades de paralelismo

- Setup: T001, T002, T003 e T004 modificam arquivos independentes.
- Foundational: T005 (schemas), T006 (teste de migration), T007 (teste de config) e T008 (models) podem avançar em paralelo depois do setup.
- US1: T012, T013 e T014 são testes em arquivos diferentes; depois T017 e T018 podem avançar em paralelo quando T015/T016 estiverem prontos.
- US2: T020 e T021 são suítes independentes de roteamento e fallback.
- US3: T024–T027 são testes independentes; depois de T028 (tokenizer), parsers, conectores HTTP, conectores Git/local e provider podem ser divididos em arquivos separados; T034/T035 também são independentes após T033.
- US4: depois de T036, T037–T039 são testes separados; T042 (query) precede T043 (evaluate) porque ambos alteram `rag_cli.py`, enquanto a lógica de avaliação fica separada em `rag_evaluation.py`.

### Exemplos de execução paralela

```text
US1 após Foundation: T012 || T013 || T014 → T015 → T016 → (T017 || T018) → T019
US2 após US1: T020 || T021 → T022 → T023
US3 após Foundation: T024 || T025 || T026 || T027 → T028 → (T029 || T030 || T031 || T032) → T033 → (T034 || T035)
US4: T036 → (T037 || T038 || T039) → T040 → T041 → T042 → T043
```

## Estratégia de implementação

### MVP funcional

Completar Setup e Foundational, depois a indexação mínima de US3 e recuperação filtrada de US4, e integrar US1/US2. A geração com referência real depende dessas quatro partes; entregar só o prompt com recuperação falsa não constitui o MVP do produto. O conjunto offline de 20 perguntas, CLI completo, documentação e gates de teste permanecem obrigatórios nesta feature.

### Entrega incremental

1. Setup + Foundation: esquema, config validada e teste PostgreSQL pgvector.
2. US1 + US2: integração segura/fail-open comprovada com providers falsos.
3. US3: indexar sources locais e iniciais incrementalmente sem chamar a geração.
4. US4: buscar fixture/índice com filtros/RRF e executar recall@k offline.
5. Polish: ligar providers reais aos workers, executar cenários ponta a ponta, documentar e validar gates.

## Notas

- Todo teste unitário usa fixture/provider falso; nenhum teste unitário consulta internet, Groq ou OpenAI.
- Reindexar por alteração de modelo/dimensão exige todas as fontes e migration correspondente; não permitir reindex parcial nesses casos.
- Conteúdo de licença desconhecida permanece local e não é enviado a embeddings nem a prompts externos sem autorização explícita configurada.
- Não criar endpoint HTTP público, não modificar schemas públicos, criação manual de trilhas ou avaliação de conhecimento.
