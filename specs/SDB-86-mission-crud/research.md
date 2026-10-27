# Pesquisa e decisões — SDB-86

## Decisão: manter `Mission` como recurso filho de `Step`

**Racional:** a criação e a listagem usam `/steps/{step_id}/missions`, enquanto
consulta, atualização e exclusão usam `/missions/{mission_id}` conforme o
contrato da task SDB-86. O `step_id` de criação vem exclusivamente da URL.

**Alternativas consideradas:** aceitar `stepId` no body ou usar somente rotas
não aninhadas. Foram rejeitadas porque permitem inconsistência entre URL,
payload e ownership e divergem do contrato funcional.

## Decisão: autorização contextual no repository

**Racional:** cada consulta deve filtrar simultaneamente `user_id`, `track_id`
quando aplicável, flags de soft delete e vínculo `Mission -> Step -> Track`.
Isso mantém o `404` uniforme para inexistência, exclusão lógica e ownership
incompatível, sem revelar qual condição falhou.

**Alternativas consideradas:** validar ownership em uma dependência FastAPI
separada ou consultar a missão sem o track e autorizar depois. A primeira
espalha regra de domínio entre camadas; a segunda aumenta risco de BOLA e de
leituras fora do escopo autorizado.

## Decisão: `PUT` com semântica parcial

**Racional:** embora `PATCH` seja a escolha REST usual para atualização parcial,
o contrato da task existente define `PUT /missions/{mission_id}` e requer
campos omitidos preservados. O schema de atualização exigirá ao menos um campo
e proibirá campos desconhecidos ou `stepId`.

**Alternativas consideradas:** trocar para `PATCH` ou tornar `PUT` substitutivo.
Ambas quebrariam o contrato já especificado ou a exigência de atualização
parcial.

## Decisão: `selectinload` filtrado por usuário

**Racional:** o repository de Step já usa
`selectinload(Mission.mission_progresses.and_(MissionProgress.mpg_user_id ==
user_id))`. O repository de Mission deve reutilizar o mesmo padrão para que
progressos sejam carregados em lote, sem N+1, e a coleção permaneça vazia
quando o usuário ainda não possui progresso.

**Alternativas consideradas:** lazy loading por missão, que gera N+1 e pode
falhar em `AsyncSession`, ou join manual no resultado principal, que multiplica
linhas e complica paginação.

## Decisão: exclusão lógica terminal

**Racional:** `msn_is_deleted` e `msn_deleted_at` serão atualizados em uma
transação, mantendo a missão e seus progressos para histórico. Todas as
consultas públicas filtrarão `msn_is_deleted.is_(False)`.

**Alternativas consideradas:** exclusão física, rejeitada porque remove o
histórico e pode acionar cascata em `mission_progress`.

## Decisão: contrato semântico camelCase

**Racional:** schemas Pydantic mapearão colunas físicas para `id`, `stepId`,
`xpReward`, `criteriaValue` e `missionProgresses`, mantendo
`from_attributes=True` e `populate_by_name=True`.

**Alternativas consideradas:** expor nomes SQL (`msn_*`, `mpg_*`), rejeitada
por violar o contrato público e o princípio de separação de camadas.
