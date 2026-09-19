# Quickstart de Validação

## Pré-requisitos

- Python >= 3.11, `uv` e Docker instalados.
- `.env` com PostgreSQL, Redis e `GROQ_API_KEY` configurados.
- Worker Celery disponível para executar a task.

## Preparação

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
```

Inicie a API e o worker conforme os comandos do ambiente do projeto. Não é
necessário endpoint novo para validar esta feature; use o fluxo interno que
publica a task ou invoque a task em teste com um `request_id` determinístico.
O contrato de entrada é `request_id`, `user_id`, `goal`, `topic` e os campos
opcionais `knowledge_level` e `assessment_answers`. Falhas de conexão, timeout
e rate limit são repetidas até três tentativas totais; falhas de validação,
persistência e erros permanentes retornam falha tratável sem detalhes internos.

## Validações automatizadas

```bash
uv run pytest tests/unit tests/integration tests/contract
uv run ruff check .
```

Os testes devem mockar o cliente Groq e controlar a sessão assíncrona. Testes
de integração devem usar PostgreSQL e Redis quando exercitarem Celery real.

## Cenários mínimos

1. Contexto válido com nível e respostas: confirmar uma trilha com todas as etapas na ordem e conteúdo inicial na primeira.
2. Contexto válido sem nível ou respostas: confirmar geração usando apenas o contexto disponível.
3. Resposta da IA com JSON malformado, campo ausente, enum inválido, posição duplicada ou texto vazio: confirmar falha sem registros.
4. Resposta com lição, quiz ou missão na segunda etapa: confirmar rejeição antes da persistência.
5. Primeira etapa sem missão: confirmar criação válida sem missão.
6. Geração válida: confirmar lições ordenadas, um quiz por lição conforme a estratégia e missão com todos os campos.
7. Geração válida: confirmar que não existem `Answer`, `Feedback`, `MissionProgress` ou `LessonFile` criados.
8. Erro de conexão, timeout e rate limit: confirmar no máximo três tentativas; erro permanente não deve repetir.
9. Reexecução com o mesmo `request_id`: confirmar reutilização da task/trilha e nenhuma duplicata; novo ID cria nova solicitação.
10. Falha durante persistência: confirmar rollback de Track, Steps, Lessons, Quizzes e Mission.

## Evidências esperadas

- O contrato da task está em [contracts/generation-task.md](contracts/generation-task.md).
- Entidades, campos e regras estão em [data-model.md](data-model.md).
- A migration do identificador idempotente deve aplicar e reverter sem erro.
- O resultado final da task deve ser serializável pelo backend Celery e não expor detalhes do provedor.
