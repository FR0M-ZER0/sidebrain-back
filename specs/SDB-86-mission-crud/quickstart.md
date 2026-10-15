# Quickstart de validação — SDB-86

## Pré-requisitos

- Python do projeto configurado e dependências instaladas.
- PostgreSQL de testes disponível conforme as fixtures existentes.
- Repositório na branch `SDB-86-mission-crud`.

## Preparação

```powershell
uv sync
```

Se a validação for executada sem `uv`, use o ambiente virtual local equivalente
ao configurado no projeto.

## Cenários de contrato

```powershell
uv run pytest tests/contract/test_mission_contract.py
```

Validar autenticação, contrato semântico, rejeição de `stepId` no payload,
paginação e respostas `404`/`422` conforme
[mission-api.md](./contracts/mission-api.md).

## Cenários unitários

```powershell
uv run pytest tests/unit/test_mission_schema.py tests/unit/test_mission_service.py
```

Validar trim e limites dos campos, enums, payload de atualização não vazio,
preservação do Step, tratamento de erro e commit/rollback.

## Cenários de integração

```powershell
uv run pytest tests/integration/test_mission_lifecycle.py
```

Validar o ciclo `POST -> GET lista -> GET detalhe -> PUT -> DELETE`, ownership
pela cadeia Track/Step, soft delete, preservação de MissionProgress e ausência
de progressos de outros usuários.

## Suite obrigatória

```powershell
uv run ruff check .
uv run pytest
```

O resultado esperado é lint sem erros e todos os testes passando. A inspeção de
consultas deve confirmar carregamento agrupado, sem uma consulta adicional por
Mission.
