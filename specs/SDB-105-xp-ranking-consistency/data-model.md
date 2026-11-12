# Data Model & Calculation Invariants — SDB-105

**Feature**: Consistência e Estratégia Síncrona de XP e Ranking (`SDB-105`)  
**Date**: 2026-11-11  
**Spec**: [spec.md](./spec.md)

## 1. Escopo de Persistência

Nenhuma nova tabela, coluna, índice, visão materializada ou migração Alembic é criada nesta demanda. A camada de persistência permanece integralmente baseada nos modelos existentes:

- `User` (`src/sidebrain_back/models/user_model.py`)
- `Mission` (`src/sidebrain_back/models/mission_model.py`)
- `MissionProgress` (`src/sidebrain_back/models/mission_progress_model.py`)

## 2. Entidades e Relacionamentos no Cálculo de XP/Ranking

```text
User (usr_is_deleted = False)
  └── 0..N MissionProgress (mpg_user_id = usr_id, mpg_status = 'done')
        └── 1 Mission (msn_id = mpg_mission_id, msn_is_deleted = False)
              └── msn_xp_reward (int > 0)
```

- **Elegibilidade de Usuário**: Apenas registros com `usr_is_deleted = False` entram no cálculo, na contagem total e nas consultas de perfil e ranking.
- **Elegibilidade de Progresso**: Apenas registros com `mpg_status = MissionProgressStatusEnum.DONE` contabilizam XP e conclusão. Estados `idle` e `in_progress`, assim como `mpg_score`, não contribuem para XP.
- **Elegibilidade de Missão**: Apenas missões com `msn_is_deleted = False` contabilizam XP e conclusão. O estado `is_deleted` de `Step` ou `Track` pai não remove o XP de uma missão ativa já concluída.

## 3. Fórmula Oficial de XP e Projeções Derivadas

Para cada usuário ativo $u$:

$$\text{xp}(u) = \sum_{\substack{p \in \text{MissionProgress}(u) \\ p.\text{status} = \text{DONE} \\ m = p.\text{mission},\; \neg m.\text{is\_deleted}}} m.\text{xp\_reward}$$

$$\text{missionsCompleted}(u) = \left|\left\{ p \in \text{MissionProgress}(u) \;\middle|\; p.\text{status} = \text{DONE} \land \neg p.\text{mission}.\text{is\_deleted} \right\}\right|$$

Sem missões elegíveis concluídas, o resultado derivado é `xp = 0` e `missionsCompleted = 0`.

### Projeções internas (`ranking_repository.py`)

| Projeção | Campos | Consumidores |
| --- | --- | --- |
| `UserXpSummary` | `xp`, `missions_completed` | `UserService._build_user_me_response` (`GET /api/v1/users/me`, `PUT /api/v1/users/me`) |
| `RankedUserRow` | `position`, `user_id`, `name`, `xp`, `missions_completed` | `RankingService.list_rankings` (`GET /api/v1/rankings`), `RankingService.get_my_ranking` (`GET /api/v1/rankings/me`) |

### Ordenação Determinística do Ranking

1. `xp DESC`
2. `usr_created_at ASC`
3. `usr_id ASC`
4. `position` inteira global `1-based` via `ROW_NUMBER()`, sem divisão ou repetição de posição em empates.

## 4. Transições e Garantias de Consistência e Idempotência

- **Conclusão síncrona transacional**:
  - `QuizService.submit_quiz_answer` adquire lock da trilha (`get_mission_track_for_quiz`), registra a resposta, atualiza resumo/lição/missões (`update_missions_by_track_id`) e badges, e executa `commit()` antes de retornar `201 Created`.
  - `MissionProgressService.recalculate_missions_by_step_id` adquire lock da trilha (`get_track_by_step_for_update`), executa `update_missions_by_track_id` e faz `commit()` antes de retornar `204 No Content`.
- **Guarda de idempotência**:
  - Ao iterar sobre as missões da trilha, `MissionProgressService.update_missions_by_track_id` verifica `progress.mpg_status == MissionProgressStatusEnum.DONE` e ignora qualquer missão já concluída, preservando `mpg_status`, `mpg_score` e `mpg_finished_in` e impedindo concessão repetida de XP.
- **Exclusão lógica imediata**:
  - `MissionService.delete_mission` executa `soft_delete` (`msn_is_deleted = True`) e `commit()`. Como `xp` e `missionsCompleted` são agregados sob demanda sem cache ou contador persistido, a consulta seguinte ao perfil ou ao ranking exclui imediatamente a missão removida.
- **Rollback em falha**:
  - Qualquer exceção antes do `commit()` aciona `rollback()`, mantendo `MissionProgress`, `xp` e `missionsCompleted` inalterados.

