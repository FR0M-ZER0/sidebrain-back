# Plano de implementação da SDB-109 — Atualizações de jobs por WebSocket

**Branch** `feat/sdb-109-Criar-endpoints-WebSocket-para-atualizacao-de-jobs-assíncronos`  
**Data** 18 de novembro de 2026 · [Especificação](spec.md) · [Backend SDB-109](https://fromzero-api.atlassian.net/browse/SDB-109) · [Cliente SDB-104](https://fromzero-api.atlassian.net/browse/SDB-104)

## Resumo

Adicionar emissão de ticket por Bearer e uma conexão WebSocket para acompanhar geração de trilha, diagnóstico, preparação de etapa e sumário. A API consome o ticket no Redis, valida o escopo da inscrição e envia o estado público lido do PostgreSQL. Quando a API ou o worker Celery confirma uma mudança, o mesmo commit acorda as réplicas inscritas via `LISTEN/NOTIFY`. Cada envio consulta o estado e a permissão atuais. Assim, quem chega depois da conclusão recebe o resultado no primeiro frame e quem se reconecta usa o mesmo identificador público.

## Contexto técnico

| Aspecto | Decisão |
|---|---|
| Linguagem e plataforma | Python ≥ 3.11, serviço ASGI FastAPI/Uvicorn e workers Celery em processos separados. |
| Dependências | Reutilizar Pydantic, SQLAlchemy assíncrono, asyncpg, Alembic, redis-py e as dependências de WebSocket da instalação FastAPI. |
| Armazenamento | PostgreSQL 16 guarda estado e vínculos. Redis 7, no banco de autenticação, guarda tickets por 60 s. As filas Celery mantêm sua configuração atual. |
| Concorrência | Consumo único entre réplicas, emissão serial por socket, releitura autorizada ao receber um sinal e revisão monotônica do sumário por etapa. |
| Escopo e compatibilidade | Dois novos pontos de entrada, quatro canais e um par autorizado por conexão. Preservar os contratos HTTP de início, as consultas HTTP e o SSE de trilhas existentes. |
| Desempenho | SC-006 exige p95 de até dois segundos para estado inicial e entrega terminal em ambiente controlado. Um listener por processo e um sinal coalescido por inscrição limitam o custo de espera. |
| Verificação | Pytest de unidade, contrato, integração, migração, concorrência entre processos e desempenho. Executar lint e suíte com `uv` antes de integrar a implementação. |

## Verificação da constituição

| Princípio | Antes da pesquisa | Após o desenho |
|---|---|---|
| I. Qualidade de código | Aprovado. Reaproveitar os estados existentes. | Aprovado. Consultas de snapshot compartilhadas entre abertura e envio e schemas públicos explícitos. |
| II. Responsabilidade única | Aprovado. Distinguir transporte, autorização e persistência. | Aprovado. Router controla frames, serviço decide acesso e projeção, repositórios consultam e atualizam dados. |
| III. Camadas | Aprovado. Respeitar injeção de dependências. | Aprovado. Providers junto às classes, recursos técnicos em `core`, sessões de worker explícitas, sessão curta para cada snapshot. |
| IV. Testes e contratos | Aprovado. Critérios ligados às cinco histórias. | Aprovado no desenho. Contrato descreve os quatro canais e o quickstart cobre corridas, expiração, revogação e compatibilidade. |
| V. Evolução segura | Aprovado. Ampliação aditiva em v1. | Aprovado. Migração reversível, dados legados tratados, erros HTTP em Problem Details e erros WebSocket correlacionados. |

A revisão do desenho passou pelos cinco princípios da constituição 1.0.0. A execução dos testes de produto e a medição de latência pertencem à implementação. [Constituição](../../.specify/memory/constitution.md) · [Arquitetura](../../docs/architecture.md) · [Convenções](../../docs/code_conventions.md)

## Estrutura e sequência de implementação

Os caminhos de código abaixo são relativos a `src/sidebrain_back/`, salvo indicação expressa.

1. **Persistência e notificação.** Acrescentar modelos e repositórios de preparação e revisão de sumário em `models/` e `repositories/`. Registrar a revisão em `migrations/versions/` na raiz. Os gatilhos observam as transições de `generation_request`, `knowledge_assessment` e das duas novas tabelas. O conteúdo público continua a ser consultado no domínio. Definir leitor de notificações em `core/` e gerenciar sua conexão em `src/main.py`. Tratar encerramento ou perda da sessão de escuta.
2. **Integrar os produtores.** Cobrir início, sucesso, falha definitiva e reentrega em `services/track_service.py`, `services/generation_service.py`, `services/knowledge_assessment_service.py` e nas três tasks existentes em `tasks/`. Registrar preparação nos dois caminhos de despacho, preservar assinatura dos jobs em fila e manter `skipped` imediato quando inelegível. Proteger os dois escritores de sumário em `services/step_summary_service.py` e seus chamadores `step_service.py` e `quiz_service.py`. Verificar a revisão também antes da escrita do texto canônico.
3. **Ticket e socket.** Acrescentar `POST /api/v1/auth/ws-ticket` ao `routers/v1/auth_router.py` com `get_current_user`. Registrar `routers/v1/job_update_router.py` em `routers/router.py` para `/api/v1/ws`. Prever `schemas/job_update_schema.py`, `services/job_update_service.py` e acesso encapsulado aos repositórios via providers. Os schemas expõem nomes de domínio, com `from_attributes=True` e `populate_by_name=True`. O serviço não recebe objetos WebSocket e o router não acessa ORM, Redis ou Celery diretamente.
4. **Ciclo de vida.** Na emissão validar posse, na abertura consumir o ticket, na inscrição comparar o par e rever acesso. Registrar a inscrição antes do snapshot e revalidar imediatamente antes de cada envio. Após o terminal, liberar o consumidor e permitir fechamento normal. Cobrir ocioso, mensagem inválida, duplicata, desconexão e perda da escuta. Registrar causas e tempos com contexto interno, protegendo tickets e conteúdo das mensagens.
5. **Publicação e verificação.** Aplicar migração, atualizar todos os produtores e só então habilitar o cliente. Documentar no README do backend o contrato, `wss://`, upgrade no proxy, configuração compartilhada e a janela para preparações anteriores. A configuração da interface consumidora pertence à SDB-104. Implementar os testes em `tests/unit/`, `tests/contract/`, `tests/integration/` e `tests/performance/`.

## Rastreabilidade do aceite

| História | Requisitos | Prova de aceite |
|---|---|---|
| US1 · Autorizar | FR-001 a FR-006, FR-016, FR-020 e FR-021 | Corrida pelo mesmo ticket, validação por canal, 404 indistinguível e erro de inscrição correlacionado. |
| US2 · Trilha | FR-007 a FR-010 e FR-015 | Sucesso consultável, falha pública, reconexão e ausência de regressão depois de um terminal. |
| US3 · Diagnóstico, preparação e sumário | FR-011 a FR-015 e FR-020 | Perguntas sem gabarito, prazo exato de 24 h, sumário mais recente, retries e produtores em processo separado. |
| US4 · Recuperar e encerrar | FR-003, FR-007 a FR-009, FR-016 a FR-018 | Corridas com o snapshot, revogação, latência, isolamento e zero recursos retidos pelo socket. |
| US5 · Integrar | FR-019 e FR-022 | Executar as quatro chamadas vigentes e o contrato publicado através do proxy de homologação. |

## Artefatos do planejamento

| Fase | Resultado |
|---|---|
| 0 · Pesquisa | [Decisões técnicas, evidências e alternativas](research.md) |
| 1 · Desenho | [Modelo de dados, autorização e transições](data-model.md) |
| 1 · Interface | [Contrato HTTP e WebSocket para o cliente](contracts/job-updates.md) |
| 1 · Validação | [Quickstart e cenários de aceite](quickstart.md) |
