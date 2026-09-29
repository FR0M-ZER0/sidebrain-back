# Quickstart de validação: SDB-75

## Pré-requisitos

- PostgreSQL e Redis disponíveis conforme `docker-compose.yml`.
- Ambiente instalado com `uv sync`.
- Migrações aplicadas com `uv run alembic upgrade head`.
- API e worker Celery executando com as configurações do projeto.

## Execução local

```bash
# aplicar a estrutura do banco
uv run alembic upgrade head

# terminal 1: API
uv run dev

# terminal 2: worker Celery
uv run celery -A sidebrain_back.core.celery_app worker --loglevel=INFO
```

## Validação automatizada

```bash
uv run ruff check .
uv run pytest
```

A suíte deve incluir os contratos de `tests/contract`, testes unitários do service/schema/task e integrações da persistência.

## Cenário 1: criação não bloqueante

1. Enviar `POST /api/v1/tracks` com `goal`, `topic`, nível e respostas válidas.
2. Confirmar `202` e `status=pending` com `request_id`.
3. Simular um provedor lento e confirmar que a resposta HTTP chega antes da conclusão do worker.
4. Executar o worker e confirmar uma Track com todos os Steps e conteúdo apenas no Step 1.

Referência: [track-generation.md](contracts/track-generation.md) e [data-model.md](data-model.md).

## Cenário 2: idempotência e conflito

1. Enviar duas requisições com o mesmo `request_id` e contexto; confirmar uma solicitação, uma task efetiva e no máximo uma Track.
2. Repetir o `request_id` com outro tópico ou usuário; confirmar `409` em Problem Details e preservação do pedido original.
3. Forçar erro permanente/transitório no worker; confirmar estado `failed`, `error_code` e ausência de registro parcial.

## Cenário 3: preparação manual

1. Com um Step ativo autorizado e progresso elegível, chamar `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next`.
2. Confirmar `202` e que o service publicou `tasks.prepare_next_step_content` sem chamar o provedor durante a requisição.
3. Repetir a chamada e confirmar que a task mantém idempotência e não duplica conteúdo.
4. Usar Step inexistente, excluído e de outro usuário; confirmar o mesmo `404` genérico.
5. Usar um Step sem próximo elegível; confirmar `200` com `status=skipped`.

## Testes de concorrência

Executar duas solicitações simultâneas de preparação para o mesmo Step e verificar que locks/checagem de conteúdo ativo deixam no máximo um conjunto ativo de Lessons, Quiz e Mission.

## Critério de conclusão

Os três cenários prioritários, os casos de conflito/falha e a concorrência devem passar junto de `uv run ruff check .` e `uv run pytest`.
