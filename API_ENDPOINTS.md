# Endpoints da API SideBrain

Catálogo dos endpoints HTTP registrados pela aplicação. Os caminhos abaixo já
incluem o prefixo comum `/api`. A API é versionada em `/v1`.

## Convenções gerais

- Salvo indicação contrária, os endpoints exigem autenticação Bearer:
  `Authorization: Bearer <accessToken>`.
- Corpos e respostas usam JSON (`Content-Type: application/json`), exceto
  respostas `204 No Content` e o stream de eventos da geração.
- Identificadores `{*_id}` são UUIDs.
- Listagens paginadas aceitam `page` (padrão `1`, mínimo `1`) e `page_size`
  (padrão `20`, entre `1` e `100`). A resposta contém `data`, `page`,
  `page_size`, `total_items` e `total_pages`.
- Erros de domínio são retornados no formato Problem Details. Erros de validação
  de request retornam `422`.

## Health

| Método e caminho | Autenticação | Request | Resposta |
|---|---|---|---|
| `GET /api/v1/health/` | Não | Sem corpo. | `200`: `{ status: "ok", datetime, version }`. |

## Autenticação

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/auth/register` | `{ name, email, password }`. Nome: 1–255 caracteres; senha: mínimo 8; e-mail válido. | `201`: `{ accessToken, tokenType: "Bearer", user: { id, name, email } }`. `409` se e-mail já estiver cadastrado. |
| `POST /api/v1/auth/login` | `{ email, password }`. | `200`: mesmo formato do cadastro. `401` para credenciais inválidas; `429` se exceder o limite de tentativas; `503` se o serviço de rate limit estiver indisponível. |

## Usuários

Todos os endpoints desta seção exigem Bearer token e operam sobre o usuário
autenticado (`/me`).

| Método e caminho | Request | Resposta |
|---|---|---|
| `GET /api/v1/users/me` | Sem corpo. | `200`: `{ id, name, email }`. |
| `PUT /api/v1/users/me` | JSON com `name`, `email` ou ambos. Pelo menos um campo deve ser enviado; valores nulos não são aceitos. | `200`: `{ id, name, email }`. `409` se o e-mail já estiver em uso. |
| `PUT /api/v1/users/me/password` | `{ currentPassword, newPassword }`; nova senha com pelo menos 8 caracteres. | `204` sem corpo. `401` se a senha atual estiver incorreta; também pode retornar `429` ou `503` pelo rate limit. |
| `DELETE /api/v1/users/me` | Sem corpo. | `204` sem corpo. |

## Trilhas

Todos os endpoints de trilhas exigem Bearer token. `TrackResponse` inclui
`id`, `icon`, `title`, `description`, `created_at`, `updated_at` e `steps`.

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/tracks` | Contexto: `goal`, `topic`; opcionais `knowledge_level`, `assessment_answers` (lista de `{ question, answer, rate }`), `assessment_id`, `request_id` e `title`. Se não enviar `title`, `goal` e `topic` são obrigatórios. | `202`: `{ status: "pending", request_id }`; geração assíncrona. |
| `GET /api/v1/tracks` | Query: `page`, `page_size`. | `200`: página de trilhas do usuário. |
| `GET /api/v1/tracks/{track_id}` | UUID da trilha. | `200`: trilha com etapas e conteúdo carregado. |
| `PATCH /api/v1/tracks/{track_id}` | Pelo menos um dos campos `title` ou `description`. | `200`: trilha atualizada. |
| `DELETE /api/v1/tracks/{track_id}` | UUID da trilha. | `204` sem corpo. |
| `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next` | UUIDs da trilha e da etapa; sem corpo. | `202`: `{ status: "accepted", step_id, task_id }` quando agenda a preparação; `200`: `{ status: "skipped", reason }` quando não há próxima etapa elegível. |
| `GET /api/v1/tracks/generations/{request_id}` | UUID da solicitação. | `200`: `{ request_id, status, track_id, error_code }`; `track_id` e `error_code` podem ser nulos. |
| `GET /api/v1/tracks/generations/{request_id}/events` | UUID da solicitação. | `200` como `text/event-stream`. Emite evento `generation` com o estado de geração e comentários periódicos de keep-alive até sucesso, falha ou desconexão. |

