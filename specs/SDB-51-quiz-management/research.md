# Research: Gerenciamento de Quizzes

## Contrato HTTP e paginação

**Decision:** Expor `POST` e `GET` em
`/api/v1/lessons/{lesson_id}/quizzes`, e `GET`, `PUT` e `DELETE` em
`/api/v1/quizzes/{quiz_id}`. A coleção usa `PaginatedResponse`, com `data`,
`page`, `page_size`, `total_items` e `total_pages`.

**Rationale:** A lesson define o relacionamento na criação e o escopo natural
da listagem; detalhe e mutações usam o identificador do quiz. `PUT` preserva o
contrato explícito da task, e o envelope paginado é normativo no projeto,
prevalecendo sobre o exemplo simplificado com `items` do Jira.

**Alternatives considered:** Aninhar todas as operações sob a lesson foi
rejeitado por duplicar identificadores sem ganho de segurança. `PATCH` foi
rejeitado porque a task define `PUT` e o único campo mutável é obrigatório.
Lista sem paginação foi rejeitada pelas convenções do repositório.

## Autenticação, ownership e ocultação de recursos

**Decision:** Todos os endpoints usam `get_current_user`. O repository aplica
ownership no SQL, seguindo `Quiz -> Lesson -> Step -> Track`, e exige Track,
Step, Lesson e Quiz ativos. Lesson em qualquer status (`idle`, `in_progress` ou
`done`) é válida. Recurso inexistente, excluído ou de outro usuário retorna
`404`; credencial ausente/inválida retorna `401`.

**Rationale:** O usuário é proprietário da Track, portanto o acesso ao Quiz é
herdado pela hierarquia. Filtrar antes de materializar evita vazamento de dados.
O projeto já usa `404` para ocultar a existência de recursos de outro usuário,
atendendo ao requisito de recusar acesso sem revelar conteúdo protegido.

**Alternatives considered:** Retornar `403` para ownership foi rejeitado por
revelar a existência do recurso e divergir da política atual. Validar somente a
Lesson sem alcançar a Track foi rejeitado por não provar ownership. Filtrar em
Python foi rejeitado porque materializaria dados não autorizados.

## Validação da pergunta e contratos públicos

**Decision:** `QuizCreateRequest` e `QuizUpdateRequest` aceitam exclusivamente
`question`. A string passa por `strip()` antes da validação de comprimento e
deve resultar em 1–1.000 caracteres; campos extras são proibidos. O
`QuizResponse` direto usa `id`, `lesson_id`, `question` e `answers`; cada
`AnswerResponse` usa `id`, `user_id`, `text` e `rate`, tipado com
`AnswerRateEnum`. A listagem reutiliza `PaginatedResponse[QuizResponse]` em vez
de duplicar o envelope em um schema próprio.

**Rationale:** Normalizar antes da restrição implementa literalmente a regra de
comprimento após remover espaços. Aliases Pydantic com
`from_attributes=True`/`populate_by_name=True` separam o contrato dos prefixos
físicos `qui_*` e `ans_*`; `default_factory=list` evita estado mutável
compartilhado para `answers`.

**Alternatives considered:** Confiar somente em `Field(max_length=1000)` antes
do `strip()` foi rejeitado porque espaços descartáveis poderiam causar falsa
rejeição. Manter `rate` como `Any` foi rejeitado por aceitar valores fora do
enum. Aceitar `lesson_id`, IDs, Answers, timestamps ou flags no body foi
rejeitado por permitir controle de campos internos.

## Consultas, eager loading e ordenação

**Decision:** Usar SQLAlchemy 2 com `select(...)` e `AsyncSession`, carregando
`Quiz.answers` por `selectinload`. A listagem ordena quizzes por
`qui_updated_at DESC, qui_id DESC`; a relação `Lesson.quizzes` recebe a mesma
ordem. `Quiz.answers` é ordenada por `ans_created_at ASC, ans_id ASC` no
mapeamento, para valer em detalhe, listagem e hierarquias. Todas as respostas do
quiz acessível são carregadas; não há filtro por `ans_user_id`.

**Rationale:** `selectinload` emite consultas secundárias agrupadas por chaves e
evita lazy I/O/N+1 na serialização assíncrona. A ordem da entidade raiz não
ordena coleções carregadas separadamente; `relationship(order_by=...)` garante
o contrato em todos os pontos. A task exige `Answer[]` associados, enquanto a
privacidade do conjunto já é garantida pelo ownership da Track.

