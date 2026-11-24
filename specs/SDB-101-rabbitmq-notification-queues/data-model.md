# Modelo de Dados e Topologia

## NotificationPayload

Mensagem JSON serializável publicada pelo produtor.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---:|---|
| `event_id` | string | sim | não vazio; usado para correlação e idempotência |
| `type` | string | sim | não vazio; identifica o tipo do evento |
| `data` | objeto JSON | sim | conteúdo do evento; não pode conter segredo conhecido pelo contrato |

O payload completo não aparece em logs.

## BrokerSettings

Configuração externa: host, porta, usuário, senha, vhost, exchange, routing key,
fila principal, exchange/filas de retry, DLX/DLQ, número máximo de tentativas,
atraso inicial e fator de backoff. Valores operacionais são tipados e limites
inválidos falham na inicialização.

## Topologia

```text
notification.exchange
  └─ notification.routing-key
       └─ notification.queue (durable, persistent)
            └─ após falha definitiva → notification.dlx
                                      └─ notification.dead-letter.queue
```

Exchange, fila principal, DLX e DLQ são duráveis. A DLQ é separada da fila
principal e preserva a mensagem para investigação.

## Estados de processamento

1. `published`: broker confirmou a publicação.
2. `available`: mensagem está na fila principal.
3. `processing`: worker recebeu e valida/executa o handler.
4. `retry_scheduled`: falha transitória, mensagem será tentada novamente após
   backoff; o log contém tentativa e erro.
5. `processed`: handler concluiu; consumer envia `ack`.
6. `dead_lettered`: payload inválido ou última tentativa falhou; consumer envia
   rejeição sem requeue e RabbitMQ roteia para a DLQ.
