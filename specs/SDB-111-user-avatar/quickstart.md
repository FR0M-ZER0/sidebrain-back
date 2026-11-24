# Quickstart de validação — SDB-111

## Pré-requisitos

Configure `JWT_SECRET_KEY` e o PostgreSQL conforme o README:

```bash
docker compose up -d
uv run alembic upgrade head
uv run dev
```

Cadastre ou autentique um usuário e guarde o `accessToken`.

## Cenário principal

Com `Authorization: Bearer <accessToken>`:

```bash
curl http://localhost:8000/api/v1/avatars
curl http://localhost:8000/api/v1/users/me
curl -X PUT http://localhost:8000/api/v1/users/me ^
  -H "Content-Type: application/json" ^
  -d "{\"avatar\":\"cat\"}"
curl http://localhost:8000/static/avatars/cat.png
curl -X PUT http://localhost:8000/api/v1/users/me ^
  -H "Content-Type: application/json" ^
  -d "{\"avatar\":null}"
```

Resultados esperados: o catálogo lista os dez avatares ativos; o perfil inicial
retorna `default.png`; a seleção retorna `cat.png`; o arquivo responde com
sucesso; e a remoção volta ao default sem alterar os demais campos.

## Cenários de rejeição e manutenção

- Slug inexistente ou desativado retorna Problem Details e preserva o avatar.
- Sem token, toda operação protegida retorna erro de autenticação.
- Após desativar um registro, o perfil retorna `default.png`; outro slug ativo
  continua selecionável.

## Testes automatizados

```bash
uv run pytest tests/unit tests/contract
uv run pytest tests/integration/test_user_profile_read.py tests/integration/test_user_profile_update.py tests/integration/test_avatar_catalog.py
uv run ruff check .
```

Os testes cobrem catálogo autenticado, imagem padrão, seleção, alteração,
remoção, slugs inválidos/inativos, autenticação e regressão do perfil.
