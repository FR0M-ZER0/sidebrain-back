# Quickstart: Validação da Geração de Missões

## Pré-requisitos

- Python 3.11 ou superior e dependências instaladas com `uv sync`.
- PostgreSQL de teste com migrações aplicadas.
- Broker Celery de teste configurado para o projeto; usar worker de teste ou eager mode conforme a infraestrutura de testes existente.
- Provedor de IA substituído por mock nos testes automatizados; chamadas reais não são necessárias.
- O fluxo de gerenciamento CRUD de Mission (service, repository, schemas e router) entregue conforme pré-requisito da feature.

## Validação automatizada

Executar, a partir da raiz do repositório:

```powershell
uv run pytest tests/unit/test_mission_generation_service.py tests/unit/test_mission_generator.py
uv run pytest tests/integration/test_mission_generation.py
uv run pytest tests/contract/test_mission_generation_contract.py
uv run ruff check .
```

### Resultados esperados

- O contrato confirma `202` com `taskId`, `200` para `missions_already_exist`, consulta autenticada de status e erros em Problem Details.
- Solicitação sem credenciais ou por Step de outro usuário não expõe ownership; inexistente, excluído e não autorizado são indistinguíveis como `404`.
- Repetição ou concorrência durante estado `pending`/`running` retorna o mesmo `taskId` e não publica task duplicada.
- Estados consultáveis distinguem `pending`, `running`, `succeeded` e `failed`; dados de outro usuário são ocultados sob `404`.
- Resposta inválida da IA (campos extras, enum inválido, título vazio ou número não positivo) não cria missão; falha durante persistência reverte o lote integral.
- A geração sob demanda persiste exatamente a quantidade solicitada; resposta com quantidade divergente não persiste parte do lote.
- Falha transitória do provedor tenta novamente até o limite configurado; parsing e validação não tentam novamente.
- Geração inicial sem missão permanece válida; uma missão presente usa o mesmo schema central da preparação incremental.
- A preparação incremental mantém sua checagem de conteúdo existente e lock atuais, sem mudança do contrato HTTP.
- Ruff e todos os testes selecionados terminam sem falhas.

## Verificação manual do fluxo

1. Autenticar como usuário dono de uma Trilha e selecionar um Step ativo sem missões.
2. Enviar `POST /v1/steps/{step_id}/missions/generate` com `{}` ou sem corpo; confirmar `202`, `status: accepted`, `stepId` e `taskId`.
3. Consultar `GET /v1/missions/generations/{task_id}` até o estado terminal; confirmar que só o usuário dono pode consultar.
4. Confirmar a missão na listagem existente do Step após `succeeded`; chamar novamente e confirmar `200` com `missions_already_exist`.
5. Repetir o POST enquanto a task ainda estiver em andamento e confirmar que o `taskId` retornado é o mesmo.
6. Repetir a consulta com outro usuário e confirmar `404`, igual à resposta para um `taskId` inexistente.

## Comandos gerais do projeto

```powershell
uv run dev
uv run ruff check .
uv run pytest
```
