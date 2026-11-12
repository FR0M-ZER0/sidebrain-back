# Contrato do Fluxo de Notificações

## Publisher

O publisher recebe um `NotificationPayload`, serializa-o em JSON UTF-8 e publica
na exchange configurada com a routing key de notificações. A publicação só
retorna sucesso após publisher confirm; payload ausente, não serializável ou
sem `event_id`, `type` ou `data` produz erro explícito e não publica.

## Consumer e handler

O consumer entrega cada payload validado ao handler `handle(payload)`. O `ack`
ocorre somente quando o handler termina sem exceção. Falha transitória agenda
retry com backoff exponencial até `max_attempts=5` por padrão. Payload inválido
não sofre retry. Após a última falha, a mensagem é rejeitada com `requeue=false`
e deve aparecer na DLQ.

## Observabilidade

Cada publicação, retry e falha definitiva registra evento estruturado com:
`event_id`, `type`, `attempt`, `error` e `timestamp`. Logs de conexão e validação
seguem o mesmo conjunto quando o `event_id` estiver disponível; nunca registram
o payload completo, senha, URL com credencial ou segredo.

## Compatibilidade

O contrato é interno de infraestrutura e não adiciona endpoint HTTP. As tasks
Celery continuam usando Redis como broker/backend, sem mudança de nomes,
agendamento ou resultado.
