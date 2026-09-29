# Data Model: Gerenciamento de Lições

## Lesson

Entidade ORM existente em `src/sidebrain_back/models/lesson_model.py`, tabela
`lesson`.

| Campo lógico | Campo físico | Tipo | Regra |
|---|---|---|---|
| `id` | `lsn_id` | UUID | PK gerada pelo banco; somente leitura |
| `step_id` | `lsn_step_id` | UUID | FK obrigatória para Step; derivada da URL e imutável |
| `title` | `lsn_title` | string(255) | Obrigatório; trim; 1–255 caracteres |
| `text` | `lsn_text` | text | Obrigatório; trim; ao menos 1 caractere |
| `status` | `lsn_status` | `LessonStatusEnum` | `idle`, `in_progress` ou `done`; criação sempre `idle` |
| `position` | `lsn_position` | integer | Obrigatório; >= 1 na aplicação; único por Step |
| `updated_at` | `lsn_updated_at` | datetime | Somente leitura; UTC gravado sem timezone pelo padrão atual |
| `is_deleted` | `lsn_is_deleted` | boolean | Controle interno; default `false` |
| `deleted_at` | `lsn_deleted_at` | datetime nullable | Controle interno; preenchido no soft delete |

### Integridade

- `UNIQUE (lsn_step_id, lsn_position)` abrange todas as linhas, inclusive as
  removidas logicamente. Assim, a posição continua reservada após soft delete.
- A mesma posição pode existir em Steps diferentes.
- A aplicação valida `position >= 1`, texto e título. O schema atual do banco
  não possui `CHECK` para essas três regras.
- A consulta preventiva permite erro `409` amigável, mas a constraint é a
  garantia final quando existem transações concorrentes.
- Não há alteração de schema nem migration prevista.

## Relacionamentos e visibilidade

```text
User 1 ── N Track 1 ── N Step 1 ── N Lesson
                                      ├── N Feedback
                                      ├── N LessonFile
                                      └── N Quiz 1 ── N Answer
```

| Relação | Regra de leitura |
|---|---|
| `Track -> Step -> Lesson` | Track, Step e Lesson devem estar ativos; Track deve pertencer ao usuário autenticado |
| `Lesson -> Feedback` | incluir somente `fbk_is_deleted=false` |
| `Lesson -> LessonFile` | incluir somente `lsf_is_deleted=false` |
| `Lesson -> Quiz` | incluir somente `qui_is_deleted=false` |
| `Quiz -> Answer` | incluir todas as Answers associadas; Answer não possui soft delete |

As coleções são eager-loaded em lote. A paginação é aplicada somente a Lesson,
nunca às coleções filhas de cada item. A listagem ordena Lessons por
`lsn_position ASC`; a posição única torna a ordem não ambígua. Quizzes e
Answers preservam as ordens já definidas nos relacionamentos ORM; esta feature
não cria uma nova garantia de ordem para Feedbacks ou LessonFiles.

## Schemas de entrada

### LessonCreateRequest

| Campo | Tipo | Obrigatório | Validação |
|---|---|---|---|
| `title` | string | sim | trim antes da validação; 1–255 |
| `text` | string | sim | trim antes da validação; não vazio |
| `position` | integer | sim | >= 1 e disponível no Step |

O status é sempre `idle`. `step_id`, IDs, timestamps, flags de exclusão e campos
desconhecidos são rejeitados.

### LessonUpdateRequest

| Campo | Tipo | Obrigatório | Validação |
|---|---|---|---|
| `title` | string | sim | mesma regra da criação |
| `text` | string | sim | mesma regra da criação |
| `status` | `LessonStatusEnum` | sim | `idle`, `in_progress` ou `done` |
| `position` | integer | sim | >= 1; pode manter a posição atual; não reordena outras Lessons |

O `PUT` é completo. `step_id` e campos internos não são editáveis.

## Schema de saída direto

`LessonResponse` expõe:

- `id`, `title`, `text`, `status`, `position`, `updated_at`;
- `feedbacks: LessonFeedbackResponse[]` com `id`, `user_id`, `text`,
  `created_at`, `updated_at`;
- `files: LessonFileResponse[]` com `id`, `path`, `file_type`, `updated_at`;
- `quizzes: LessonQuizResponse[]` com `id`, `question`, `updated_at` e
  `answers`;
- cada `LessonAnswerResponse` contém `id`, `user_id`, `text`, `rate`,
  `created_at`, `updated_at`.

Todos os responses usam `ConfigDict(from_attributes=True,
populate_by_name=True)`, aliases de validação para os campos físicos e
`default_factory=list` para coleções. Os schemas próprios da hierarquia de
Lesson adaptam os mesmos dados públicos sem renomear os responses históricos
de Track/Step nesta versão.

## Estados e transições

| Evento | Estado anterior | Estado posterior | Efeito adicional |
|---|---|---|---|
| Criar | inexistente | `idle` | associa ao Step da URL e cria filhos vazios |
| Atualizar | `idle`, `in_progress` ou `done` | qualquer um dos três | substitui título, texto e posição; atualiza `updated_at` |
| Remover | ativo | soft-deleted | define `is_deleted=true`, `deleted_at` e `updated_at`; filhos não mudam |
| Operar após remoção | soft-deleted | sem transição | retorna `404` |

Uma Lesson sob Step ou Track removido também é invisível, mesmo que sua própria
flag permaneça ativa.
