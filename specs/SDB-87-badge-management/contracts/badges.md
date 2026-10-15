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

## Listar badges

`GET /badges?page=1&page_size=20`

Response `200`: envelope paginado de `BadgeResponse`, somente badges ativos,
ordenados por atualização e ID de forma determinística. `page_size` aceita de 1
a 100. Página além do total retorna `data: []` e metadados consistentes.

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
