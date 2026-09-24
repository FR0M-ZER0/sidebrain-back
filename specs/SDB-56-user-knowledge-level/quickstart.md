# Quickstart de Validação — Avaliação de Conhecimento

Este guia valida o fluxo completo descrito em
[contracts/assessments.md](./contracts/assessments.md) e as invariantes de
[data-model.md](./data-model.md). Ele não substitui os testes automatizados.

## Pré-requisitos

- Python 3.11 ou superior;
- Docker com PostgreSQL e Redis disponíveis conforme o `.env`;
- credenciais Groq válidas para o cenário real de geração;
- um usuário autenticado e seu token Bearer;
- branch
  `feat/sdb-56-criar-endpoint-para-gerenciamento-do-nivel-de-conhecimento-do-usuario`.

## Preparar o ambiente

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
```

Em terminais separados:

```bash
uv run dev
```

```bash
uv run celery -A sidebrain_back.core.celery_app worker --loglevel=info
```

Defina as variáveis usadas nos exemplos:

```bash
export API_URL=http://localhost:8080/api/v1
export TOKEN="<token-bearer-do-usuario>"
```

## Cenário 1 — Gerar, consultar e concluir uma avaliação

### 1. Iniciar

```bash
curl -i -X POST "$API_URL/assessments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Python assíncrono",
    "objective": "Criar APIs com FastAPI",
    "skip": false
  }'
```

Resultado esperado:

- `202 Accepted`;
- header `Location` apontando para a avaliação;
- body com `assessment_id` e `status="pending"`;
- nenhuma espera pela resposta do provider.

Guarde o ID retornado:

```bash
export ASSESSMENT_ID="<assessment_id-retornado>"
```

### 2. Consultar até ficar pronta

```bash
curl -s "$API_URL/assessments/$ASSESSMENT_ID" \
  -H "Authorization: Bearer $TOKEN"
```

Enquanto `pending`, `questions=[]`. Ao concluir:

- `status="generated"`;
- exatamente 5 perguntas;
- exatamente 4 alternativas em cada pergunta;
- `score=null` e `level=null`;
- nenhum campo `is_correct` ou `correct_alternative_id`.

### 3. Submeter exatamente uma alternativa por pergunta

Copie os cinco pares de IDs públicos da consulta anterior:

```bash
curl -i -X POST "$API_URL/assessments/$ASSESSMENT_ID/answers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {"question_id": "<q1>", "alternative_id": "<a1>"},
      {"question_id": "<q2>", "alternative_id": "<a2>"},
      {"question_id": "<q3>", "alternative_id": "<a3>"},
      {"question_id": "<q4>", "alternative_id": "<a4>"},
      {"question_id": "<q5>", "alternative_id": "<a5>"}
    ]
  }'
```

Resultado esperado:

- `200 OK`;
- `status="completed"`;
- score entre 0 e 5;
- level conforme `0–1 beginner`, `2–3 intermediate`, `4 advanced`,
  `5 pro`;
- `completed_at` preenchido;
- nenhum gabarito ou correção individual exposto.

Repita a mesma submissão. O resultado esperado é `409 Conflict`, sem
alteração do score, level, respostas ou timestamp já persistidos.

## Cenário 2 — Pular a avaliação

```bash
curl -i -X POST "$API_URL/assessments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Álgebra linear",
    "objective": null,
    "skip": true
  }'
```

Resultado inicial esperado: `202 pending`. Consulte o ID até obter:

- `status="skipped"`;
- `level="beginner"`;
- `score=null`;
- `questions=[]`;
- `completed_at` preenchido.

No log/spy do teste, confirme que a mesma
`tasks.prepare_knowledge_assessment` foi executada e que o client Groq não foi
instanciado nem chamado. Tentar enviar respostas para este ID retorna `409`.

## Cenário 3 — Reutilizar somente avaliação ativa

Envie duas vezes o mesmo payload normalizado de criação antes de responder:

- em `pending`, ambas retornam o mesmo ID e `202`;
- em `generated`, a repetição retorna o mesmo ID e `200`;
- somente uma task é publicada.

Depois de `completed`, repita a criação. Um novo `assessment_id` deve ser
criado, pois estados terminais não bloqueiam reavaliação.

O teste de integração concorrente deve enviar as duas criações em paralelo e
comprovar que o índice único parcial mantém apenas uma linha ativa.

## Cenário 4 — Rejeitar payloads e vínculos inválidos

Valide pelo menos:

1. `subject` ausente, vazio ou só espaços, inclusive com `skip=true`:
   `422`;
2. `objective` informado só com espaços: `422`;
3. `user_id`, `level`, `score`, `status` ou campo extra: `422`;
4. quatro ou seis respostas: `422`;
5. pergunta repetida: `422`;
6. pergunta desconhecida ou de outra avaliação: `422`;
7. alternativa de outra pergunta: `422`;
8. avaliação inexistente ou de outro usuário: o mesmo `404`;
9. submissão em `pending`, `skipped`, `completed` ou `failed`: `409`.

Após cada `422` ou `409`, consulte a avaliação e confirme que nenhum estado,
score, level ou conjunto de respostas mudou.

## Cenário 5 — Falhas e retry da task

Com doubles do provider:

- `APIConnectionError`, `APITimeoutError` e `RateLimitError`: confirmar
  até três retries adicionais e esperas progressivas 1/2/4 segundos;
- sucesso após falha transitória: estado final `generated`, sem conteúdo
  parcial anterior;
- retries esgotados: estado final `failed`, questions vazias e error code
  sanitizado;
- JSON/schema/gabarito inválido: falha definitiva imediata, sem retry;
- falha de publicação no endpoint: `503` e registro `failed`;
- redelivery após `generated`, `skipped`, `completed` ou `failed`: nenhum
  dado é sobrescrito.

Inspecione os logs e confirme ausência de subject, objective, prompt, resposta
bruta, alternativas, gabarito e credenciais.

## Testes automatizados

Executar primeiro a suíte focal:

```bash
uv run pytest \
  tests/unit/test_knowledge_assessment_schema.py \
  tests/unit/test_knowledge_assessment_generator.py \
  tests/unit/test_knowledge_assessment_service.py \
  tests/unit/test_knowledge_assessment_repository.py \
  tests/contract/test_knowledge_assessment_contract.py \
  tests/contract/test_knowledge_assessment_http_contract.py \
  tests/integration/test_knowledge_assessment_migration.py \
  tests/integration/test_knowledge_assessment_task.py \
  tests/integration/test_knowledge_assessment_lifecycle.py
```

Depois, executar os gates completos:

```bash
uv run ruff check .
uv run pytest
```

Se `uv` não estiver no PATH no ambiente Windows local, os equivalentes são:

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```

## Verificação da migration

Em banco de teste descartável:

```bash
uv run alembic upgrade head
uv run alembic downgrade b2c3d4e5f6a7
uv run alembic upgrade head
```

Confirmar:

- criação e remoção reversível das quatro tabelas e do enum de status;
- preservação do enum compartilhado `step_level` no downgrade;
- FKs compostas e cascatas;
- índice único parcial para avaliações `pending|generated`;
- índice que permite no máximo uma alternativa correta por pergunta;
- checks de estado, score e level.
