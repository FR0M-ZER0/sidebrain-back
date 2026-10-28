# Contrato HTTP: Badges

Base path: `/api/v1`. Todos os endpoints exigem Bearer válido reconhecido por
`get_current_user`. Qualquer usuário autenticado pode operar.

## Representações

### BadgeResponse

```json
{
  "id": "00000000-0000-0000-0000-000000000101",
  "name": "Primeira trilha",
  "description": "Conclua uma trilha.",
  "rarity": "common",
  "criteria": "tracks_completed",
  "criteria_value": 1,
  "updated_at": "2026-10-07T12:00:00Z",
  "progress": [
    {
      "id": "00000000-0000-0000-0000-000000000201",
      "status": "in_progress",
      "updated_at": "2026-10-07T12:30:00Z"
    }
  ]
}
```

`progress` contém somente o progresso do usuário autenticado e é `[]` quando
não existe. Nenhum nome `bdg_*` ou `bpg_*`, vínculo interno ou flag de exclusão
é publicado.

Os badges são definições globais; a associação/progresso é independente para
cada usuário. O progresso tem os estados `idle`, `in_progress` e `done` e não
aceita escrita do cliente.

### Lista paginada

```json
{
  "data": [],
  "page": 1,
  "page_size": 20,
  "total_items": 0,
  "total_pages": 0
}
```

## Criar badge

`POST /badges`

Request:

```json
{
  "name": "  Primeira trilha  ",
  "description": "Conclua uma trilha.",
  "rarity": "common",
  "criteria": "tracks_completed",
  "criteria_value": 1
}
```

Response `201`: `BadgeResponse`, com `name` igual a `Primeira trilha` e
`progress: []`.

Quando o badge é criado depois de atividades que já satisfazem seu critério,
use `POST /badges/recalculate-progress` para sincronizar o progresso do usuário.

## Listar badges

`GET /badges?page=1&page_size=20`

Response `200`: envelope paginado de `BadgeResponse`, somente badges ativos,
ordenados por atualização e ID de forma determinística. `page_size` aceita de 1
a 100. Página além do total retorna `data: []` e metadados consistentes.

Filtros opcionais podem ser combinados com AND:

| Query | Valores e comportamento |
|---|---|
| `status` | `idle`, `in_progress` ou `done`, referente somente ao progresso do usuário autenticado. Badge sem progresso é considerado `idle`. |
| `rarity` | `common`, `rare`, `epic` ou `legendary`. |
| `criteria` | `xp_gained`, `tracks_completed`, `lessons_completed`, `right_answers`, `day_streak`, `tracks_created` ou `missions_completed`. |
| `q` | Busca parcial, case-insensitive, em nome ou descrição; 1–255 caracteres após remoção de espaços externos. `%` e `_` são tratados literalmente. |
| `sort` | `recent` (padrão) ou `oldest`, usando a maior data entre atualização da definição e atualização do progresso do usuário; empates usam UUID do badge. |

Exemplos:

- Todos os badges: `GET /api/v1/badges?page=1&page_size=20`
- Badges em progresso: `GET /api/v1/badges?status=in_progress&sort=recent`
- Badges raros ainda não iniciados: `GET /api/v1/badges?status=idle&rarity=rare`
- Buscar por nome/descrição: `GET /api/v1/badges?q=Python`
- Critério de streak: `GET /api/v1/badges?criteria=day_streak`

Filtros de progresso usam outer join restrito ao usuário atual. Portanto, o
progresso de outro usuário nunca altera o status do badge para o chamador. A
listagem é somente leitura: não cria nem recalcula progressos. Sem resultados,
retorna `200` com `data: []`; valores de filtro inválidos ou parâmetros
desconhecidos retornam `422`.

## Consultar badge

`GET /badges/{badge_id}`

Response `200`: `BadgeResponse` ativo, com progresso filtrado pelo usuário.
UUID malformado ou parâmetro de paginação inválido retorna `422`. Badge
inexistente ou removido retorna `404`.

## Atualizar badge