O estado de geração pode ser `pending`, `succeeded` ou `failed`.
`GET` de status e stream só mostram solicitações pertencentes ao usuário atual.

## Etapas (Steps)

Todos os endpoints exigem Bearer token. O corpo de criação/atualização contém
`level` (`beginner`, `intermediate`, `advanced` ou `pro`) e `title` (1–255
caracteres). `StepResponse` contém `id`, `level`, `title`, `status`,
`updated_at`, `lessons` e `missions`.

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/tracks/{track_id}/steps` | `{ level, title }`. | `201`: etapa criada. |
| `GET /api/v1/tracks/{track_id}/steps` | Query: `page`, `page_size`. | `200`: página de etapas. |
| `GET /api/v1/tracks/{track_id}/steps/{step_id}` | UUIDs da trilha e da etapa. | `200`: etapa. |
| `PUT /api/v1/tracks/{track_id}/steps/{step_id}` | `{ level, title }` (ambos obrigatórios). | `200`: etapa atualizada. |
| `DELETE /api/v1/tracks/{track_id}/steps/{step_id}` | UUIDs da trilha e da etapa. | `204` sem corpo. |

## Lições

Todos os endpoints exigem Bearer token. Campos de lição: `title`, `text` e
`position` (inteiro >= 1). Para atualização, `status` também é obrigatório
(`idle`, `in_progress` ou `done`). A resposta contém `id`, `title`, `text`,
`status`, `position`, `updated_at`, `feedbacks`, `files` e `quizzes`.

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/steps/{step_id}/lessons` | `{ title, text, position }`. | `201`: lição criada. |
| `GET /api/v1/steps/{step_id}/lessons` | Query: `page`, `page_size`. | `200`: página de lições. |
| `GET /api/v1/lessons/{lesson_id}` | UUID da lição. | `200`: lição. |
| `PUT /api/v1/lessons/{lesson_id}` | `{ title, text, position, status }`. | `200`: lição atualizada. |
| `DELETE /api/v1/lessons/{lesson_id}` | UUID da lição. | `204` sem corpo (exclusão lógica). |

## Quizzes e respostas

Todos os endpoints exigem Bearer token. Perguntas aceitam texto não vazio de
até 1.000 caracteres. `QuizResponse` contém `id`, `lesson_id`, `question` e
`answers`; uma resposta contém `id`, `user_id`, `text` e `rate`.

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/lessons/{lesson_id}/quizzes` | `{ question }`. | `201`: quiz criado. |
| `GET /api/v1/lessons/{lesson_id}/quizzes` | Query: `page`, `page_size`. | `200`: página de quizzes. |
| `GET /api/v1/quizzes/{quiz_id}` | UUID do quiz. | `200`: quiz e respostas. |
| `POST /api/v1/quizzes/{quiz_id}/answers` | `{ text }` (1–10.000 caracteres). | `201`: resposta criada, incluindo `rate` (`good`, `perfect`, `wrong` ou `almost_got_it`). |
| `PUT /api/v1/quizzes/{quiz_id}` | `{ question }`. | `200`: quiz atualizado. |
| `DELETE /api/v1/quizzes/{quiz_id}` | UUID do quiz. | `204` sem corpo (exclusão lógica). |

## Missões

Todos os endpoints exigem Bearer token. Criação requer `title`, `difficulty`,
`xpReward`, `criteria` e `criteriaValue`. Dificuldades: `easy`, `medium`,
`hard`, `very_hard`. Critérios: `number_of_lessons_completed`,
`get_all_answer_right_in_a_lesson`, `complete_a_step`, `complete_a_track`,
`number_of_steps_completed` ou `get_all_answers_right`. Resposta: missão,
incluindo progresso quando disponível.

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/steps/{step_id}/missions` | `{ title, difficulty, xpReward, criteria, criteriaValue }`. `xpReward` >= 0 e `criteriaValue` > 0. | `201`: missão criada. |
| `GET /api/v1/steps/{step_id}/missions` | Query: `page`, `page_size`. | `200`: página de missões. |
| `GET /api/v1/missions/{mission_id}` | UUID da missão. | `200`: missão. |
| `PUT /api/v1/missions/{mission_id}` | Um ou mais campos editáveis da criação. | `200`: missão atualizada. |
| `DELETE /api/v1/missions/{mission_id}` | UUID da missão. | `204` sem corpo (exclusão lógica). |

