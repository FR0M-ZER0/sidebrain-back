# Pesquisa de Decisões: SDB-89

**Data da pesquisa**: 2026-10-19

**Contexto**: Python 3.11, PostgreSQL 16, FastAPI/SQLAlchemy async, Celery, Groq e `pgvector` já presentes no repositório. O MCP Context7 não está disponível nesta sessão; as decisões foram verificadas em documentação oficial e nos padrões locais.

## 1. Persistência vetorial e busca híbrida

**Decision**: Usar PostgreSQL com pgvector, distância cosseno, índice HNSW `vector_cosine_ops`, busca textual full-text nativa com `tsvector`/GIN e RRF para mesclar as listas. O padrão inicial usa dimensão 1536, `top_k=8`, 50 candidatos por ramo e constante RRF `k=60`; reranqueamento fica desativado.

**Rationale**:

- O repositório já usa PostgreSQL 16 e declara pgvector; a migration `f6a7b8c9d0e1_habilita_pgvector.py` já executa `CREATE EXTENSION IF NOT EXISTS vector`.
- `text-embedding-3-small` produz 1536 dimensões por padrão; pgvector `vector` e HNSW suportam essa dimensão.
- HNSW com operadores de cosseno corresponde à métrica escolhida. Filtros de idioma, nível e tipo devem estar em ambas as buscas; como HNSW pode filtrar após a varredura, a recuperação deve buscar candidatos acima de `top_k` e medir recall filtrado nas 20 perguntas.
- PostgreSQL 16 fornece `tsvector`, `websearch_to_tsquery` e índice GIN. `ts_rank_cd` pode ordenar resultados textuais, mas **não é BM25**. RRF combina posições/ranks, não scores incomparáveis, pela soma `1 / (k + rank)`.
- A configuração `simple` do full-text conserva tokens sem stemming em inglês, útil para nomes de API e identificadores de código. A avaliação inclui termos de API e símbolos para revelar limites do parser lexical.

**Alternatives considered**: banco vetorial externo foi rejeitado por decisão explícita do produto; ordenação lexical e vetorial sem fusão de ranks foi rejeitada por misturar escalas diferentes; reranker remoto foi adiado para evitar latência e custo adicionais.

**Dimensionamento**: a coluna física v1 será `VECTOR(1536)` e a dimensão será validada contra a configuração. Alterar dimensão exige migration compatível, reconstrução de índice e reindexação completa; mudar somente variável de ambiente sem migration deve falhar na validação da operação RAG. A migration de feature não recria nem remove a extensão preexistente.

## 2. Embeddings, tokenização, custo e credenciais

**Decision**: Implementar `EmbeddingProvider` substituível com adapter assíncrono OpenAI para `text-embedding-3-small`; criar `AsyncOpenAI` sob demanda. A API key é opcional no carregamento da aplicação. Usar batches limitados por número de entradas e soma de tokens, com retry limitado na camada da aplicação e custo baseado em preço configurado.

**Rationale**:

- O guia oficial registra 1536 dimensões padrão, limite de 8192 tokens por input e cobrança por tokens de entrada. Batches devem respeitar o limite de até 2048 entradas e 300 mil tokens totais, além do limite individual; configuração inicial conservadora: até 64 chunks por chamada.
- A SDK Python possui retries próprios; desabilitá-los no cliente do adapter evita multiplicar tentativas com retry externo. A política da aplicação usa no máximo três tentativas totais, respeita `Retry-After` quando válido e aplica backoff exponencial limitado com jitter em erros transitórios. Erros de credencial/entrada não são repetidos.
- Uso de tokens retornado pela API alimenta a estimativa; preço por milhão de tokens é uma opção de configuração, ausente por padrão. Nenhum preço corrente fica hardcoded. Sem preço configurado, o relatório informa custo indisponível, não zero.
- Cache é chaveado por `content_hash + model_id + dimensions`; chunks inalterados reutilizam vetor existente. Modelo e dimensão são persistidos junto ao embedding.
- `tiktoken` com encoding `cl100k_base` para `text-embedding-3-small` fica atrás de `RagTokenizer`, não acoplado ao algoritmo de chunking.
- Em recuperação, calcular embedding da consulta antes de abrir a sessão curta usada pelo repository; não manter conexão/transação SQLAlchemy enquanto se aguarda a API externa.
- Chunks usuais de 400–600 tokens estão sob o limite da API. Se texto prefixado mais um bloco indivisível ultrapassar 8192 tokens, o bloco permanece integral na tabela e no full-text, mas não recebe vetor; assim pode ser recuperado lexicalmente sem truncar ou enviar um bloco parcial.

