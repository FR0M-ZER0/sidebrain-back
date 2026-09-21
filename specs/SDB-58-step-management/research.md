# Research: Gerenciamento de Etapas

## Contexto

A especificação `SDB-58` e a issue `SDB-58` do Jira definem CRUD de `Step` subordinado a `Track`, com autorização por usuário, exclusão lógica e leitura da árvore de conteúdo já existente. O modelo `Step`, os enums `StepLevelEnum`/`StepStatusEnum` e os relacionamentos filhos já existem no código.

## Decisão: Reutilizar o fluxo em camadas existente

**Decisão**: adicionar `step_repository.py`, `step_service.py`, `step_schema.py` e `routers/v1/step_router.py`, usando providers com `Depends`, e registrar o router em `src/sidebrain_back/routers/router.py`.

**Racional**: `TrackService`/`TrackRepository` já estabelecem o padrão de `AsyncSession`, ownership por `user_id`, `ProblemDetailError`, paginação e soft delete. Repetir esse contrato localmente mantém a separação `router -> service -> repository -> model` exigida pela constituição.

**Alternativas consideradas**: colocar as operações diretamente em `TrackService` ou no router. Foram rejeitadas porque misturariam responsabilidades e violariam a fronteira de camadas.

## Decisão: preservar o prefixo público efetivo

**Decisão**: documentar e implementar os endpoints como `/api/v1/tracks/{track_id}/steps`.

**Racional**: o agregador central usa `prefix="/api"` e o router de Track usa `prefix="/v1/tracks"`; o contrato precisa refletir a URL efetivamente exposta pela aplicação.

**Alternativas consideradas**: documentar somente `/v1/...` ou alterar o prefixo global. Foram rejeitadas porque a primeira diverge do runtime e a segunda amplia o impacto para clientes existentes.

## Decisão: `PUT` completo para atualização

**Decisão**: o endpoint `PUT` recebe obrigatoriamente `level` e `title`; campos extras são rejeitados e os campos internos nunca entram no schema de entrada.

**Racional**: FR-011 e a assumption da especificação definem atualização completa, enquanto `Step` não possui PATCH no escopo.

**Alternativas consideradas**: PATCH parcial ou aceitar um payload genérico. Foram rejeitadas por incompatibilidade com o contrato da feature e por permitirem ambiguidade sobre campos gerenciados pelo sistema.

## Decisão: autorização na consulta de Step e Track

**Decisão**: toda operação carrega o `Track`/`Step` filtrando simultaneamente o ID da URL, `Track.trk_user_id` e flags de exclusão lógica; inexistência, ownership incompatível e recurso excluído resultam em 404 uniforme.

**Racional**: evita vazamento de existência e reproduz o comportamento vigente de `TrackService`.

**Alternativas consideradas**: buscar o Step primeiro e verificar o Track depois. Foi rejeitada porque aumenta o risco de acesso cruzado e duplica consultas/autorização.

## Decisão: carregamento hierárquico agrupado

**Decisão**: usar `selectinload` aninhado, com critérios de exclusão lógica nos filhos e filtro de `MissionProgress` pelo usuário autenticado. A consulta deve usar `.unique()` quando necessário.

**Racional**: a documentação oficial do SQLAlchemy 2 recomenda `selectinload` em `AsyncSession` para evitar lazy loading, e aceita sub-opções para relações aninhadas. O padrão já está implementado em `TrackRepository._hierarchy_options`.

**Alternativas consideradas**: lazy loading, consultas por filho ou um JOIN monolítico. Foram rejeitadas por risco de N+1, por acoplamento com o ciclo assíncrono e por duplicação de linhas na árvore.

## Decisão: schemas públicos separados do ORM

**Decisão**: `StepCreate`/`StepUpdate` expõem somente `level` e `title`; `StepResponse` expõe `id`, `level`, `title`, `status`, `updated_at`, `lessons` e `missions`. Schemas filhos de leitura podem ser reutilizados do contrato de Track quando compatíveis.

**Racional**: `PublicModel`/`ConfigDict(from_attributes=True, populate_by_name=True)` já é o padrão local para ocultar nomes físicos e campos de auditoria.

**Alternativas consideradas**: retornar o modelo ORM ou duplicar CRUD dos filhos. Foram rejeitadas por exporem detalhes internos e excederem o escopo FR-020.

## Decisão: paginação e status HTTP

**Decisão**: listar Steps com `page` e `page_size` no envelope `PaginatedResponse`; criar retorna 201, listar/consultar/atualizar retornam 200 e remover retorna 204 sem corpo.

**Racional**: segue `docs/code_conventions.md`, `pagination_schema.py`, FR-005 e FR-017.

**Alternativas consideradas**: lista sem envelope ou 200 no DELETE. Foram rejeitadas por incompatibilidade com o contrato vigente.

## Decisão: ordenação estável e resposta de criação

**Decisão**: ordenar listagens por `stp_updated_at DESC, stp_id DESC`. A criação retorna o Step persistido com listas de `lessons` e `missions` vazias.

**Racional**: o modelo não possui `position` e uma ordem natural de banco não é determinística. A criação não cria filhos, portanto não precisa de uma segunda leitura hierárquica; consultas GET usarão as opções completas de carregamento.

**Alternativas consideradas**: depender da ordem incidental do banco ou recarregar a árvore após toda criação. A primeira não é estável e a segunda adiciona consultas sem benefício funcional para um Step novo.

## Fontes consultadas

- Jira `SDB-58`, issue de gerenciamento de etapas (a consulta MCP foi bloqueada por permissão de rede; a especificação local foi usada como fonte funcional).
- `docs/architecture.md`, `docs/code_conventions.md` e `TrackRepository` do repositório.
- FastAPI oficial via Context7: `Depends`, validação de request e `status_code` em path operations.
- SQLAlchemy 2 oficial via Context7: `selectinload`, sub-opções aninhadas e filtragem de relações.
