---

description: "Task list for deterministic AI memory"
---

# Tasks: Memória determinística da IA

**Input**: Design documents from `specs/SDB-92-ai-memory/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/ai-memory.md` and `quickstart.md`.

**Organization**: Tasks are grouped by user story so each increment can be
implemented and tested independently after the shared foundation is complete.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare configuration, exports and migration conventions for the
memory feature without changing any public route.

- [ ] T001 [P] Add `AI_MEMORY_ENABLED`, fingerprint-version and lease settings to `src/sidebrain_back/core/constants.py` and document their environment defaults in `.env.example`
- [ ] T002 [P] Register the new memory models, enums and repositories in `src/sidebrain_back/models/__init__.py`, `src/sidebrain_back/enums/__init__.py` and `src/sidebrain_back/repositories/__init__.py`
- [ ] T003 [P] Add feature test fixtures and shared cache/provider fakes in `tests/conftest.py` without exposing generated payloads or PII in logs

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the persistent entities and cross-cutting interfaces that
all user stories depend on.

**CRITICAL**: Complete this phase before implementing any user story.

- [ ] T004 Create `TopicAlias` and `GenerationCache` ORM models in `src/sidebrain_back/models/topic_alias_model.py` and `src/sidebrain_back/models/generation_cache_model.py`, including the required normalized fields, `track`/`assessment` content types, `pending`/`ready`/`failed` states, lease fields, audit fields and immutable-ready invariants from `data-model.md`
- [ ] T005 Add cache and alias enums in `src/sidebrain_back/enums/generation_cache_enum.py` with only the contract values `track`, `assessment`, `pending`, `ready` and `failed`
- [ ] T006 Add the Alembic migration in `migrations/versions/<new_revision>_cria_memoria_deterministica.py` for both global tables, `(fingerprint, content_type)` uniqueness, normalized alias uniqueness, the initial `ingles -> lingua inglesa` seed, and additive nullable `source`/`cache_id` columns on `generation_request` plus `source` on `knowledge_assessment`; include a reversible downgrade
- [ ] T007 Extend `src/sidebrain_back/models/generation_request_model.py` and `src/sidebrain_back/models/knowledge_assessment_model.py` with nullable legacy-compatible `source` fields and optional `cache_id` relationship/FK, preserving existing ownership, status and soft-delete behavior
- [ ] T008 Add validated `source` fields to `src/sidebrain_back/schemas/generation_schema.py` and `src/sidebrain_back/schemas/knowledge_assessment_schema.py` as `Literal["ai", "cache"] | None = None`, preserving `from_attributes` behavior and existing request/response shapes
- [ ] T009 Define the internal memory protocols and dependency providers in `src/sidebrain_back/repositories/generation_cache_repository.py` and `src/sidebrain_back/services/ai_memory_service.py` for lookup, lease reservation, ready publication, failure release and user-instance materialization; keep HTTP concerns out of these layers
- [ ] T010 Verify the migration and model metadata together with `tests/integration/test_ai_memory_migration.py`, including downgrade, legacy rows without `source`, unique constraints and the initial alias

**Checkpoint**: Persistent memory entities, additive schemas and internal
interfaces are ready; user-story work may proceed.

## Phase 3: User Story 1 - Reutilizar conteúdo equivalente entre usuários (Priority: P1) 🎯 MVP

**Goal**: Reuse one validated Track or Knowledge Assessment payload across
users while materializing independent records with fresh ownership and IDs.

**Independent Test**: Generate a valid Track or Assessment for one user, repeat
the equivalent request for another user, observe one provider call,
`source=cache` on the second result, and verify that all cloned records have
new IDs and independent ownership/progress.

### Tests for User Story 1

- [ ] T011 [P] [US1] Add Track cache-hit/miss and clone contract coverage in `tests/contract/test_ai_memory_track_contract.py`, asserting one provider call, `source=cache`, fresh Track/Step/Lesson/Quiz/Mission IDs and current-user ownership
- [ ] T012 [P] [US1] Add Assessment cache-hit/miss and clone contract coverage in `tests/contract/test_ai_memory_assessment_contract.py`, asserting copied questions/alternatives with new IDs and empty answers, score and completion state
- [ ] T013 [P] [US1] Add cross-user integration coverage in `tests/integration/test_ai_memory_reuse.py`, asserting the global cache is immutable and user progress, feedback, login, badge and streak records are not shared

### Implementation for User Story 1

