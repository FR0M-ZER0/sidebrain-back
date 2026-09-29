# Modelo de Dados — Avaliação de Conhecimento

## Visão geral

`KnowledgeAssessment` é a raiz do agregado. Perguntas, alternativas e
respostas escolhidas existem somente dentro de uma avaliação. O nível é
contextual ao assunto da avaliação e não é armazenado em `User`.

```text
User 1 ─── N KnowledgeAssessment
                  │
                  ├── 1 ─── 5 KnowledgeAssessmentQuestion
                  │                 │
                  │                 └── 1 ─── 4 KnowledgeAssessmentAlternative
                  │
                  └── 0 ─── 5 KnowledgeAssessmentAnswer
```

## Enum KnowledgeAssessmentStatusEnum

Valores persistidos no tipo PostgreSQL `knowledge_assessment_status`:

| Valor | Significado |
|---|---|
| `pending` | Solicitação aceita; task ainda não concluiu a preparação. |
| `generated` | Cinco perguntas completas estão prontas para resposta. |
| `skipped` | Usuário pulou; nível `beginner` definido sem perguntas. |
| `completed` | Cinco respostas corrigidas e resultado persistido. |
| `failed` | Preparação terminou definitivamente sem conteúdo utilizável. |

## KnowledgeAssessment

Tabela: `knowledge_assessment`

| Campo lógico (físico) | Tipo | Obrigatório | Regras |
|---|---|---:|---|
| `assessment_id` (`kas_id`) | UUID | sim | PK; criado pelo service HTTP e fornecido explicitamente ao model. |
| `user_id` (`kas_user_id`) | UUID | sim | FK para `user.usr_id`, `ON DELETE CASCADE`; indexado. |
| `subject` (`kas_subject`) | varchar(255) | sim | Trim; 1..255; obrigatório inclusive no skip. |
| `objective` (`kas_objective`) | text | não | Ausente é `null`; se enviado, trim e 1..1000. |
| `skip` (`kas_skip`) | boolean | sim | Default false; participa do contexto idempotente. |
| `context_fingerprint` (`kas_context_fingerprint`) | char(64) | sim | SHA-256 do JSON canônico de subject/objective/skip normalizados. |
| `status` (`kas_status`) | KnowledgeAssessmentStatusEnum | sim | Default `pending`; transições fechadas descritas abaixo. |
| `score` (`kas_score`) | smallint | não | Inteiro 0..5 somente em `completed`; `null` nos demais estados. |
| `level` (`kas_level`) | StepLevelEnum | não | Reusa o enum PostgreSQL `step_level`; presente em `skipped` e `completed`. |
| `error_code` (`kas_error_code`) | varchar(100) | não | Código interno sanitizado somente em `failed`. |
| `created_at` (`kas_created_at`) | datetime | sim | `now()` no banco. |
| `updated_at` (`kas_updated_at`) | datetime | sim | `now()`; atualizado em toda transição. |
| `completed_at` (`kas_completed_at`) | datetime | não | Preenchido em `skipped` e `completed`. |

### Índices e constraints

- Índice normal em `kas_user_id`.
- Índice único parcial
  `(kas_user_id, kas_context_fingerprint) WHERE kas_status IN ('pending', 'generated')`.
- Check `kas_score BETWEEN 0 AND 5` quando não nulo.
- Checks de estado:
  - `pending`: score, level, error_code e completed_at nulos;
  - `generated`: score, level, error_code e completed_at nulos;
  - `skipped`: skip=true, level=beginner, score/error_code nulos e
    completed_at preenchido;
  - `completed`: score e level preenchidos, error_code nulo e completed_at
    preenchido;
  - `failed`: score/level/completed_at nulos e error_code preenchido.
- Em `completed`, o par score/level deve respeitar:
  `0..1 -> beginner`, `2..3 -> intermediate`, `4 -> advanced`,
  `5 -> pro`. O service calcula e o banco protege a coerência com check.

## KnowledgeAssessmentQuestion

Tabela: `knowledge_assessment_question`

| Campo lógico (físico) | Tipo | Obrigatório | Regras |
|---|---|---:|---|
| `question_id` (`kaq_id`) | UUID | sim | PK gerada pelo backend; nunca usa o ID arbitrário do provider como chave pública. |
| `assessment_id` (`kaq_assessment_id`) | UUID | sim | FK para assessment, `ON DELETE CASCADE`. |
| `statement` (`kaq_statement`) | text | sim | Trim, não vazio. |
| `position` (`kaq_position`) | smallint | sim | 1..5. |

Constraints:

- `UNIQUE (kaq_assessment_id, kaq_position)`;
- `CHECK (kaq_position BETWEEN 1 AND 5)`;
- constraint única auxiliar em `(kaq_id, kaq_assessment_id)` para reforçar FKs
  compostas das respostas.

Exatamente cinco linhas são validadas antes da escrita e inseridas junto da
transição `pending -> generated` na mesma transação.

## KnowledgeAssessmentAlternative

Tabela: `knowledge_assessment_alternative`

| Campo lógico (físico) | Tipo | Obrigatório | Regras |
|---|---|---:|---|
| `alternative_id` (`kaa_id`) | UUID | sim | PK gerada pelo backend. |
| `question_id` (`kaa_question_id`) | UUID | sim | FK para question, `ON DELETE CASCADE`. |
| `text` (`kaa_text`) | text | sim | Trim, não vazio. |
| `position` (`kaa_position`) | smallint | sim | 1..4. |
| `is_correct` (`kaa_is_correct`) | boolean | sim | Interno; nunca pertence ao schema público. |

