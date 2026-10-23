# Contrato HTTP — Mission

Prefixo da API: `/api/v1`.

Todos os endpoints exigem autenticação. Um Step ou Mission inexistente,
excluído logicamente ou pertencente a outro usuário produz o mesmo Problem
Details `404`.

## Criar

`POST /steps/{step_id}/missions`

Request:

```json
{
  "title": "Complete 3 lessons",
  "difficulty": "medium",
  "xpReward": 100,
  "criteria": "number_of_lessons_completed",
  "criteriaValue": 3
}
```

Resposta `201`:

```json
{
  "id": "uuid",
  "stepId": "uuid",
  "title": "Complete 3 lessons",
  "difficulty": "medium",
  "xpReward": 100,
  "criteria": "number_of_lessons_completed",
  "criteriaValue": 3,
  "updatedAt": "2026-10-14T21:00:00",
  "missionProgresses": []
}
```

## Listar

`GET /steps/{step_id}/missions?page=1&page_size=20`

Resposta `200`: `PaginatedResponse[MissionResponse]`, com no máximo 100
itens por página e somente os progressos do usuário autenticado.

## Listar todas as missões, agrupadas por trilha

`GET /missions`

Lista somente missões do usuário autenticado, com trilha e etapa ativas.
Não é necessário informar uma etapa. Os filtros são opcionais e combinados
com AND:

| Query | Valores e comportamento |
|---|---|
| `page` | Inteiro >= 1; padrão `1`. |
| `page_size` | Inteiro entre 1 e 100; padrão `20`. |
| `status` | `idle`, `in_progress` ou `done`. Sem filtro, inclui todos. |
| `track_id` | UUID de uma trilha. Trilha inexistente, excluída ou alheia retorna página vazia. |
| `difficulty` | `easy`, `medium`, `hard` ou `very_hard`. |
| `criteria` | Um dos seis critérios de missão. |
| `q` | Busca parcial no título da missão, sem diferenciar maiúsculas/minúsculas; 1–255 caracteres após remoção de espaços externos. `%` e `_` são literais. |
| `sort` | `recent` (padrão) ou `oldest`, pela última atividade. |

**A paginação conta missões, não trilhas.** `total_items` é o total de missões
que atendem aos filtros; `page_size` limita a soma das missões dos grupos da
página. A seleção e a paginação acontecem antes do agrupamento. Uma trilha
pode aparecer em várias páginas; o frontend pode unir os grupos por `trackId`.
Não são incluídos grupos vazios.

`lastActivityAt` é a maior data entre a atualização da missão e a atualização
do progresso do usuário. Não representa necessariamente a data de criação.
Empates são resolvidos pelo UUID da missão na mesma direção da ordenação.
Os grupos seguem a primeira ocorrência de cada trilha na página, e suas
missões preservam a ordem selecionada.

Missões sem registro de progresso são tratadas como `status: "idle"` e
`score: 0`, inclusive no filtro. `missionProgresses` permanece vazio nesse caso;
este GET não cria nem recalcula progresso. Quando existe registro, o status e
score do usuário são publicados também diretamente no item, para facilitar
a exibição dos cards. Cada item inclui todos os campos de `MissionResponse`,
mais `stepTitle`, `status`, `score` e `lastActivityAt`.

Exemplo de resposta `200`:

```json
{
  "data": [
    {
      "trackId": "a14058b7-7a64-4003-b3ef-01ee8ff092b0",
      "trackTitle": "JavaScript para Web",
      "trackIcon": "📘",
      "missions": [
        {
          "id": "6efcd6d5-43be-466b-a21a-8a67fb365031",
          "stepId": "51a23e1b-40be-4101-baae-06e895049234",
          "stepTitle": "Fundamentos",
          "title": "Conclua 3 lições da etapa: Fundamentos",
          "difficulty": "easy",
          "xpReward": 100,
          "criteria": "number_of_lessons_completed",
          "criteriaValue": 3,
          "updatedAt": "2026-10-22T20:00:00",
          "missionProgresses": [],
          "status": "idle",
          "score": 0,
          "lastActivityAt": "2026-10-22T20:00:00"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 1,
  "total_pages": 1
}
```

Exemplos de uso:

- Todas: `GET /api/v1/missions?page=1&page_size=20`
- Em progresso: `GET /api/v1/missions?status=in_progress&sort=recent`
- Concluídas: `GET /api/v1/missions?status=done`
- De uma trilha: `GET /api/v1/missions?track_id={track_id}`
- Busca e dificuldade: `GET /api/v1/missions?q=Fundamentos&difficulty=easy`

Sem resultados ou página além do total: `200` com `data: []`. Parâmetros
inválidos ou desconhecidos retornam `422`; sem autenticação, `401`.

## Consultar

`GET /missions/{mission_id}`

Resposta `200`: `MissionResponse`.

