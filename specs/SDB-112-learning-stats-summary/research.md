# Pesquisa e decisões — SDB-112

## Decisão: aninhar a consulta sob o recurso do próprio usuário

- **Decision**: Publicar `GET /api/v1/users/me/statistics`, sem parâmetro de
  usuário e protegido por `get_current_user`.
- **Rationale**: O agregador da API aplica o prefixo `/api`; o roteador de
  usuários usa `/v1/users` e já oferece `/me`. A nova consulta pertence ao
  mesmo usuário autenticado e não permite escolher um titular diferente.
- **Alternatives considered**:
  - Criar uma rota com identificador de usuário: rejeitada por contrariar o
    isolamento de dados privados.
  - Criar um recurso de estatísticas sem vínculo explícito ao usuário: rejeitado
    por afastar a rota do padrão existente de recursos próprios.
- **Evidence**: `src/sidebrain_back/routers/router.py`,
  `src/sidebrain_back/routers/v1/user_router.py` e
  `tests/contract/test_ranking_contract.py`.

## Decisão: reutilizar a consulta individual do ranking

- **Decision**: Injetar `RankingRepository` no serviço e usar
  `get_user_ranking(user.usr_id)` como fonte de `xp`, `missionsCompleted` e
  `position`.
- **Rationale**: A consulta existente deriva XP e missões de missões ativas
  concluídas e calcula a posição com a ordenação determinística já definida.
  Usar a mesma projeção evita divergências e fornece `404` se o usuário não
  estiver elegível no ranking.
- **Alternatives considered**:
  - Reimplementar soma de XP, contagem e posição em um novo repositório:
    rejeitada por duplicar regras existentes.
  - Consultar perfil e ranking em sequência pela camada HTTP: rejeitada por
    acoplar o serviço a chamadas HTTP e repetir dependências.
- **Evidence**: `src/sidebrain_back/repositories/ranking_repository.py`,
  `src/sidebrain_back/services/ranking_service.py`,
  `src/sidebrain_back/services/user_service.py` e
  `specs/SDB-90-user-ranking-management/research.md`.

## Decisão: ler conquistas desbloqueadas sem recalcular progresso

- **Decision**: Contar registros de `BadgeProgress` do usuário com status
  `done`, associados a `Badge` não removido logicamente.
- **Rationale**: O estado `done` representa a conquista concluída; as consultas
  existentes omitem badges removidos. O repositório de estatísticas terá
  somente consultas de leitura e não chamará os fluxos de atualização de
  badges.
- **Alternatives considered**:
  - Recalcular badges durante a consulta: rejeitada, pois pode inserir ou
    atualizar progresso e viola o requisito de somente leitura.
  - Contar estados `idle` ou `in_progress`: rejeitada, pois não representam
    conquistas desbloqueadas.
- **Evidence**: `src/sidebrain_back/enums/badge_progress_status_enum.py`,
  `src/sidebrain_back/models/badge_model.py`,
  `src/sidebrain_back/models/badge_progress_model.py` e
  `src/sidebrain_back/services/badge_progress_service.py`.

## Decisão: tratar sequência expirada na leitura, usando data UTC

- **Decision**: Ler o valor e a data de atualização de `DayStreak`; retornar o
  valor se a data UTC for hoje ou ontem, e zero se for anterior ou inexistente.
  Não gravar a expiração nem bloquear o registro para atualização.
- **Rationale**: O fluxo de atividade existente atualiza a sequência por data
  UTC, incrementa quando a atividade anterior foi ontem e reinicia após uma
  lacuna. A consulta traduz uma sequência antiga para zero sem alterar o estado
  persistido. O método atual de leitura do repositório de badges usa
  `FOR UPDATE`, portanto não será reaproveitado para a consulta read-only.
- **Alternatives considered**:
  - Redefinir a sequência armazenada durante a leitura: rejeitada por violar
    somente leitura.
  - Considerar somente atividade de hoje como atual: rejeitada porque ocultaria
    uma sequência válida antes de a pessoa registrar atividade no dia corrente.
- **Evidence**: `src/sidebrain_back/services/badge_progress_service.py`,
  `src/sidebrain_back/repositories/badge_progress_repository.py` e
  `src/sidebrain_back/models/day_streak_model.py`.

## Decisão: não introduzir armazenamento ou dependências externas

- **Decision**: Representar o resumo apenas como projeção de resposta; consultar
  as tabelas existentes e não criar migrations.
- **Rationale**: Todos os cinco valores já têm fonte de dados ou consulta
  existente. A persistência de um resumo criaria risco de desatualização e
  duplicação.
- **Alternatives considered**:
  - Manter uma tabela de snapshots: rejeitada por aumentar a complexidade e
    exigir sincronização com cada alteração de progresso.
- **Evidence**: `src/sidebrain_back/models/` e
  `src/sidebrain_back/repositories/ranking_repository.py`.

## Diretrizes de bibliotecas consultadas

- FastAPI documenta o uso de `response_model` para documentar, validar,
  serializar e filtrar os campos de saída; isso sustenta o schema público
  restrito do resumo.
- SQLAlchemy 2 documenta consultas `SELECT` assíncronas com `AsyncSession`;
  as operações planejadas não incluem gravação, flush ou commit.

Referências:
- https://fastapi.tiangolo.com/tutorial/response-model/
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