**Alternatives considered:** Lazy loading foi rejeitado por I/O implícito e
N+1. `joinedload` foi rejeitado pela multiplicação de linhas em várias coleções.
Ordenar apenas a consulta direta foi rejeitado porque a hierarquia continuaria
indeterminística. Filtrar Answers pelo usuário atual foi rejeitado por omitir
filhos exigidos pelo contrato.

Documentação consultada: [SQLAlchemy AsyncIO](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html),
[ORM SELECT](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html) e
[Relationship Loading](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html).

## Transações e exclusão lógica

**Decision:** O service valida acesso antes da mutação, executa criação,
atualização ou soft delete dentro da mesma unidade transacional, materializa o
response necessário antes de concluir o commit e faz rollback em falhas. DELETE
marca `qui_is_deleted=true`, preenche `qui_deleted_at` e atualiza
`qui_updated_at`; nunca chama exclusão física nem altera Answers.

**Rationale:** Isso impede dados parciais e não dispara o `ON DELETE CASCADE` da
FK de Answer. Separar `ProblemDetailError` das exceções inesperadas preserva
erros de domínio e oculta detalhes de persistência nos erros `500`.

**Alternatives considered:** DELETE físico foi rejeitado por destruir Quiz e
Answers. Commit antes de compor/recarregar a resposta foi rejeitado porque uma
falha posterior poderia reportar erro após persistir a mutação. Cascatear soft
delete para Answers foi rejeitado porque Answer não possui esse ciclo de vida.

## Hierarquia pública e compatibilidade

**Decision:** Registrar o novo router no agregador e ampliar a resposta
hierárquica de Track para garantir `lesson_id` em Quiz e `user_id` em Answer.
Os schemas de quiz compartilham um núcleo canônico; extensões específicas da
hierarquia preservam os timestamps já publicados por `track_schema.py`. O
carregamento existente de `TrackRepository` continua filtrando quizzes
excluídos e passa a respeitar as ordens do mapeamento.

**Rationale:** A feature exige `Lesson -> Quiz[] -> Answer[]` e a hierarquia
completa. Acrescentar campos é uma evolução compatível da API v1; remover
timestamps já publicados seria incompatível e violaria a constituição. O núcleo
compartilhado evita duplicar aliases e enum.

**Alternatives considered:** Substituir silenciosamente o schema hierárquico
pelo response mínimo foi rejeitado por quebra de contrato. Manter duas cópias
independentes dos schemas foi rejeitado por risco de divergência. Duplicar
queries na camada de service para remontar a árvore foi rejeitado por
acoplamento e N+1.

## Banco e índices

**Decision:** Não criar migration nesta fase. `quiz` e `answer` já possuem UUID,
FKs, timestamps, enum e campos de soft delete necessários. Testes medirão o
número de queries e o alvo de 2 segundos; se houver falha, `EXPLAIN ANALYZE`
deve fundamentar uma feature de índice, sem alterar a migration inicial.

**Rationale:** Para o cenário acordado de 50 quizzes e 500 respostas, eliminar
N+1 é a intervenção necessária e mensurável. Índices adicionais afetam escrita
e armazenamento e não devem ser adicionados sem evidência de cardinalidade ou
plano de execução.

**Alternatives considered:** Criar antecipadamente índices compostos em
`quiz(qui_lesson_id, qui_updated_at, qui_id)` e
`answer(ans_question_id, ans_created_at, ans_id)` foi rejeitado nesta fase por
ser especulativo. Alterar colunas ou enums foi rejeitado porque todos os
atributos requeridos já existem.

## Estratégia de testes

**Decision:** Cobrir schemas e services com testes unitários; rotas, autenticação
e Problem Details com testes de contrato contra a aplicação agregada; e filtros,
ordem, soft delete, preservação de Answers e contagem de queries com PostgreSQL
real. Comparar a quantidade de statements para 1 e 50 quizzes.

**Rationale:** Os testes atuais de hierarquia apenas comprovam que uma opção de
loader existe e a fixture `AsyncSession()` não tem bind. Eles não detectam
vazamento de ownership, ordem incorreta, cascata física ou N+1.

**Alternatives considered:** Mocks isolados foram mantidos para regras de
service, mas rejeitados como única prova de comportamento ORM. Verificar somente
o JSON foi rejeitado porque não comprova preservação física nem custo de query.