**Alternatives considered**: credencial obrigatória na inicialização foi rejeitada porque quebra fluxos sem RAG; preço embutido no código foi rejeitado por envelhecer; cortar código silenciosamente ou dividi-lo no meio foi rejeitado porque contradiz o requisito de preservação.

## 3. Classificação e integração com geração

**Decision**: `RagRoutingService` aplica primeiro um pré-filtro determinístico sem chamadas externas: contextos sem menção a Python/JavaScript (incluindo aliases conhecidos) retornam `use_rag=False`, `language=None` e confiança `0.0`. Para candidatos com menção, usa o cliente Groq e `GROQ_MODEL` existentes para classificar `goal + topic` em JSON validado por Pydantic. Só retorna decisão positiva com idioma `python`/`javascript` e confiança `>= 0.80`. Se Groq falhar ou JSON for inválido, um fallback determinístico exige simultaneamente menção ao idioma e intenção explícita de aprender/programar; esse match forte retorna confiança `0.80`, e qualquer outro resultado retorna `use_rag=False`, `language=None` e confiança `0.0`.

**Rationale**:

- Geração inicial já recebe goal, topic e nível em `GenerationInput`; integrar contexto RAG antes de `GenerationService` não altera schemas públicos nem o JSON de saída.
- `Track.trk_generation_request_id` liga uma trilha gerada a `GenerationRequest.goal/topic`. Trilhas manuais podem não ter esse vínculo e devem sempre seguir sem RAG. A etapa incremental usa o idioma do contexto original, não inferência a partir do título da etapa.
- O pré-filtro permite que assuntos sem menção aos idiomas terminem sem chamada adicional ao Groq classificador, embeddings ou recuperação. Uma menção incidental pode chegar ao classificador Groq, mas só resultado positivo qualificado aciona embedding e consulta.
- Classificação e recuperação são opcionais: exceções do RAG são capturadas e registradas antes da chamada Groq de geração; não se convertem em erro de geração nem ampliam a política de retries existente.
- A consulta de contexto incremental deve acontecer fora da transação/lock de escrita da etapa. Depois da recuperação, a task readquire o lock e revalida existência de conteúdo para preservar idempotência diante de concorrência.
- O bloco de referências é delimitado como material não confiável/de apoio com título e URL; instruções e schema JSON original mantêm precedência.
- O nível do contexto inicial usa `knowledge_level` quando disponível. Na preparação incremental usa o nível da etapa-alvo; `pro` mapeia somente para o filtro RAG `advanced`.

**Alternatives considered**: classificação por presença isolada da palavra Python/JavaScript foi rejeitada por aceitar menções incidentais; buscar o idioma pelo título da etapa foi rejeitado por sinal fraco; fazer RAG requisito da task Celery foi rejeitado por alterar retries/idempotência e bloquear gerações quando OpenAI está indisponível.

## 4. Conectores, parsing e políticas de coleta

**Decision**: Conectores independentes para URL, sitemap, Git e diretório local; `httpx.AsyncClient` reutilizado por execução, `urllib.robotparser` alimentado com conteúdo obtido por HTTP assíncrono, XML da biblioteca padrão para sitemap e subprocesso Git com diretório temporário para checkout raso. Parsing HTML usa BeautifulSoup com escopo principal configurável; Markdown usa `markdown-it-py`; RST usa `docutils` com diretivas perigosas restringidas.

**Rationale**:

