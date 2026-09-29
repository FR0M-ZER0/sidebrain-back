# Implementation Plan: Nível de Conhecimento do Usuário

**Branch**: `feat/sdb-56-criar-endpoint-para-gerenciamento-do-nivel-de-conhecimento-do-usuario` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-56-user-knowledge-level/spec.md`

## Summary

Implementar um fluxo autenticado e assíncrono para iniciar, consultar e
concluir avaliações de conhecimento. O endpoint cria e persiste o
`assessment_id` canônico antes de enfileirar
`tasks.prepare_knowledge_assessment`; a task existente será evoluída para
preservar esse identificador, gerar um gabarito exclusivamente interno e
persistir cinco perguntas com suas alternativas em uma transação. A submissão
é corrigida no backend sob bloqueio da avaliação, grava as cinco escolhas e
classifica o resultado como `beginner`, `intermediate`, `advanced` ou
`pro`. O nível pertence à avaliação e ao assunto, sem alterar o `User`.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: FastAPI >= 0.141.1, Pydantic >= 2.11.0,
SQLAlchemy >= 2.0.52, asyncpg >= 0.31.0, Alembic >= 1.19.2, Celery >=
5.6.3, Redis >= 8.1.0 e Groq >= 1.7.0

**Storage**: PostgreSQL para avaliações, perguntas, alternativas, respostas e
resultado; Redis permanece somente como broker/result backend do Celery e não
é fonte de verdade do domínio

**Testing**: Pytest >= 9.1.1 com testes unitários, de contrato e de integração
contra PostgreSQL; modo eager para a integração funcional controlada da task e
uma suíte de desempenho direcionada com PostgreSQL, Redis e worker Celery reais,
sem substituir os testes de persistência e concorrência

**Target Platform**: Serviço ASGI e worker Celery em ambiente Linux/container,
com PostgreSQL e Redis

**Project Type**: Web service/API

**Performance Goals**: confirmação com `assessment_id` em até 2 segundos para
pelo menos 95% das solicitações válidas; avaliação gerada ou pulada em até 30
segundos para pelo menos 95% dos fluxos sem retry

**Constraints**: exatamente 5 perguntas e 4 alternativas por pergunta;
gabarito nunca público; assunto obrigatório inclusive no skip; no máximo 3
retries adicionais somente para conexão, timeout e rate limit; nenhuma
persistência parcial; apenas uma submissão terminal; ownership oculto por
`404`; nenhuma criação ou alteração de Track, Step, Lesson ou Mission

**Scale/Scope**: 3 endpoints autenticados, 5 estados de avaliação, 4 novas
tabelas normalizadas, 1 migration reversível e evolução do fluxo SDB-53 já
existente

### Estratégia de compatibilidade da task

`tasks.prepare_knowledge_assessment` manterá o nome registrado durante a
migração.

- Mensagens antigas continuam sendo aceitas como contrato v1.
- Chamadas da SDB-56 usam argumentos nomeados, `contract_version=2` e o
  `assessment_id` canônico.
- O resultado v1 permanece compatível durante a janela de migração.
- O fluxo v2 retorna somente `assessment_id` e `status`.
- Testes cobrem mensagens v1 já enfileiradas e chamadas v2.
- A remoção do contrato v1 exige atualização de todos os produtores, drenagem
  das filas e uma tarefa posterior explícita.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pré-design

- **I. Qualidade e Clean Code — PASS**: o desenho reaproveita a task oficial,
  define contratos internos e públicos separados e evita duplicar prompt ou
  regra de classificação.
- **II. Responsabilidade Única — PASS**: router trata HTTP; service controla
  estados, correção e transações; repository encapsula consultas/locks; models
  representam persistência; task orquestra o processamento assíncrono.
- **III. Camadas — PASS**: o fluxo permanece
  `routers -> services -> repositories -> models`; a task abre sessão própria
  e compõe service/repository fora do ciclo do FastAPI.
- **IV. Testes e Contratos — PASS**: a evolução da task possui contrato v1
  temporariamente compatível, contrato v2 explícito e testes de mensagens
  antigas e novas, além dos testes unitários, de contrato e de integração.
- **V. Simplicidade e Evolução Segura — PASS**: a task mantém o mesmo nome e usa
  uma janela de compatibilidade documentada; a remoção do contrato v1 fica fora
  desta entrega e exige migração posterior explícita.
- **Padrões técnicos — PASS**: usa `Depends`, AsyncSession, Alembic, schemas
  estritos, nomes públicos de negócio e Problem Details vigente.

### Pós-design

- **PASS**: o modelo normalizado reforça os vínculos usados na correção sem
  reutilizar entidades incompatíveis de Quiz/Answer.
- **PASS**: índice único parcial e lock de linha resolvem as duas corridas
  concretas do requisito sem adicionar infraestrutura nova.
- **PASS**: os contratos mantêm gabarito, prompt, payload bruto do provider,
  task id e detalhes internos fora das respostas.
- **PASS**: não há violação constitucional nem dúvida técnica pendente.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-56-user-knowledge-level/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── assessments.md
└── tasks.md                 # gerado posteriormente por /speckit-tasks
```

### Source Code (repository root)

```text
src/sidebrain_back/
├── core/
│   └── celery_app.py                         # registro da task existente
├── enums/
│   └── knowledge_assessment_status_enum.py
├── models/
│   ├── knowledge_assessment_model.py
│   ├── knowledge_assessment_question_model.py
│   ├── knowledge_assessment_alternative_model.py
│   ├── knowledge_assessment_answer_model.py
│   ├── user_model.py                         # relacionamento
│   └── __init__.py
├── repositories/
│   └── knowledge_assessment_repository.py
├── routers/
│   ├── router.py
│   └── v1/
│       └── knowledge_assessment_router.py
├── schemas/
│   └── knowledge_assessment_schema.py        # interno + público
├── services/
│   ├── knowledge_assessment_generator.py
│   └── knowledge_assessment_service.py
└── tasks/
    └── knowledge_assessment_task.py

migrations/
├── env.py
└── versions/
    └── <revision>_cria_avaliacoes_de_conhecimento.py

tests/
├── contract/
│   ├── test_knowledge_assessment_contract.py
│   └── test_knowledge_assessment_http_contract.py
├── integration/
│   ├── test_knowledge_assessment_lifecycle.py
│   ├── test_knowledge_assessment_migration.py
│   └── test_knowledge_assessment_task.py
├── performance/
│   └── test_knowledge_assessment_performance.py
└── unit/
    ├── test_knowledge_assessment_generator.py
    ├── test_knowledge_assessment_repository.py
    ├── test_knowledge_assessment_schema.py
    └── test_knowledge_assessment_service.py
```

**Structure Decision**: manter o projeto único e a organização por camada já
adotada. O prefixo de domínio `knowledge_assessment` será usado em todos os
arquivos, enquanto o contrato HTTP curto será `/api/v1/assessments`. A task
SDB-53 será evoluída em seu módulo atual, sem criar caminho paralelo de
geração. As quatro tabelas ficam separadas porque a correção depende de vínculos
verificáveis entre avaliação, pergunta, alternativa e escolha.

## Complexity Tracking

Nenhuma violação constitucional requer justificativa. Um teste direcionado com
PostgreSQL, Redis e worker Celery reais será usado para validar o ciclo de vida
e os critérios de desempenho; o provider será substituído por uma implementação
determinística, evitando custo e instabilidade externos. O outbox transacional
permanece fora do escopo. O plano segue o padrão já usado de persistir, fazer
commit e então publicar a task, marcando a avaliação como `failed` se a
publicação falhar.
