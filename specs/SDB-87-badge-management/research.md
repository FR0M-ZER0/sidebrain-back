# Pesquisa e decisões

## Stack e camadas

**Decisão**: Implementar a feature em FastAPI com Pydantic v2, SQLAlchemy 2 assíncrono, `AsyncSession`, `Depends` e Pytest, seguindo `router -> service -> repository -> model`.

**Rationale**: É o fluxo normativo do repositório e já é usado pelos CRUDs de Quiz, Lesson e Step. Mantém HTTP, regras de negócio, persistência e representação pública separados.

**Alternativas consideradas**: Acesso direto ao SQLAlchemy no router foi rejeitado porque viola a separação de camadas; uma camada genérica de CRUD foi rejeitada porque as regras de unicidade normalizada e composição de progresso são específicas de Badge.

## Contrato e validação

**Decisão**: Criar schemas próprios para criação, atualização e resposta. O nome será `strip()`-ado, rejeitado quando vazio ou maior que 255 caracteres, e o schema de atualização exigirá ao menos um campo enviado. Raridade, critério e `criteria_value` serão validados pelos enums e por `gt=0`.

**Rationale**: A validação declarativa impede persistência parcial e os aliases dos schemas ocultam `bdg_*` e `bpg_*`. `model_fields_set` diferencia campo omitido de descrição explicitamente nula.

**Alternativas consideradas**: Validar apenas no service foi rejeitado porque permitiria contratos inconsistentes e duplicaria mensagens; expor os modelos ORM foi rejeitado por revelar nomes físicos e relacionamentos internos.

## Unicidade de nomes ativos

**Decisão**: O repository buscará conflito somente em badges não removidos, comparando `lower(bdg_name)` com o nome normalizado em minúsculas. A verificação será feita antes de criar e antes de atualizar; conflitos retornam `409`.

**Rationale**: A regra libera nomes de badges removidos e trata maiúsculas/minúsculas conforme a especificação, preservando no banco e no response o valor com extremidades removidas. Os modelos e a migration existentes não possuem índice parcial de unicidade e a especificação declara que não haverá alteração estrutural nesta feature.

**Alternativas consideradas**: Uma constraint global impediria reutilizar o nome após soft delete; uma migration com índice único parcial seria mais forte contra corridas, mas ultrapassa o escopo declarado e exigiria decisão de schema. A implementação deve registrar teste de concorrência como risco residual.

## Composição de progresso

**Decisão**: Consultas do Badge usarão `selectinload(Badge.badge_progresses.and_(BadgeProgress.bpg_user_id == user_id))`, ordenando de forma determinística quando necessário. O response publicará apenas `id`, `status` e `updated_at` do progresso, em uma lista `progress` ou `progresses` definida pelo contrato.

**Rationale**: O relacionamento é existente, a filtragem ocorre na consulta e não depois da serialização, e o usuário autenticado nunca recebe progresso de terceiros. Badge sem progresso retorna lista vazia.

**Alternativas consideradas**: Carregar todos os progressos e filtrar em Python foi rejeitado por risco de exposição e custo; uma consulta separada por badge foi rejeitada por gerar N+1.

## Persistência e exclusão

**Decisão**: O service controla `commit`/`rollback`; o repository cria, atualiza e marca `bdg_is_deleted` e `bdg_deleted_at`, sem `delete()` físico. Listagem e detalhe filtram badges ativos, ocultando inexistência e remoção sob `404`.

**Rationale**: Preserva o histórico e evita a cascata física de `BadgeProgress`. O padrão coincide com os demais recursos do projeto.

**Alternativas consideradas**: DELETE físico foi rejeitado pelos requisitos de histórico; restauração foi deixada fora do escopo.

## Paginação e desempenho

**Decisão**: Usar `page >= 1`, `1 <= page_size <= 100`, defaults 1/20 e `PaginatedResponse.build`, com ordenação estável por `bdg_updated_at` e `bdg_id`.

**Rationale**: Reutiliza o contrato normativo e garante metadados consistentes, inclusive página além do total. O carregamento em lote do progresso mantém o número de statements constante.

**Alternativas consideradas**: Paginação baseada em cursor foi rejeitada por incompatibilidade com o contrato vigente; ordenar somente por data pode produzir instabilidade em empates.
