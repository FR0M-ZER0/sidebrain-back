---

description: "Tarefas de implementação da SDB-56 — nível de conhecimento do usuário"
---

# Tasks: Nível de Conhecimento do Usuário

**Input**: Documentos de design em `/specs/SDB-56-user-knowledge-level/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/assessments.md](./contracts/assessments.md) e
[quickstart.md](./quickstart.md)

**Tests**: Obrigatórios pela especificação, pelo plano e pela constituição. Em
cada história, escrever os testes indicados e confirmar que falham antes da
implementação correspondente.

**Organization**: As tarefas estão agrupadas por história para manter cada
incremento implementável e verificável. As fases de setup e fundação contêm
somente os elementos compartilhados que bloqueiam todas as histórias.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode ser executada em paralelo porque altera arquivos diferentes e
  não depende de outra tarefa ainda incompleta da mesma fase.
- **[Story]**: mapeia a tarefa para US1, US2, US3 ou US4.
- Todos os itens informam os caminhos exatos que devem ser alterados.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Introduzir o vocabulário compartilhado do novo domínio sem alterar
o comportamento da API.

- [X] T001 Criar `KnowledgeAssessmentStatusEnum` com os valores exatos `pending`, `generated`, `skipped`, `completed` e `failed`, e exportá-lo em `src/sidebrain_back/enums/knowledge_assessment_status_enum.py` e `src/sidebrain_back/enums/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Criar persistência, schemas e acesso a dados compartilhados por
todas as histórias.

**CRITICAL**: Nenhuma história deve ser implementada antes desta fase.

### Tests for the foundation

- [X] T002 [P] Escrever testes da migration para as quatro tabelas, enum de status, reutilização de `step_level`, checks, FKs compostas, cascatas, índices únicos parciais e downgrade até `b2c3d4e5f6a7` em `tests/integration/test_knowledge_assessment_migration.py`
- [X] T003 [P] Escrever testes dos schemas compartilhados para aliases públicos, `ConfigDict(from_attributes=True, populate_by_name=True)`, `extra="forbid"`, UUIDs e invariantes de estado sem exposição de nomes físicos ou gabarito em `tests/unit/test_knowledge_assessment_schema.py` e `tests/contract/test_knowledge_assessment_contract.py`

### Models and migration

- [X] T004 [P] Criar `KnowledgeAssessment` com `kas_id` UUID canônico, `kas_user_id` FK, `kas_subject` obrigatório após trim com 1..255 caracteres inclusive no skip, `kas_objective` nulo quando ausente e com 1..1000 caracteres quando informado, `kas_skip` booleano, fingerprint SHA-256 com 64 caracteres, status, score nulo ou 0..5, `StepLevelEnum` nulo ou coerente com skipped/completed, error code e timestamps, incluindo checks por estado em `src/sidebrain_back/models/knowledge_assessment_model.py`
- [X] T005 [P] Criar `KnowledgeAssessmentQuestion` com UUID do backend, assessment FK com cascade, statement não vazio, position 1..5, `UNIQUE(assessment_id, position)` e chave composta auxiliar `(question_id, assessment_id)` em `src/sidebrain_back/models/knowledge_assessment_question_model.py`
- [X] T006 [P] Criar `KnowledgeAssessmentAlternative` com UUID do backend, question FK com cascade, text não vazio, position 1..4, `UNIQUE(question_id, position)`, `is_correct` interno e índice único parcial por pergunta quando correto em `src/sidebrain_back/models/knowledge_assessment_alternative_model.py`
- [X] T007 [P] Criar `KnowledgeAssessmentAnswer` com assessment/question/alternative FKs, timestamp, `UNIQUE(assessment_id, question_id)` e FKs compostas que provem que a pergunta pertence à avaliação e a alternativa pertence à pergunta em `src/sidebrain_back/models/knowledge_assessment_answer_model.py`
- [X] T008 Integrar os quatro models ao relacionamento `User.knowledge_assessments`, aos exports e ao metadata do Alembic em `src/sidebrain_back/models/user_model.py`, `src/sidebrain_back/models/__init__.py` e `migrations/env.py`
- [X] T009 Criar migration reversível `c3d4e5f6a7b8` após `b2c3d4e5f6a7`, com enum `knowledge_assessment_status`, tabelas pai/filhas, checks de score/estado/corte, índice ativo `(user_id, context_fingerprint) WHERE status IN ('pending','generated')`, índice de uma correta por pergunta e downgrade filhos→pai→enum em `migrations/versions/c3d4e5f6a7b8_cria_avaliacoes_de_conhecimento.py`

