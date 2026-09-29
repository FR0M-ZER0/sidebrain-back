# Research: Gerenciamento de Lições

## Contrato HTTP, escopo e paginação

**Decision:** Expor `POST` e `GET` em
`/api/v1/steps/{step_id}/lessons`, e `GET`, `PUT` e `DELETE` em
`/api/v1/lessons/{lesson_id}`. A listagem usa
`PaginatedResponse[LessonResponse]`, com `page=1`, `page_size=20`, limite de
100 e ordem por `position ASC`.

**Rationale:** A URL do Step define o vínculo na criação e o escopo natural da
coleção; operações sobre uma Lesson já identificada não precisam repetir o pai.
O prefixo `/api` vem do agregador real, e o envelope `data`, `page`, `page_size`,
`total_items`, `total_pages` é normativo no repositório, prevalecendo sobre o
exemplo simplificado `items` do Jira.

**Alternatives considered:** Aninhar detalhe e mutações sob Step foi rejeitado
por duplicar contexto sem elevar a segurança. Lista sem paginação foi rejeitada
pelas convenções. `PATCH` foi rejeitado porque a especificação resolveu `PUT`
como substituição completa dos quatro campos editáveis.

## Autenticação, ownership e ocultação

**Decision:** Todos os endpoints exigem `get_current_user`. O repository prova
acesso no SQL pela cadeia `Lesson -> Step -> Track`, exigindo Lesson, Step e
Track ativos e `Track.trk_user_id == user.usr_id`. Step/Lesson inexistente,
excluído, sob pai excluído ou de outro usuário retorna `404` uniforme.

**Rationale:** A propriedade existe em Track, não em Lesson. Aplicar os filtros
antes de materializar a entidade evita vazamento por diferença entre `403` e
`404` e segue a política já usada em Quiz e Step. Credencial ausente, inválida
ou referente a usuário excluído continua retornando `401` no dependency layer.

**Alternatives considered:** Retornar `403` para ownership foi rejeitado por
revelar que o recurso existe. Verificar autorização em Python após uma busca
por ID foi rejeitado porque traz dados protegidos para a aplicação. Confiar
somente no `step_id` sem alcançar Track foi rejeitado por não provar ownership.

## Schemas, validação e compatibilidade

**Decision:** `LessonCreateRequest` aceita apenas `title`, `text` e `position`;
`LessonUpdateRequest` exige `title`, `text`, `status` e `position`. Ambos usam
`extra="forbid"`, removem espaços das extremidades antes de validar, limitam o
título normalizado a 255 caracteres e exigem texto não vazio e posição >= 1.
O response direto usa nomes `snake_case` públicos, coleção `files` e adapters
de leitura próprios para reproduzir a árvore exigida sem expor prefixos
físicos: Feedback usa `user_id`; Quiz e Answer incluem seus timestamps e Answer
usa `user_id`. Os responses já publicados por Track/Step permanecem inalterados
nesta versão.

**Rationale:** Inputs fechados impedem que o cliente controle ID, Step, status
inicial, timestamps ou soft delete. Validar depois da normalização implementa a
regra funcional sem aceitar strings de espaços. Preservar os contratos
hierárquicos anteriores evita uma mudança incompatível na API v1; `files` é
usado pelos novos endpoints conforme o contrato da feature.

**Alternatives considered:** Reutilizar o ORM como response foi rejeitado por
expor `lsn_*`. Tornar campos do PUT opcionais foi rejeitado pela clarificação da
spec. Renomear globalmente `lesson_files` nas respostas antigas foi rejeitado
por quebrar consumidores; essa unificação exige versão ou migração própria.

## Posição única e concorrência

**Decision:** Consultar antecipadamente se a posição já está reservada no Step,
incluindo Lessons removidas, para retornar `409` claro; manter a constraint
PostgreSQL existente `UNIQUE (lsn_step_id, lsn_position)` como autoridade final
contra corridas. No update, a própria Lesson é excluída da verificação. Uma
violação única detectada no `flush`/`commit` causa rollback e o mesmo `409`.

**Rationale:** A constraint não é parcial e, portanto, já preserva a posição
após soft delete. A pré-validação melhora o erro no caso comum, mas somente a
constraint garante correção quando duas transações concorrentes observam a
posição livre. A mesma posição permanece permitida em Steps distintos.

**Alternatives considered:** Confiar apenas na consulta prévia foi rejeitado
por race condition. Criar índice único parcial para linhas ativas foi rejeitado
porque liberaria posições apagadas, contrariando a spec. Reordenar outras
Lessons foi rejeitado por estar explicitamente fora da regra definida.

