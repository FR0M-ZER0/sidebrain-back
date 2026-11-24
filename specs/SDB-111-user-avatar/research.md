# Pesquisa — SDB-111 avatar do usuário

## Decisões

### Catálogo persistido e versionado

- **Decisão:** criar uma tabela `avatar` com `slug` textual único, nome, caminho
  relativo da imagem e `is_active`; inserir os dez registros iniciais na
  migração Alembic com seed idempotente. O usuário terá uma coluna
  `usr_avatar_slug` nullable com foreign key para `avatar.slug`.
- **Racional:** o slug imutável é exatamente o identificador definido na
  especificação, e a tabela permite desativação sem apagar histórico. A coluna
  nullable torna a migração aditiva e preserva usuários existentes.
- **Alternativas consideradas:** somente configuração Python foi rejeitada porque
  não oferece integridade referencial; UUID foi rejeitado porque o contrato exige
  slug estável; seed não idempotente foi rejeitado por falhar em ambientes
  parcialmente atualizados.

### Referência da imagem e fallback

- **Decisão:** manter os arquivos PNG em `src/sidebrain_back/static/avatars/` e
  montar esse diretório com `StaticFiles` no caminho `/static`. O banco armazena
  somente o caminho relativo, e o serviço retorna `imageUrl` com esse caminho.
- **Racional:** a documentação oficial do FastAPI recomenda montar
  `StaticFiles(directory=..., name=...)` para servir imagens. Isso evita upload,
  processamento e storage externo, conforme o escopo.
- **Alternativas consideradas:** URLs absolutas foram rejeitadas porque a
  especificação definiu URL relativa; base64 foi rejeitado por aumentar payloads.

### Contratos HTTP

- **Decisão:** adicionar `GET /api/v1/avatars`, protegido pela autenticação,
  retornando somente avatares ativos. Estender `PUT /api/v1/users/me` com
  `avatar: string | null`; campo ausente mantém a seleção e `null` remove.
  `GET /api/v1/users/me` retornará `avatar` como objeto resolvido, usando o
  registro padrão quando não houver seleção ativa.
- **Racional:** reutiliza o endpoint de perfil existente, evita duplicação e
  mantém o catálogo separado da atualização.
- **Alternativas consideradas:** endpoint dedicado de seleção foi rejeitado por
  duplicar o fluxo de perfil; retornar somente o slug foi rejeitado porque o
  cliente precisa da referência da imagem.

### Validação e transação

- **Decisão:** `AvatarService`/`AvatarRepository` consultam o catálogo; a regra
  de seleção ativa é aplicada em `UserService` antes de atualizar e fazer
  commit. Falha de validação não altera o usuário e retorna Problem Details.
- **Racional:** preserva a separação de camadas documentada em
  `docs/architecture.md` e mantém a atualização atômica.
- **Alternativas consideradas:** validação na rota foi rejeitada por colocar
  regra de negócio em HTTP; aceitar qualquer slug foi rejeitado por permitir
  referências inativas.

## Evidências

- A arquitetura vigente define `routers -> services -> repositories -> models`
  e DI via `Depends` em [docs/architecture.md](../../docs/architecture.md).
- Os schemas públicos usam `ConfigDict(from_attributes=True,
  populate_by_name=True)` e erros seguem Problem Details em
  [docs/code_conventions.md](../../docs/code_conventions.md).
- FastAPI documenta o uso de `StaticFiles` para imagens:
  <https://fastapi.tiangolo.com/tutorial/static-files/>.
- O prefixo efetivo da aplicação é `/api/v1`, pois o router raiz usa `/api` e
  o router de usuários usa `/v1/users`; o contrato deve explicitar isso.
- Testes de integração já aplicam `alembic upgrade head` e isolam cada caso com
  rollback, portanto a nova migração e os cenários do catálogo devem seguir esse
  mecanismo existente.
