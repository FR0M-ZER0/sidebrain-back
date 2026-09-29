# Data Model: Gerenciamento de Etapas

## Step

Entidade ORM já existente em `src/sidebrain_back/models/step_model.py`, tabela `step`.

| Campo lógico | Campo físico | Tipo | Regra |
|---|---|---|---|
| `id` | `stp_id` | UUID | Chave primária gerada pelo banco; somente leitura |
| `track_id` | `stp_track_id` | UUID | FK obrigatória para `Track`; derivada da URL e não exposta no request |
| `level` | `stp_level` | `StepLevelEnum` | Obrigatório; `beginner`, `intermediate`, `advanced` ou `pro` |
| `title` | `stp_title` | string | Obrigatório, 1 a 255 caracteres após trim |
| `status` | `stp_status` | `StepStatusEnum` | Gerenciado pelo sistema; `idle`, `in_progress` ou `done` |
| `updated_at` | `stp_updated_at` | datetime | Auditoria; somente leitura |
| `is_deleted` | `stp_is_deleted` | boolean | Controle de soft delete; interno |
| `deleted_at` | `stp_deleted_at` | datetime nullable | Preenchido na exclusão lógica; interno |

## Relacionamentos de leitura

- `Track 1 -> N Step`: somente Steps do Track ativo e pertencente ao usuário atual.
- `Step 1 -> N Lesson`: somente Lessons não excluídas.
- `Lesson 1 -> N Quiz`: somente Quizzes não excluídos; cada Quiz carrega `Answer[]`.
- `Lesson 1 -> N Feedback`: somente Feedbacks não excluídos.
- `Lesson 1 -> N LessonFile`: somente arquivos não excluídos.
- `Step 1 -> N Mission`: somente Missions não excluídas.
- `Mission 1 -> N MissionProgress`: somente progressos associados ao usuário autenticado.

A leitura deve omitir todos os filhos com soft delete, sem marcar ou apagar os
filhos quando o Step for excluído. A composição deve ser carregada em lote com
`selectinload` e os resultados deduplicados quando necessário.

## Schemas públicos

### Entrada

- `StepCreate`: `level`, `title`, ambos obrigatórios; `extra="forbid"`.
- `StepUpdate`: `level`, `title`, ambos obrigatórios; `extra="forbid"`.
- Nenhum schema de entrada aceita `id`, `track_id`, `status`, timestamps ou flags de exclusão.

### Saída

`StepResponse` expõe somente os campos públicos `id`, `level`, `title`, `status`,
`updated_at`, `lessons` e `missions`. Os objetos filhos seguem os schemas
públicos já usados pela árvore de Track: `LessonResponse`, `QuizResponse`,
`AnswerResponse`, `FeedbackResponse`, `LessonFileResponse`, `MissionResponse` e
`MissionProgressResponse`.

## Estados e transições

- Criação: `is_deleted=false`, status inicial `idle` conforme o modelo.
- Atualização: somente `level` e `title`; status e auditoria permanecem sob controle do sistema.
- Exclusão: `is_deleted=false -> true`, `deleted_at` recebe o instante da operação e o registro físico permanece.
- Step excluído é terminal para as operações normais desta feature: GET/PUT/DELETE retornam 404.
