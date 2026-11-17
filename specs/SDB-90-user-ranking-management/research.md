# Pesquisa e decisões — SDB-90

## Decisão: cálculo derivado de XP e `missionsCompleted` via agregação SQL

- **Decision**: Calcular `xp` como `COALESCE(SUM(Mission.msn_xp_reward), 0)` e `missions_completed` como `COUNT(Mission.msn_id)` diretamente no banco via `LEFT JOIN` a partir de `User` (`usr_is_deleted.is_(False)`) para `MissionProgress` (`mpg_status == MissionProgressStatusEnum.DONE`) e `Mission` (`msn_is_deleted.is_(False)`), agrupando por `User.usr_id`, `User.usr_name` e `User.usr_created_at`.
- **Rationale**: Não existe coluna `usr_xp` persistida em `User` e a especificação proíbe criar novas tabelas ou colunas. O `LEFT JOIN` condicional preserva usuários ativos com `XP = 0` no leaderboard, ignora progressos `idle`/`in_progress`, ignora `mpg_score` e missões com soft delete, e independe do estado de exclusão lógica de `Step` ou `Track` pais.
- **Alternatives considered**:
  - Persistir coluna `usr_xp` em `user`: rejeitado por violar a restrição explícita de não alterar o schema do banco nesta task.
  - Carregar entidades ORM com `selectinload` e somar em Python: rejeitado por gerar tráfego de dados desnecessário e impedir paginação e ordenação eficientes no banco.

## Decisão: ordenação determinística e cálculo de posição global (`1-based`)

- **Decision**: Ordenar sempre por `xp DESC, usr_created_at ASC, usr_id ASC`. Em `list_rankings`, executar `count_ranked_users` (total de usuários ativos) e `list_rankings` paginado (`OFFSET`/`LIMIT`), atribuindo `position = offset + index + 1` (equivalente exato a `ROW_NUMBER()` sobre a ordenação determinística total). Em `get_user_ranking`, usar uma CTE/subquery com `ROW_NUMBER() OVER (ORDER BY xp DESC, usr_created_at ASC, usr_id ASC)` sobre os usuários ativos agregados e filtrar pelo `usr_id` autenticado em uma única query.
- **Rationale**: Como a chave de ordenação `(xp DESC, usr_created_at ASC, usr_id ASC)` é estritamente única (pois `usr_id` é chave primária), a posição global na página `p` é matematicamente determinística e contínua entre páginas, e a CTE com `ROW_NUMBER()` em `get_user_ranking` garante que `GET /api/v1/rankings/me` retorne exatamente a mesma posição que `GET /api/v1/rankings` em uma única consulta SQL, sem N+1.
- **Alternatives considered**:
  - Usar `RANK()` ou `DENSE_RANK()` compartilhando posições em empates: rejeitado porque o requisito define posições distintas (`1-based`) decididas pelo critério de desempate.
  - Paginar a listagem em memória na camada de serviço para localizar o usuário autenticado em `/rankings/me`: rejeitado por degradar linearmente com o número de usuários.

## Decisão: contrato público semântico em `camelCase` e paginação normativa

- **Decision**: Criar `RankingEntryResponse` em `schemas/ranking_schema.py` com `ConfigDict(from_attributes=True, populate_by_name=True)`, expondo exclusivamente `position`, `userId`, `name`, `xp` e `missionsCompleted` (sem `totalUsers`), e reutilizar `PaginatedResponse[RankingEntryResponse]` para `GET /api/v1/rankings`.
- **Rationale**: Segue `docs/code_conventions.md`, mantém compatibilidade com o envelope paginado normativo (`data`, `page`, `page_size`, `total_items`, `total_pages`) e assegura que ambos os endpoints compartilhem exatamente o mesmo schema de item sem vazar `usr_email`, `usr_password_hash` ou prefixos físicos (`usr_*`, `msn_*`, `mpg_*`).
- **Alternatives considered**:
  - Adicionar `totalUsers` em `GET /api/v1/rankings/me`: rejeitado na fase de clarificação para manter simetria total com `RankingEntryResponse` e evitar query adicional.
  - Expor nomes em `snake_case` (`user_id`, `missions_completed`): rejeitado pois o contrato da SDB-90 especifica `userId` e `missionsCompleted`.

## Decisão: autenticação via `get_current_user` e tratamento de `404` no `RankingService`

- **Decision**: Proteger `GET /api/v1/rankings` e `GET /api/v1/rankings/me` com `Depends(get_current_user)` sem alterar `core/auth.py`. Em `RankingService.get_my_ranking`, consultar `ranking_repository.get_user_ranking(user.usr_id)` e, caso retorne `None` (usuário inexistente ou com `usr_is_deleted = True`), lançar `ProblemDetailError(404, "Não encontrado", "Usuário não encontrado.")`.
- **Rationale**: Mantém o comportamento transversal de autenticação (`401` para credenciais ausentes ou inválidas) e cumpre o requisito de domínio de retornar `404` no formato Problem Details (RFC 9457) quando o usuário consultado no serviço de ranking não é encontrado como ativo.
- **Alternatives considered**:
  - Criar uma dependência de autenticação separada apenas para o ranking que permita usuários com soft delete: rejeitado na clarificação por duplicar infraestrutura de `core/auth.py` e divergir do padrão das demais rotas.
