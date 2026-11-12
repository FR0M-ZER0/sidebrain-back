# Quickstart de Validação — SDB-105

## Pré-requisitos

- Ambiente Python do projeto sincronizado via `uv` (`.venv` com Python 3.11+).
- PostgreSQL de testes ativo com extensão `pgvector` para os testes de integração:

```powershell
docker compose --profile test up -d --wait postgres_test
```

- Branch atual: `feat/sdb-105-adiciona-filas-gerenciar-xp-ranking`.

## Preparação

```powershell
uv sync
```

*(Caso execute sem rede utilizando o ambiente já provisionado, use `uv run --no-sync`.)*

## 1. Validação ponta a ponta da SDB-105 (Testes de Integração)

Executar o novo conjunto de testes de integração HTTP ponta a ponta e os testes correlatos já existentes:

```powershell
uv run --no-sync pytest tests/integration/test_xp_ranking_consistency.py tests/integration/test_ranking_lifecycle.py tests/integration/test_mission_progress.py tests/integration/test_user_profile_read.py
```

**Resultados esperados:**
- Submissão de resposta via `POST /api/v1/quizzes/{quiz_id}/answers` atualiza e comita o progresso da missão na mesma transação; consultas imediatas a `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me` retornam exatamente o mesmo `xp`, `missionsCompleted` e `position` atualizado sem depender de worker/fila.
- Recálculo via `POST /api/v1/steps/{step_id}/missions/recalculate-progress` e novas submissões de quiz sobre missão já concluída mantêm `xp` e `missionsCompleted` inalterados (idempotência).
- Exclusão lógica via `DELETE /api/v1/missions/{mission_id}` remove imediatamente a recompensa da missão no perfil e no ranking; exclusão lógica apenas de `Step`/`Track` pai preserva o XP da missão ativa concluída.
- Falha antes do commit não produz conclusão nem alteração parcial de XP/ranking.
- Contagem constante de queries SQL mantida nas consultas de ranking.

## 2. Validação de Contratos e Unitários Relacionados

```powershell
uv run --no-sync pytest tests/contract/test_ranking_contract.py tests/contract/test_user_profile_read_contract.py tests/unit/test_ranking_schema.py tests/unit/test_ranking_service.py tests/unit/test_mission_progress_service.py tests/unit/test_quiz_service.py
```

## 3. Verificação da Restrição Arquitetural (Zero Filas para XP/Ranking)

Confirmar no diff (`git diff dev..HEAD` / arquivos modificados) e em `src/sidebrain_back/tasks/` que:
- Nenhuma task Celery, dependência de fila (ex.: RabbitMQ) ou tabela/coluna de cache/contador de XP foi adicionada.
- A fórmula oficial de XP, a decisão síncrona sem filas e os critérios de reavaliação futura estão documentados no [`README.md`](../../README.md) e nas docstrings do fluxo correspondente.

## 4. Qualidade Global (Lint, Formatação e Suíte Completa)

```powershell
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
```

Todos os checks de lint, formatação e suíte de testes devem passar sem falhas.