- Cada documento falha isoladamente; falha de rede, parsing ou licença é relatada sem interromper as demais páginas/fontes.
- Crawler possui User-Agent identificável e contato configurável, timeout, concorrência por host e intervalo mínimo configurável. Respeita regras `robots.txt`; conteúdo de `robots.txt` é cacheado por até 24h. Em falha de rede/5xx que torne o arquivo inacessível, não faz crawl daquele host; 429 respeita `Retry-After`. `robots.txt` não substitui termos de uso/licença.
- O parser remove nav, footer, scripts, publicidade e sidebars por seletores estruturais; preserva títulos, headings, URLs canônicas, fences/blocos de código, linguagem detectada e ordem de explicação/código. Não executa exemplos.
- Normalização de prosa não reindenta blocos de código. `docutils` não deve processar inclusões locais ou conteúdo raw não confiável.
- `git` usa argumentos sem shell, clone raso e commit SHA como versão; local aceita somente Markdown/RST conforme inclusões. URLs são apenas HTTP(S) e restritas aos escopos configurados.
- Defaults iniciais conservadores: máximo de 2 requisições simultâneas por host, intervalo mínimo de 1 segundo (ou maior valor solicitado pela fonte), profundidade máxima 4 e timeout configurável. Cache robots até 24h; `5xx`/falha de rede é fail-closed, `429` interrompe/reagenda respeitando `Retry-After`.
- Escopos: Python Tutorial inclui somente `/3/tutorial/**`; biblioteca Python inclui somente `/3/library/**`; ambos excluem busca, índices gerados, static/assets e URLs com query. MDN inclui somente `/en-US/docs/Web/JavaScript/**`, excluindo `/files/**`, mídia, APIs web e caminhos fora do subtree JavaScript. Sitemap, quando usado, também passa pelos mesmos filtros.

**Alternatives considered**: crawler concorrente sem política por host foi rejeitado; parsing com regex sobre HTML foi rejeitado por perder hierarquia/blocos; clone completo de repositório foi rejeitado em favor de checkout raso.

## 5. Fontes e licenças

**Decision**: Configuração por tipo de conteúdo permite `license`/`license_url` da prosa e sobrescritas de código, além de uma política explícita de processamento externo por tipo. Fontes iniciais: `python-tutorial`, `python-library` e `mdn-javascript`. Licença ausente/desconhecida é armazenada como desconhecida; não é inferida de outra parte da fonte. Conteúdo sem licença demonstrável permanece no índice local para auditoria/busca lexical, mas por padrão não é enviado a embeddings nem incluído em prompts de provedores externos até que a configuração documente permissão apropriada.

**Rationale**:

- Python documenta prosa sob PSF License Version 2; exemplos/receitas de documentação a partir do Python 3.8.6 também sob Zero-Clause BSD. Atribuições são guardadas por chunk/conteúdo.
- MDN declara prosa normalmente sob CC BY-SA 2.5 ou posterior; exemplos de código depois de 20/08/2010 em CC0 e exemplos anteriores em MIT. A documentação atual informa que a plataforma não permite determinar essa data por amostra. Portanto, `mdn-javascript` usa licença de prosa configurada e licença de código `unknown` quando nenhuma evidência por amostra estiver disponível; não se atribui CC0 ou MIT por presunção.
- A coluna de atribuição permite `external_processing=false` para conteúdo com licença desconhecida, impedindo envio a OpenAI/Groq até revisão de fonte/licença. O texto permanece local e o relatório registra a contagem; não é promovido a contexto de geração.
- Para não perder proveniência ao deduplicar, conteúdo canônico fica em `RagChunkModel` e cada origem/licença/seção fica em `RagChunkAttributionModel`. Resultado de recuperação agrega as atribuições preservadas.

**Alternatives considered**: uma única licença para toda fonte foi rejeitada por conflito com as licenças documentadas; copiar a licença mais permissiva para exemplos MDN foi rejeitado por não ser demonstrável; apagar atribuições duplicadas foi rejeitado.

**Observação operacional**: escopo de coleta e licença configurada devem ser revistos antes de habilitar fonte adicional; documentação oficial das licenças é a autoridade para atualizar o YAML.

## 6. Chunking e deduplicação

**Decision**: Dividir por headings/seções, depois por blocos recursivos de texto com tokenizer substituível; alvo 500 tokens configurável e overlap inicial 12%. Código é unidade indivisível e fica associado ao texto de introdução sempre que possível. Deduplicação exata usa hash de conteúdo normalizado; deduplicação aproximada calcula SimHash configurável e agrupa candidatos, sem apagar atribuições.

**Rationale**:

- Alvo/overlap ficam no YAML e o contador inclui prefixo de título/seção.
- Hash exato é estável e também alimenta cache de embedding. Identidade do chunk inclui versão do chunker para uma mudança de algoritmo invalidar os segmentos corretos.
- SimHash de 64 bits com distância Hamming configurável detecta quase duplicatas sem dependência adicional. Código é comparado separadamente; diferenças de código nunca são colapsadas apenas por similaridade de prosa. Grupos aproximados são deduplicados na apresentação/recuperação, mantendo os documentos e atribuições associados.
- Chunk acima do limite OpenAI mantém conteúdo completo e fica somente no ramo lexical; todos os outros limites respeitam tokenização configurada.

