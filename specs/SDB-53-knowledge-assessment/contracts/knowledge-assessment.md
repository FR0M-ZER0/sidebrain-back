# Contrato Interno: Knowledge Assessment

Este contrato descreve a fronteira entre o fluxo chamador, a task Celery e o fluxo posterior. Nao cria endpoint HTTP.

## Disparo da task

Nome: `tasks.prepare_knowledge_assessment`

Argumentos JSON:

```json
{
  "user_id": "8d4e1d4b-3b0e-4f2d-a5f4-123456789abc",
  "subject": "Python assíncrono",
  "objective": "Criar APIs com FastAPI",
  "skip": false
}
```

`user_id` e fornecido pelo contexto autenticado do fluxo chamador. O cliente final nao deve preencher esse campo. Quando `skip=true`, `subject` pode ser omitido.

## Resultado generated

```json
{
  "assessment_id": "a0c2e6f1-71f8-4f80-91db-123456789abc",
  "status": "generated",
  "level": null,
  "questions": [
    {
      "id": "q1",
      "statement": "Qual afirmacao descreve ...?",
      "alternatives": [
        {"id": "a", "text": "..."},
        {"id": "b", "text": "..."},
        {"id": "c", "text": "..."},
        {"id": "d", "text": "..."}
      ]
    }
  ]
}
```

O array `questions` contem exatamente cinco itens. O exemplo mostra uma pergunta; a implementacao deve retornar cinco.

## Resultado skipped

```json
{
  "assessment_id": "a0c2e6f1-71f8-4f80-91db-123456789abc",
  "status": "skipped",
  "level": "beginner",
  "questions": []
}
```

## Falhas

- Contexto invalido, resposta externa invalida ou quantidade diferente de cinco: falha definitiva de validacao, sem resultado parcial.
- Conexao, timeout ou rate limit do provider: retry limitado com backoff.
- Credencial invalida ou erro HTTP definitivo do provider: falha definitiva, sem retry indefinido.

O fluxo posterior deve consumir somente um `AsyncResult` concluido com um dos dois formatos acima. A task nao cria nem altera Track, Step, Lesson ou Mission.
