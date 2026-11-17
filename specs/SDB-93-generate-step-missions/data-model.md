# Data Model: Geração de Missões por IA

## MissionGenerationRequest

Representa uma solicitação de geração de missões para um Step e seu estado consultável. É registro operacional do domínio de geração, separado da entidade `Mission`.

| Campo | Tipo conceitual | Obrigatório | Regras |
|---|---|---:|---|
| `id` | UUID | Sim | Identificador da solicitação. |
| `task_id` | string | Sim | ID pré-atribuído da task; único e usado como identificador público da consulta. |
| `step_id` | UUID | Sim | Step ativo alvo; chave estrangeira. |
| `user_id` | UUID | Sim | Usuário proprietário no momento da solicitação; usado para autorização. |
| `status` | enum | Sim | `pending`, `running`, `succeeded` ou `failed`. |
| `error_code` | string curta ou nulo | Não | Código estável, sem prompt, resposta ou detalhe sensível. |
| `created_at` | timestamp | Sim | Instante da criação do pedido. |
| `started_at` | timestamp ou nulo | Não | Instante em que o worker inicia o processamento. |
| `finished_at` | timestamp ou nulo | Não | Instante de conclusão ou falha. |

### Constraints e índices

- `task_id` é único.
- `step_id` e `user_id` referenciam entidades existentes; a consulta confere o proprietário do registro e Step ativo.
- A criação concorrente de pedidos para o mesmo Step é serializada pelo bloqueio curto da linha do Step; se já existir pedido `pending`/`running`, retornar esse registro ao proprietário em vez de criar outro.
- Pedidos em estado terminal não bloqueiam nova solicitação quando o Step continua sem missões.
- A migração deve seguir o padrão vigente de timestamps, nomes de colunas e chaves estrangeiras nas models do projeto.

### Transições

```text
pending ──worker inicia──> running ──lote persistido──> succeeded
    │                           └──falha terminal──> failed
    └──falha ao publicar──> failed
```

- `RETRY` interno do Celery permanece publicamente `running`.
- A transição a `succeeded` ocorre na mesma transação que grava todas as missões.
- Falha de validação, parsing ou persistência reverte o lote; em uma transação separada, a solicitação passa a `failed` com `error_code`.
- Solicitação ignorada porque o Step já tem missões não cria registro de geração ativo nem missão.

## Mission

Entidade de negócio existente, pertencente a exatamente um `Step`. Nenhuma coluna de `Mission` deve ser adicionada por esta feature.

| Campo de geração | Regra |
|---|---|
| `title` | Texto aparado, entre 1 e 255 caracteres. |
| `difficulty` | Um de `easy`, `medium`, `hard`, `very_hard`. |
| `xp_reward` | Inteiro estritamente maior que zero. |
| `criteria` | Um de `number_of_lessons_completed`, `get_all_answer_right_in_a_lesson`, `complete_a_step`, `complete_a_track`, `number_of_steps_completed`, `get_all_answers_right`. |
| `criteria_value` | Inteiro estritamente maior que zero. |

O Step pai é fornecido pelo servidor, nunca pela IA. A missão começa ativa e sem `MissionProgress`, `Answer`, `Feedback` ou `LessonFile`. Campos adicionais na saída são rejeitados. Na geração sob demanda, a resposta deve conter exatamente o número solicitado por `count`; lista vazia, insuficiente ou maior que o pedido invalida todo o lote.

## Entidades contextuais (leitura)

- **User**: proprietário da solicitação e da Trilha associada.
- **Track**: fornece título e descrição para contexto pedagógico; deve pertencer ao usuário autenticado.
- **Step**: alvo da geração; fornece título e nível. Steps anteriores contribuem títulos e níveis para progressão.
- **Mission existentes**: usadas apenas para idempotência e contexto; missões ativas impedem nova geração sob demanda.
- **Task Celery**: execução assíncrona correlacionada por `task_id`; não é fonte de autorização nem de estado público.
