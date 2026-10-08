# Plano de Implementação: Memória determinística da IA

**Branch**: `SDB-92-ai-memory` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/SDB-92-ai-memory/spec.md`

## Summary

Adicionar memória global e imutável para os payloads validados de trilhas e
avaliações. O serviço normalizará os contextos, aplicará aliases curados e
calculará um SHA-256 versionado com prompt, modelo e schema. Uma entrada global
com unicidade persistente e lease de curta duração reservará a geração; após
validação, o payload será armazenado uma vez e materializado em novos registros
do usuário por clonagem profunda. Lookup, lock e persistência do cache serão
otimizações tolerantes a falhas: indisponibilidade seguirá pelo fluxo de IA,
enquanto falhas de validação ou da persistência da instância continuarão sendo
erros da geração.

## Technical Context

**Language/Version**: Python >=3.11

**Primary Dependencies**: FastAPI 0.141+, Pydantic 2.11+, SQLAlchemy 2.0+,
PostgreSQL/asyncpg, Alembic, Redis 8+, Celery 5.6+, pytest e ruff

**Storage**: PostgreSQL para aliases, artefatos globais e estado de lease;
Redis para lock distribuído opcional de curta duração; JSON versionado para
payloads canônicos

**Testing**: pytest com testes unitários, de contrato e integração; `uv run
ruff check .`; `uv run pytest`; testes de migration e concorrência quando
aplicáveis

**Target Platform**: Serviço Linux executado via FastAPI e workers Celery

**Project Type**: Web service HTTP versionado

**Performance Goals**: Cache hit deve evitar o provedor e permanecer compatível
com a latência de uma consulta local; geração assíncrona não deve manter
transação aberta durante a chamada externa

**Constraints**: Não criar endpoint público novo; preservar requests e
históricos legados; manter `routers -> services -> repositories -> models`;
chamadas ao provedor fora de transações longas; conteúdo global somente após
validação; logs sem payload integral, tokens, e-mails ou contexto sensível

**Scale/Scope**: Fluxos atuais de geração assíncrona de Track e Knowledge
Assessment, seus schemas, repositories, services, tasks, configuração,
migration e testes. Geração incremental futura de Step não recebe fingerprint
independente nesta versão.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Qualidade e Clean Code**: PASS. Normalização, fingerprint, cache e
  clonagem terão responsabilidades separadas e reutilizarão os validadores
  Pydantic existentes.
- **II. Responsabilidade única**: PASS. Routers expõem contratos; services
  orquestram fallback e domínio; repositories encapsulam PostgreSQL; tasks
  coordenam worker; lock/cache não conterão regras de HTTP.
- **III. Separação de camadas**: PASS. A composição continuará via `Depends`;
  tasks abrirão suas próprias sessões; schemas não exporão modelos ORM.
- **IV. Testes e contratos verificáveis**: PASS condicionado à implementação.
  O design exige testes de normalização, aliases, cache hit/miss, concorrência,
  clonagem, fallback, versionamento e compatibilidade aditiva de SSE/detalhe.
- **V. Simplicidade e evolução segura**: PASS. Não haverá endpoint novo nem
  alteração incompatível; o cache é uma otimização isolada e falhas dele fazem
  fallback explícito para IA. A migration terá downgrade e constraints.

Não há violação constitucional que exija justificativa.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-92-ai-memory/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ai-memory.md
└── tasks.md              # gerado posteriormente por /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── sidebrain_back/
│   ├── core/
│   ├── enums/
│   ├── models/
│   ├── repositories/
│   ├── routers/v1/
│   ├── schemas/
│   ├── services/
│   └── tasks/
├── main.py
migrations/versions/
└── [nova migration da memória]

tests/
├── contract/
├── integration/
├── performance/
└── unit/
```

**Structure Decision**: Projeto único FastAPI em `src/sidebrain_back`,
organizado nas camadas normativas. O cache e aliases serão modelos persistidos,
com repositories e services próprios ou compartilhados por domínio; a
materialização chamará os repositories existentes para preservar a criação de
IDs, ownership e cascatas. Contratos permanecem em
`specs/SDB-92-ai-memory/contracts/`; testes seguem a divisão existente.

## Complexity Tracking

Não aplicável: nenhum gate constitucional foi violado.

## Phase 0: Research Summary

As decisões e evidências estão em [research.md](research.md). O padrão
selecionado usa `AsyncSession` com transações curtas, constraint única para o
fingerprint e lease persistido; `FOR UPDATE` protege transições de estado e o
lock Redis é apenas uma otimização dispensável. FastAPI mantém os campos
aditivos em schemas e o SSE atual continua emitindo o request individual.

## Phase 1: Design Summary

- [data-model.md](data-model.md) define aliases, cache global, requests,
  payloads e transições, incluindo a separação entre artefato e instância.
- [contracts/ai-memory.md](contracts/ai-memory.md) define os campos aditivos
  nos endpoints existentes e os contratos internos de lookup, reserva,
  publicação e clonagem.
- [quickstart.md](quickstart.md) define comandos e cenários executáveis para
  provar os critérios de sucesso da feature.

## Constitution Check: pós-design

- **I. Qualidade e Clean Code**: PASS. O design centraliza canonicalização e
  hashing em um componente determinístico e deixa clonagem nos repositories de
  domínio.
- **II. Responsabilidade única**: PASS. Estado do cache, payload validado e
  instâncias do usuário são entidades distintas; tasks não introduzem regra de
  negócio.
- **III. Separação de camadas**: PASS. Nenhum router acessa cache ou task
  diretamente; services compõem repositories via providers.
- **IV. Testes e contratos verificáveis**: PASS. Todos os cenários normativos
  têm correspondência no quickstart e os campos aditivos são cobertos por
  contratos.
- **V. Simplicidade e evolução segura**: PASS. Não há nova rota pública,
  fingerprints antigos permanecem legíveis e `AI_MEMORY_ENABLED=false` retorna
  ao caminho de IA.

O gate pós-design passa; não há clarificação pendente.