## Consultas hierárquicas e ausência de N+1

**Decision:** Usar `select(...)` com `AsyncSession` e `selectinload` encadeado
para `Lesson.feedbacks`, `Lesson.lesson_files`, `Lesson.quizzes` e
`Quiz.answers`. Aplicar critérios `is_deleted=false` a Feedback, LessonFile e
Quiz; Answer não possui soft delete. Listagem e detalhe materializam a árvore
antes da serialização, e a listagem pagina somente a entidade raiz.

**Rationale:** A documentação atual do SQLAlchemy 2 recomenda eager loading em
fluxos assíncronos para impedir I/O implícito ao acessar relacionamentos.
`selectinload` agrupa cada coleção em uma consulta por relacionamento e evita a
multiplicação cartesiana de um `JOIN` monolítico. O número de statements fica
constante em relação ao número de Lessons e filhos, que é exatamente o que
SC-008 mede.

**Alternatives considered:** Lazy loading foi rejeitado por I/O implícito e
N+1 em `AsyncSession`. `joinedload` de todas as coleções foi rejeitado pela
multiplicação de linhas entre Feedbacks, Files, Quizzes e Answers. Montar a
árvore no service com queries por Lesson foi rejeitado por acoplamento e custo
proporcional.

Documentação consultada: [SQLAlchemy AsyncIO](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html),
[Relationship Loading](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
e [Session Transactions](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html).

## Transações, respostas e soft delete

**Decision:** O service controla a unidade transacional. Criação, atualização e
remoção validam acesso e conflito, mutam a entidade, fazem `flush` quando
necessário, materializam o response antes do commit e executam rollback em
`ProblemDetailError`, `IntegrityError` ou falha inesperada. DELETE define
`lsn_is_deleted=true`, `lsn_deleted_at` e `lsn_updated_at` no mesmo instante,
sem apagar nem modificar filhos.

**Rationale:** A mutação inteira permanece atômica e falhas não deixam estado
parcial. Soft delete não aciona `ON DELETE CASCADE`; logo Feedbacks,
LessonFiles, Quizzes e Answers continuam fisicamente intactos. Carregar filhos
antes da serialização evita acesso lazy depois que a transação termina.

**Alternatives considered:** DELETE físico foi rejeitado por destruir a árvore.
Propagar soft delete aos filhos foi rejeitado por exceder o escopo. Commitar
antes de construir a resposta foi rejeitado porque uma falha posterior poderia
reportar erro após persistir a operação.

## Banco e migrations

**Decision:** Não criar migration. O modelo e a migration inicial já possuem
UUID, FK obrigatória para Step, enum `lesson_status`, campos de auditoria e soft
delete, `String(255)`, `Text`, posição inteira e a constraint única composta
necessária.

**Rationale:** Nenhuma alteração de schema é necessária para os requisitos. A
constraint existente inclui linhas removidas e satisfaz diretamente a reserva
de posição. Índices adicionais só devem ser propostos com evidência de
`EXPLAIN ANALYZE` caso o benchmark falhe por acesso ao banco.

**Alternatives considered:** Nomear novamente ou recriar a constraint foi
rejeitado por gerar churn sem benefício funcional. Adicionar índices
antecipadamente para todos os filhos foi rejeitado como otimização especulativa.

## Estratégia de testes e desempenho

**Decision:** Cobrir schemas e services com testes unitários; rotas,
autenticação, status e Problem Details com testes de contrato; e ownership,
constraint concorrente, atomicidade, soft delete, filtros dos filhos, ordem e
contagem SQL com PostgreSQL real. O benchmark executa 5 aquecimentos e 100
requisições sequenciais autenticadas, mede p95 e compara statements entre 1 e
50 Lessons com a mesma cardinalidade de filhos por Lesson.

**Rationale:** Mocks provam orquestração, mas não provam constraints,
relacionamentos, filtros de loader nem comportamento transacional real. A
instrumentação já usada pelos testes de Quiz com o evento
`before_cursor_execute` fornece a métrica exigida por SC-008.

**Alternatives considered:** Verificar apenas o JSON foi rejeitado porque não
detecta N+1 nem preservação física. Usar SQLite foi rejeitado porque enums,
constraints e comportamento transacional devem refletir PostgreSQL 16. Rodar o
benchmark com concorrência foi rejeitado porque a spec define requisições
sequenciais e sem concorrência.
