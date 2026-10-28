# Modelo de dados — SDB-90

Nenhuma tabela nova e nenhuma coluna nova serão criadas. O ranking é um modelo de leitura derivado sobre as entidades existentes `User`, `Mission` e `MissionProgress`.

## Entidades de Origem (Somente Leitura)

### User (`models/user_model.py` — tabela `user`)

| Campo persistido | Tipo | Uso no Ranking |
| --- | --- | --- |
| `usr_id` | `UUID` | Identificador projetado como `userId` e 2º critério de desempate (`ASC`) |
| `usr_name` | `String(255)` | Nome projetado como `name` |
| `usr_created_at` | `DateTime` | 1º critério de desempate em empates de XP (`ASC`) |
| `usr_is_deleted` | `Boolean` | Filtro obrigatório `usr_is_deleted.is_(False)` |
| `usr_email`, `usr_password_hash`, `usr_updated_at`, `usr_deleted_at` | diversos | **Nunca expostos** no contrato de ranking |

### Mission (`models/mission_model.py` — tabela `mission`)

| Campo persistido | Tipo | Uso no Ranking |
| --- | --- | --- |
| `msn_id` | `UUID` | Contabilizado em `missionsCompleted` quando concluída e ativa |
| `msn_xp_reward` | `Integer` | Somado em `xp` quando o progresso do usuário está `done` e a missão está ativa |
| `msn_is_deleted` | `Boolean` | Filtro obrigatório `msn_is_deleted.is_(False)` para contabilização |
| Demais campos (`msn_*`) | diversos | **Nunca expostos** no contrato de ranking |

### MissionProgress (`models/mission_progress_model.py` — tabela `mission_progress`)

| Campo persistido | Tipo | Uso no Ranking |
| --- | --- | --- |
| `mpg_user_id` | `UUID` | Vínculo com `User.usr_id` |
| `mpg_mission_id` | `UUID` | Vínculo com `Mission.msn_id` |
| `mpg_status` | `MissionProgressStatusEnum` | Condição de contabilização: `mpg_status == 'done'` (`idle` e `in_progress` são ignorados) |
| `mpg_score`, `mpg_finished_in`, `mpg_updated_at` | diversos | Ignorados no cálculo de XP e **nunca expostos** |

## Projeção Derivada e Regras de Negócio

```text
User (usr_is_deleted = false)
  └── LEFT JOIN MissionProgress (mpg_user_id = usr_id AND mpg_status = 'done')
        └── LEFT JOIN Mission (msn_id = mpg_mission_id AND msn_is_deleted = false)
```

- **Fórmula de XP**: `xp = COALESCE(SUM(Mission.msn_xp_reward), 0)` (inteiro `>= 0`).
- **Fórmula de Missões Concluídas**: `missionsCompleted = COUNT(Mission.msn_id)` (inteiro `>= 0`).
- **Independência de hierarquia superior**: O cálculo considera apenas `usr_is_deleted = false`, `msn_is_deleted = false` e `mpg_status = 'done'`, independentemente do estado de exclusão lógica de `Step` ou `Track`.
- **Ordenação e Posição**:
  - `ORDER BY xp DESC, usr_created_at ASC, usr_id ASC`
  - `position`: inteiro `>= 1` (`1-based`), sequencial e global (sem divisão de posição em caso de empate).

## Schemas Públicos (`schemas/ranking_schema.py`)

### `RankingEntryResponse`

| Campo público | Atributo interno | Tipo | Regras |
| --- | --- | --- | --- |
| `position` | `position` | `int` | Obrigatório, `>= 1` (`1-based`, sequencial global) |
| `userId` | `user_id` | `UUID` | Obrigatório (`alias="userId"`, `serialization_alias="userId"`) |
| `name` | `name` | `str` | Obrigatório |
| `xp` | `xp` | `int` | Obrigatório, `>= 0` |
| `missionsCompleted` | `missions_completed` | `int` | Obrigatório, `>= 0` (`alias="missionsCompleted"`, `serialization_alias="missionsCompleted"`) |

### `RankingListResponse`

Reutiliza `PaginatedResponse[RankingEntryResponse]` (`schemas/pagination_schema.py`):
- `data`: `list[RankingEntryResponse]`
- `page`: `int` (`>= 1`, padrão `1`)
- `page_size`: `int` (`1..100`, padrão `20`)
- `total_items`: `int` (`>= 0`, total de usuários ativos)
- `total_pages`: `int` (`>= 0`)
