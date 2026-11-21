# Implementation Plan: Resumo de Estatísticas de Aprendizagem

**Branch**: `feat/sdb-112-endpoint-estatistica-usuario` | **Date**: 2026-11-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-112-learning-stats-summary/spec.md`

## Summary

Disponibilizar um resumo autenticado e somente de leitura em
`GET /api/v1/users/me/statistics`, contendo XP, missões concluídas, posição no
ranking, conquistas desbloqueadas e sequência atual de atividade. O serviço
reutilizará a consulta individual já existente do ranking para manter os três
valores consistentes, e consultará separadamente a contagem de conquistas ativas
concluídas e a sequência de atividade. A sequência será considerada atual quando
a última atividade ocorreu hoje ou ontem em UTC; caso contrário, será exibida
como zero, sem alterar registros.

## Technical Context

**Language/Version**: Python >=3.11 (limite declarado pelo projeto)

**Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2 assíncrono

**Storage**: PostgreSQL existente, acessado por `AsyncSession`; nenhuma tabela
ou coluna nova

**Testing**: Pytest; testes unitários, de contrato, integração e desempenho já
organizados no repositório

**Target Platform**: Serviço web existente; implantação e configuração de
container permanecem inalteradas

**Project Type**: API web

**Performance Goals**: Pelo menos 95% das consultas em até 2 segundos, conforme
SC-006

**Constraints**: Somente leitura; autenticação existente; não duplicar regras
do ranking ou da concessão de XP; resposta sem dados privados adicionais

**Scale/Scope**: Uma consulta consolidada para o usuário autenticado, usando os
registros existentes; sem novas métricas, persistência ou histórico

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Antes da pesquisa

- **I. Qualidade de código e Clean Code**: PASS — a composição fica em um
  serviço dedicado, com consultas e projeções pequenas e explícitas.
- **II. Responsabilidade única e coesão**: PASS — rota, schema, serviço e
  repositório mantêm suas responsabilidades separadas.
- **III. Separação clara de camadas**: PASS — fluxo previsto
  `router -> service -> repositories -> models`, com composição via `Depends`.
- **IV. Testes e contratos verificáveis**: PASS — haverá testes unitários,
  integração, contrato e validação de desempenho conforme o critério definido.
- **V. Simplicidade e evolução segura**: PASS — consulta nova, sem migração ou
  mudança incompatível; erros mantêm Problem Details.

**Gate**: PASS. Não há violação constitucional que exija justificativa ou
clarificação.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-112-learning-stats-summary/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── user-statistics-api.md
```

### Source Code (repository root)

```text
src/
├── main.py
└── sidebrain_back/
    ├── routers/
    │   ├── router.py
    │   └── v1/
    │       └── user_statistics_router.py
    ├── schemas/
    │   └── user_statistics_schema.py
    ├── services/
    │   └── user_statistics_service.py
    └── repositories/
        └── user_statistics_repository.py

tests/
├── contract/
│   └── test_user_statistics_contract.py
├── integration/
│   └── test_user_statistics.py
├── performance/
│   └── test_user_statistics_performance.py
└── unit/
    ├── test_user_statistics_schema.py
    └── test_user_statistics_service.py
```

**Structure Decision**: A feature segue a API Python existente em
`src/sidebrain_back/`, com os arquivos nomeados por domínio e camada conforme
`docs/code_conventions.md`. O novo roteador será incluído no agregador
`src/sidebrain_back/routers/router.py`; a rota usará o prefixo global `/api` e
o prefixo de usuário `/v1/users`. Os testes seguem as pastas unit, contract,
integration e performance já existentes. Nenhum modelo persistente ou
migration será criado.

### Depois do design

- **I. Qualidade de código e Clean Code**: PASS — o serviço de estatísticas
  consolida respostas sem replicar regras de domínio.
- **II. Responsabilidade única e coesão**: PASS — consultas ficam no
  repositório de estatísticas e o cálculo da validade da sequência fica no
  serviço.
- **III. Separação clara de camadas**: PASS — dependências seguem a direção
  normativa; a rota não acessa diretamente modelos ou repositórios.
- **IV. Testes e contratos verificáveis**: PASS — o contrato OpenAPI e os
  cenários unitários, de contrato, integração e desempenho estão previstos.
- **V. Simplicidade e evolução segura**: PASS — sem persistência nova,
  alterações incompatíveis ou efeitos colaterais; erros permanecem no formato
  Problem Details.

**Gate pós-design**: PASS. O design preserva os contratos existentes e não
requer exceções à constituição.

## Complexity Tracking

Nenhuma violação constitucional ou projeto adicional introduzido.
