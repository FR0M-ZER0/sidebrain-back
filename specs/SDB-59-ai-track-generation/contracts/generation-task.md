# Contrato Interno: Task de Geração

A feature não adiciona endpoint HTTP. O contrato abaixo é entre o fluxo de
solicitação/acompanhamento e a task Celery.

## Entrada serializável

```json
{
  "request_id": "uuid-estavel-da-solicitacao",
  "user_id": "uuid-do-usuario",
  "goal": "Aprender fundamentos de Python",
  "topic": "Python",
  "knowledge_level": "beginner",
  "assessment_answers": [
    {"question": "...", "answer": "...", "rate": "wrong"}
  ]
}
```

`knowledge_level` e `assessment_answers` podem ser omitidos. `request_id`,
`user_id`, `goal` e `topic` são obrigatórios. IDs são parâmetros internos e
nunca aparecem no conteúdo enviado pela IA como identificadores de persistência.

## Prompt e resposta da IA

O prompt deve declarar que:

- a coleção completa de etapas deve ser gerada na ordem da estratégia;
- o conteúdo detalhado deve existir somente para a primeira etapa;
- as etapas posteriores devem conter apenas posição, nível e título;
- a resposta deve seguir o schema estruturado, sem texto fora do JSON.

A resposta validada tem a forma lógica:

```json
{
  "title": "Python do zero",
  "description": "...",
  "steps": [
    {
      "position": 1,
      "level": "beginner",
      "title": "Sintaxe essencial",
      "lessons": [
        {
          "position": 1,
          "title": "Variáveis",
          "text": "...",
          "quiz": {"question": "..."}
        }
      ],
      "mission": {
        "title": "Pratique variáveis",
        "difficulty": "easy",
        "xp_reward": 20,
        "criteria": "number_of_lessons_completed",
        "criteria_value": 1
      }
    },
    {
      "position": 2,
      "level": "intermediate",
      "title": "Estruturas de controle",
      "lessons": [],
      "mission": null
    }
  ]
}
```

A implementação deve rejeitar conteúdo não vazio em etapas posteriores, campos
faltantes, posições inválidas, enums desconhecidos, valores fora do domínio e
missão não prevista.

## Saída da task

Sucesso:

```json
{
  "status": "succeeded",
  "request_id": "uuid-estavel-da-solicitacao",
  "track_id": "uuid-da-trilha-gerada"
}
```

Falha tratável:

```json
{
  "status": "failed",
  "request_id": "uuid-estavel-da-solicitacao",
  "error_code": "generation_validation_failed",
  "detail": "Não foi possível gerar a trilha."
}
```

Os códigos devem distinguir falha transitória esgotada, resposta inválida,
entrada inválida, conflito de idempotência e persistência. A mensagem pública
não deve conter SQL, stack trace, prompt, token ou resposta bruta do provedor.

## Retry e idempotência

Falhas de conexão, timeout e rate limit podem ser repetidas até três tentativas
totais com backoff. Falhas permanentes e validação não geram retry. Reentrega
com o mesmo `request_id` retorna a task/trilha já associada; um novo pedido exige
novo identificador.