## Feedbacks

Todos os endpoints exigem Bearer token. O campo `text` deve ser não vazio.
Resposta: `{ id, lesson_id, author_id, text, created_at, updated_at }`.

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/lessons/{lesson_id}/feedbacks` | `{ text }`. | `201`: feedback criado. |
| `GET /api/v1/lessons/{lesson_id}/feedbacks` | Query: `page`, `page_size`. | `200`: página de feedbacks. |
| `GET /api/v1/feedbacks/{feedback_id}` | UUID do feedback. | `200`: feedback. |
| `PATCH /api/v1/feedbacks/{feedback_id}` | `{ text }`. | `200`: feedback atualizado (somente o autor pode alterá-lo). |
| `DELETE /api/v1/feedbacks/{feedback_id}` | UUID do feedback. | `204` sem corpo. |

## Badges

Todos os endpoints exigem Bearer token. Criação requer `name`, `rarity`,
`criteria` e `criteria_value`; `description` é opcional. Raridades: `common`,
`rare`, `epic`, `legendary`. Critérios: `xp_gained`, `tracks_completed`,
`lessons_completed`, `right_answers`, `day_streak`, `tracks_created` ou
`missions_completed`. A resposta inclui `id`, dados do badge, `updated_at` e
progresso do usuário.

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/badges` | `{ name, description?, rarity, criteria, criteria_value }`, com `criteria_value` > 0. | `201`: badge criado. |
| `GET /api/v1/badges` | Query: `page`, `page_size`. | `200`: página de badges. |
| `GET /api/v1/badges/{badge_id}` | UUID do badge. | `200`: badge. |
| `PATCH /api/v1/badges/{badge_id}` | Um ou mais campos editáveis; `name`, se informado, não pode ser nulo. | `200`: badge atualizado. |
| `DELETE /api/v1/badges/{badge_id}` | UUID do badge. | `204` sem corpo. |

## Avaliações de conhecimento

Todos os endpoints exigem Bearer token. Avaliações podem estar nos estados
`pending`, `generated`, `skipped`, `completed` ou `failed`.

| Método e caminho | Request | Resposta |
|---|---|---|
| `POST /api/v1/assessments` | `{ subject, objective?, skip? }`; `subject` obrigatório (até 255 caracteres), `objective` opcional (até 1.000), `skip` padrão `false`. | `202` com `{ assessment_id, status }` normalmente; `200` quando a avaliação existente está no estado `generated`. Inclui header `Location: /api/v1/assessments/{assessment_id}`. |
| `GET /api/v1/assessments/{assessment_id}` | UUID da avaliação. | `200`: detalhe com assunto, objetivo, estado, perguntas/alternativas quando disponíveis, resultado e timestamps. |
| `POST /api/v1/assessments/{assessment_id}/answers` | `{ answers: [{ question_id, alternative_id }, ...] }`; exatamente cinco respostas, sem repetir `question_id`. | `200`: detalhe atualizado com resultado (`score`, `level`, `completed_at`). |

## Ranking

Todos os endpoints exigem Bearer token. Cada entrada contém posição, usuário,
nome, XP e missões concluídas.

| Método e caminho | Request | Resposta |
|---|---|---|
| `GET /api/v1/rankings` | Query: `page`, `page_size`. | `200`: página `{ data, page, page_size, total_items, total_pages }`; cada item tem `{ position, userId, name, xp, missionsCompleted }`. |
| `GET /api/v1/rankings/me` | Sem corpo. | `200`: entrada do usuário atual. `404` se o usuário não estiver disponível no ranking. |
