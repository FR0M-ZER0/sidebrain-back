# Research: Filas RabbitMQ para Notificações

## Decisão: cliente assíncrono `aio-pika`

**Rationale:** O backend já é Python assíncrono e `aio-pika` oferece conexão
assíncrona, publisher confirms, reconexão e controle explícito de `ack`/`reject`.
Isso permite que o worker não bloqueie o processo e só confirme mensagens depois
do handler.

**Alternativas consideradas:** `pika` síncrono (exigiria thread ou bloqueio no
worker); Celery com RabbitMQ (rejeitado porque a especificação exige preservar
Celery/Redis e manter o fluxo separado).

## Decisão: topologia durável com mensagens persistentes e DLQ

**Rationale:** A fila principal e a DLQ serão duráveis, exchanges e bindings
serão declarados idempotentemente, e cada mensagem usará `DeliveryMode.PERSISTENT`.
Publisher confirms e `mandatory=True` evitam sucesso falso para mensagens
rejeitadas ou não roteáveis.

**Alternativas consideradas:** exchange default sem confirmação (não fornece
diagnóstico de roteamento); filas não duráveis (perdem topologia após reinício).

## Decisão: retry no consumer com backoff exponencial e limite configurável

**Rationale:** O limite padrão de cinco tentativas vem da especificação. O
consumer manterá a tentativa no envelope/cabeçalho e aguardará um atraso
exponencial configurável entre tentativas; após a última falha, rejeitará sem
requeue para a DLQ. Mensagens inválidas não devem entrar em retry.

**Alternativas consideradas:** ciclo DLX+TTL para cada atraso (mais complexo e
dependente de múltiplas filas); `nack(requeue=True)` imediato (pode causar loop
quente e não preserva backoff).

## Decisão: configuração externa via Pydantic Settings

**Rationale:** `core.constants.Env` já centraliza `.env` e validações. Serão
adicionados parâmetros RabbitMQ com defaults locais não sensíveis; credenciais
serão obrigatórias para ambientes que não usem defaults e nunca serão gravadas
em código ou logs.

**Alternativas consideradas:** URL fixa no módulo (vaza ambiente e impede
deploy); reutilizar a URL do Celery (viola isolamento funcional).

## Evidência consultada

- Documentação `aio-pika`: filas duráveis, `DeliveryMode.PERSISTENT`, publisher
  confirms e semântica de `ProcessContext`.
- Documentação RabbitMQ: dead-letter exchange, rejeição com `requeue=false` e
  padrões de retry.
- Documentação Celery: URLs de broker/backend Redis, confirmando que a
  configuração atual deve permanecer inalterada.