### Shared schemas, fixtures and repository

- [X] T010 Implementar DTOs internos e públicos compartilhados, mantendo provider IDs separados dos UUIDs públicos, exigindo cinco perguntas distintas, quatro alternativas distintas por pergunta e `correct_alternative_id` pertencente à própria pergunta, e omitindo gabarito dos schemas públicos em `src/sidebrain_back/schemas/knowledge_assessment_schema.py`
- [X] T011 Adicionar factories PostgreSQL para avaliação, pergunta, alternativa correta/incorreta e resposta selecionada, com usuários distintos para ownership, em `tests/conftest.py`
- [X] T012 [P] Escrever testes de repository para create/get, filtro conjunto por assessment+user, avaliação ativa por fingerprint, carregamento com `selectinload`, lock `FOR UPDATE` e ausência de N+1 em `tests/unit/test_knowledge_assessment_repository.py`
- [X] T013 Implementar `KnowledgeAssessmentRepository` e `get_knowledge_assessment_repository` com create/get, busca ativa, consulta autorizada, consulta bloqueante e carregamento da hierarquia em `src/sidebrain_back/repositories/knowledge_assessment_repository.py`
- [X] T014 Executar e estabilizar os testes de fundação em `tests/integration/test_knowledge_assessment_migration.py`, `tests/unit/test_knowledge_assessment_schema.py`, `tests/contract/test_knowledge_assessment_contract.py` e `tests/unit/test_knowledge_assessment_repository.py`

**Checkpoint**: o banco representa o agregado completo, os schemas separam
contrato interno/público e o repository oferece ownership e lock; as histórias
podem começar.

---

## Phase 3: User Story 1 — Iniciar avaliação de conhecimento (Priority: P1) MVP

**Goal**: Aceitar uma avaliação autenticada, criar o `assessment_id` canônico,
reutilizar contexto ativo, enfileirar a task oficial e disponibilizar cinco
perguntas públicas completas ou uma falha sanitizada.

**Independent Test**: Fazer `POST /api/v1/assessments` com subject/objective
válidos, observar `202 pending`, processar a task com generator fake e
consultar o mesmo ID em `generated` com exatamente cinco perguntas × quatro
alternativas, score/level nulos e nenhum gabarito; repetir o mesmo contexto e
confirmar o mesmo ID e uma única publicação.

### Tests for User Story 1

