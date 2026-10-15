# Research: SDB-81

## Contexto verificado

`core/auth.py` aceita hoje o UUID como Bearer e consulta `User` ativo. `User` já contém nome, e-mail, hash e soft delete, mas o banco só tem `UNIQUE (usr_email)`, sensível a caixa. `core/errors.py` produz corpo Problem Details, porém descarta os headers de `HTTPException`, inclusive `WWW-Authenticate`. Redis 7 já atende Celery nos bancos `/0` e `/1`; não há limitador HTTP. `seed.py` usa `usr_password_hash="hash_ana"`, que não é hash verificável. Testes e guias antigos ainda usam UUID puro como Bearer.

## Decisão: hash e validação de senha

- **Decision**: adicionar `pwdlib[argon2]`; gerar Argon2id com `PasswordHash.recommended()` e verificar a senha contra o hash persistido. Executar geração/verificação em thread para não bloquear o event loop dos endpoints assíncronos. Exigir ao menos 8 caracteres na senha nova; não acrescentar regra de complexidade não pedida.
- **Rationale**: Argon2id é apropriado para senha, e o tutorial atual de segurança do FastAPI o usa. O custo deverá ser medido no ambiente alvo para SC-006; nenhum valor de senha ou hash entra em resposta ou log.
- **Alternatives considered**: texto claro ou hash rápido não protegem a senha; bcrypt é possível, mas a escolha Argon2id evita seu limite tradicional de entrada e segue a referência atual do FastAPI. `usr_updated_at` não representa política de senha.

## Decisão: JWT e revogação

- **Decision**: adicionar `PyJWT`, configurar segredo forte obrigatório fora do repositório e fixar HS256 na emissão e decodificação. Exigir `sub` (UUID), `iat`, `exp` (60 min) e `ver` (inteiro). O provider HTTP `get_current_user`, em `routers/v1/auth_router.py`, extrai o Bearer e chama `AuthService`; o service valida a identidade via repository, busca usuário ativo e compara `ver` à nova coluna `usr_token_version`. `core/auth.py` deixa de consultar o model e contém só o extrator HTTP compartilhado. Troca de senha bloqueia a linha e incrementa versão junto do novo hash na mesma transação. Exclusão é recusada pela leitura de usuário ativo.
- **Rationale**: a verificação a cada acesso revoga tokens antigos após o commit sem lista de bloqueio; os routers protegidos já dependem de `get_current_user` e mantêm sua assinatura. Mudar apenas o import retira de `core` o acesso indevido ao model e respeita `router -> service -> repository -> model`. Tokens UUID puros passam a falhar.
- **Alternatives considered**: usar `usr_updated_at` é incorreto porque hoje só tem default inicial e pode mudar por perfil; guardar todos os tokens ou manter blacklist adiciona estado e limpeza; derivar claim do hash com HMAC acopla token à implementação do hash. A coluna inteira é explícita e pequena.
- **Limite operacional**: requests que já passaram pela autenticação antes do commit de troca/exclusão não podem ser cancelados retroativamente; a próxima validação observa o estado novo. Conter mutações críticas com nova leitura/lock no service.

## Decisão: unicidade case-insensitive

- **Decision**: normalizar entradas com strip + lower; consultar e-mail usando `lower(btrim(usr_email))`; criar índice único funcional `uq_user_usr_email_normalized` nessa expressão, incluindo linhas excluídas. Manter a constraint única física existente. Antes da implantação, executar consulta de grupos duplicados por e-mail normalizado e interromper a migração caso existam; reconciliar titulares sem apagar relacionamentos. Converter somente SQLSTATE `23505` da constraint/índice de e-mail em `409` após rollback.
- **Rationale**: a pré-consulta melhora a mensagem, mas apenas o índice resolve corrida entre registros/alterações simultâneos. A expressão cobre registros antigos com espaços ou letras maiúsculas sem reescrever dados.
- **Alternatives considered**: confiar apenas em lower no service permite corrida e writes externos; `UNIQUE (usr_email)` atual permite variações de caixa; normalização em massa poderia mudar dados legados e não resolveria a corrida sem índice.
- **Implantação**: em base ativa, criar índice concorrentemente com bloco autocommit do Alembic, após pré-verificação. Se uma escrita concorrente causar falha, remover eventual índice `INVALID` com `DROP INDEX CONCURRENTLY`, reconciliar e repetir. Em base pequena com janela de manutenção, criação transacional com bloqueio de escrita é alternativa operacional. Downgrade remove índice e coluna de versão; não há reescrita de e-mails.

## Decisão: limitar tentativas