`PATCH /badges/{badge_id}`

Request parcial:

```json
{
  "name": "Primeira trilha avançada",
  "description": null
}
```

Response `200`: `BadgeResponse` atualizado. O payload deve conter ao menos um
campo editável; campos omitidos são preservados. `id`, datas, progresso,
raridade/critério inválidos, campos extras, nome vazio ou conflito de nome
retornam `422` ou `409`, respectivamente, sem alteração parcial.

## Remover badge

`DELETE /badges/{badge_id}`

Response `204` sem body. O badge permanece armazenado com exclusão lógica e
seus progressos permanecem preservados. Repetir a operação retorna `404`.

## Conceder e atualizar progresso

O progresso individual é atualizado automaticamente no mesmo commit que uma
atividade relevante:

- responder a um quiz atualiza respostas corretas, lições concluídas, trilhas
  concluídas, missões concluídas, XP ganho e streak diário;
- persistir uma trilha nova, por geração ou criação legada, atualiza trilhas
  criadas e o streak diário.

As consultas de badges carregam o progresso salvo do usuário. O badge passa a
`idle` quando o valor do critério é zero, `in_progress` quando ele é positivo
mas inferior à meta e `done` quando atinge ou supera `criteria_value`. Um badge
`done` é terminal: atividades futuras e recálculos não removem a conquista.

### Escopo das métricas

| Critério | Valor contado |
|---|---|
| `xp_gained` | Soma dos `xpReward` das missões concluídas do usuário, usando a mesma fonte do ranking. |
| `missions_completed` | Quantidade de missões ativas com progresso `done` do usuário. |
| `tracks_created` | Trilhas persistidas pelo usuário, inclusive as posteriormente excluídas logicamente. |
| `lessons_completed` | Lições ativas em trilhas ativas do usuário que têm ao menos um quiz ativo e todos esses quizzes respondidos. Não exige acertos. |
| `right_answers` | Quizzes ativos da hierarquia ativa do usuário com ao menos uma resposta `good` ou `perfect`; cada quiz conta uma vez. |
| `tracks_completed` | Trilhas ativas com ao menos uma etapa ativa e conteúdo não vazio em cada etapa: cada etapa precisa ter lições ativas, e cada lição precisa ter ao menos um quiz ativo, todos respondidos. |
| `day_streak` | Dias consecutivos de atividade usando a data UTC da atividade. Responder um quiz (mesmo incorretamente) ou persistir uma trilha conta como atividade; várias atividades no mesmo dia contam apenas uma vez. Um dia sem atividade reinicia o streak na próxima atividade. |

Missões e seus progressos excluídos logicamente não geram XP nem entram na
contagem de missões concluídas. Em critérios de conteúdo, pais e filhos
excluídos logicamente são ignorados. Uma lição/etapa/trilha vazia não é
considerada concluída.

### Recalcular progresso existente

`POST /badges/recalculate-progress`

Não recebe body. Recalcula os estados a partir dos dados já persistidos e é
idempotente. É útil para badge criado após as atividades ou para sincronizar
dados anteriores à automação. Não registra uma nova atividade nem incrementa o
streak diário. Resposta `204` sem body; `401` para usuário não autenticado e
`404` se o usuário não estiver disponível.

O recálculo é executado sob lock do usuário para que atividades concorrentes
não percam atualizações nem criem progressos duplicados. O status `done` e o
ranking derivado de XP permanecem consistentes.

## Autorização e erros

- `401`: credencial ausente, inválida ou usuário excluído.
- `404`: badge inexistente ou removido; a API não distingue os casos.
- `409`: nome normalizado já usado por outro badge ativo.
- `422`: UUID, paginação ou payload inválido.
- `500`: falha interna sem SQL, stack trace ou credenciais.

Formato mínimo de Problem Details:

```json
{
  "type": "https://sidebrain.api/errors/404",
  "title": "Não encontrado",
  "status": 404,
  "detail": "Badge não encontrado"
}
```

Erros de validação podem incluir `errors` com campo e mensagem.
