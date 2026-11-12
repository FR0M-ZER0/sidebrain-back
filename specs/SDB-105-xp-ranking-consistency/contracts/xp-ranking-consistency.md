# Contrato de Consistência Cross-Endpoint — XP, Missões, Perfil e Ranking (SDB-105)

**Feature**: Consistência e Estratégia Síncrona de XP e Ranking (`SDB-105`)  
**Prefixo da API**: `/api/v1`

Esta tarefa **não altera nem cria rotas HTTP** e **não modifica formatos de payload** já estabelecidos em `SDB-81` (perfil de usuário), `SDB-86` (missões), `SDB-51` (quizzes) e `SDB-90` (ranking). Este contrato documenta as invariantes síncronas entre os endpoints existentes.

## 1. Endpoints Envolvidos

### Mutações que alteram estado de conclusão ou elegibilidade de XP

| Operação | Endpoint | Efeito Síncrono antes da Resposta |
| --- | --- | --- |
| Submeter resposta de quiz | `POST /api/v1/quizzes/{quiz_id}/answers` (`201 Created`) | Avalia resposta, registra conclusão da aula se aplicável, recalcula progresso das missões da trilha sob lock e realiza `commit()` antes de responder. |
| Recalcular progresso das missões da etapa | `POST /api/v1/steps/{step_id}/missions/recalculate-progress` (`204 No Content`) | Reavalia missões da trilha sob lock, mantém missões já `done` inalteradas (idempotente) e realiza `commit()` antes de responder. |
| Excluir missão logicamente | `DELETE /api/v1/missions/{mission_id}` (`204 No Content`) | Marca `msn_is_deleted = True` e realiza `commit()` antes de responder. |

### Consultas que expõem XP, missões concluídas e posição

| Operação | Endpoint | Campos Relevantes na Resposta (`200 OK`) |
| --- | --- | --- |
| Consultar perfil autenticado | `GET /api/v1/users/me` | `UserMeResponse`: `xp`, `missionsCompleted` |
| Atualizar perfil autenticado | `PUT /api/v1/users/me` | `UserMeResponse`: `xp`, `missionsCompleted` |
| Listar ranking geral | `GET /api/v1/rankings` | `PaginatedResponse[RankingEntryResponse]`: `position`, `userId`, `name`, `xp`, `missionsCompleted` |
| Consultar própria posição no ranking | `GET /api/v1/rankings/me` | `RankingEntryResponse`: `position`, `userId`, `name`, `xp`, `missionsCompleted` |

## 2. Invariantes Contratuais entre Endpoints

1. **Consistência imediata pós-commit (sem fila)**:
   - Imediatamente após `201 Created` em `POST /api/v1/quizzes/{quiz_id}/answers` ou `204 No Content` em `POST /api/v1/steps/{step_id}/missions/recalculate-progress`, qualquer chamada subsequente a `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me` **MUST** refletir o novo `xp`, `missionsCompleted` e `position` sem aguardar processamento em background.
2. **Igualdade estrita entre Perfil e Ranking**:
   - Para qualquer usuário ativo $u$ em um mesmo estado persistido:
     - `GET /api/v1/users/me` -> `(xp, missionsCompleted)` **==**
     - `GET /api/v1/rankings/me` -> `(xp, missionsCompleted)` **==**
     - Entrada de $u$ em `GET /api/v1/rankings` -> `(xp, missionsCompleted)`.
   - A `position` em `GET /api/v1/rankings/me` **MUST** ser idêntica à `position` do mesmo usuário na página correspondente de `GET /api/v1/rankings`.
3. **Idempotência de conclusão**:
   - Repetir `POST /api/v1/steps/{step_id}/missions/recalculate-progress` ou enviar novas respostas via `POST /api/v1/quizzes/{quiz_id}/answers` após uma missão atingir `done` **MUST NOT** incrementar novamente `xp` nem `missionsCompleted`.
4. **Exclusão lógica**:
   - Após `204 No Content` em `DELETE /api/v1/missions/{mission_id}`, consultas subsequentes a `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me` **MUST** desconsiderar imediatamente a recompensa daquela missão.
   - Se apenas a etapa (`DELETE /api/v1/tracks/{track_id}/steps/{step_id}`) ou trilha (`DELETE /api/v1/tracks/{track_id}`) pai for excluída logicamente após a conclusão da missão, os pontos e a contagem dessa missão ativa **MUST** permanecer preservados.
5. **Atomicidade em falha**:
   - Se a submissão de quiz falhar antes da confirmação (`4xx`/`5xx`), `xp`, `missionsCompleted` e `position` permanecem inalterados nas consultas seguintes.

