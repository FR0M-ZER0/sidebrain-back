# Tasks: Resumo de Estatísticas de Aprendizagem

**Input**: Design documents from `specs/SDB-112-learning-stats-summary/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/user-statistics-api.md`, `quickstart.md`

**Tests**: Required by the feature specification; add focused unit, contract,
integration, and performance tests.

**Organization**: Tasks are grouped by user story. All paths are relative to the
repository root.

## Phase 1: Setup

**Purpose**: Project initialization and shared infrastructure.

The existing project, dependencies, test layout, database configuration,
authentication, and error handlers are already present. No setup task,
dependency change, or migration is required.

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites for all user stories.

No new foundational component is required. The feature reuses the existing
authenticated-user dependency, database session, ranking repository, and
Problem Details handling.

---

## Phase 3: User Story 1 - Consultar o próprio resumo de aprendizagem (Priority: P1)

**Goal**: Return all five learning statistics for the authenticated user in one
read-only response, reusing the authoritative ranking values.

**Independent Test**: With a user who has completed missions, unlocked badges,
and recent activity, compare XP, completed missions, and position with the
existing profile and ranking responses; verify the badge count and current
streak against their recorded data.

### Tests for User Story 1

- [ ] T001 [P] [US1] Add response-schema unit tests for `xp >= 0`, `missionsCompleted >= 0`, `position >= 1`, `badgesUnlocked >= 0`, and `currentDayStreak >= 0` in `tests/unit/test_user_statistics_schema.py`
- [ ] T002 [P] [US1] Add a contract test for `GET /api/v1/users/me/statistics` verifying the exact five public fields and camelCase names in `tests/contract/test_user_statistics_contract.py`
- [ ] T003 [P] [US1] Add a PostgreSQL integration test comparing summary XP, missions, and position with the profile and ranking endpoints for the same user in `tests/integration/test_user_statistics.py`

### Implementation for User Story 1

- [ ] T004 [P] [US1] Define the `UserStatisticsResponse` schema with exactly `xp`, `missionsCompleted`, `position`, `badgesUnlocked`, and `currentDayStreak` in `src/sidebrain_back/schemas/user_statistics_schema.py`
- [ ] T005 [P] [US1] Add read-only queries for the authenticated user's active unlocked-badge count and day-streak record in `src/sidebrain_back/repositories/user_statistics_repository.py`; count only `BadgeProgress` status `done` joined to non-deleted badges, and do not lock or mutate streak rows
- [ ] T006 [US1] Implement `UserStatisticsService` in `src/sidebrain_back/services/user_statistics_service.py`; reuse `RankingRepository.get_user_ranking`, return the existing not-found error when no active ranking row exists, and compose the five response values using the UTC streak rule
- [ ] T007 [US1] Add `GET /api/v1/users/me/statistics` with `get_current_user` and the response schema in `src/sidebrain_back/routers/v1/user_statistics_router.py`, then register it in `src/sidebrain_back/routers/router.py`

**Checkpoint**: The authenticated endpoint returns all five values consistently
with existing ranking rules and does not write progress data.

---

## Phase 4: User Story 2 - Consultar o resumo sem progresso e preservar a privacidade (Priority: P1)

**Goal**: Verify zero-progress defaults, position behavior, authentication, and
isolation between users.

**Independent Test**: Query an authenticated user with no progress while another
user has progress; verify zero counts, the caller's ranking position, and no
disclosure of the other user's statistics. Verify unauthenticated requests are
rejected in Problem Details format.

### Tests for User Story 2

- [ ] T008 [P] [US2] Add contract tests for unauthenticated `401` Problem Details, absence of user-selecting inputs, and a response containing no identity or private fields in `tests/contract/test_user_statistics_contract.py`
- [ ] T009 [P] [US2] Add an integration test verifying zero counts for an active user without progress, ranking position consistency, and isolation from another user's nonzero statistics in `tests/integration/test_user_statistics.py`

**Checkpoint**: Empty-state and privacy scenarios pass without changing
authentication behavior or existing profile and ranking contracts.

---

## Phase 5: User Story 3 - Interpretar corretamente a sequência de atividade (Priority: P2)

**Goal**: Verify UTC day-boundary behavior and that an expired streak is
presented as zero without changing stored data.

