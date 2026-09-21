# Research: SDB-75

## Contexto técnico

A implementação atual já possui `GenerationInput`, `GenerationService`, `GenerationRepository`, `generate_track_task` e `prepare_next_step_content_task`. A criação HTTP, porém, usa `TrackService.create_track` para inserir apenas uma Track síncrona. A idempotência existente depende de `Track.trk_generation_request_id` e só cobre uma Track ativa; não há registro para pedido pendente, fingerprint do contexto ou falha antes da criação.

## Decisão: persistir uma solicitação de geração separada

- **Decision**: criar uma entidade/tabela de solicitação de geração com `request_id` único, usuário, fingerprint do contexto, estado (`pending`, `succeeded`, `failed`), `track_id` opcional, `error_code` opcional e timestamps.
- **Rationale**: o endpoint precisa registrar o pedido antes do worker e a aplicação precisa observar conflito de contexto e falhas sem depender de uma Track já criada. A unicidade do `request_id` e uma atualização transacional tornam concorrentes idempotentes.
- **Alternatives considered**: adicionar estado e payload completo em `Track` foi rejeitado porque não representa falhas sem Track, mistura ciclo de vida de pedido com domínio de trilha e aumenta o acoplamento.

## Decisão: fingerprint determinístico para conflito de idempotência

- **Decision**: normalizar o contexto validado (`goal`, `topic`, `knowledge_level`, `assessment_answers`) e persistir um hash estável; repetir `request_id` com fingerprint diferente retorna conflito em Problem Details, enquanto o mesmo fingerprint retorna a aceitação/resultado lógico já existente.
- **Rationale**: comparar o payload validado evita diferenças de formatação e impede que uma chave de idempotência seja reutilizada para outro contexto.
- **Alternatives considered**: comparar apenas o `request_id` foi rejeitado porque aceitaria silenciosamente contextos divergentes; armazenar o JSON sem fingerprint foi rejeitado por tornar a comparação e indexação menos explícitas.

## Decisão: contrato assíncrono do POST de Track

- **Decision**: `POST /api/v1/tracks` recebe `LearningContext` mais `request_id` opcional e retorna `202 Accepted` com `{status, request_id}`. O service persiste/encontra o pedido e chama `generate_track_task.delay(...)`; não chama Groq nem espera `AsyncResult`.
- **Rationale**: `delay()` é a API curta do Celery para publicar uma task e retornar imediatamente. FastAPI permite definir o status HTTP e o response model no decorator.
- **Alternatives considered**: manter `201 TrackResponse` foi rejeitado porque a Track ainda não existe; usar `BackgroundTasks` foi rejeitado porque o projeto já possui Celery, retry e worker dedicado.

## Decisão: falhas do worker

- **Decision**: a task continua retornando `GenerationSuccess`/`GenerationFailure`, mas atualiza a solicitação de geração em transação para `succeeded` ou `failed`. Erros transitórios mantêm retry limitado; validação, resposta inválida, falha permanente e retries esgotados persistem `error_code` sem relançar uma falha para o endpoint que já respondeu 202.
- **Rationale**: o cliente não pode receber um 500 retrospectivo; o estado persistido permite observabilidade e preserva a atomicidade da geração.
- **Alternatives considered**: deixar apenas o resultado do backend Celery foi rejeitado porque não garante persistência de negócio nem acompanhamento independente do backend de resultados.

## Decisão: preparação manual

- **Decision**: adicionar `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next`. O router injeta `TrackService`; o service consulta a cadeia ativa Track -> Step, filtra ownership, reaproveita `get_next_step_to_prepare` e chama a task existente com `.delay()`.
- **Rationale**: mantém a regra de elegibilidade e idempotência fora do router. A consulta deve combinar usuário, IDs da URL e exclusão lógica para ocultar inexistência, exclusão e falta de permissão sob o mesmo 404.
- **Alternatives considered**: expor a task diretamente no router foi rejeitado pela arquitetura; criar uma segunda task foi rejeitado porque duplicaria concorrência e persistência de conteúdo.

## Decisão: resposta sem próximo Step

- **Decision**: retornar `200 OK` com `status: skipped` e `reason: no_eligible_next_step` quando a solicitação for válida, mas não houver próximo Step elegível; retornar `202 Accepted` com `status: accepted` e identificador da task quando houver enfileiramento.
- **Rationale**: ausência de trabalho é resultado de domínio, não erro HTTP, enquanto a task enfileirada representa processamento futuro.
- **Alternatives considered**: responder 404 foi rejeitado porque o Step atual pode existir e estar autorizado; responder sempre 202 esconderia que nada foi enfileirado.

## Referências técnicas verificadas

- FastAPI: request bodies Pydantic, `Depends` e declaração de status/response model no path operation.
- Celery: `delay()` publica uma task e retorna `AsyncResult`; `retry()` reenvia a task e deve ser limitado para não criar retry infinito.
- Convenções locais: `docs/architecture.md`, `docs/code_conventions.md` e `.specify/memory/constitution.md` exigem router -> service -> repository -> model, tasks com sessão própria, schemas sem nomes físicos e Problem Details.

Todos os desconhecidos do Technical Context foram resolvidos; não restam marcadores `NEEDS CLARIFICATION`.
