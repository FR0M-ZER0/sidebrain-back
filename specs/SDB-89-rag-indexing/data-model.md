# Modelo de Dados: Índice RAG

## Configuração de fonte (YAML, não tabela de domínio)

Cada entrada define `name`, `type`, URL/sitemap/repositório/caminho, idioma, nível, licença de prosa e overrides por tipo de conteúdo, URL da licença, política de processamento externo por tipo, regras de inclusão/exclusão, estratégia de versão e parâmetros do conector. Configuração global define modelo/dimensão de embedding, tokenizer, chunk size, overlap, deduplicação aproximada, timeout, concorrência, intervalo por host, lote e preço de token. Credenciais não ficam no YAML.

Fontes iniciais:

- `python-tutorial`: `https://docs.python.org/3/tutorial/`, escopo tutorial, nível beginner, versão pela URL final/canonical.
- `python-library`: `https://docs.python.org/3/library/`, escopo biblioteca padrão, nível intermediate, versão pela URL final/canonical.
- `mdn-javascript`: `https://developer.mozilla.org/en-US/docs/Web/JavaScript/`, escopo JavaScript guide/reference, versão por ETag/Last-Modified quando disponível.

Python usa PSF-2.0 para prosa e registra a dupla licença aplicável a exemplos a partir de Python 3.8.6 (PSF-2.0/0BSD). MDN usa CC-BY-SA-2.5-or-later para prosa; licença de código é `unknown` quando a data de amostra não é demonstrável. Nenhuma licença é inferida de outra parte da página.

## Entidades persistidas

### RagDocumentModel (`rag_document`)

- `doc_id`: identificador estável do par `source_name + canonical_url/path`.
- `source_name`, `source_url`, `canonical_url`, `title`.
- `document_hash`: hash do conteúdo normalizado atual para detectar mudanças.
- `source_version`: versão/commit/ETag/estratégia resolvida; pode ser nula se a fonte não informar.
- `collected_at`, `updated_at`.
- Unique: (`source_name`, `canonical_url`). Uma falha de coleta não apaga o documento preexistente.

### RagChunkModel (`rag_chunk`)

- `chunk_id`: hash estável do texto normalizado e versão do algoritmo de chunking.
- `content_hash`: hash usado para cache e comparação incremental.
- `text`: prefixo de título/caminho de seção mais explicação e código preservado integralmente.
- `duplicate_fingerprint`, `duplicate_group_id`: fingerprint aproximado opcional para agrupamento deduplicado na recuperação.
- `search_vector`: `tsvector` do texto de busca, indexado por GIN.
- `created_at`.
- Conteúdo exato pode ser compartilhado por mais de um documento; ele só é eliminado quando não tem nenhuma atribuição.

### RagChunkAttributionModel (`rag_chunk_attribution`)

Uma linha por atribuição de origem/documento/seção, evitando que a deduplicação elimine proveniência.

- `chunk_id`, `doc_id`: chaves estrangeiras para chunk e documento.
- `section_path`, `source_name`, `source_url`, `title` (snapshot de origem para resposta de recuperação rastreável).
- `language`: `python` ou `javascript`.
- `level`: `beginner`, `intermediate` ou `advanced`.
- `content_type`: `concept`, `code_example`, `reference`, `tutorial` ou `exercise`.
- `topics`: tags extraídas por regras.
- `license`, `license_url`: licença aplicável a este conteúdo; valor desconhecido é explícito/nulo e não herda silenciosamente a licença de outro tipo.
- `external_processing_allowed`: snapshot da política da fonte para enviar conteúdo a providers externos. `false` impede embedding e inclusão em contexto de geração; o trecho permanece local e recebe busca lexical para inspeção operacional conforme configuração.
- Unique: (`chunk_id`, `doc_id`, `section_path`, `license`).
- Índices: B-tree em `language`, `level` e `content_type`; GIN em `topics`.

### RagChunkEmbeddingModel (`rag_chunk_embedding`)

- `chunk_id`: chave para conteúdo textual canônico.
- `model_id`, `dimensions`, `tokenizer_id`, `chunker_version`.
- `embedding`: pgvector `VECTOR(1536)` na configuração inicial, com índice HNSW `vector_cosine_ops`.
- `input_tokens`, `created_at`.
- Unique/cache: (`chunk_id`, `model_id`, `dimensions`).
- Um chunk maior que 8192 tokens não recebe linha de embedding; seu texto e `tsvector` continuam disponíveis para busca lexical.
- Uma mudança de dimensão requer migration correspondente, reconstrução de índice e reindexação completa; configurações incompatíveis devem falhar antes de indexar/consultar.

## Relações e ciclo de atualização

```text
RagDocument 1 ── N RagChunkAttribution N ── 1 RagChunk 1 ── N RagChunkEmbedding
```

1. O identificador de documento é estável independente do hash do conteúdo.
2. A coleta calcula o hash do documento; se não mudou, conserva chunks e embeddings.
3. Ao mudar, são recriadas as atribuições do documento e apenas chunks sem cache por `content_hash + model_id + dimensions` recebem embeddings.
4. Remoções são reconciliadas apenas após enumeração bem-sucedida da fonte; falha em página mantém sua versão anterior. Limpeza de chunk exige ausência de todas as atribuições.
5. Hash exato colapsa conteúdo idêntico mantendo todas as atribuições. Fingerprint aproximado agrupa candidatos segundo limiar configurável; código com conteúdo diferente não é colapsado por similaridade de prosa.
6. `RagChunkEmbedding` é indexado por modelo/dimensão. Reindexação completa verifica segredo/config/schema antes de alterar dados; durante rebuild in-place a recuperação pode ter cobertura parcial e a geração usa fail-open.

## Validações

- Toda linha de atribuição deve apontar para documento e chunk existentes e manter licença disponível ou explicitamente ausente.
- Atribuição com licença desconhecida não pode ser enviada a embeddings ou a prompts externos por padrão; uma exceção exige valor explícito de configuração para aquele tipo de conteúdo.
- `language`, `level` e `content_type` aceitam somente os domínios documentados. `pro` do domínio de Steps é convertido para `advanced` no serviço de recuperação, não persistido como enum RAG nem alterado em schemas públicos.
- Vetores persistidos devem ter exatamente a dimensão configurada e o `model_id` ativo. Não misturar vetor/modelo incompatível numa consulta.
- Conteúdo, código e provenance são mantidos em UTF-8; normalização de whitespace nunca reindenta bloco de código.
- A avaliação local referencia `chunk_id` estáveis e/ou URLs/seções esperadas.
