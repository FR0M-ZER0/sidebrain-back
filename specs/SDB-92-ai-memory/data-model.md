# Modelo de dados — SDB-92

## Entidades novas

### TopicAlias

Tabela global de curadoria determinística.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `alias` | string | obrigatório, normalizado, único |
| `canonical_topic` | string | obrigatório, normalizado |
| `alias_version` | string/int | versão da curadoria |
| `created_at` | datetime | preenchido pelo banco |
| `is_active` | boolean | desativação sem apagar histórico |

A migration inicial inclui `ingles -> lingua inglesa`; nenhum alias é inferido.

### GenerationCache

Artefato global, imutável após ficar `ready`.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `fingerprint` | string(64) | SHA-256, obrigatório |
| `content_type` | enum | `track` ou `assessment` |
| `fingerprint_version` | string | obrigatório |
| `prompt_version` | string | obrigatório |
| `provider` | string | obrigatório |
| `model` | string | obrigatório |
| `canonical_context` | JSON | contexto sem PII |
| `payload` | JSON | obrigatório apenas em `ready` |
| `status` | enum | `pending`, `ready`, `failed` |
| `lease_owner` | string nullable | worker que reservou |
| `lease_expires_at` | datetime nullable | expiração da reserva |
| `failure_code` | string nullable | falha interna sem payload |
| `created_at`, `updated_at` | datetime | auditoria |

Constraint única: `(fingerprint, content_type)`. Entradas `ready` não podem
ter payload, contexto, versões ou modelo alterados.

## Entidades existentes alteradas

### GenerationRequest

Mantém ownership e auditoria por usuário. Adicionar `source` (`ai`/`cache`,
nullable para legado) e `cache_id` (FK opcional, `SET NULL`). O fingerprint
legado continua preservado; novas solicitações usam o fingerprint versionado,
sem recálculo em massa.

### KnowledgeAssessment

Adicionar `source` ao modelo de resposta/persistência conforme migration.
Questions, alternatives, answers, score, status e progresso continuam próprios
do usuário; o cache fornece apenas o payload de perguntas e chaves privadas.

### Schemas públicos

`GenerationProgress` e `AssessmentDetail` recebem
`source: Literal["ai", "cache"] | None = None`, mantendo leitura de históricos
e compatibilidade com clientes antigos.

## Relações

```text
TopicAlias (global)
GenerationCache (global, 1) ──< GenerationRequest (por usuário)
GenerationCache (global, 1) ──< Track materialized (por usuário, via request)
GenerationCache (global, 1) ──< KnowledgeAssessment materialized (por usuário)
Track ──< Step ──< Lesson ── Quiz
Step ── Mission
KnowledgeAssessment ──< Question ──< Alternative
```

A exclusão da instância não afeta o artefato global. A clonagem gera novos
UUIDs e copia somente valores estruturais validados.

## Canonicalização e fingerprint

1. Validar que o texto possui conteúdo.
2. Aplicar Unicode NFKD e remover marcas diacríticas.
3. Aplicar `casefold`, trim, colapsar whitespace e remover pontuação
   periférica.
4. Consultar alias exato na tabela `TopicAlias`.
5. Ordenar chaves JSON e normalizar respostas pela ordem semântica definida.
6. Hashear envelope com versões, tipo, contexto, nível, respostas, provider e
   model.

## Transições

```text
pending --worker com lease--> generating (lease ativa)
generating --payload válido + commit atômico--> ready
generating --falha de IA/validação--> failed
failed --lease expirada e retry--> generating
ready --lookup--> materialização por usuário (sem mutar ready)
```

Erro de lookup/lock/persistência do cache resulta em miss observável e
`source=ai`. Falha de validação ou da transação de materialização não publica
conteúdo e segue o erro da geração.
