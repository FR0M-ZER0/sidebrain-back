# Data Model: Geração incremental de conteúdo de Steps

## Entidades existentes Reutilizadas

### Track
- `trk_id`: UUID PK
- `trk_user_id`: UUID do proprietário
- `trk_title`: string
- `trk_description`: string | null
- `trk_created_at`, `trk_updated_at`: timestamps
- `trk_is_deleted`, `trk_deleted_at`: soft delete
- Relação: `Track -> Step[]`

### Step
- `stp_id`: UUID PK
- `stp_track_id`: UUID FK para Track
- `stp_level`: enum de nível
- `stp_title`: string
- `stp_status`: enum de status
- `stp_updated_at`: timestamp
- `stp_is_deleted`, `stp_deleted_at`: soft delete
- Relações: `Step -> Lesson[]`, `Step -> Mission[]`

### Lesson
- `lsn_id`: UUID PK
- `lsn_step_id`: UUID FK para Step
- `lsn_title`, `lsn_text`: texto da lição
- `lsn_status`: `idle`, `active` etc. conforme enum
- `lsn_position`: inteiro único por Step
- `lsn_updated_at`: timestamp
- `lsn_is_deleted`, `lsn_deleted_at`: soft delete
- Constraints: `UniqueConstraint("lsn_step_id", "lsn_position")`
- Relações: `Lesson -> Quiz[]`

### Quiz
- `qui_id`: UUID PK
- `qui_lesson_id`: UUID FK para Lesson
- `qui_question`: texto da pergunta
- `qui_updated_at`: timestamp
- `qui_is_deleted`, `qui_deleted_at`: soft delete
- Relações: `Quiz -> Answer[]` (fora do escopo da geração incremental)

### Mission
- `msn_id`: UUID PK
- `msn_step_id`: UUID FK para Step
- `msn_title`, `msn_difficulty`, `msn_xp_reward`, `msn_criteria`, `msn_criteria_value`
- `msn_updated_at`: timestamp
- `msn_is_deleted`, `msn_deleted_at`: soft delete

## Entidade de contexto de geração

### GenerationContext
Representa o payload de contexto do provedor e não é persistido como tabela.

- `track_id`: UUID
- `track_title`, `track_description`: contexto geral
- `current_step_id`, `current_step_title`, `current_step_level`
- `previous_steps`: lista ordenada com títulos, status e conteúdo já existente
- `active_lessons_total`: int
- `active_lessons_completed`: int
- `completion_ratio`: float ou percentual
- `next_step_id`: UUID opcional
- `generation_constraints`: regras internas do produto (nenhuma Answer, Feedback, LessonFile, MissionProgress)

## Regras de validação

- A geração só dispara quando `completion_ratio >= 0.80`.
- O cálculo considera apenas Lessons ativas e não excluídas.
- O próximo Step deve pertencer à mesma Track, estar ativo e sem conteúdo gerado elegível.
- O conteúdo gerado não pode definir `id`, `track_id`, `step_id`, `lesson_id`, `mission_id`, `created_at`, `updated_at`, `is_deleted` ou estados de persistência.
- `position` das Lessons deve ser único no Step e obedecer à ordenação gerada.
- Qualquer falha na persistência de Lessons, Quizzes ou Missions deve causar rollback do lote inteiro.

## Relacionamentos e transições

- `Track` possui muitos `Step`s.
- `Step` possui muitas `Lesson`s e `Mission`s.
- `Lesson` possui muitos `Quiz`s.
- O conteúdo gerado é aditivo; não cria entidades fora do escopo.
- O estado da geração é observável via task logs e falhas de execução; não exige novos campos na tabela de Step.

## Observações de implementação

- O modelo de domínio já existe; esta feature não cria novos campos de negócio nem altera o contrato HTTP público.
- A lógica de geração deverá ser encapsulada em service/task, reutilizando o fluxo assíncrono do projeto e mantendo os repositories de persistência no mesmo padrão das outras features.
