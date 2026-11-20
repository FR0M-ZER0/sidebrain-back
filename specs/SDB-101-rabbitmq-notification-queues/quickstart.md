# Quickstart de Validação

## Pré-requisitos

- Python 3.11+, `uv` e Docker Compose.
- Arquivo `.env` local preenchido a partir de [.env.example](../../.env.example).
- Não versionar credenciais reais.

## Iniciar infraestrutura

1. Adicionar o serviço RabbitMQ ao Compose com healthcheck.
2. Executar `docker compose up -d rabbitmq`.
3. Confirmar saúde com `docker compose ps` e a porta AMQP configurada.
4. Em outro terminal, iniciar o worker de notificações pelo comando documentado
   no README após a implementação.

## Validações unitárias

Executar `uv run pytest tests/unit/notifications -q`. O conjunto deve verificar:

- schema mínimo e rejeição de payload inválido;
- declaração da exchange, fila durável, routing key e DLQ;
- publisher confirm e erro de mensagem não roteável;
- `ack` somente após sucesso;
- backoff, limite de cinco tentativas, logs estruturados e DLQ;
- ausência de dependência de RabbitMQ externo.

## Validação de integração

Com o broker saudável, executar os testes de integração de notificações. Publicar
um payload válido, consumir com handler controlado e verificar que ele deixa a
fila após `ack`. Repetir com handler que falha para observar cinco tentativas e
uma mensagem na DLQ. Enviar pelo menos 1.000 payloads válidos e verificar que
cada um termina processado ou na DLQ, sem descarte silencioso.

## Regressão

Executar `uv run ruff check .` e `uv run pytest`. Confirmar que as tasks Celery
existentes continuam apontando para Redis e que o worker Celery ainda inicia
com `uv run celery -A sidebrain_back.core.celery_app worker --loglevel=info`.