**Alternatives considered**: split por contagem de caracteres foi rejeitado por ser incompatível com orçamento de embedding; overlap zero foi rejeitado por perder contexto de fronteira; mesclar blocos de código por similaridade aproximada foi rejeitado por poder apagar diferenças técnicas relevantes.

## 7. Persistência, indexação incremental e migration

**Decision**: Quatro modelos: documento, conteúdo de chunk, atribuição de origem/licença e embedding por modelo/dimensão. Migration encadeada após `f6a7b8c9d0e1`; `vector` não é recriada no upgrade novo nem removida no downgrade. GIN full-text, HNSW cosine, B-tree dos filtros e GIN das tags.

**Rationale**:

- Documento tem ID estável por fonte+URL canônica e hash do conteúdo/versionamento; chunk tem ID/hash estável; associações many-to-many preservam origens quando texto idêntico aparece em mais de uma fonte; embedding identifica modelo e dimensão.
- Indexação compara hash de documento e chunk, só gera embeddings alterados e remove associações obsoletas da fonte operada. Chunk canônico só é removido se não houver atribuição restante. Falha ao baixar um documento preserva a versão anterior.
- Reindexação total valida configuração, chave e dimensão antes de alterar o índice; reconstrói fontes e embeddings e informa que consultas podem ter cobertura parcial durante a execução. Deve ser executada em janela de baixa utilização.
- A migration existente já é idempotente (`CREATE EXTENSION IF NOT EXISTS vector`). A nova migration cria tabelas/índices reversíveis e parte do head existente. Os models precisam ser registrados em `models/__init__.py` e `migrations/env.py`.

**Alternatives considered**: armazenar vetores em outro serviço foi rejeitado; um vetor genérico sem dimensão/index coerentes foi rejeitado; eliminar a extensão em downgrade foi rejeitado por risco a outros objetos.

**CI**: `.github/workflows/ci.yml` usa `postgres:16-alpine`, que não garante pgvector. Alinhar o banco de integração/CI para `pgvector/pgvector:pg16` ou serviço equivalente antes de testar migrations/modelo vetorial; a fixture local atual `create_all` não habilita extensão sozinha.

## 8. Dependências

- Declarar como runtime: `openai`, `tiktoken`, `PyYAML`, `beautifulsoup4`, `markdown-it-py`, `docutils`.
- Mover `httpx>=0.28.1` do grupo de desenvolvimento para runtime, sem adicionar uma segunda entrada.
- Reutilizar `pgvector` existente e standard library para `argparse`, `robotparser`, XML, subprocess e retry/backoff; evitar dependências para retry, Git ou sitemap.
- Verificar versões suportadas de `openai`, `tiktoken`, BeautifulSoup, markdown-it-py e docutils no `uv.lock` antes da implementação; não fixar preço por token como dependência.

## Referências consultadas

- [OpenAI embeddings](https://platform.openai.com/docs/guides/embeddings) e [preços](https://developers.openai.com/api/docs/pricing) — dimensão, tokens de input, modelo e custo.
- [pgvector](https://github.com/pgvector/pgvector) e [pgvector-python / SQLAlchemy](https://github.com/pgvector/pgvector-python#sqlalchemy) — HNSW, cosine, filtros, full-text híbrido e exemplo RRF.
- [PostgreSQL 16 full-text search](https://www.postgresql.org/docs/16/textsearch.html) — tsvector, GIN, parser, consultas e ranking lexical.
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-asyncsession-with-concurrent-tasks) — ciclo de AsyncSession.
- [HTTPX AsyncClient](https://www.python-httpx.org/async/) — reutilização de cliente, pooling e requests async.
- [Python argparse](https://docs.python.org/3/library/argparse.html) e [urllib.robotparser](https://docs.python.org/3/library/urllib.robotparser.html) — CLI e parsing de robots.
- [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309), [RFC 6585 (429)](https://www.rfc-editor.org/rfc/rfc6585.html#section-4) e [RFC 9110 Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3).
- [Licença da documentação Python](https://docs.python.org/3/license.html), [licenciamento MDN](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Attrib_copyright_license), [API de embeddings](https://developers.openai.com/api/reference/resources/embeddings/methods/create) e [tiktoken](https://github.com/openai/tiktoken).
- Padrões locais verificados em `docs/architecture.md`, `docs/code_conventions.md`, tasks e testes de geração, `pyproject.toml`, migration de pgvector e `.github/workflows/ci.yml`.
