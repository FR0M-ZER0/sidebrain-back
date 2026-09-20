# Quickstart de Validacao

## Pre-requisitos

- Python >= 3.11, `uv` e dependencias instaladas com `uv sync`.
- Redis disponivel para execucao real do worker (`docker compose up -d`).
- `GROQ_API_KEY`, `GROQ_MODEL`, `REDIS_HOST` e `REDIS_PORT` configurados para smoke test externo.

## Validacao automatizada sem rede

Execute os testes focados:

```bash
uv run pytest tests/unit/test_knowledge_assessment_schema.py tests/unit/test_knowledge_assessment_service.py tests/integration/test_knowledge_assessment_task.py tests/contract/test_knowledge_assessment_contract.py
```

O resultado esperado inclui cenarios de skip sem chamada ao provider, cinco perguntas validas, assunto invalido, resposta incompleta, JSON invalido e retry apenas para falhas transitorias.

## Validacao completa

```bash
uv run ruff check .
uv run pytest
```

## Smoke test da task

1. Inicie Redis com `docker compose up -d`.
2. Inicie um worker Celery apontando para `sidebrain_back.core.celery_app.celery_app`.
3. Envie o contrato de disparo documentado em [contracts/knowledge-assessment.md](contracts/knowledge-assessment.md) pelo fluxo chamador.
4. Consulte o `AsyncResult` ate concluir.
5. Confirme que `generated` possui cinco perguntas estruturadas ou que `skipped` possui `level=beginner` e `questions=[]`.
6. Confirme no Flower ou logs estruturados o status da task, tentativa e falha sem prompt, resposta ou credenciais.

## Criterios de aprovacao

- Nenhuma chamada Groq ocorre no caminho `skip=true`.
- Nenhum resultado parcial e retornado quando a validacao falha.
- Somente indisponibilidade transitoria dispara retry, limitado a tres novas tentativas.
- Nenhuma entidade de trilha ou conteudo e criada ou alterada.