- [X] T015 [P] [US1] Expandir testes do generator para exigir payload somente com perguntas e `correct_alternative_id`, cinco IDs de pergunta distintos, quatro alternativas distintas por pergunta, gabarito pertencente à pergunta e ausência de assessment_id/status/level controlados pelo provider em `tests/unit/test_knowledge_assessment_generator.py`
- [X] T016 [P] [US1] Escrever testes do service para trim e limites subject/objective, fingerprint canônico, UUID criado antes do enqueue, commit antes da publicação, deduplicação pending/generated, nova criação após terminal, corrida de `IntegrityError` e publish failure→failed/503 em `tests/unit/test_knowledge_assessment_service.py`
- [X] T017 [P] [US1] Expandir os testes da task para cobrir payloads v1 já enfileirados e chamadas v2, preservar o ID canônico, persistir 5 perguntas/20 alternativas atomicamente, não publicar parcial, parametrizar `APIConnectionError`/`APITimeoutError`/`RateLimitError`, validar três retries com esperas exatas de 1/2/4 segundos sem jitter, exaustão→failed, falha definitiva sem retry, redelivery idempotente e logs sanitizados em `tests/integration/test_knowledge_assessment_task.py`
- [X] T018 [P] [US1] Escrever contrato de `POST /api/v1/assessments` para 202 novo/pending, 200 generated reutilizado, Location, extras/limites 422, auth 401, publish failure 503 e Problem Details em `tests/contract/test_knowledge_assessment_http_contract.py`
- [X] T019 [P] [US1] Escrever integração criação→task→consulta para pending sem parcial, generated com 5×4 sem gabarito, failed sanitizado e corrida de duas criações mantendo uma avaliação ativa/task em `tests/integration/test_knowledge_assessment_lifecycle.py`

### Implementation for User Story 1

- [X] T020 [P] [US1] Remover assessment_id/status/level do prompt do provider, solicitar `correct_alternative_id`, validar JSON integral e manter a integração Groq exclusivamente em `src/sidebrain_back/services/knowledge_assessment_generator.py`
- [X] T021 [P] [US1] Adicionar operações atômicas `pending -> generated` e `pending -> failed`, criação dos UUIDs públicos, persistência de 5 questions/20 alternatives e no-op para redelivery terminal em `src/sidebrain_back/repositories/knowledge_assessment_repository.py`
- [X] T022 [US1] Implementar criação, normalização/fingerprint, deduplicação protegida pelo índice parcial, projeção pending/generated/failed, composição do generator e transações sem manter lock durante chamada externa em `src/sidebrain_back/services/knowledge_assessment_service.py`
- [X] T023 [US1] Evoluir `tasks.prepare_knowledge_assessment` mantendo o nome registrado e compatibilidade temporária com mensagens v1; aceitar chamadas v2 por argumentos nomeados com `contract_version=2`, `assessment_id`, `user_id`, `subject`, `objective` e `skip`; preservar o retorno legado para v1 e retornar somente assessment_id/status para v2; abrir AsyncSession própria, delegar ao service e persistir failed somente após falha definitiva ou retries esgotados em `src/sidebrain_back/tasks/knowledge_assessment_task.py`
- [X] T024 [US1] Criar `POST /api/v1/assessments` e polling mínimo de pending/generated/failed com `get_current_user`, Depends do service, códigos 202/200, Location e registro do router em `src/sidebrain_back/routers/v1/knowledge_assessment_router.py` e `src/sidebrain_back/routers/router.py`
- [X] T025 [US1] Executar e estabilizar a suíte US1 em `tests/unit/test_knowledge_assessment_generator.py`, `tests/unit/test_knowledge_assessment_service.py`, `tests/integration/test_knowledge_assessment_task.py`, `tests/contract/test_knowledge_assessment_http_contract.py` e `tests/integration/test_knowledge_assessment_lifecycle.py`

**Checkpoint**: US1 entrega o MVP gerável e acompanhável, preservando o ID e o
gabarito interno.

---

## Phase 4: User Story 2 — Responder e obter o nível calculado (Priority: P1)

**Goal**: Receber um conjunto terminal de cinco escolhas, corrigir no servidor e
persistir respostas, score e nível em uma única transação.

**Independent Test**: Sem depender da geração externa, semear uma avaliação
`generated` própria com 5×4 e gabarito, submeter cinco escolhas para cada
score de 0 a 5 e confirmar os cortes; submeter quantidade, IDs ou vínculos
inválidos e confirmar 422 sem mutação; enviar duas submissões concorrentes e
confirmar um 200 e um 409.

### Tests for User Story 2

