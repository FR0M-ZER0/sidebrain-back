# Implementation Plan: Autenticação e perfil do usuário

**Branch**: `sdb-81-criar-endpoints-para-autenticacao-e-gerenciamento-do-perfil-do-usuario` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Jira SDB-81 e `specs/SDB-81-user-auth-profile/spec.md`.

## Summary

Criar cadastro e entrada por e-mail e senha, quatro operações sobre `/users/me` e substituir o Bearer provisório de UUID por JWT assinado. O banco continuará sendo a fonte da identidade e do estado ativo; uma versão de credencial persistida permitirá revogar todos os tokens anteriores à troca de senha. PostgreSQL garantirá unicidade do e-mail sem distinção de caixa, inclusive sob concorrência. Redis aplicará limites separados às falhas de entrada e troca de senha. O contrato existente dos outros recursos permanece, com troca obrigatória da credencial Bearer.

## Technical Context

**Language/Version**: Python >=3.11.

**Primary Dependencies**: FastAPI >=0.141.1, Pydantic >=2.11, SQLAlchemy >=2.0.52, Alembic >=1.19.2, asyncpg, Redis/redis-py >=8.1; adicionar `pwdlib[argon2]`, `PyJWT` e `email-validator` para senha, token e validação de e-mail.

**Storage**: PostgreSQL 16; tabela `user` existente, nova coluna `usr_token_version` e índice único sobre `lower(btrim(usr_email))`. Redis 7, banco lógico `/2`, para contadores e bloqueios transitórios; `/0` e `/1` seguem reservados ao Celery.

**Testing**: pytest em `tests/unit`, `tests/integration`, `tests/contract` e ensaio de performance; `uv run ruff check .`, `uv run pytest`, migração Alembic upgrade/downgrade e validação da implantação.

**Target Platform**: API FastAPI com PostgreSQL e Redis, executável localmente e em servidor Linux; hash de senha executado fora do event loop.

**Project Type**: Serviço HTTP com rotas versionadas em `/api/v1`.

**Performance Goals**: Em 20 clientes simultâneos, ao menos 95% das operações válidas de cadastro, entrada e consulta de perfil em até 2 segundos (SC-006), medidos no ambiente alvo.

**Constraints**: JWT HS256 com expiração de 60 minutos e segredo obrigatório fora do código; Argon2id; 5 falhas em janela móvel de 15 minutos seguidas de bloqueio de 15 minutos; usuário excluído e versão antiga de credencial sem acesso; nenhum segredo ou hash na API; 204 sem corpo; Problem Details nos erros; migração coordenada dos clientes que enviam UUID puro.

**Scale/Scope**: 6 operações HTTP, novo repository/service/schema de usuário e autenticação, segurança e limitador em `core`, uma migração do usuário, ajustes de configurações, testes e documentação de consumidores. Sem refresh token, recuperação de senha, OAuth, roles ou efeitos em `login`/`day_streak`.

## Constitution Check

*Gate avaliado antes da pesquisa da Fase 0.*

- **I. Qualidade e Clean Code — PASS**: helpers de segurança e limite têm responsabilidades definidas; a rota pública reutiliza a representação de usuário.
- **II. Responsabilidade única — PASS**: validação de credenciais e mutações ficam em services; repository concentra consultas e persistência.
- **III. Camadas — PASS após refatoração planejada**: routers usam `Depends` para services; services usam repository e segurança transversal de `core`. O provider HTTP `get_current_user` sai de `core/auth.py` e fica em `routers/v1/auth_router.py`, delegando a consulta ao `AuthService` sem mudar a assinatura das rotas protegidas.
- **IV. Testes e contratos — PASS condicionado à implementação**: há cenários de contrato, unidade, integração, migração e carga descritos em [quickstart.md](quickstart.md). Nenhum código foi alterado nesta fase.
- **V. Simplicidade e evolução — PASS**: versão de credencial é o menor estado persistido para revogação; mudança incompatível do Bearer tem procedimento de migração para consumidores e erros padronizados.

Não há violação constitucional ou questão de desenho em aberto. Colisões de e-mail e hashes legados são condições de implantação com pré-verificação e ação definida em [research.md](research.md).

## Project Structure

### Documentation (this feature)

```text
specs/SDB-81-user-auth-profile/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── auth-profile.md
└── checklists/
    └── requirements.md
```

`tasks.md` pertence à etapa posterior `/speckit-tasks`.

### Source Code (repository root)

```text
src/sidebrain_back/
├── core/auth.py, security.py, rate_limit.py, constants.py, errors.py
├── models/user_model.py
├── repositories/user_repository.py
├── schemas/user_schema.py, auth_schema.py
├── services/user_service.py, auth_service.py
└── routers/router.py, v1/auth_router.py, v1/user_router.py
migrations/versions/*_user_auth.py
tests/unit/, tests/integration/, tests/contract/, tests/performance/
```

**Structure Decision**: manter o projeto único em `src/sidebrain_back` e o fluxo normativo `router -> service -> repository -> model`. `core` contém segurança, Redis e tratamento transversal, sem importar `models` ou `repositories`. O provider `get_current_user` em `routers/v1/auth_router.py` compõe Bearer e `AuthService`; os demais routers apenas mudam o import, mantendo a assinatura de suas operações. Providers de repository e service ficam junto das respectivas classes. Testes que enviam UUID provisório devem passar a emitir token real.

## Phase 0: Research Summary

[research.md](research.md) registra decisões, razões, alternativas e referências para Argon2id, JWT, revogação, unicidade, limite de tentativas, erros e implantação. Todas as escolhas técnicas necessárias estão resolvidas.

## Phase 1: Design Summary

- [data-model.md](data-model.md): campos, invariantes, estados e migração de `User`, credencial e buckets transitórios.
- [contracts/auth-profile.md](contracts/auth-profile.md): seis endpoints, schemas públicos, códigos, headers e formato de erro.
- [quickstart.md](quickstart.md): preparação, validação ponta a ponta, concorrência, segurança, migração de consumidores e critérios de conclusão.

## Constitution Check: pós-design

- **I e II — PASS**: a versão do token e os buckets de limite têm finalidade concreta; não duplicam regras de usuário nos routers.
- **III — PASS**: o contrato exige `Depends`; a origem HTTP chega ao service apenas como dado já extraído pelo router.
- **IV — PASS no design**: cada regra crítica possui cenário de contrato, persistência ou concorrência no quickstart; a execução é gate da implementação, não desta fase documental.
- **V — PASS**: migração reversível de esquema, pré-verificação de dados antigos, plano de corte do Bearer e Problem Details preservam evolução controlada.

Nenhuma violação permanece após o design. Esta entrega contém somente plano e artefatos de desenho; implementação e testes executáveis ficam para a etapa de tarefas.
