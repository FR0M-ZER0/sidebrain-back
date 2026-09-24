# Contrato interno: Knowledge Assessment

A task oficial continua registrada como `tasks.prepare_knowledge_assessment`.
Durante a janela de migração ela aceita os contratos v1 e v2 para que mensagens
já publicadas possam ser drenadas sem quebra de compatibilidade.

## Contrato v1 — compatibilidade temporária

Chamadas antigas usam argumentos posicionais ou equivalentes:

```json
{
  "user_id": "8d4e1d4b-3b0e-4f2d-a5f4-123456789abc",
  "subject": "Python assíncrono",
  "objective": "Criar APIs com FastAPI",
  "skip": false
}
```

O retorno legado continua incluindo `assessment_id`, `status`, `level` e
`questions`. Em `generated`, existem cinco perguntas com quatro alternativas e
`level=null`; em `skipped`, `questions=[]` e `level="beginner"`.

## Contrato v2 — fluxo persistido

Novos produtores devem enviar somente argumentos nomeados e informar
`contract_version=2`:

```json
{
  "contract_version": 2,
  "assessment_id": "36e29823-e41f-4212-8c28-c3de41beb183",
  "user_id": "8d4e1d4b-3b0e-4f2d-a5f4-123456789abc",
  "subject": "Python assíncrono",
  "objective": "Criar APIs com FastAPI",
  "skip": false
}
```

O `assessment_id` é criado e persistido pela API antes do enqueue e permanece
canônico durante todo o ciclo. A task abre sua própria `AsyncSession`, confere o
contexto e não aceita que o provider substitua esse identificador.

O provider retorna somente o payload interno abaixo. Seus IDs são locais ao
provider e nunca se tornam UUIDs públicos:

```json
{
  "questions": [
    {
      "id": "q1",
      "statement": "Qual construção aguarda uma coroutine?",
      "alternatives": [
        {"id": "a", "text": "await"},
        {"id": "b", "text": "yield"},
        {"id": "c", "text": "pass"},
        {"id": "d", "text": "break"}
      ],
      "correct_alternative_id": "a"
    }
  ]
}
```

O payload completo contém exatamente cinco perguntas distintas, quatro
alternativas distintas por pergunta e um `correct_alternative_id` pertencente à
própria pergunta. O backend cria os UUIDs públicos e persiste o gabarito apenas
internamente. O retorno v2 ao result backend é mínimo:

```json
{
  "assessment_id": "36e29823-e41f-4212-8c28-c3de41beb183",
  "status": "generated"
}
```

Em `skip=true`, a mesma task não constrói o client do provider e persiste
`skipped/beginner`. Falhas transitórias recebem três retries com esperas de 1,
2 e 4 segundos; falhas definitivas persistem `failed`. Redelivery de estado
terminal é no-op.

## Remoção futura do v1

O contrato v1 só pode ser removido depois de:

1. atualizar todos os produtores para argumentos nomeados v2;
2. confirmar que não há mensagens v1 pendentes ou reservadas no broker;
3. drenar ou expirar os resultados legados ainda consumidos;
4. verificar métricas e logs por pelo menos uma janela operacional completa;
5. remover os testes v1 e publicar a alteração como breaking change.

A task não cria nem altera Track, Step, Lesson ou Mission. Logs não incluem
subject, objective, prompt, resposta bruta, alternativas, gabarito ou
credenciais.
