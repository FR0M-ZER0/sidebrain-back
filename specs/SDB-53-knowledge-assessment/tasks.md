# Tasks: Avaliação de Conhecimento para Trilhas

**Input**: Design documents from `/specs/SDB-53-knowledge-assessment/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Os testes abaixo são incluídos porque a feature define cenários de validação, retry e skip explícitos com critérios independentes.

**Organization**: As tarefas estão agrupadas por história de usuário para permitir implementação e teste independentes de cada incremento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo quando atua em arquivos diferentes e sem dependência de tarefa incompleta
- **[Story]**: História de usuário a que a tarefa pertence (ex.: US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar a estrutura e os pontos de integração para a feature sem alterar trilhas ou modelos persistentes.

- [X] T001 [P] Criar a estrutura inicial da feature em src/sidebrain_back/schemas/knowledge_assessment_schema.py, src/sidebrain_back/services/knowledge_assessment_service.py, src/sidebrain_back/services/knowledge_assessment_generator.py, src/sidebrain_back/tasks/knowledge_assessment_task.py e tests/unit/test_knowledge_assessment_schema.py
- [X] T002 [P] Ajustar fixtures e ambiente de teste em tests/conftest.py para permitir execução eager do Celery e mocks do provider sem expor credenciais

## Phase 2: Foundational tasks

**Purpose**: Estabelecer o contrato e regras compartilhadas que sustentam os três fluxos de avaliação.

- [X] T003 Implementar os DTOs de contexto e resultado em src/sidebrain_back/schemas/knowledge_assessment_schema.py com `AssessmentContext`, `KnowledgeAlternative`, `KnowledgeQuestion` e `KnowledgeAssessmentResult`, incluindo `extra="forbid"` e validações para `subject`, `objective`, `skip`, `status`, `level` e quantidade fixa de cinco perguntas
- [X] T004 Implementar a regra de negócio central em src/sidebrain_back/services/knowledge_assessment_service.py para decidir `skipped` vs. `generated`, normalizar `subject`/`objective`, rejeitar assunto vazio e impedir retorno parcial em qualquer falha de validação
- [X] T005 Implementar o adaptador para geração externa em src/sidebrain_back/services/knowledge_assessment_generator.py e ajustar src/sidebrain_back/core/groq_client.py para encapsular `client.chat.completions.create`, timeout, `response_format={"type": "json_object"}` e parsing seguro do payload Groq
- [X] T006 Implementar a orquestração assíncrona em src/sidebrain_back/tasks/knowledge_assessment_task.py com `bind=True`, `self.retry` para falhas transitórias, sem logs de prompt/resposta/credenciais e serialização do resultado em JSON

## Phase 3: User Story 1 - Gerar avaliação inicial de conhecimento

**Goal**: Produzir exatamente cinco perguntas estruturadas e relacionadas ao assunto e ao objetivo do usuário, sem criar trilhas.

**Independent Test**: Solicitar uma avaliação com assunto e objetivo válidos e verificar que o resultado expõe cinco perguntas estruturadas e validáveis.

- [X] T007 [US1] Criar o teste de contrato de resultado gerado em tests/contract/test_knowledge_assessment_contract.py para validar `assessment_id`, `status`, `questions` e invariantes de `generated`
- [X] T010 [P] [US1] Criar testes unitários em tests/unit/test_knowledge_assessment_schema.py para `generated` com cinco perguntas, alternativa válida e rejeição de payload incompleto
- [X] T011 [P] [US1] Criar testes unitários em tests/unit/test_knowledge_assessment_service.py para assunto inválido, objetivo opcional e rejeição de respostas parcialmente preenchidas
- [X] T008 [US1] Implementar a geração do fluxo de avaliação em src/sidebrain_back/services/knowledge_assessment_service.py para montar uma resposta de sucesso com dados do assunto/objetivo, cinco perguntas e alternativas em ordem estável
- [X] T009 [US1] Implementar o retorno final da task em src/sidebrain_back/tasks/knowledge_assessment_task.py para expor `model_dump(mode="json")` e entregar o payload pronto ao fluxo posterior

## Phase 4: User Story 2 - Iniciar sem avaliação

**Goal**: Permitir o caminho explícito de `skip=true` sem provider, sem perguntas e com nível inicial `beginner`.

**Independent Test**: Solicitar avaliação com `skip=true` e verificar que retorna `status=skipped`, `level=beginner`, `questions=[]` e sem chamada externa.

- [X] T012 [US2] Criar o teste de integração em tests/integration/test_knowledge_assessment_task.py para validar `skip=true` sem invocar o serviço externo e sem criar trilhas
- [X] T013 [US2] Implementar a ramificação de `skip` em src/sidebrain_back/services/knowledge_assessment_service.py e garantir que o assunto não seja exigido quando o usuário pede para pular
- [X] T014 [P] [US2] Validar o contrato de saída em src/sidebrain_back/schemas/knowledge_assessment_schema.py para `skipped` com `level="beginner"`, `questions=[]` e `status="skipped"`

## Phase 5: User Story 3 - Consumir um resultado confiável

**Goal**: Bloquear resultados inválidos, tratar retry de falhas transitórias e deixar a avaliação consumível sem dados parciais.

**Independent Test**: Simular respostas válidas, inválidas e indisponibilidade temporária do provider e verificar validação, retry e ausência de conteúdo parcial.

- [X] T015 [US3] Criar testes de falha e retry em tests/unit/test_knowledge_assessment_service.py e tests/integration/test_knowledge_assessment_task.py para provider indisponível, JSON inválido, resposta incompleta e erro definitivo
- [X] T016 [US3] Implementar a política de retry na task em src/sidebrain_back/tasks/knowledge_assessment_task.py para repetir apenas `APIConnectionError`, `APITimeoutError` e `RateLimitError` com limite de três tentativas e backoff controlado
- [X] T017 [US3] Implementar a rejeição de resultados não conformes em src/sidebrain_back/services/knowledge_assessment_service.py e src/sidebrain_back/schemas/knowledge_assessment_schema.py para bloquear menos/mais de cinco perguntas, identificadores vazios e alternativas inválidas
- [X] T018 [P] [US3] Revisar e alinhar o contrato publicado em specs/SDB-53-knowledge-assessment/contracts/knowledge-assessment.md para refletir `generated`, `skipped`, erros definitivos e ausência de uso de `userId` como input público

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalizar observabilidade, execução e validação final do fluxo de feature.

- [X] T019 [P] Revisar logs e mascaramento em src/sidebrain_back/core/groq_client.py e src/sidebrain_back/tasks/knowledge_assessment_task.py para garantir que nenhum prompt, resposta ou credencial seja exposto em erro ou log estruturado
- [X] T020 [P] Executar a validação focada da feature com `uv run pytest tests/unit/test_knowledge_assessment_schema.py tests/unit/test_knowledge_assessment_service.py tests/integration/test_knowledge_assessment_task.py tests/contract/test_knowledge_assessment_contract.py`
- [X] T021 [P] Executar a revisão final de qualidade com `uv run ruff check .` e `uv run pytest` para confirmar que a feature não altera trilhas, conteúdos ou regras da API existente

## Dependencies

- **Story order**: US1 → US2 → US3
- **Critical path**: T003 → T004 → T005 → T006 → T008/T013/T016 → T009/T014/T017 → T019/T020/T021
- **User Story 2** depende de T004 e T006 para o ramo de `skip`; a tarefa não precisa esperar o provider em pleno funcionamento.
- **User Story 3** depende de T005, T006 e T008 para cobrir retry, validação e rejeição de resultados inválidos.

## Parallel execution examples

- **US1**: T007, T010 e T011 podem rodar em paralelo antes da implementação do serviço.
- **US2**: T012 e T014 podem rodar em paralelo após a regra de `skip` ficar disponível.
- **US3**: T015 e T018 podem rodar em paralelo enquanto a lógica de retry e validação não conformes é implementada.
- **Polish**: T019, T020 e T021 podem ser executados em paralelo somente após todas as histórias concluídas e sem bloqueios de regressão.

## Implementation strategy

- **MVP first**: Entregar US1 como increment mínimo e verificável, com `status=generated` e cinco perguntas válidas.
- **Incremental delivery**: Depois do MVP, ativar US2 para pular sem provider e US3 para reforçar confiabilidade e retry.
- **Validation gates**: cada fase deve ser concluída com os testes específicos de sua story antes de prosseguir para a próxima.

## Summary

- **Total task count**: 21
- **Task count per user story**: US1 = 5, US2 = 3, US3 = 4
- **Parallel opportunities identified**: 8 tarefas com marcação `[P]` e 3 grupos de execução paralela por story/phase
- **Independent test criteria**:
  - US1: assunto válido + objetivo opcional + 5 perguntas estruturadas
  - US2: `skip=true` + `level=beginner` + `questions=[]` + sem provider
  - US3: payload inválido ou externa indisponível + retry controlado + retorno sem conteúdo parcial
- **Suggested MVP scope**: Somente US1 e os testes e validações obrigatórios de contrato e serviço.
- **Format validation**: Todas as tarefas seguem o checklist obrigatório com checkbox, ID sequencial, marca `[P]` quando aplicável, label de story apenas nas tarefas de user story e caminho exato do arquivo em cada item.
