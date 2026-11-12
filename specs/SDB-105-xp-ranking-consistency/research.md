# Research & Architectural Decisions — SDB-105

**Feature**: Consistência e Estratégia Síncrona de XP e Ranking (`SDB-105`)  
**Date**: 2026-11-11  
**Spec**: [spec.md](./spec.md)

## 1. Fonte única de verdade para XP e ranking

- **Decision**: Manter `RankingRepository._ranking_summary()` em `src/sidebrain_back/repositories/ranking_repository.py` como a única implementação de cálculo de `xp` e `missions_completed`, compartilhada tanto por `RankingService` (`GET /api/v1/rankings` e `GET /api/v1/rankings/me`) quanto por `UserService` (`GET /api/v1/users/me` e `PUT /api/v1/users/me`).
- **Rationale**: A inspeção do código confirmou que `RankingService` e `UserService` já consultam exatamente a mesma agregação SQL (`COALESCE(SUM(Mission.msn_xp_reward), 0)` e `COUNT(Mission.msn_id)` sobre usuários ativos, `MissionProgress` com status `done` e missões com `msn_is_deleted = false`). Manter essa agregação centralizada garante consistência estrita entre perfil e ranking sem risco de divergência entre leituras.
- **Alternatives considered**:
  - Persistir coluna `usr_xp` na tabela `user` atualizada por evento/worker: rejeitada porque duplicaria a fonte de verdade, exigiria reconciliação e violaria o escopo explícito da `SDB-105`.
  - Criar materialized view para ranking: rejeitada pelo mesmo motivo (introduz atraso/consistência eventual sem evidência de gargalo).

## 2. Atualização síncrona pós-commit vs. filas assíncronas

- **Decision**: Não criar filas, tasks Celery, dependências de RabbitMQ ou workers para cálculo/concessão de XP ou ranking; preservar a execução síncrona transacional em `QuizService.submit_quiz_answer` e `MissionProgressService.recalculate_missions_by_step_id`.
- **Rationale**: Em `QuizService.submit_quiz_answer`, a resposta do quiz, o progresso das missões (`MissionProgressService.update_missions_by_track_id`) e o progresso de badges ocorrem dentro da mesma transação e são persistidos com `await self.db.commit()` antes de retornar `201 Created`. O único disparo assíncrono existente após o commit é `TrackService.enqueue_next_step_preparation` (preparação de conteúdo futuro da trilha), que não participa do cálculo de XP ou ranking. Introduzir fila para XP traria consistência eventual sem justificativa de carga medida.
- **Alternatives considered**:
  - Publicar evento em fila Celery/Redis ou RabbitMQ após conclusão de missão: rejeitada explicitamente pela decisão arquitetural da `SDB-105` (só deve ser reavaliada em tarefa futura com evidência medida de contenção/latência, SLA explícito de atraso aceitável e desenho de outbox transacional, idempotência, ordenação/concorrência e reconciliação).

## 3. Idempotência e regras de exclusão lógica

- **Decision**: Preservar a guarda de idempotência em `MissionProgressService.update_missions_by_track_id` (que ignora registros já com `mpg_status == MissionProgressStatusEnum.DONE`) e o filtro de elegibilidade em `RankingRepository._ranking_summary()` (exclui apenas `User.usr_is_deleted = true` e `Mission.msn_is_deleted = true`, mantendo XP de missões ativas concluídas mesmo se `Step` ou `Track` pai forem removidos logicamente).
- **Rationale**: Garante alinhamento integral com a especificação pré-existente do ranking (`SDB-90`) e com os critérios de aceite da `SDB-105` (recalculo repetido não duplica recompensa; exclusão lógica da missão remove imediatamente o XP nas consultas subsequentes).
- **Alternatives considered**:
  - Filtrar também `Step.stp_is_deleted` e `Track.trk_is_deleted` no cálculo de XP: rejeitada na clarificação (`Q2`) para manter coerência com `SDB-90` e impedir perda retroativa de XP do estudante quando uma trilha é removida após a conclusão da missão.

## 4. Estratégia de testes ponta a ponta

- **Decision**: Adicionar uma suíte dedicada de integração HTTP (`tests/integration/test_xp_ranking_consistency.py`) que encadeie as rotas públicas reais (`POST /api/v1/quizzes/{quiz_id}/answers`, `POST /api/v1/steps/{step_id}/missions/recalculate-progress`, `DELETE /api/v1/missions/{mission_id}`, `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me`) sobre o PostgreSQL de testes, preservando a verificação de contagem constante de queries já existente em `tests/integration/test_ranking_lifecycle.py` sem introduzir novos testes de carga.
- **Rationale**: Os testes atuais cobriam progresso de missão (`test_mission_progress.py`) e ranking/perfil (`test_ranking_lifecycle.py`, `test_user_profile_read.py`) de maneira isolada. Um fluxo HTTP ponta a ponta comprova diretamente todos os critérios da `SDB-105` (visibilidade imediata pós-commit sem worker, igualdade entre perfil e ranking, idempotência em recálculo/resubmissão, rollback em falha e efeito imediato de exclusão lógica da missão vs. preservação sob exclusão lógica de `Step`/`Track`).
- **Alternatives considered**:
  - Testar apenas na camada de `Service`/`Repository`: rejeitada na clarificação (`Q3`) por não exercitar a fronteira completa de commit e serialização das rotas HTTP.
  - Criar suíte de benchmark/carga nesta etapa: rejeitada na clarificação (`Q3`) por estar fora de escopo até eventual necessidade medida.

## 5. Documentação junto ao fluxo correspondente

- **Decision**: Documentar a fórmula oficial de XP, a decisão síncrona sem filas e os critérios para reavaliação futura em nova seção do `README.md` (junto à documentação de rotas/fluxos da API) e em docstrings concisas nos módulos do fluxo (`ranking_repository.py`, `ranking_service.py`, `user_service.py`, `quiz_service.py`, `mission_progress_service.py`).
- **Rationale**: Atende diretamente à clarificação (`Q1`) e ao critério de aceite da `SDB-105` sem duplicar documentos extensos ou alterar contratos de API.
- **Alternatives considered**:
  - Documentar apenas em `specs/` ou apenas em `docs/`: rejeitada na clarificação (`Q1`) por deixar a decisão menos visível a quem consulta o `README.md` ou lê diretamente os módulos do fluxo.