- **Decision**: usar `redis.asyncio` já instalado, no banco `/2`, com cliente compartilhado e fechado no lifespan. Scripts Lua atômicos com relógio do Redis mantêm janela móvel de falhas de 15 minutos e bloqueio de 15 minutos. Entrada usa e-mail normalizado + origem; troca usa UUID da conta + origem. Identificadores nas chaves físicas são digests, sem e-mail em claro. A quinta falha ainda recebe `401` e arma o bloqueio; a próxima recebe `429` com `Retry-After`. Sucesso fora do bloqueio limpa apenas o bucket correspondente. `422` não entra na contagem.
- **Rationale**: estado compartilhado funciona entre instâncias e scripts atômicos resolvem atualizações simultâneas; unknown/deleted e-mail passa pelo mesmo contador e por verificação com hash fictício para reduzir diferença observável. O script de finalização deve revalidar o bloqueio após a verificação de senha para impedir que sucesso concorrente ultrapasse um bloqueio recém-criado.
- **Alternatives considered**: memória por processo perde consistência entre workers/reinícios; consulta SQL para cada tentativa aumenta carga e exige estrutura persistente não pedida; leitura e escrita Redis em comandos separados introduzem corrida. Indisponibilidade do Redis resulta em erro operacional `503` em login/troca, sem ignorar o limite.
- **Origem**: o router passa `request.client.host` ao service. Em produção, a infraestrutura deve configurar proxies confiáveis do Uvicorn; não usar `X-Forwarded-For` diretamente do request.

## Decisão: schemas e erros

- **Decision**: requests Pydantic com `extra="forbid"`, validação de e-mail com `email-validator`/`EmailStr`, trim e limites após normalização. `UserUpdateRequest` exige ao menos um campo; `PasswordUpdateRequest` usa `currentPassword`/`newPassword`. Responses usam `ConfigDict(from_attributes=True, populate_by_name=True)` e aliases explícitos para `id`, `name`, `email`, `accessToken` e `tokenType`.
- **Rationale**: o cliente não escolhe identidade, hash ou flags. Um response model estrito evita que campos físicos saiam por acidente.
- **Alternatives considered**: serializar ORM diretamente expõe estrutura interna; aceitar extras silenciosamente confundiria o cliente e violaria FR-017.
- **Erro transversal**: ampliar `core/errors.py` para repassar headers de `HTTPException` e headers opcionais de `ProblemDetailError`, com `application/problem+json`. Assim, `401` Bearer preserva `WWW-Authenticate: Bearer` e `429` informa `Retry-After`.

## Decisão: migração dos consumidores e dados existentes

- **Decision**: publicar contrato novo e janela de corte coordenada; consumidores passam a chamar cadastro ou entrada e armazenar `accessToken`, renovando-o por nova entrada quando expirar. No corte, a API recusa UUID puro em todos os recursos protegidos. Atualizar testes e documentação histórica que usam `Bearer <user_id>` e o seed de desenvolvimento para um hash Argon2id válido.
- **Rationale**: o requisito exige invalidar o mecanismo provisório sem alterar o contrato funcional dos demais recursos.
- **Alternatives considered**: aceitar UUID e JWT em paralelo manteria a autenticação vulnerável e contrariaria FR-008; refresh token e recuperação por e-mail estão fora do escopo.
- **Pré-condição de implantação**: auditar os hashes de contas existentes. Valores fictícios como `hash_ana` não possuem senha verificável; essas contas precisam de credencial Argon2id provisionada por processo operacional antes do corte. A API não poderá reconstruir senhas nem transformar hash fictício em senha real. Não executar `seed.py` contra base com dados: ele apaga registros.

## Referências verificadas

- [FastAPI: OAuth2 com JWT e hash Argon2](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).
- [PyJWT: uso, claims e validação](https://pyjwt.readthedocs.io/en/stable/usage.html).
- [OWASP: armazenamento de senhas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
- [PostgreSQL: índices por expressão](https://www.postgresql.org/docs/16/indexes-expressional.html) e [criação concorrente](https://www.postgresql.org/docs/16/sql-createindex.html).
- [Alembic: operações de índice](https://alembic.sqlalchemy.org/en/latest/ops.html) e [bloco autocommit](https://alembic.sqlalchemy.org/en/latest/api/runtime.html).
- [Redis: padrões de rate limiter](https://github.com/redis/docs/blob/main/content/develop/use-cases/rate-limiter/_index.md) e [redis-py assíncrono](https://github.com/redis/redis-py/blob/master/docs/examples/asyncio_examples.ipynb).
- [Uvicorn: implantação atrás de proxy](https://github.com/kludex/uvicorn/blob/main/docs/deployment/index.md).

Todas as decisões necessárias ao design foram tomadas. Dados legados incompatíveis são um gate de implantação com diagnóstico e ação definidos, não uma lacuna de requisito.