- [ ] T014 [US1] Implement canonical cache-envelope and versioned SHA-256 fingerprint creation in `src/sidebrain_back/services/ai_memory_service.py`, including content type, canonical context, knowledge level, normalized assessment answers, prompt version, provider and model
- [ ] T015 [US1] Implement `GenerationCacheRepository` lookup, idempotent reservation, lease ownership, ready publication and failed release in `src/sidebrain_back/repositories/generation_cache_repository.py` using short transactions and re-read after uniqueness conflicts
- [ ] T016 [US1] Add Track payload serialization, schema revalidation and deep materialization in `src/sidebrain_back/repositories/track_repository.py` and `src/sidebrain_back/services/track_service.py`, creating fresh aggregates and initial empty progress
- [ ] T017 [US1] Add Assessment payload serialization, schema revalidation and deep materialization in `src/sidebrain_back/repositories/knowledge_assessment_repository.py` and `src/sidebrain_back/services/knowledge_assessment_service.py`, creating fresh Assessment/Question/Alternative records
- [ ] T018 [US1] Integrate cache lookup, validated publication and clone fallback into `src/sidebrain_back/tasks/generate_track_task.py` and `src/sidebrain_back/tasks/knowledge_assessment_task.py` without holding a database transaction during provider calls
- [ ] T019 [US1] Pass `source` and `cache_id` through `src/sidebrain_back/services/track_service.py`, `src/sidebrain_back/services/knowledge_assessment_service.py` and existing repositories while retaining legacy fingerprints and request idempotency
- [ ] T020 [US1] Expose additive `source` values in `src/sidebrain_back/routers/v1/track_router.py`, `src/sidebrain_back/routers/v1/knowledge_assessment_router.py` and their existing schemas/SSE serialization without adding a public endpoint

**Checkpoint**: A validated Track or Assessment can be reused independently
between users with no shared mutable state.

## Phase 4: User Story 2 - Reconhecer contextos equivalentes de forma determinística (Priority: P1)

**Goal**: Canonicalize equivalent text and apply only curated aliases before
fingerprinting, while keeping old fingerprints readable.

**Independent Test**: Canonicalize casing, accents, Unicode-combined text,
whitespace and punctuation variants; verify equal fingerprints, the exact
`ingles -> lingua inglesa` alias, and distinct fingerprints for level, model,
prompt or fingerprint-version changes.

### Tests for User Story 2

- [ ] T021 [P] [US2] Add normalization unit tests in `tests/unit/test_ai_memory_normalization.py` for NFKD diacritic removal, casefold, trim, whitespace collapse, peripheral punctuation and rejection of empty content
- [ ] T022 [P] [US2] Add alias and fingerprint unit tests in `tests/unit/test_ai_memory_fingerprint.py`, covering exact `ingles` mapping, no fuzzy inference, sorted JSON determinism, content type, level, normalized answers, model and prompt-version separation
- [ ] T023 [P] [US2] Add legacy and version-invalidation integration tests in `tests/integration/test_ai_memory_fingerprint_version.py`, confirming old fingerprints remain queryable and are not mass-recalculated

### Implementation for User Story 2

- [ ] T024 [US2] Implement deterministic text canonicalization and validation in `src/sidebrain_back/services/ai_memory_service.py` using Unicode NFKD, removed combining marks, casefold, collapsed whitespace and peripheral punctuation removal
- [ ] T025 [US2] Implement exact normalized alias lookup and versioned alias loading in `src/sidebrain_back/repositories/topic_alias_repository.py` and `src/sidebrain_back/services/ai_memory_service.py`, applying aliases only after canonicalization and never inferring unknown aliases
- [ ] T026 [US2] Replace the legacy Track and Assessment fingerprint paths in `src/sidebrain_back/services/generation_request_service.py` and `src/sidebrain_back/services/knowledge_assessment_service.py` with the versioned memory envelope while preserving legacy reads and request compatibility

**Checkpoint**: Equivalent contexts produce the same current fingerprint;
version/model/level changes produce misses without rewriting history.

## Phase 5: User Story 3 - Preservar integridade durante concorrência e falhas (Priority: P1)

**Goal**: Make cache reuse safe under concurrent workers and make cache
availability failures fall back to normal AI generation.

**Independent Test**: Run concurrent requests for one fingerprint and inject
lookup, lock, persistence, invalid-payload and provider failures; verify at
most one provider call, no partial records, lease recovery and `source=ai`
fallback when memory is unavailable or disabled.

### Tests for User Story 3

- [ ] T027 [P] [US3] Add concurrent lease and uniqueness integration tests in `tests/integration/test_ai_memory_concurrency.py`, asserting one winner, one ready cache entry, no duplicate materialized aggregates and recovery after lease expiration
- [ ] T028 [P] [US3] Add cache failure and disabled-configuration tests in `tests/integration/test_ai_memory_fallback.py`, covering lookup, Redis lock, cache write failures and `AI_MEMORY_ENABLED=false` with successful `source=ai` generation
- [ ] T029 [P] [US3] Add invalid-payload and transaction-rollback tests in `tests/integration/test_ai_memory_atomicity.py`, asserting invalid content is never published and mid-materialization failures leave no partial user records
- [ ] T030 [P] [US3] Extend `tests/contract/test_track_contract.py`, `tests/contract/test_knowledge_assessment_contract.py` and `tests/unit/test_track_sse.py` to verify additive `source` compatibility for polling, detail and SSE consumers

