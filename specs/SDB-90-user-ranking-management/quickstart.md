# Quickstart de validação — SDB-90

## Pré-requisitos

- Ambiente Python do projeto configurado (`.venv` / `uv`).
- PostgreSQL de testes ativo (via Docker Compose conforme configuração do projeto) para os testes de integração.
- Repositório na branch `feat/sdb-90-criar-endpoints-para-gerenciamento-do-ranking-dos-usuarios`.

## Preparação

```powershell
uv sync
```

Caso execute sem rede ou diretamente pelo ambiente virtual já provisionado, utilize `.venv/Scripts/pytest.exe` e `.venv/Scripts/ruff.exe` (ou `uv run --no-sync`).

## Cenários de Contrato

```powershell
uv run --no-sync pytest tests/contract/test_ranking_contract.py
```

Verifica:
- Autenticação obrigatória (`401` sem token ou com token inválido) em `GET /api/v1/rankings` e `GET /api/v1/rankings/me`.
- Paginação normativa (`page`, `page_size`, `total_items`, `total_pages`) e rejeição `422` para `page < 1`, `page_size < 1` ou `page_size > 100`.
- Contrato semântico exato de `RankingEntryResponse` (`position`, `userId`, `name`, `xp`, `missionsCompleted`) e ausência de vazamento de `usr_email`, `usr_password_hash` ou campos `usr_*`/`msn_*`/`mpg_*`.
- Retorno `404` em Problem Details para `GET /api/v1/rankings/me` quando o usuário não é encontrado como ativo pelo serviço, conforme [ranking-api.md](./contracts/ranking-api.md).

## Cenários Unitários

```powershell
uv run --no-sync pytest tests/unit/test_ranking_schema.py tests/unit/test_ranking_service.py
```

Verifica:
- Serialização e aliases (`userId`, `missionsCompleted`) de `RankingEntryResponse` e `RankingListResponse`.
- Regras de `RankingService.list_rankings` e `RankingService.get_my_ranking`, incluindo repasse de offset/limit, montagem de `PaginatedResponse` e erro `404` quando `get_user_ranking` retorna `None`.

## Cenários de Integração

```powershell
uv run --no-sync pytest tests/integration/test_ranking_lifecycle.py
```

Verifica com banco PostgreSQL real:
- Cálculo de XP como soma de `msn_xp_reward` apenas de missões ativas com `mpg_status = done` (ignorando `idle`, `in_progress`, `mpg_score` e missões deletadas).
- Inclusão de usuários ativos sem missões concluídas com `xp = 0` e `missionsCompleted = 0`.
- Exclusão de usuários com soft delete (`usr_is_deleted = true`) da listagem, do total de itens e do cálculo de posições.
- Preservação do XP de missões ativas mesmo quando `Step` ou `Track` pai está com soft delete.
- Ordenação determinística (`xp DESC, usr_created_at ASC, usr_id ASC`), continuidade de `position` entre páginas e consistência exata entre `GET /api/v1/rankings` e `GET /api/v1/rankings/me`.
- Quantidade constante de queries SQL por requisição (ausência de N+1 ao comparar 1 e múltiplos usuários no ranking).

## Verificação Geral de Qualidade

```powershell
uv run --no-sync ruff check .
uv run --no-sync pytest
```

Todos os checks de lint e a suíte de testes devem passar sem erros.