- [X] T026 [P] [US2] Escrever testes dos schemas de submissão para exatamente cinco respostas, question_id único, UUIDs válidos, `extra="forbid"` no root/itens e rejeição de user_id/level/score/status/is_correct em `tests/unit/test_knowledge_assessment_schema.py` e `tests/contract/test_knowledge_assessment_contract.py`
- [X] T027 [P] [US2] Escrever testes do service para scores 0..5 e cortes exatos `0–1 beginner`, `2–3 intermediate`, `4 advanced`, `5 pro`, conjunto completo de perguntas, alternativa cruzada, estados incompatíveis, rollback e segunda submissão em `tests/unit/test_knowledge_assessment_service.py`
- [X] T028 [P] [US2] Escrever integração PostgreSQL para persistência das cinco respostas, FKs de vínculo, atomicidade, `SELECT FOR UPDATE`, duas submissões concorrentes e preservação do primeiro resultado em `tests/integration/test_knowledge_assessment_lifecycle.py`
- [X] T029 [P] [US2] Escrever contrato de `POST /api/v1/assessments/{assessment_id}/answers` para 200 completed, 404 ownership/inexistência, 409 estado terminal/pending, 422 cardinalidade/duplicidade/vínculos/extras e 500 com rollback em `tests/contract/test_knowledge_assessment_http_contract.py`

### Implementation for User Story 2

- [X] T030 [P] [US2] Implementar `AssessmentAnswerInput`, request com exatamente cinco itens distintos e resposta completed sem campos controlados pelo cliente em `src/sidebrain_back/schemas/knowledge_assessment_schema.py`
- [X] T031 [P] [US2] Implementar validação de vínculos e persistência atômica de cinco `KnowledgeAssessmentAnswer` sob lock da avaliação, com transição condicional `generated -> completed`, score, level e completed_at em `src/sidebrain_back/repositories/knowledge_assessment_repository.py`
- [X] T032 [US2] Implementar `submit_knowledge_assessment_answers`, correção somente pelo `is_correct` persistido, tabela de corte, 404 uniforme, 422 sem mutação, 409 de estado e commit/rollback em `src/sidebrain_back/services/knowledge_assessment_service.py`
- [X] T033 [US2] Adicionar `POST /api/v1/assessments/{assessment_id}/answers` autenticado e retornar a projeção completed em `src/sidebrain_back/routers/v1/knowledge_assessment_router.py`
- [X] T034 [US2] Executar e estabilizar a suíte US2 em `tests/unit/test_knowledge_assessment_schema.py`, `tests/contract/test_knowledge_assessment_contract.py`, `tests/unit/test_knowledge_assessment_service.py`, `tests/integration/test_knowledge_assessment_lifecycle.py` e `tests/contract/test_knowledge_assessment_http_contract.py`

**Checkpoint**: US2 classifica todas as pontuações e rejeita qualquer
submissão inválida ou repetida sem alterar o resultado.

---

## Phase 5: User Story 3 — Prosseguir sem responder à avaliação (Priority: P1)

**Goal**: Processar `skip=true` pela mesma task oficial, sem provider, e
persistir `skipped/beginner` sem perguntas nem score.

**Independent Test**: Iniciar uma avaliação com subject válido e `skip=true`,
confirmar 202/pending seguido de skipped/beginner, questions vazias,
completed_at preenchido, zero chamadas ao Groq e 409 ao tentar responder.

### Tests for User Story 3

- [X] T035 [P] [US3] Escrever testes de schema/service exigindo subject após trim com 1..255 caracteres mesmo em skip, objective ausente permitido mas vazio informado inválido, deduplicação pelo contexto incluindo skip e novo ID após estado terminal em `tests/unit/test_knowledge_assessment_schema.py` e `tests/unit/test_knowledge_assessment_service.py`
- [X] T036 [P] [US3] Escrever integração da task para skip sem construir/chamar `KnowledgeAssessmentGenerator`, transição atômica pending→skipped, level beginner, score null, questions vazias, completed_at e redelivery sem alteração em `tests/integration/test_knowledge_assessment_task.py`
- [X] T037 [P] [US3] Escrever contrato HTTP do fluxo skip para POST 202 pending, GET skipped/beginner sem perguntas e POST answers 409 preservando o resultado em `tests/contract/test_knowledge_assessment_http_contract.py`