### Implementation for User Story 3

- [ ] T031 [US3] Complete lease acquisition, renewal, expiry and `FOR UPDATE` conflict handling in `src/sidebrain_back/repositories/generation_cache_repository.py`, with persistent uniqueness as the correctness guarantee and optional Redis locking as an optimization
- [ ] T032 [US3] Add cache exception boundaries and structured hit/miss/avoided-call logging in `src/sidebrain_back/services/ai_memory_service.py` and `src/sidebrain_back/core/logging.py`, recording only fingerprint, content type, source and outcome, never payload, tokens, e-mail or sensitive context
- [ ] T033 [US3] Wire `AI_MEMORY_ENABLED` and optional Redis lock behavior through `src/sidebrain_back/core/constants.py` and `src/sidebrain_back/core/redis.py`, making lookup/lock/persistence failures observable misses and preserving the AI path
- [ ] T034 [US3] Make Track and Assessment task publication atomic in `src/sidebrain_back/tasks/generate_track_task.py` and `src/sidebrain_back/tasks/knowledge_assessment_task.py`, validating payloads before cache publication and rolling back instance persistence on any materialization failure
- [ ] T035 [US3] Preserve the existing Problem Details errors and status codes in `src/sidebrain_back/services/generation_errors.py`, `src/sidebrain_back/services/track_service.py` and `src/sidebrain_back/services/knowledge_assessment_service.py` so only validation/materialization failures surface publicly
- [ ] T036 [US3] Confirm polling and SSE source propagation in `src/sidebrain_back/routers/v1/track_router.py` and `src/sidebrain_back/schemas/generation_schema.py`, including `source=None` for legacy requests

**Checkpoint**: Concurrent and degraded cache operation cannot corrupt or
block the existing AI generation flow.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete feature, documentation and operational
compatibility after all desired stories are complete.

- [ ] T037 [P] Update `docs/architecture.md` and `docs/code_conventions.md` with the memory repository/service boundaries, immutable global artifacts, lease rules and additive `source` contract
- [ ] T038 [P] Update `specs/SDB-92-ai-memory/quickstart.md` with the final test selectors, migration command, configuration switch and expected hit/miss observability fields
- [ ] T039 Run `uv run ruff check .` and fix only lint issues introduced by the AI memory implementation across `src/sidebrain_back`, `migrations/versions` and `tests`
- [ ] T040 Run the focused commands from `specs/SDB-92-ai-memory/quickstart.md`, then `uv run pytest`, and record any environment limitation or regression in the implementation handoff

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001-T003 can run in parallel.
- **Foundational (Phase 2)**: Depends on Phase 1; T004-T005 can run in parallel,
  T006-T008 depend on the model/enums decisions, and T009-T010 depend on the
  persistent schema and interfaces.
- **User Story 1 (Phase 3)**: Depends on Phase 2; T011-T013 can run in
  parallel, then T014-T020 implement the reuse path.
- **User Story 2 (Phase 4)**: Depends on the shared fingerprint envelope from
  T014 and the cache schema from Phase 2; T021-T023 can run in parallel, then
  T024-T026 finalize canonicalization and legacy compatibility.
- **User Story 3 (Phase 5)**: Depends on the cache operations from T015 and
  the materialization path from T016-T020; T027-T030 can run in parallel,
  followed by T031-T036.
- **Polish (Phase 6)**: Depends on all selected user stories; T037-T038 can
  run in parallel before T039-T040.

### User Story Dependencies

- **US1 (P1)**: Depends only on the foundational schema, providers and
  interfaces; it is the suggested MVP.
- **US2 (P1)**: Can be developed independently after the foundation, but its
  final fingerprint integration should be applied before US1 is considered
  production-ready.
- **US3 (P1)**: Depends on the reuse path from US1 and the deterministic
  fingerprint behavior from US2 for meaningful concurrency and fallback tests.

### Parallel Opportunities

- Setup tasks T001-T003.
- Foundational model/export work T004-T005 and test fixture work T003.
- All contract/unit/integration test tasks within each story marked `[P]`.
- Once Phase 2 is complete, US1 and the isolated US2 normalization tests can
  proceed in parallel; US3 starts after the reuse path exists.
- Documentation T037-T038 can run in parallel, followed by the validation
  commands T039-T040.

## Implementation Strategy

1. **MVP first**: Complete Phase 1, Phase 2, US1 and the minimum US2
   canonicalization needed for a versioned cache hit. This delivers one
   validated cross-user reuse path without changing public routes.
2. **Incremental hardening**: Complete the remaining US2 tests and legacy
   compatibility, then US3 lease/concurrency/fallback/atomicity behavior.
3. **Safe delivery**: Keep `AI_MEMORY_ENABLED=false` as an operational
   rollback, run migration and focused contract/integration suites before the
   full suite, and verify that cache failures remain transparent misses.
