# Contrato HTTP: autenticação e perfil (SDB-81)

Base: `/api/v1`. JSON de sucesso usa os nomes abaixo, sem prefixos físicos `usr_*`. Erros usam `Content-Type: application/problem+json` e o formato Problem Details. Não há campo `user_id` na URL ou no corpo das operações de perfil.

## Schemas públicos

| Schema | Campos | Validação |
| --- | --- | --- |
| `UserRegisterRequest` | `name`, `email`, `password` | Todos obrigatórios; nome com trim e 1–255 caracteres; e-mail válido, trim + lower e até 255; senha com ao menos 8 caracteres. |
| `UserLoginRequest` | `email`, `password` | Ambos obrigatórios; e-mail normalizado para busca. Erro de credencial não distingue endereço inexistente, excluído ou senha errada. |
| `UserUpdateRequest` | `name` e/ou `email` | Ao menos um campo; não aceita `null`; mesmas regras de nome/e-mail do cadastro. |
| `PasswordUpdateRequest` | `currentPassword`, `newPassword` | Ambos obrigatórios; nova senha com ao menos 8 caracteres e diferente da atual. |
| `UserResponse` | `id`, `name`, `email` | `id` UUID; somente dados públicos. |
| `UserMeResponse` | `id`, `name`, `email`, `createdAt`, `xp`, `missionsCompleted` | Perfil autenticado, data original de criação e resumo de gamificação; XP e missões concluídas são agregados das missões com progresso `done`. |
| `AuthResponse` | `accessToken`, `tokenType`, `user` | `tokenType` sempre `Bearer`; `user` é `UserResponse`. |

Todos os requests rejeitam campos não previstos com `422`, inclusive `id`, `password_hash`, `usr_*`, timestamps e estado de exclusão. Respostas jamais incluem senha, hash, versão do token ou flags internas.

## POST `/auth/register`

Público. Exemplo de request:

```json
{"name":"Maria Silva","email":"Maria@Exemplo.com","password":"S3nhaF0rte!"}
```

Resposta `201`:

```json
{
  "accessToken": "<jwt>",
  "tokenType": "Bearer",
  "user": {
    "id": "00000000-0000-4000-8000-000000000001",
    "name": "Maria Silva",
    "email": "maria@exemplo.com"
  }
}
```

- `409`: e-mail normalizado já reservado, inclusive por conta excluída ou tentativa concorrente.
- `422`: campos ausentes, inválidos ou extras. Nenhum registro parcial.

## POST `/auth/login`

Público. Request `{"email":" maria@exemplo.com ","password":"S3nhaF0rte!"}`. Resposta `200`: mesmo `AuthResponse` do cadastro, com token novo.

- `401`: e-mail inexistente, usuário excluído ou senha incorreta produzem o mesmo título/detalhe genéricos. Nenhuma indicação de existência da conta.
- `429`: após cinco falhas para e-mail normalizado + origem nos 15 minutos anteriores, tentativas subsequentes ficam bloqueadas por 15 minutos. A quinta falha ainda retorna `401`. O bloqueio vale também para e-mails desconhecidos e mesmo que a senha seguinte seja correta. Header `Retry-After` em segundos.
- `422`: payload inválido, sem incremento da contagem.
- `503`: limitador indisponível; não prosseguir sem o controle.

Uma entrada bem-sucedida fora do bloqueio zera o contador dessa combinação. A resposta não inclui refresh token.

## Autenticação Bearer dos recursos protegidos

Enviar `Authorization: Bearer <accessToken>`. O token tem validade de 60 minutos, identifica somente seu titular e é exigido também nos demais routers existentes. Falta, esquema incorreto, UUID puro, assinatura inválida, expiração, versão antiga após troca de senha e conta excluída retornam `401` com corpo Problem Details e `WWW-Authenticate: Bearer`. Nenhum recurso protegido é retornado.

## GET `/users/me`

Protegido. Sem body. Resposta `200` (`UserMeResponse`):

```json
{"id":"00000000-0000-4000-8000-000000000001","name":"Maria Silva","email":"maria@exemplo.com","createdAt":"2026-10-22T12:00:00","xp":300,"missionsCompleted":2}
```

- `401`: Bearer ausente/inválido ou conta já excluída na autenticação.
- `404`: conta fica indisponível após validar a credencial e antes de concluir a leitura de perfil.

## PUT `/users/me`

Protegido. Enviar `{"name":"Maria S. Souza"}`, `{"email":"maria.souza@exemplo.com"}` ou ambos. Resposta `200`: `UserMeResponse` com valores persistidos e o mesmo resumo atual de XP e missões concluídas retornado por `GET /users/me`.

- `401`/`404`: mesma distinção da consulta de perfil.
- `409`: novo e-mail pertence a outra conta, inclusive excluída. O mesmo e-mail da própria conta não conflita.
- `422`: body vazio, `null`, dados inválidos ou campos extras/proibidos. Nenhuma alteração é aplicada.

Esta rota não modifica a senha nem revoga tokens.

## PUT `/users/me/password`

Protegido. Request:

```json
{"currentPassword":"S3nhaF0rte!","newPassword":"N0vaS3nhaF0rte!"}
```

Resposta `204`: corpo vazio. Após o commit, senha antiga e todos os tokens anteriores, inclusive o usado na chamada, são recusados; entrar com a senha nova produz token válido.

- `401`: Bearer inválido ou senha atual incorreta. Bearer inválido preserva `WWW-Authenticate: Bearer`.
- `404`: conta fica indisponível após autenticação.
- `422`: body inválido, nova senha com menos de 8 caracteres ou igual à atual.
- `429`: após cinco senhas atuais incorretas para a conta + origem em janela de 15 minutos; bloqueio por 15 minutos, `Retry-After`.
- `503`: limitador indisponível.

Falha de credencial conta apenas neste limite; sucesso fora do bloqueio zera somente este contador.

## DELETE `/users/me`

Protegido. Sem body. Resposta `204`: corpo vazio. A linha do usuário e seus relacionamentos permanecem no banco; `usr_is_deleted` passa a verdadeiro e `usr_deleted_at` é preenchido. A partir do commit, login e uso de token antigo retornam `401`.

- `401`: Bearer ausente/inválido ou conta excluída detectada na autenticação.
- `404`: conta ficou indisponível depois da autenticação, sem nova mutação.

## Formato de erro

```json
{
  "type": "https://sidebrain.api/errors/401",
  "title": "Erro de autenticação",
  "status": 401,
  "detail": "Credenciais inválidas."
}
```

`422` pode trazer `errors: [{"field":"body.email","message":"..."}]`. Detalhes de `401` de login e de `429` não variam com a existência da conta. Nenhum erro inclui senha, hash, token ou nome físico de coluna.