**Independent Test**: Exercise activity recorded today, yesterday, before
yesterday, and no activity; compare the response with stored values before and
after each read.

### Tests for User Story 3

- [ ] T010 [P] [US3] Add service unit tests for a streak updated today, yesterday, earlier than yesterday, and no streak record using a controlled UTC date in `tests/unit/test_user_statistics_service.py`
- [ ] T011 [P] [US3] Add an integration test proving that querying an expired streak leaves `DayStreak` and badge-progress records unchanged in `tests/integration/test_user_statistics.py`

**Checkpoint**: Current streak is valid through the prior UTC day, expires after
that boundary, and reads never reset persisted progress.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Performance, regression, and final verification.

- [ ] T012 [P] Add a 20-client performance test measuring the endpoint's P95 against the 2-second target in `tests/performance/test_user_statistics_performance.py`, following the `AUTH_PERFORMANCE_BASE_URL` convention
- [ ] T013 Run focused tests, `uv run --no-sync ruff check .`, and `uv run --no-sync pytest`; record actual results and any external performance-test prerequisite in `specs/SDB-112-learning-stats-summary/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks; project infrastructure already exists.
- **Foundational (Phase 2)**: No tasks; existing authentication, database, and
  error handling are reused.
- **User Story 1 (Phase 3)**: Starts immediately; its tests precede implementation.
- **User Story 2 (Phase 4)**: Depends on User Story 1 because it validates the
  same endpoint's empty-state and privacy behavior.
- **User Story 3 (Phase 5)**: Depends on User Story 1 because it validates the
  sequence returned by that endpoint. After User Story 1, Stories 2 and 3 can
  be tested in parallel.
- **Polish (Phase 6)**: Depends on all desired user-story tests and
  implementation tasks.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on another user story.
- **User Story 2 (P1)**: Depends on the endpoint and response contract from
  User Story 1.
- **User Story 3 (P2)**: Depends on the sequence field and read-only service
  from User Story 1; independent of User Story 2 after that.

### Within Each User Story

- Add the story's tests before implementation and verify they fail for the
  missing behavior.
- In User Story 1, schema and repository can be implemented in parallel after
  its tests; the service depends on both, and the router depends on the service
  and schema.
- User Stories 2 and 3 primarily add focused acceptance coverage for behavior
  implemented in the shared User Story 1 endpoint.

### Parallel Opportunities

- **User Story 1**: T001, T002, and T003 touch separate test files and can be
  authored in parallel. After they fail as expected, T004 and T005 can be
  implemented in parallel.
- **User Story 2**: T008 and T009 can be authored in parallel because contract
  and integration tests use separate files.
- **User Story 3**: T010 and T011 can be authored in parallel because unit and
  integration tests use separate files.
- **Across stories**: After User Story 1 is complete, User Stories 2 and 3 can
  proceed in parallel if staffing allows.

## Parallel Example: User Story 1

```text
After T001-T003 confirm expected failures:
Task: T004 Define UserStatisticsResponse in src/sidebrain_back/schemas/user_statistics_schema.py
Task: T005 Add read-only user statistics queries in src/sidebrain_back/repositories/user_statistics_repository.py

Then complete T006 before T007.
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Reuse existing infrastructure; no setup or migration is needed.
2. Add and fail the schema, contract, and consistency tests (T001-T003).
3. Implement the schema and read-only repository queries (T004-T005).
4. Implement the service and authenticated route (T006-T007).
5. Validate all five fields and confirm profile/ranking consistency.

User Story 1 includes the complete five-field summary and its UTC streak
semantics, so it is a useful MVP without returning provisional or stale values.

### Incremental Delivery

1. Complete User Story 1 and verify the core contract and consistency.
2. Add User Story 2 coverage for users without progress and private-data
   isolation.
3. Add User Story 3 coverage for streak expiry and read-only behavior.
4. Run performance and full regression checks.

## Notes

- `[P]` tasks use different files and have no dependency on each other.
- `[US1]`, `[US2]`, and `[US3]` map to the corresponding specification stories.
- No migration or new dependency is expected.
- Update the quickstart with observed validation results; do not mark skipped
  performance checks as passing.
