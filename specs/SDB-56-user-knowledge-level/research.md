# Pesquisa e Decisões

## Decisão: Persistir o nível no agregado da avaliação

**Racional:** o nível mede conhecimento sobre um assunto e pode variar entre
avaliações do mesmo usuário. A avaliação será a raiz do agregado e guardará
contexto, estado, pontuação e nível; perguntas, alternativas e escolhas serão
entidades filhas normalizadas. O perfil `User` receberá somente o
relacionamento, nunca um campo global de nível.

**Alternativas consideradas:** adicionar `level` ao `User` foi rejeitado
porque perderia o contexto do assunto. Uma entidade separada
`AssessmentResult` foi rejeitada porque existe no máximo um resultado
terminal por avaliação e os campos cabem na própria raiz. Guardar todo o
agregado em JSON foi rejeitado porque enfraqueceria FKs, unicidade, ownership e
a validação dos vínculos usados na correção.

## Decisão: Criar quatro tabelas próprias do domínio

**Racional:** `knowledge_assessment`,
`knowledge_assessment_question`,
`knowledge_assessment_alternative` e `knowledge_assessment_answer`
representam, respectivamente, o ciclo de vida, as cinco perguntas, as vinte
alternativas e as cinco escolhas terminais. Constraints por posição e vínculo
complementam as validações do service. A submissão é o conjunto atômico das
cinco respostas mais a transição para `completed`, portanto não precisa de
uma quinta tabela.

**Alternativas consideradas:** reutilizar `Quiz`/`Answer` foi rejeitado
porque essas entidades dependem de Lesson/Track e possuem semântica diferente.
Reutilizar `GenerationRequest` foi rejeitado porque ele controla geração de
trilhas, não avaliação. Uma tabela de submissão foi rejeitada porque não há
edição, múltiplas tentativas nem histórico de submissões.

## Decisão: Criar o identificador canônico antes da task

**Racional:** o service HTTP gera o UUID, persiste a avaliação `pending` e
faz commit antes de publicar a task. A task existente recebe
`assessment_id`, `user_id`, `subject`, `objective` e `skip`; o registro
persistido é a fonte autoritativa e os argumentos são validados contra ele.
Assim, o mesmo ID acompanha criação, polling, geração, submissão e resultado.

**Alternativas consideradas:** aceitar o UUID retornado pelo provider ou usar o
`AsyncResult.id` como fonte de verdade foi rejeitado porque ambos transferem
identidade de domínio para infraestrutura externa. Criar uma task nova foi
rejeitado porque duplicaria o fluxo oficial exigido pela SDB-53.

## Decisão: Evoluir o contrato interno da SDB-53 com gabarito

**Racional:** o generator passará a produzir somente as perguntas e, em cada
uma, um `correct_alternative_id` que deve apontar para exatamente uma das
quatro alternativas. O schema interno valida cinco IDs de pergunta distintos,
quatro IDs de alternativa distintos por pergunta e a referência do gabarito.
Na persistência, o backend gera UUIDs próprios para perguntas/alternativas e
converte a referência em `is_correct`. Schemas públicos fazem projeção
explícita sem esse campo.

**Alternativas consideradas:** confiar em `score` ou `level` do cliente foi
rejeitado por definição. Persistir IDs arbitrários produzidos pela IA como
chaves públicas foi rejeitado por falta de controle e estabilidade. Colocar
`correct_alternative_id` na tabela de pergunta foi rejeitado porque criaria
uma FK circular; `is_correct` com índice único parcial evita esse ciclo.

## Decisão: Manter o skip dentro da task oficial

**Racional:** toda criação, inclusive `skip=true`, persiste `pending` e
dispara `tasks.prepare_knowledge_assessment` com os argumentos previstos do
contexto, mantendo `objective` opcional. No ramo skip, a task não instancia nem chama o
provider e muda atomicamente a avaliação para `skipped`, com
`level=beginner`, `score=null` e zero perguntas. O assunto continua
obrigatório.

**Alternativas consideradas:** concluir o skip diretamente no endpoint foi
rejeitado porque o requisito do Jira exige o disparo da task existente também
nesse fluxo. Permitir assunto ausente foi rejeitado pela clarificação da
especificação.

## Decisão: Modelar cinco estados e transições fechadas

**Racional:** o ciclo permitido é
`pending -> generated -> completed`, `pending -> skipped` ou
`pending -> failed`. `skipped`, `completed` e `failed` são terminais.
`pending` e `failed` nunca expõem conteúdo parcial; `generated` contém
cinco perguntas completas sem nível; `completed` contém escolhas, score e
nível coerentes.

**Alternativas consideradas:** adicionar `processing` foi rejeitado porque
não é necessário para o contrato público nem para a consistência. Reabrir ou
editar uma avaliação terminal foi rejeitado; reavaliar exige uma nova
avaliação.

## Decisão: Garantir idempotência ativa no PostgreSQL

**Racional:** o contexto é normalizado com trim, preservando caixa e espaços
internos; `objective` ausente permanece `null` e texto vazio informado é
inválido. Um SHA-256 de JSON canônico de `subject`, `objective` e `skip`
forma o fingerprint. Um índice único parcial em
`(user_id, context_fingerprint)` para `pending|generated` impede duplicatas
concorrentes. O service busca o ativo primeiro e, em corrida de insert, trata
`IntegrityError`, relê o vencedor e não reenfileira.