## Atualizar

`PUT /missions/{mission_id}`

Request parcial:

```json
{
  "title": "Complete 5 lessons",
  "xpReward": 200,
  "criteriaValue": 5
}
```

Resposta `200`: `MissionResponse`. `stepId` não pode ser alterado.

## Excluir

`DELETE /missions/{mission_id}`

Resposta `204` sem corpo. A missão permanece persistida, mas não aparece em
consultas posteriores.

## Erros

- `401`: usuário não autenticado.
- `404`: recurso não encontrado ou não autorizado.
- `422`: UUID, paginação, enum, título ou valores numéricos inválidos.
- `500`: falha interna tratada pelo contrato Problem Details existente.

## Progresso e conclusão automática

`POST /api/v1/quizzes/{quiz_id}/answers` salva a resposta, conclui a lição
quando todos os seus quizzes ativos forem respondidos e recalcula as missões
ativas da mesma trilha em uma única transação. Cada missão usa o escopo de seu
critério, conforme a tabela abaixo. O frontend não envia status nem percentual.

As consultas de missão retornam `missionProgresses` e as consultas de trilha
retornam `steps[].missions[].mission_progresses`. Cada progresso contém `id`,
`status`, `score`, `finished_in` e `updated_at`:

- `idle`: nenhuma resposta registrada no escopo da missão.
- `in_progress`: atividade iniciada, mas o critério ainda não foi satisfeito.
- `done`: critério satisfeito; `score` é `100` e `finished_in` registra a conclusão.
- `score` é o percentual inteiro de progresso (arredondado para baixo), de 0 a 100;
  não representa XP. Para concluir três lições, uma concluída resulta em `33`,
  duas em `66` e três em `100`.

| Critério | Regra e percentual |
|---|---|
| `number_of_lessons_completed` | Lições concluídas **da etapa da missão** / `criteriaValue`. |
| `complete_a_step` | Lições concluídas / total de lições ativas **da etapa da missão**; exige 100%. |
| `get_all_answer_right_in_a_lesson` | Todos os quizzes de pelo menos uma lição **da etapa da missão** têm um acerto; o percentual usa a lição com maior proporção de acertos. |
| `get_all_answers_right` | Quizzes com acerto / total de quizzes **da etapa da missão**, sem incluir outras etapas. Lições sem quizzes ainda bloqueiam a conclusão. |
| `number_of_steps_completed` | Etapas concluídas **da mesma trilha** / `criteriaValue`. |
| `complete_a_track` | Etapas concluídas / total de etapas ativas **da mesma trilha**; exige 100%. |

`criteriaValue` define a meta nos dois critérios de contagem. Nos critérios de
conclusão ou de todos os acertos, a condição é booleana; use `criteriaValue: 1`.
O percentual parcial é calculado a partir do conteúdo ativo.

Regras de avaliação:

- Uma lição precisa ter ao menos um quiz ativo, e todos os seus quizzes precisam
  ter uma resposta do usuário. Acertar é exigido somente pelos critérios de acerto.
- `good` e `perfect` são acertos; `wrong` e `almost_got_it` não são. Uma tentativa
  correta em qualquer momento é suficiente para aquele quiz.
- Repetições de resposta não aumentam a contagem: cada quiz é contado uma vez.
- Status editados manualmente em Lesson/Step não são evidência de conclusão:
  as missões usam as respostas persistidas do proprietário da trilha.
- Etapas sem lições e lições sem quizzes não são concluídas automaticamente.
  Etapas futuras ainda sem conteúdo impedem a conclusão da trilha.
- Recursos excluídos logicamente e respostas de outros usuários não entram no cálculo.
- O limiar de 80% continua servindo apenas para preparar a próxima etapa.
- Missões `done` preservam a data de conclusão e não regridem ao recalcular.
  A unicidade usuário/missão e o lock da trilha evitam duplicação de progresso;
  o ranking deriva o XP dessas missões concluídas.

### Recalcular respostas anteriores

`POST /api/v1/steps/{step_id}/missions/recalculate-progress`

Requer Bearer token e não recebe corpo. Recalcula o progresso com base nas
respostas já salvas, inclusive para missões criadas depois dessas respostas.
Atualiza as missões da trilha da etapa informada, respeitando os escopos acima.
Também cria registros `idle/0` para missões sem atividade. A rota é idempotente.

Resposta: `204` sem corpo. Depois, consulte a trilha ou as missões para obter o
progresso. Etapa/trilha inexistente, excluída ou alheia retorna `404`;
ausência de autenticação retorna `401`.

Exemplo de progresso retornado por uma consulta de missão:

```json
{
  "missionProgresses": [
    {
      "id": "uuid",
      "status": "in_progress",
      "score": 66,
      "finished_in": null,
      "updated_at": "2026-10-22T20:30:00"
    }
  ]
}
```
