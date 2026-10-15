# Quickstart de validação: SDB-81

Este guia valida os endpoints implementados conforme o [plano](plan.md) e o
[contrato HTTP](contracts/auth-profile.md), cobrindo configuração, migração,
autenticação e gerenciamento do próprio perfil.

## Pré-requisitos e implantação

1. Configurar `.env` a partir de `.env.example`, incluindo PostgreSQL, Redis e um `JWT_SECRET_KEY` forte e privado. Não versionar o segredo. Confirmar que a origem real do cliente chega a `request.client.host` por proxy confiável.
2. Auditar os e-mails de **todas** as contas, inclusive excluídas, antes de criar o índice:

   ```sql
   SELECT lower(btrim(usr_email)) AS email_normalizado,
          count(*) AS quantidade,
          array_agg(usr_id) AS usuarios
   FROM "user"
   GROUP BY 1
   HAVING count(*) > 1;
   ```

   Resultado esperado: zero linhas. Se houver colisões, reconciliar titulares e dados relacionados antes de continuar. Auditar também `usr_password_hash`: valores fictícios como `hash_ana` do `seed.py` não permitem entrada e exigem provisionamento de credencial válida antes do corte.
3. Instalar, iniciar infraestrutura e aplicar a migração:

   ```bash
   uv sync
   docker compose up -d
   uv run alembic upgrade head
   uv run dev
   ```

   Não executar `seed.py` contra base com dados, pois ele apaga registros. Em produção, coordenar a implantação e a mudança dos consumidores antes de recusar o Bearer UUID antigo.

## Verificação automatizada após a implementação

```bash
uv run ruff check .
uv run pytest
```

A cobertura deve incluir schemas/services/security/limitador em `tests/unit`, persistência e migração em `tests/integration`, respostas/headers em `tests/contract` e SC-006 em `tests/performance`. Validar também `uv run alembic downgrade -1` e novo upgrade em banco descartável: a versão da credencial e o índice funcional devem desaparecer/reaparecer sem apagar contas. Não fazer downgrade da produção durante o corte dos consumidores.

## Fluxo ponta a ponta

Com a API em `http://127.0.0.1:8080`, executar em shell com `curl`:

```bash
BASE=http://127.0.0.1:8080/api/v1
curl -i -X POST "$BASE/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Maria Silva","email":" Maria@Exemplo.com ","password":"S3nhaF0rte!"}'
```

Esperado: `201`, `accessToken`, `tokenType: "Bearer"` e `user` contendo somente `id`, `name`, `email: "maria@exemplo.com"`. Guardar o token retornado como `TOKEN` no shell. Confirmar no banco que `usr_password_hash` não é a senha enviada.

```bash
curl -i "$BASE/users/me" -H "Authorization: Bearer $TOKEN"
curl -i -X PUT "$BASE/users/me" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Maria S. Souza"}'
curl -i -X PUT "$BASE/users/me/password" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"currentPassword":"S3nhaF0rte!","newPassword":"N0vaS3nhaF0rte!"}'
```

Esperado: `200` com perfil público nas duas primeiras chamadas e `204` sem corpo na terceira. O token `TOKEN` agora recebe `401` em `GET /users/me` e em um endpoint protegido preexistente, como `GET /tracks`. A senha antiga falha no login; a nova gera outro token, `NEW_TOKEN`.

```bash
curl -i -X DELETE "$BASE/users/me" \
  -H "Authorization: Bearer $NEW_TOKEN"
curl -i "$BASE/users/me" \
  -H "Authorization: Bearer $NEW_TOKEN"
```

Esperado: `204` vazio, depois `401` com `WWW-Authenticate: Bearer`. O login dessa conta também recebe `401`; a linha do usuário e os relacionamentos continuam no banco, com `usr_is_deleted=true` e `usr_deleted_at` preenchido.

## Casos de contrato e segurança

1. Repetir o cadastro com o mesmo e-mail em outra caixa, inclusive após soft delete: `409`. Enviar dois cadastros simultâneos com o mesmo endereço: exatamente um `201` e um `409`, sem conta duplicada. Repetir na atualização de e-mail entre contas.
2. Enviar corpo vazio, nome só com espaços, e-mail inválido, senha curta, `null` e campos proibidos para cada request pertinente: `422` em Problem Details, sem mutação. A atualização só do próprio e-mail atual normalizado recebe `200`.
3. Testar Bearer ausente, UUID puro, token adulterado, expirado e token de usuário excluído em `/users/me` e um router antigo: `401`, `WWW-Authenticate: Bearer`, nenhum dado. Simular exclusão entre autenticação e operação de perfil: `404` sem alteração.
4. Testar e-mail desconhecido, conta excluída e senha errada no login: mesma resposta `401`, sem indicação da causa. Senha atual errada na troca: `401`, senha antiga preservada. Nova senha igual à atual: `422`.
5. Para cada par e-mail normalizado + origem, provocar cinco falhas de login em 15 minutos: cinco `401`; a tentativa seguinte recebe `429` com `Retry-After` e Problem Details, inclusive para e-mail desconhecido e senha correta. Após 15 minutos, o bloqueio termina. Repetir para conta + origem na troca de senha; os contadores das duas operações são independentes. Um sucesso zera o próprio contador; `422` não conta. Repetir sob concorrência e simular Redis indisponível: não deve haver bypass.
6. Confirmar `Content-Type: application/problem+json` nos erros, ausência de senha/hash/token em logs e erros, e ausência de `usr_*` em todas as respostas.

## Corte dos consumidores

Atualizar clientes e guias que hoje enviam `Authorization: Bearer <usr_id>`, inclusive testes históricos. Clientes existentes devem obter `accessToken` por `POST /auth/login` com credenciais válidas; novos clientes podem registrar conta. Depois do corte, UUID puro não funciona, e token expirado exige nova entrada. Comunicar aos consumidores o horário do corte e validar, com ao menos cinco integrações, cadastro, entrada e consulta de perfil sem explicações adicionais (SC-007).

## Critério de conclusão

Os cenários acima, os critérios SC-001 a SC-008, lint, suíte pytest, migração e a medição de 20 clientes simultâneos devem passar no ambiente de validação antes da integração da implementação.