**Alternativas consideradas:** apenas consultar antes de inserir foi rejeitado
por permitir corrida. Incluir estados terminais no índice foi rejeitado porque
impediria reavaliação. Casefold e colapso de espaços internos foram rejeitados
por fundirem assuntos que o requisito não declarou equivalentes.

## Decisão: Corrigir e concluir sob lock de linha

**Racional:** a submissão carrega a avaliação por `assessment_id + user_id`
com `SELECT FOR UPDATE`, revalida `generated`, verifica o conjunto exato das
cinco perguntas e os vínculos alternativa-pergunta, calcula a pontuação e
persiste escolhas, nível, `completed_at` e estado na mesma transação. Duas
submissões concorrentes são serializadas: a primeira conclui e a segunda
encontra estado terminal e recebe `409`.

**Alternativas consideradas:** corrigir no router foi rejeitado por misturar
HTTP e domínio. Confiar somente em um check anterior ao commit foi rejeitado
por permitir dupla conclusão. Criar outra task para a correção foi rejeitado
porque a operação é curta, transacional e não acessa provider externo.

## Decisão: Não manter transação durante a chamada externa

**Racional:** a task lê e valida o contexto, gera e valida todo o payload fora
de transação longa e depois abre uma transação curta, bloqueia a avaliação,
revalida `pending` e grava filhos + estado. Redelivery que encontra estado
posterior não sobrescreve dados. Falhas transitórias deixam `pending` para o
retry; falha permanente ou retries esgotados fazem `pending -> failed`.

**Alternativas consideradas:** manter `FOR UPDATE` durante a chamada Groq foi
rejeitado por prolongar locks. Persistir perguntas conforme chegam foi
rejeitado por violar atomicidade. Usar apenas o result backend do Celery foi
rejeitado por expiração, falta de ownership e acoplamento à infraestrutura.

## Decisão: Preservar a política estrita de retry e observabilidade

**Racional:** somente `APIConnectionError`, `APITimeoutError` e
`RateLimitError` recebem até três retries adicionais com esperas 1/2/4
segundos. Erros de autenticação, status definitivo, JSON, schema, contexto ou
persistência não entram em retry automático. Logs registram assessment/task
id, tentativa, evento e tipo da exceção, sem subject, objective, prompt,
resposta bruta, credencial ou gabarito.

**Alternativas consideradas:** `autoretry_for=(Exception,)` foi rejeitado por
repetir falhas permanentes. Registrar payload para depuração foi rejeitado por
expor conteúdo protegido. Um outbox transacional eliminaria a janela entre
commit e publicação, mas foi adiado porque o projeto não possui essa
infraestrutura; falha de publicação será marcada como `failed` em nova
transação.

## Decisão: Expor três endpoints sob /api/v1/assessments

**Racional:** `POST /assessments` inicia ou reutiliza a avaliação ativa,
`GET /assessments/{assessment_id}` permite polling e consulta do resultado, e
`POST /assessments/{assessment_id}/answers` recebe o conjunto terminal de
cinco escolhas. Recursos alheios e inexistentes retornam o mesmo `404`;
payload/vínculo inválido retorna `422`; estado incompatível retorna `409`;
falha ao publicar retorna `503`.

**Alternativas consideradas:** um endpoint global
`/users/me/level` foi rejeitado porque o nível é contextual.
`/knowledge-assessments` é mais explícito, mas o caminho curto
`/assessments` segue o exemplo do requisito sem perder o domínio nos schemas
e nomes internos. Listagem, edição e exclusão ficaram fora do escopo.

## Decisão: Testar regras, contratos e concorrência em níveis distintos

**Racional:** testes unitários cobrem schemas, gabarito, cortes 0..5,
fingerprint, transições e retry; testes de contrato cobrem chaves públicas,
status HTTP, Problem Details e ausência de gabarito; integração PostgreSQL
cobre migration, FKs, índice parcial, ownership, atomicidade, corrida de
criação, dupla submissão e fluxo task -> polling -> respostas -> nível.

**Alternativas consideradas:** considerar o modo eager como prova de um worker
real foi rejeitado; ele é útil para integração determinística, mas não prova
broker, entrega ou backend. Um smoke com worker/Redis real é recomendado quando
o ambiente de CI suportar, sem substituir a suíte determinística.

## Fontes consultadas

- `specs/SDB-56-user-knowledge-level/spec.md` e descrição da SDB-56 no Jira.
- `docs/architecture.md`, `docs/code_conventions.md` e
  `.specify/memory/constitution.md`.
- Código e artefatos da SDB-53 em
  `src/sidebrain_back/{schemas,services,tasks}` e
  `specs/SDB-53-knowledge-assessment/`.
- Documentação SQLAlchemy 2.0 para
  [AsyncSession e transações](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html),
  [bloqueio FOR UPDATE](https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html)
  e [índices/conflitos parciais no PostgreSQL](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html),
  consultada via Context7.
