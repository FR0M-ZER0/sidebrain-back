# Modelo de dados

## Badge

Entidade global do catálogo persistida na tabela `badge`.

| Campo público | Campo persistido | Tipo | Regras |
|---|---|---|---|
| `id` | `bdg_id` | UUID | Gerado pelo banco; nunca aceito no request |
| `name` | `bdg_name` | string | `strip()`, 1 a 255 caracteres; único entre ativos sem diferenciar maiúsculas/minúsculas |
| `description` | `bdg_description` | string ou nulo | Opcional; nulo permitido; significado preservado |
| `rarity` | `bdg_rarity` | `BadgeRarityEnum` | `common`, `rare`, `epic` ou `legendary` |
| `criteria` | `bdg_criteria` | `BadgeCriteriaEnum` | `xp_gained`, `tracks_completed`, `lessons_completed`, `right_answers`, `day_streak`, `tracks_created` ou `missions_completed` |
| `criteria_value` | `bdg_criteria_value` | inteiro | Maior que zero |
| `updated_at` | `bdg_updated_at` | datetime | Gerado/atualizado pelo sistema; não aceito no request |

Os campos `bdg_is_deleted` e `bdg_deleted_at` são internos. Badges com
`bdg_is_deleted = true` não participam de listagem, detalhe ou composição.

## BadgeProgress

Registro existente de progresso do usuário em um badge, carregado somente como
filho do Badge nesta feature.

| Campo público | Campo persistido | Tipo | Regras |
|---|---|---|---|
| `id` | `bpg_id` | UUID | Exposto como identificador do progresso |
| `status` | `bpg_status` | `BadgeProgressStatusEnum` | `idle`, `in_progress` ou `done` |
| `updated_at` | `bpg_updated_at` | datetime | Atualização do progresso |

`bpg_user_id` e `bpg_badge_id` não são publicados. A relação é única por
usuário/badge no banco, mas a seleção da resposta deve filtrar pelo usuário
autenticado. Badge sem registro correspondente retorna `progress: []`.

## Relações

- `Badge 1:N BadgeProgress` por `badge_progress.bpg_badge_id`.
- `User 1:N BadgeProgress` por `badge_progress.bpg_user_id`.
- Badge é recurso raiz e não possui ownership; qualquer usuário autenticado pode operar.
- A exclusão lógica de Badge preserva seus `BadgeProgress` e não aciona exclusão física em cascata.

## Operações e estados

1. **Criar**: valida request, confirma ausência de conflito ativo, persiste Badge ativo e retorna progresso vazio.
2. **Ativo**: participa de listagem, detalhe e atualização.
3. **Atualizar**: exige ao menos um campo editável; campos omitidos permanecem inalterados.
4. **Removido**: grava `bdg_is_deleted=true` e `bdg_deleted_at`; é estado terminal nesta feature e responde `404` para consultas, atualização e nova remoção.

## Invariantes

- Nenhum request controla identificadores, timestamps, flags de exclusão ou relacionamentos.
- Nome persistido é sempre normalizado nas extremidades.
- Conflito de nome é avaliado apenas contra badges ativos e sem distinção de caixa.
- Falha de validação, inexistência ou conflito ocorre antes do commit; o service faz rollback em erros de persistência.