Constraints:

- `UNIQUE (kaa_question_id, kaa_position)`;
- `CHECK (kaa_position BETWEEN 1 AND 4)`;
- índice único parcial em `kaa_question_id WHERE kaa_is_correct = true`, que
  garante no máximo uma correta;
- constraint única auxiliar em `(kaa_id, kaa_question_id)`.

O schema interno garante pelo menos uma correta e exatamente quatro
alternativas antes da transação. Assim, validação integral + índice parcial
garantem exatamente uma correta por pergunta.

## KnowledgeAssessmentAnswer

Tabela: `knowledge_assessment_answer`

| Campo lógico (físico) | Tipo | Obrigatório | Regras |
|---|---|---:|---|
| `answer_id` (`kar_id`) | UUID | sim | PK. |
| `assessment_id` (`kar_assessment_id`) | UUID | sim | FK para assessment, `ON DELETE CASCADE`. |
| `question_id` (`kar_question_id`) | UUID | sim | FK para question. |
| `alternative_id` (`kar_alternative_id`) | UUID | sim | FK para alternative. |
| `created_at` (`kar_created_at`) | datetime | sim | Momento da submissão terminal. |

Constraints:

- `UNIQUE (kar_assessment_id, kar_question_id)`, impedindo duas escolhas para
  a mesma pergunta;
- FK composta `(kar_question_id, kar_assessment_id)` para
  `knowledge_assessment_question(kaq_id, kaq_assessment_id)`;
- FK composta `(kar_alternative_id, kar_question_id)` para
  `knowledge_assessment_alternative(kaa_id, kaa_question_id)`.

As FKs compostas reforçam no banco que a pergunta pertence à avaliação e que a
alternativa pertence à pergunta. O service ainda valida o conjunto completo
antes de qualquer insert.

## Contratos internos gerados

O provider não controla IDs persistidos nem estado de domínio. Seu payload
validado possui:

- exatamente cinco perguntas, com IDs internos distintos;
- enunciado não vazio;
- quatro alternativas com IDs distintos por pergunta;
- `correct_alternative_id` apontando para uma alternativa da própria
  pergunta.

`assessment_id`, `status`, `score` e `level` são sempre definidos pelo
backend fora do payload do provider.

## Transições de estado

```text
nova solicitação
      │
      ▼
   pending ───────────────► failed
      │                       ▲
      ├── skip=true ─────► skipped
      │
      └── geração válida ► generated ─── submissão válida ───► completed
```

- `pending -> generated`: persiste 5 questions + 20 alternatives e muda o
  estado na mesma transação.
- `pending -> skipped`: não chama provider, não cria filhos, define
  `beginner` e `completed_at`.
- `pending -> failed`: não deixa filhos utilizáveis e grava somente código
  sanitizado.
- `generated -> completed`: sob lock da raiz, persiste 5 answers, score,
  level e `completed_at` atomicamente.
- Não existem transições saindo de `skipped`, `completed` ou `failed`.

## Regras de acesso e carregamento

- Toda leitura HTTP filtra `kas_id` e `kas_user_id` na mesma consulta.
- Recurso inexistente e recurso de outro usuário resultam no mesmo `404`.
- `selectinload` carrega questions, alternatives e answers em quantidade
  constante de queries, sem N+1.
- A consulta pública só projeta `id`, `statement` e
  `alternatives[{id,text}]`; `is_correct` nunca é serializado.
- `pending`, `skipped` e `failed` retornam lista pública de perguntas
  vazia. `generated` e `completed` retornam as cinco perguntas.

## Concorrência e atomicidade

### Criação

1. Normalizar o contexto e calcular o fingerprint.
2. Procurar avaliação ativa do mesmo usuário/contexto.
3. Se ausente, inserir `pending` e fazer commit.
4. Se houver conflito do índice parcial, fazer rollback/savepoint, reler a
   avaliação vencedora e retorná-la sem nova task.
5. Somente o criador enfileira a task; falha de publicação marca o registro
   `failed` em nova transação.

### Preparação pela task

1. Validar argumentos e registro persistido, sem lock longo.
2. No skip, não construir generator.
3. Na geração, chamar o provider e validar o payload inteiro fora de transação
   longa.
4. Abrir transação curta, bloquear a avaliação por ID, revalidar `pending`,
   persistir tudo e mudar o estado.
5. Redelivery que encontra estado diferente de `pending` não altera dados.

### Submissão

1. Buscar por `assessment_id + user_id FOR UPDATE`.
2. Exigir estado `generated`.
3. Validar exatamente uma escolha para cada uma das cinco perguntas e todos os
   vínculos.
4. Calcular score e nível em memória.
5. Inserir as cinco respostas e mudar a raiz para `completed` no mesmo commit.

## Migration

A nova revisão depende do head atual `b2c3d4e5f6a7`. O upgrade cria o enum de
status, a raiz, as três tabelas filhas, checks, FKs e índices nessa ordem. O
downgrade remove respostas, alternativas, perguntas, avaliação e por fim o
enum. `step_level` é reutilizado com `create_type=False` e não é removido no
downgrade desta feature.
