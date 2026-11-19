# Quickstart de validação — SDB-112

## Pré-requisitos

- Ambiente do projeto configurado com `uv`.
- PostgreSQL de testes disponível na configuração usada por
  `tests/conftest.py` para os testes de integração.
- Um token Bearer válido para testar a rota no serviço em execução, ou os
  overrides de dependências usados pelos testes de contrato.

## Executar testes focados

### Unitários: schema e regras do serviço

```powershell
uv run --no-sync pytest tests/unit/test_user_statistics_schema.py tests/unit/test_user_statistics_service.py
```

Verifica:
- Limites e aliases do contrato público.
- Retorno da sequência para atividade hoje, ontem, expirada e ausente.
- Reuso da consulta de ranking e erro para usuário não encontrado.
- Contagem de conquistas desbloqueadas sem atualizar ou recalcular progresso.

### Contrato e autenticação

```powershell
uv run --no-sync pytest tests/contract/test_user_statistics_contract.py
```

Verifica:
- Resposta `200` com exatamente os cinco campos definidos em
  [user-statistics-api.md](./contracts/user-statistics-api.md).
- Autenticação obrigatória, Problem Details e isolamento do usuário atual.
- Ausência de identificadores, e-mail, credenciais e campos internos.

### Integração com PostgreSQL

```powershell
uv run --no-sync pytest tests/integration/test_user_statistics.py
```

Verifica:
- Igualdade entre XP, missões concluídas e posição do resumo e dos recursos
  existentes de perfil e ranking.
- Inclusão apenas de conquistas ativas com progresso `done`.
- Sequência sem registro, recente ou expirada, incluindo ausência de mutações
  durante as consultas.
- Usuário sem progresso, usuário indisponível e isolamento entre usuários.

### Desempenho

```powershell
uv run --no-sync pytest tests/performance/test_user_statistics_performance.py
```

Executa a medição do endpoint em ambiente configurado e valida o percentil 95
de até 2 segundos conforme SC-006. Se o ambiente externo de desempenho não
estiver configurado, o teste deve indicar o pré-requisito ausente e ser marcado
como não executado, não como aprovado.

## Verificação geral

```powershell
uv run --no-sync ruff check .
uv run --no-sync pytest
```

O fluxo só está validado quando lint e testes aplicáveis passam. A consulta não
deve criar migrations nem alterar dados de progresso, atividade ou conquistas.