### Implementation for User Story 3

- [X] T038 [US3] Adicionar operação atômica e idempotente `pending -> skipped` com `skip=true`, `level=beginner`, `score=null`, `error_code=null`, zero filhos e completed_at preenchido em `src/sidebrain_back/repositories/knowledge_assessment_repository.py`
- [X] T039 [US3] Implementar o ramo skip no service/task oficial antes da criação do client Groq e ampliar `get_knowledge_assessment` e o GET existente para projetar `skipped`, `level=beginner`, `score=null` e questions vazias, mantendo subject obrigatório e o enqueue com assessment_id/user_id/subject/objective/skip em `src/sidebrain_back/services/knowledge_assessment_service.py`, `src/sidebrain_back/tasks/knowledge_assessment_task.py` e `src/sidebrain_back/routers/v1/knowledge_assessment_router.py`
- [X] T040 [US3] Executar e estabilizar a suíte US3 em `tests/unit/test_knowledge_assessment_schema.py`, `tests/unit/test_knowledge_assessment_service.py`, `tests/integration/test_knowledge_assessment_task.py` e `tests/contract/test_knowledge_assessment_http_contract.py`

**Checkpoint**: US3 conclui iniciantes sem provider e não permite respostas.

---

## Phase 6: User Story 4 — Consultar o resultado da avaliação (Priority: P2)

**Goal**: Consultar uma avaliação própria nos cinco estados com representação
coerente, perguntas em lote quando aplicável e ownership invisível.

**Independent Test**: Semear avaliações próprias em pending, generated,
skipped, completed e failed, consultar cada uma e validar questions/score/level/
error_code/completed_at por estado; consultar ID inexistente e ID alheio e
confirmar respostas 404 idênticas.

### Tests for User Story 4

- [X] T041 [P] [US4] Completar testes de contrato do GET nos cinco estados, UUID inválido 422, auth 401, 404 idêntico para inexistente/alheio e allowlist pública de error_code limitada a `generation_failed` e `invalid_generation_result`; verificar ausência de exceções, códigos do provider, user_id, task id, retry e gabarito em `tests/contract/test_knowledge_assessment_http_contract.py`
- [X] T042 [P] [US4] Escrever integração de ownership, carregamento constante com `selectinload`, ordem question position 1..5/alternative position 1..4 e consulta completed sem N+1 em `tests/integration/test_knowledge_assessment_lifecycle.py`
- [X] T043 [P] [US4] Escrever testes de projeção por estado: pending/failed/skipped com questions vazias, generated/completed com 5×4, score/level somente quando permitidos e gabarito sempre ausente em `tests/unit/test_knowledge_assessment_service.py`

### Implementation for User Story 4

- [X] T044 [P] [US4] Finalizar `AssessmentDetail`, questions/alternatives públicas e validadores das invariantes de pending/generated/skipped/completed/failed em `src/sidebrain_back/schemas/knowledge_assessment_schema.py`
- [X] T045 [P] [US4] Finalizar consulta `assessment_id + user_id` com `selectinload` de perguntas/alternativas/respostas, ordenação estável e nenhuma consulta global prévia que revele ownership em `src/sidebrain_back/repositories/knowledge_assessment_repository.py`
- [X] T046 [US4] Finalizar `get_knowledge_assessment` e `GET /api/v1/assessments/{assessment_id}` para os cinco estados, com 404 uniforme e Problem Details, em `src/sidebrain_back/services/knowledge_assessment_service.py` e `src/sidebrain_back/routers/v1/knowledge_assessment_router.py`
- [X] T047 [US4] Executar e estabilizar a suíte US4 em `tests/contract/test_knowledge_assessment_http_contract.py`, `tests/integration/test_knowledge_assessment_lifecycle.py` e `tests/unit/test_knowledge_assessment_service.py`

