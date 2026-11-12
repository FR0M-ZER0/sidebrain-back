# Implementation Plan: Filas RabbitMQ para Notificações

**Branch**: `SDB-101-rabbitmq-notification-queues` | **Date**: 2026-11-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-101-rabbitmq-notification-queues/spec.md`

## Summary

Adicionar um fluxo de notificações desacoplado, com broker RabbitMQ local,
publisher e worker assíncronos próprios. O fluxo usará `aio-pika`, configuração
externa e filas duráveis com mensagens persistentes, sem alterar o broker,
backend ou as tasks Celery existentes em Redis. O worker validará o payload,
confirmará sucessos, aplicará até cinco retries com backoff exponencial e
isolará mensagens inválidas ou definitivamente falhas em uma DLQ.

## Technical Context

**Language/Version**: Python >=3.11

**Primary Dependencies**: FastAPI/Pydantic Settings existentes, `aio-pika`,
RabbitMQ e `uv`; Celery/Redis permanecem sem alteração

**Storage**: RabbitMQ como transporte durável; sem nova persistência de domínio

**Testing**: Pytest unitário com broker substituído; integração opcional com
RabbitMQ local; Ruff para lint

**Target Platform**: Serviço FastAPI e worker Python executados localmente ou
em ambiente de desenvolvimento via Docker Compose

**Project Type**: Projeto único, serviço web com worker assíncrono separado

**Performance Goals**: processar pelo menos 1.000 mensagens de teste sem descarte
silencioso; não bloquear o fluxo produtor enquanto o worker estiver indisponível

**Constraints**: payload mínimo `event_id`, `type`, `data`; máximo padrão de cinco
tentativas; logs não podem conter payload completo ou segredos; Celery continua
em Redis; credenciais somente por ambiente

**Scale/Scope**: configuração de broker, topologia de exchange/filas, publisher,
consumer/handler, retry/DLQ, Compose, documentação e testes do fluxo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Princípios I-II: publisher, consumer, configuração e handler terão
  responsabilidades separadas; regras de retry ficarão no worker/infraestrutura.
- [x] Princípio III: o fluxo de notificações será uma integração de
  infraestrutura fora das camadas de domínio, sem router acessando broker diretamente.
- [x] Princípio IV: haverá testes unitários de schema/topologia/publisher/worker e
  cenários de integração documentados, incluindo confirmação e DLQ.
- [x] Princípio V: não haverá migração de Celery para RabbitMQ; erros usarão logs
  estruturados e configurações incompatíveis falharão explicitamente.
- [x] Padrões técnicos: Pydantic Settings, Pytest, Ruff e `uv` serão mantidos;
  segredos não serão adicionados ao repositório.

**Gate pré-pesquisa**: PASS. A especificação não possui clarificações pendentes
e o desenho preserva os contratos e o transporte Celery existentes.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-101-rabbitmq-notification-queues/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── notification-queue.md
└── tasks.md                 # criado posteriormente por /speckit-tasks
```

### Source Code (repository root)

```text
src/
└── sidebrain_back/
    ├── core/constants.py                 # configurações RabbitMQ
    └── notifications/
        ├── broker.py                     # conexão e topologia
        ├── schemas.py                    # payload validado
        ├── publisher.py                  # publicação confirmada
        ├── consumer.py                   # consumo, ack, retry e DLQ
        └── handler.py                    # contrato de processamento
tests/
├── unit/notifications/
└── integration/notifications/
docker-compose.yml
.env.example
```

**Structure Decision**: Um pacote de infraestrutura `notifications` mantém o
fluxo fora de `tasks/`, evitando que o novo worker seja confundido com tasks
Celery e preservando a separação documentada. A configuração compartilhada
continua em `core/constants.py`; o Compose somente declara o serviço local.

## Phase 0: Research

As decisões e fontes estão registradas em [research.md](./research.md). Não há
`NEEDS CLARIFICATION` restante: `aio-pika` será usado por ser assíncrono e
oferecer confirmações, a publicação usará mensagens persistentes, e a DLQ será
acionada por rejeição sem requeue após o limite de tentativas.

## Phase 1: Design

- [data-model.md](./data-model.md) define payload, configurações, topologia e
  estados de processamento.
- [contracts/notification-queue.md](./contracts/notification-queue.md) define o
  contrato do publisher, handler, eventos de log e roteamento.
- [quickstart.md](./quickstart.md) define validação local e unitária reproduzível.

**Design pós-pesquisa**: PASS. O publisher aguarda confirmação do broker e usa
`mandatory=True`; o consumer confirma apenas após o handler, rejeita mensagens
inválidas sem requeue e controla retries com atraso exponencial antes de publicar
na DLQ. A topologia será declarada idempotentemente com os mesmos parâmetros em
publisher e consumer.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nenhuma | N/A | A solução usa abstrações mínimas e preserva Celery/Redis. |
