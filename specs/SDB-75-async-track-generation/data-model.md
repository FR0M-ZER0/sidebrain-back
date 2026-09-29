# Data Model: SDB-75

## GenerationRequest

Registro de controle da solicitação assíncrona, separado da entidade Track.

| Campo lógico | Tipo | Regras |
|---|---|---|
| `request_id` | UUID | obrigatório, único, chave de idempotência |
| `user_id` | UUID | obrigatório, ownership do pedido |
| `context_fingerprint` | string | obrigatório, hash do contexto validado |
| `goal` | texto | obrigatório; conteúdo validado pelo schema |
| `topic` | texto | obrigatório; conteúdo validado pelo schema |
| `knowledge_level` | enum opcional | mesmo domínio de Step |
| `assessment_answers` | JSON opcional | respostas validadas pelo schema |
| `status` | enum | `pending`, `succeeded` ou `failed`; default `pending` |
| `track_id` | UUID opcional | preenchido em sucesso; referência à Track criada |
| `error_code` | string opcional | preenchido em falha; não armazena segredo ou stack trace |
| `created_at` / `updated_at` | datetime | auditoria e atualização de estado |

### Restrições

- `request_id` deve ter índice/constraint único.
- A combinação de `request_id` e fingerprint deve ser comparada antes de publicar uma nova task.
- Transições permitidas: `pending -> succeeded`, `pending -> failed`; repetição de pedido concluído ou falho não recria a solicitação.
- `track_id` é obrigatório quando `status = succeeded` e nulo nos demais estados.
- `error_code` é obrigatório quando `status = failed` e nulo em `pending`/`succeeded`.
- A migração deve ser reversível e acompanhar testes de persistência.

## Track

Entidade de percurso pertencente ao usuário. Continua usando `trk_generation_request_id` para compatibilidade com a idempotência de geração existente, mas o vínculo lógico com o pedido deve ser preenchido junto com `GenerationRequest.track_id` em sucesso.

- Uma Track pode ter vários Steps ordenados.
- Uma Track gerada deve ter todas as etapas previstas.
- Apenas o Step de posição 1 recebe Lessons/Mission na geração inicial.
- Consultas públicas filtram `user_id` e exclusão lógica.

## Step e conteúdo

- `Step` pertence a uma Track e possui posição, nível, título, status e exclusão lógica.
- `Lesson` pertence ao Step; `Quiz` pertence à Lesson; `Mission` pertence ao Step.
- O endpoint manual valida a cadeia ativa `Track -> Step` e, quando a regra de progresso exigir conteúdo, a consulta de progresso considera Lessons ativas.
- O conteúdo do próximo Step é criado pela task existente em transação atômica, com lock e checagem de conteúdo ativo.

## Fluxos de estado

```text
GenerationRequest: pending --geração bem-sucedida--> succeeded
                  pending --falha terminal/retry esgotado--> failed

Prepare-next: authorized + eligible --delay()--> accepted
              authorized + no eligible next step --> skipped
              missing/deleted/not owned --> 404 Problem Details
```

## Validação de entrada

`LearningContext` mantém `extra="forbid"`, texto não vazio, enums de domínio e respostas de avaliação válidas. `request_id` é opcional na entrada pública; a API gera UUID quando ausente e o schema interno `GenerationInput` recebe o valor final junto do `user_id`.
