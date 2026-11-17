# Validação com consumidores da API

**Data:** 2026-10-14  
**Ambiente:** API local, PostgreSQL 16 efêmero e Redis 7.  
**Método:** cinco sessões HTTP independentes, implementadas sem importar
módulos internos da aplicação. Cada sessão recebeu somente os caminhos,
campos e respostas definidos pelo contrato público.

Esta é uma validação técnica automatizada de consumidores do contrato. Ela
não representa pesquisa de usabilidade com participantes humanos.

## Registro

| Consumidor | Cadastro | Entrada | Perfil | Sem esclarecimento | Evidência |
| --- | --- | --- | --- | --- | --- |
| consumer-01 | `201` | `200` | `200` | Sim | `pytest` — caso `consumer-01` aprovado |
| consumer-02 | `201` | `200` | `200` | Sim | `pytest` — caso `consumer-02` aprovado |
| consumer-03 | `201` | `200` | `200` | Sim | `pytest` — caso `consumer-03` aprovado |
| consumer-04 | `201` | `200` | `200` | Sim | `pytest` — caso `consumer-04` aprovado |
| consumer-05 | `201` | `200` | `200` | Sim | `pytest` — caso `consumer-05` aprovado |

Cada consumidor criou uma conta exclusiva, entrou com as próprias
credenciais, consultou o próprio perfil com o token retornado no login e
removeu a conta ao final. O teste conferiu também que as respostas expõem
somente os campos públicos do contrato. Nenhuma senha ou token foi registrada
como evidência.

## Resultado

O comando abaixo executou os cinco casos contra a aplicação em execução:

```powershell
$env:AUTH_CONSUMER_BASE_URL='http://127.0.0.1:18080'
.\.venv\Scripts\python.exe -m pytest `
  tests/acceptance/test_auth_consumer_validation.py -q -p no:cacheprovider
```

Resultado observado: `5 passed in 1.09s`.

O critério SC-007 exige cinco consumidores e ao menos quatro jornadas
concluídas sem esclarecimentos adicionais. A execução obteve **5 de 5**;
portanto, o critério foi atendido no escopo de validação técnica do contrato.
