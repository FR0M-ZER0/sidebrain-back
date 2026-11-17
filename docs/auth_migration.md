# Migração para autenticação JWT

A SDB-81 substitui o Bearer contendo UUID puro por JWT HS256. O corte deve ser
coordenado com todos os consumidores: depois da implantação, nenhum endpoint
protegido aceita `Authorization: Bearer <usr_id>`.

## Preparação

1. Defina um `JWT_SECRET_KEY` forte, privado e diferente por ambiente.
2. Antes da migração, procure colisões em todas as contas, inclusive excluídas:

   ```sql
   SELECT lower(btrim(usr_email)) AS email_normalizado,
          count(*) AS quantidade,
          array_agg(usr_id) AS usuarios
   FROM "user"
   GROUP BY lower(btrim(usr_email))
   HAVING count(*) > 1;
   ```

3. Reconcile cada colisão antes do upgrade. A migração é interrompida se a
   consulta retornar linhas.
4. Audite `usr_password_hash`. Valores fictícios ou incompatíveis não podem ser
   convertidos em senha; provisione uma nova credencial Argon2id por processo
   operacional.

Se a criação concorrente do índice falhar, remova o índice inválido com
`DROP INDEX CONCURRENTLY IF EXISTS uq_user_usr_email_normalized`, corrija a
colisão e reaplique a revisão.

## Mudança dos clientes

- Novas contas usam `POST /api/v1/auth/register`.
- Contas existentes usam `POST /api/v1/auth/login`.
- O cliente armazena `accessToken` e envia
  `Authorization: Bearer <accessToken>`.
- O token expira em 60 minutos. Não existe refresh token; ao expirar, o cliente
  realiza novo login.
- Trocar a senha invalida imediatamente todos os tokens anteriores.
- Excluir a conta invalida o login e os tokens anteriores.

O deploy deve aplicar a migração, publicar a API e trocar os consumidores na
mesma janela acordada. Não mantenha aceitação paralela do UUID puro.

## Reversão

O downgrade remove o índice normalizado e `usr_token_version`, preservando as
contas. Tokens emitidos pelo novo código deixam de ser compatíveis após a
reversão; coordene também o rollback dos clientes. Não reverta produção no meio
do corte sem um plano explícito de credenciais.