**Checkpoint**: todas as histórias estão funcionais e cada estado possui
representação pública determinística e segura.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Atualizar documentação, validar segurança, migrations, desempenho
e gates globais depois das histórias desejadas.

- [X] T048 [P] Atualizar o contrato interno da SDB-53 documentando a janela de compatibilidade v1/v2, argumentos nomeados do v2, assessment_id canônico, payload interno com `correct_alternative_id`, retorno de cada versão e procedimento necessário para futura remoção do v1 em `specs/SDB-53-knowledge-assessment/contracts/knowledge-assessment.md`
- [X] T049 [P] Documentar o fluxo assessment→task→persistência→submissão, ownership, estados e limites de camada em `docs/architecture.md`
- [X] T050 [P] Documentar os três endpoints, polling, skip, tabela de corte e comandos do worker em `README.md`
- [X] T051 Validar upgrade→downgrade até `b2c3d4e5f6a7`→upgrade da migration e todas as constraints descritas em `migrations/versions/c3d4e5f6a7b8_cria_avaliacoes_de_conhecimento.py` e `tests/integration/test_knowledge_assessment_migration.py`
- [X] T052 Executar integralmente os cenários de geração, submissão, skip, idempotência, validação e falhas descritos em `specs/SDB-56-user-knowledge-level/quickstart.md`
- [X] T053 Revisar logs, schemas e respostas para impedir prompt, resposta bruta, credenciais, gabarito, exceções, códigos internos, user_id, task id e dados alheios; permitir subject e objective somente nas respostas autenticadas ao proprietário e impedir esses valores nos logs em `src/sidebrain_back/tasks/knowledge_assessment_task.py`, `src/sidebrain_back/schemas/knowledge_assessment_schema.py` e `tests/contract/test_knowledge_assessment_http_contract.py`
- [X] T054 Escrever um teste automatizado ponta a ponta que execute POST de criação → task em modo controlado → GET generated → POST das cinco respostas → GET completed, validando os UUIDs públicos e o nível calculado em `tests/integration/test_knowledge_assessment_lifecycle.py`
- [X] T055 Criar teste de desempenho para SC-007 com pelo menos 100 solicitações válidas, concorrência máxima de 10 e cálculo reproduzível do P95 da confirmação com assessment_id em `tests/performance/test_knowledge_assessment_performance.py`
- [X] T056 Criar teste de desempenho para SC-008 com PostgreSQL, Redis e worker Celery reais, provider determinístico, pelo menos 100 avaliações sem retry e cálculo do P95 até generated/skipped em `tests/performance/test_knowledge_assessment_performance.py`
- [X] T057 Executar `uv run ruff check .` e corrigir todos os achados nos arquivos alterados sob `src/sidebrain_back/`, `tests/` e `migrations/`
- [X] T058 Executar `uv run pytest`, executar separadamente `tests/performance/test_knowledge_assessment_performance.py` quando necessário e corrigir regressões em `tests/` até todos os gates passarem

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 — Setup**: inicia imediatamente.
- **Phase 2 — Foundational**: depende de T001 e bloqueia todas as histórias.
- **Phase 3 — US1**: depende da fundação; entrega o primeiro incremento
  utilizável.
- **Phase 4 — US2**: depende da fundação e pode ser testada com assessment
  generated semeado; o fluxo público ponta a ponta depende da US1.
- **Phase 5 — US3**: depende da US1 porque estende o mesmo POST e a mesma task.
- **Phase 6 — US4**: depende da fundação e pode ser testada com estados
  semeados; a validação integrada final usa os estados produzidos por
  US1/US2/US3.
- **Phase 7 — Polish**: depende de todas as histórias incluídas na entrega.

### User Story Dependency Graph

