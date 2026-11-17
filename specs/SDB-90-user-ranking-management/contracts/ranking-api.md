# Contrato HTTP — Ranking de Usuários

Prefixo da API: `/api/v1`.

Todos os endpoints são exclusivamente de leitura (`GET`) e exigem autenticação via `Authorization: Bearer <token>` (`Depends(get_current_user)`). Todas as respostas de erro seguem o padrão Problem Details (RFC 9457) definido em `core/errors.py`.

## 1. Listar Ranking Geral

`GET /api/v1/rankings`

Lista o leaderboard global de usuários ativos ordenado por XP decrescente.

### Query Parameters

| Parâmetro | Tipo | Padrão | Regras |
| --- | --- | --- | --- |
| `page` | `integer` | `1` | `>= 1` |
| `page_size` | `integer` | `20` | `1..100` |

### Resposta `200 OK`

`PaginatedResponse[RankingEntryResponse]`

```json
{
  "data": [
    {
      "position": 1,
      "userId": "3b9c8e72-7c2f-4b0e-9d58-44b0f6c1a111",
      "name": "Maria Silva",
      "xp": 1250,
      "missionsCompleted": 12
    },
    {
      "position": 2,
      "userId": "9a1f2d34-1b2c-4d5e-8f90-123456789abc",
      "name": "João Souza",
      "xp": 900,
      "missionsCompleted": 9
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 150,
  "total_pages": 8
}
```

### Regras de Contrato

- `position` é global e 1-based: na página 2 com `page_size=20`, o primeiro item tem `position = 21`.
- Empates de `xp` recebem posições distintas decididas por `usr_created_at ASC, usr_id ASC`.
- Usuários ativos sem missões concluídas aparecem com `"xp": 0` e `"missionsCompleted": 0`.
- Quando `page` ultrapassa `total_pages` (ou não há usuários ativos), `data` retorna `[]` mantendo `page`, `page_size`, `total_items` e `total_pages` consistentes.
- Nenhum campo interno (`usr_*`, `msn_*`, `mpg_*`, `email`, `password_hash`) é exposto.

### Erros

- `401 Unauthorized`: token ausente, malformado, inválido ou pertencente a usuário inativo na autenticação.
- `422 Unprocessable Entity`: `page < 1`, `page_size < 1`, `page_size > 100` ou tipos não inteiros.

---

## 2. Consultar Posição do Usuário Autenticado

`GET /api/v1/rankings/me`

Retorna diretamente a entrada do usuário autenticado no ranking global, sem necessidade de paginar a listagem.

### Request

Sem parâmetros de query ou corpo. Requer cabeçalho `Authorization: Bearer <token>`.

### Resposta `200 OK`

`RankingEntryResponse`

```json
{
  "position": 3,
  "userId": "c4d5e6f7-89ab-4cde-9012-3456789abcde",
  "name": "Usuário Atual",
  "xp": 750,
  "missionsCompleted": 7
}
```

### Regras de Contrato

- Retorna exatamente os mesmos 5 campos (`position`, `userId`, `name`, `xp`, `missionsCompleted`) e os mesmos valores que o usuário ocupa na listagem geral `GET /api/v1/rankings`.
- Não inclui `totalUsers`.

### Erros

- `401 Unauthorized`: token ausente, malformado ou inválido em `get_current_user`.
- `404 Not Found`: usuário autenticado não encontrado ou marcado como removido logicamente (`usr_is_deleted = true`) ao consultar o serviço de ranking.
