# Contrato HTTP — Avatar

Base: `/api/v1`. Todas as rotas abaixo exigem `Authorization: Bearer
<accessToken>`.

## `GET /avatars`

Retorna somente as opções ativas:

```json
{
  "data": [
    {
      "slug": "cat",
      "name": "Gato",
      "imageUrl": "/static/avatars/cat.png"
    }
  ]
}
```

O array contém os dez registros iniciais enquanto todos estiverem ativos. O
catálogo não usa paginação porque seu tamanho é pequeno e fixado pelo backend.

## `GET /users/me`

O response atual permanece compatível e ganha:

```json
{
  "avatar": {
    "slug": "cat",
    "name": "Gato",
    "imageUrl": "/static/avatars/cat.png"
  }
}
```

Sem seleção ou com avatar inativo, `avatar` usa o objeto default descrito em
[data-model.md](../data-model.md).

## `PUT /users/me`

O request atual ganha o campo opcional `avatar`:

```json
{ "avatar": "fox" }
```

- campo ausente: mantém a seleção atual;
- `{"avatar": null}`: remove a seleção;
- slug inexistente ou inativo: rejeita com Problem Details e não altera o
  perfil;
- `name` e `email` mantêm o comportamento atual.

As referências são relativas e utilizáveis sob
`/static/avatars/{slug}.png`. `default.png` deve existir e permanecer servida.