```text
Setup → Foundation → US1 (iniciar/gerar/polling) ──┬──→ US2 (responder/classificar)
                                                   ├──→ US3 (skip)
Foundation ────────────────────────────────────────└──→ US4 (consulta completa)

US1 + US2 + US3 + US4 → Polish
```

### Within Each User Story

- Escrever e confirmar a falha dos testes antes da implementação.
- Models/schemas/repository antes do service.
- Service antes do endpoint/task que o compõe.
- Implementação antes da estabilização da suíte focal.
- Não avançar do checkpoint com testes da história falhando.

### Parallel Opportunities

- Fundação: T002 e T003 podem ocorrer em paralelo; T004–T007 são models em
  arquivos distintos e também podem ocorrer em paralelo; T012 pode ser escrito
  enquanto os models são implementados.
- US1: T015–T019 são suites em arquivos distintos; depois, T020 e T021 podem
  ocorrer em paralelo antes de T022.
- US2: T026–T029 podem ocorrer em paralelo; T030 e T031 podem ocorrer em
  paralelo antes de T032.
- US3: T035–T037 podem ocorrer em paralelo antes de T038/T039.
- US4: T041–T043 podem ocorrer em paralelo; T044 e T045 podem ocorrer em
  paralelo antes de T046.
- Polish: T048–T050 podem ocorrer em paralelo.

---

## Parallel Example: User Story 1

```text
Em paralelo:
Task T015: testes do generator
Task T016: testes do service de criação/idempotência
Task T017: testes da task/retries
Task T018: contrato HTTP POST
Task T019: integração lifecycle

Depois dos testes:
Task T020: generator interno
Task T021: transições do repository
```

## Parallel Example: User Story 2

```text
Em paralelo:
Task T026: contrato dos schemas de respostas
Task T027: regras de correção/corte
Task T028: atomicidade e concorrência PostgreSQL
Task T029: contrato HTTP de answers

Depois dos testes:
Task T030: schemas de submissão
Task T031: persistência sob lock
```

## Parallel Example: User Story 3

```text
Em paralelo:
Task T035: validação subject/skip
Task T036: integração da task sem provider
Task T037: contrato HTTP do skip
```

## Parallel Example: User Story 4

```text
Em paralelo:
Task T041: contrato GET dos cinco estados
Task T042: ownership/carregamento PostgreSQL
Task T043: projeções do service

Depois dos testes:
Task T044: schemas de detalhe
Task T045: query autorizada com selectinload
```

---

## Implementation Strategy

### MVP First — User Story 1

1. Concluir Phase 1.
2. Concluir Phase 2 e validar a migration/fundação.
3. Concluir US1.
4. Parar e validar independentemente: POST cria o ID, a task persiste 5×4 e o
   polling retorna generated sem gabarito.
5. Demonstrar o MVP antes de iniciar classificação e skip.

### Incremental Delivery

1. Setup + Foundation → agregado persistente e seguro.
2. US1 → avaliação gerada e acompanhável.
3. US2 → avaliação corrigida e nível calculado.
4. US3 → caminho beginner sem provider.
5. US4 → consulta completa dos cinco estados.
6. Polish → documentação, segurança, migration e gates completos.

### Parallel Team Strategy

Após a fundação:

- uma pessoa pode implementar US1;
- outra pode preparar US2 com fixtures `generated`;
- outra pode preparar os contratos/testes de US4 com registros semeados;
- US3 inicia quando o POST/task da US1 estiver disponível.

## Notes

- `[P]` significa arquivos diferentes e ausência de dependência incompleta.
- Tasks com `[USn]` pertencem exclusivamente à fase daquela história.
- O result backend do Celery não é fonte de verdade; PostgreSQL é obrigatório.
- A task existente deve ser evoluída; não criar nova task ou prompt paralelo.
- Não adicionar nível global ao `User`, listagem, edição, exclusão ou mudanças
  em Track/Step/Lesson/Mission.
- Commit após cada tarefa ou grupo lógico pequeno.
