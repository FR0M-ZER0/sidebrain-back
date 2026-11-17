# Data model: SDB-81

## User (`user`)

Entidade raiz já persistida em `src/sidebrain_back/models/user_model.py`. Esta feature mantém os relacionamentos com Track, Answer, Feedback, MissionProgress, BadgeProgress, Login, KnowledgeAssessment e DayStreak; o soft delete não aciona cascata nem altera esses registros.

| Campo físico | Tipo | Regra |
| --- | --- | --- |
| `usr_id` | UUID | Chave primária; gerada pelo banco; identidade usada em `sub`. |
| `usr_name` | string(255) | Obrigatório, trim, 1–255 caracteres após normalização. |
| `usr_email` | string(255) | Obrigatório, trim + lower em novas escritas; e-mail válido; unicidade sobre `lower(btrim(usr_email))`, inclusive usuários excluídos. |
| `usr_password_hash` | string(255) | Hash Argon2id; nunca senha em claro ou campo público. |
| `usr_token_version` | inteiro não nulo | **Novo**, default `0`; incrementado apenas na troca bem-sucedida de senha. |
| `usr_is_deleted` | booleano | `false` na criação; `true` na exclusão lógica. |
| `usr_deleted_at` | datetime anulável | `null` na criação; horário UTC da exclusão lógica. |
| `usr_created_at`, `usr_updated_at` | datetime | Mantidos como metadados internos. `usr_updated_at` não participa da revogação. |

### Invariantes e transições

- Conta ativa: `usr_is_deleted = false`, `usr_deleted_at = null`. Conta excluída: `usr_is_deleted = true`, `usr_deleted_at` preenchido; transição terminal no escopo desta feature.
- Cadastro persiste nome e e-mail normalizados e hash Argon2id; após commit, emite JWT para o `usr_id` e a versão `0`.
- Login, consulta e mutação exigem conta ativa. E-mail excluído continua reservado. Usuário desconhecido, excluído ou senha errada produzem o mesmo resultado de login.
- Atualização de perfil altera somente nome e/ou e-mail; não altera senha, versão, id ou flags. Atualizar para o próprio e-mail normalizado não é conflito.
- Troca de senha relê a conta sob bloqueio de linha, verifica a senha atual, exige nova senha diferente e incrementa `usr_token_version` na mesma transação do novo hash. O commit invalida tokens de versões anteriores.
- Exclusão marca a linha e preenche `usr_deleted_at` na mesma transação. Qualquer token da conta excluída falha na próxima validação.
- Os services controlam commit/rollback; o repository faz apenas leitura e escrita. Buscar por ID ou e-mail para autenticação filtra `usr_is_deleted = false`, exceto a verificação de e-mail reservado, que considera também linhas excluídas.

### Migração

1. Verificar colisões com `lower(btrim(usr_email))` em todas as linhas, inclusive excluídas. Havendo grupos duplicados, interromper a implantação e reconciliar seus dados antes da migração; não escolher titular automaticamente.
2. Adicionar `usr_token_version integer NOT NULL DEFAULT 0` e índice único funcional `lower(btrim(usr_email))`. Conservar a constraint única atual de `usr_email`.
3. O índice é a garantia final sob cadastro/atualização simultâneos; o service converte apenas a violação dessa unicidade em `409` após rollback.
4. Downgrade remove o índice funcional e a coluna nova. A migração não reescreve e-mails existentes, portanto o esquema é reversível; tokens emitidos no novo formato deixam de funcionar após rollback.

## Credencial de acesso (JWT; não persistida)

| Claim | Regra |
| --- | --- |
| `sub` | `usr_id` em formato UUID string. |
| `iat` | Instante de emissão em UTC. |
| `exp` | Instante de expiração, 60 minutos após emissão. |
| `ver` | Valor inteiro de `usr_token_version` no momento da emissão. |

Assinatura HS256 com segredo obrigatório do ambiente. A validação exige essas claims, algoritmo fixo, assinatura, prazo, UUID válido, versão igual à linha atual e usuário ativo. UUID puro, token adulterado ou expirado falham com `401`. O JWT não carrega e-mail, senha ou hash. Não há refresh token nem tabela de sessão.

## Buckets de tentativas (Redis; transitórios)

| Operação | Chave lógica | Estado |
| --- | --- | --- |
| Entrada | `login` + e-mail normalizado + origem | Falhas da janela móvel de 15 min e bloqueio de 15 min após a quinta. Inclui endereços desconhecidos/excluídos. |
| Troca de senha | `password` + `usr_id` + origem | Mesmo limite, independente do login. |

As chaves físicas usam digest, sem e-mail em claro; cada chave tem TTL. Scripts Lua atômicos usam o relógio do Redis para verificar janela/bloqueio e registrar falhas. A quinta falha ainda recebe `401` e inicia o bloqueio; tentativas seguintes recebem `429`, inclusive com credencial correta. Um sucesso fora do bloqueio zera somente seu bucket. Erros de payload `422` não contam. Redis indisponível interrompe a operação protegida pelo limite com erro operacional, em vez de ignorar o controle.

## Perfil público

`UserResponse` publica somente `id`, `name` e `email`; `AuthResponse` acrescenta `accessToken`, `tokenType: "Bearer"` e `user`. Schemas Pydantic fazem o mapeamento explícito dos campos `usr_*`, com `ConfigDict(from_attributes=True, populate_by_name=True)`. Nenhum metadado interno, hash ou versão é serializado.
