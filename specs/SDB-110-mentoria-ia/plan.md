# Implementation Plan: Mentoria de aprendizagem por IA

**Branch**: `feat/sdb-110-adiciona-mentor-ia` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Especificação em `specs/SDB-110-mentoria-ia/spec.md`

## Summary

Disponibilizar conversas de mentoria autenticadas, cada uma vinculada a uma trilha própria e imutável. O mentor deve orientar o estudo sem resolver atividades pelo estudante, fundamentando recomendações em dados permitidos da trilha escolhida. O desenho usa persistência própria, autorização específica versionada, geração assíncrona com Celery e isolamento de histórico. O estudante poderá consultar e apagar uma conversa ou todo o histórico.

## Technical Context

**Language/Version**: Python >=3.11.

**Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, Celery, Redis e cliente OpenAI compatível já existente. Injeção com `Depends`; chamada síncrona do provedor em worker, não no event loop HTTP.

**Storage**: PostgreSQL para conversas, mensagens, autorização e estado de geração; Redis como broker, sem conteúdo privado nas tarefas ou resultados.

**Testing**: pytest unitário, contrato e integração PostgreSQL; Ruff; avaliação de cenários sintéticos conforme SC-001 a SC-006, sem participantes reais.

**Target Platform**: backend em servidor Linux com API e worker Celery.

**Project Type**: serviço web FastAPI versionado.

**Performance Goals**: submissão assíncrona e paginação; sem meta de latência ou escala numérica estabelecida pela spec. Definir e monitorar capacidade/limites a partir de medições; timeout inicial do provedor de 30 segundos, configurável.

**Constraints**: dados da trilha do próprio usuário; consentimento anterior a qualquer envio; sem conteúdo privado em broker, logs, cache global ou resultados de tasks; resposta completa validada; exclusão física do conteúdo; nenhuma alteração automática no aprendizado.

**Scale/Scope**: uma geração ativa por conversa; várias conversas por trilha; entrada até 4.000 caracteres e listagens paginadas (1–100 itens). Sem notificações proativas, áudio, RAG ou interface frontend nesta fase.

## Constitution Check

| Princípio / gate | Antes da pesquisa | Após o design |
|---|---|---|
| I. Código coeso, explícito e testável | Atende: gerador e contexto separados | Atende: contratos e testes isolam responsabilidades |
| II. Responsabilidade única | Atende: domínio dedicado | Atende: persistência, orquestração e tasks separadas |
| III. Camadas e `Depends` | Atende: router → service → repository → model | Atende: worker compõe serviços sem depender de HTTP |
| IV. Testes e contratos | Atende: plano prevê unitários, integração e contrato | Atende: critérios, falhas, migração e isolamento especificados |
| V. Simplicidade e evolução segura | Atende: contratos v1 aditivos | Atende: Problem Details, migração e logs sem dados sensíveis |

Nenhuma exceção constitucional proposta. A conformidade operacional e jurídica do armazenamento externo exige validação antes da produção; não é garantida pelo desenho.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-110-mentoria-ia/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/mentoria.md
└── tasks.md                 # etapa posterior, não criado neste plano
```

### Source Code (repository root)

```text
src/sidebrain_back/
├── models/                  # conversa, mensagem, geração e autorização
├── schemas/                 # entradas, saídas e validações da mentoria
├── repositories/            # acesso isolado por dono, projeção e operações atômicas
├── services/                # consentimento, contexto, orquestração e geração
├── routers/v1/              # contrato HTTP de mentoria
├── routers/router.py        # registro do router
└── tasks/                   # worker de geração e recuperação de despacho
migrations/versions/         # migration aditiva, constraints e índices
tests/unit/
tests/integration/
tests/contract/
```

**Structure Decision**: estender as camadas existentes, com arquivos `<domínio>_<camada>.py` e providers junto às classes; registrar modelos em `models/__init__.py` e `migrations/env.py`. Verificar a revisão Alembic atual no momento da implementação. Respeitar `docs/architecture.md` e `docs/code_conventions.md`.

## Design e etapas

1. **Persistência e isolamento**: criar entidades e migração conforme [data-model.md](data-model.md); verificar propriedade e estado da trilha em todos os acessos; manter sequências estáveis e isolamento entre conversas.
2. **Autorização e privacidade**: apresentar aviso versionado com destinatário real, categorias e finalidade; registrar aceite específico e revogação. Proibir envio externo sem autorização corrente. Validar a política de retenção e as obrigações do fornecedor antes da ativação em produção.
3. **Contexto e orientação**: construir projeção mínima da trilha, avaliações comprovadamente vinculadas e mensagens da conversa. Filtrar também usuário das respostas de quiz; não usar carregamento genérico da hierarquia nem cache global de geração. Usar prompt de mentor e tratar conteúdo do estudante como dados não confiáveis.
4. **Geração e recuperação**: persistir mensagem e geração idempotente, criar registro de despacho recuperável e executar task que recebe apenas IDs. Recuperar `queued` e detectar `processing` abandonado com identificador de tentativa e transição condicional; não repetir envio inconclusivo até resolver sua reserva. Revalidar posse, estado e autorização; limitar timeout e retries; validar resposta e disponibilizá-la por consulta individual desde US1.
5. **Exclusão e concorrência**: além do lock consultivo por usuário, persistir reservas de envio e bloqueio de privacidade transacionais conforme [data-model.md](data-model.md). Revogação e exclusão bloqueiam novas reservas e não confirmam sucesso enquanto houver envio inconclusivo; retornar `503` com bloqueio mantido quando a conclusão não puder ser comprovada. Sem transação aberta no I/O; integrar exclusão lógica de trilha/conta ao expurgo físico.
6. **Contratos**: implementar endpoints e códigos de [contracts/mentoria.md](contracts/mentoria.md), paginação padrão, Problem Details e schemas compatíveis com as convenções.
7. **Validação**: testar ownership com dois usuários e duas trilhas, autorização/revogação, não vazamento do contexto, falhas e retry, idempotência, corridas com exclusão, ausência de texto em logs/filas, migração e execução completa das metas amostradas da spec. Usar [quickstart.md](quickstart.md).

## Riscos e decisões operacionais

- O lock por usuário pode ser perdido enquanto o processo continua ativo. A reserva durável permanece até confirmação segura do término local da tentativa; em caso inconclusivo, preservar bloqueio e exigir comprovação operacional de encerramento antes de liberá-lo. A disponibilidade pode ser afetada; timeout ou perda de conexão, sozinhos, não provam que o envio terminou. Não afirmar que dados enviados anteriormente ao provedor foram apagados.
- A consistência entre commit e publicação da task exige recuperação periódica do despacho persistente e deduplicação; a recuperação de `processing` deve impedir publicação por tentativa obsoleta e não prometer exatamente uma chamada externa.
- Conteúdo de terceiros, resultados antigos e avaliações puladas não são evidência de desempenho atual. Se o vínculo da avaliação à trilha não existir, omiti-la.
- Documentar política do provedor, retenção legal e processo de resposta a exclusão antes da produção. Não assumir obrigação legal específica sem validação.
- Context7 indisponível; documentações oficiais consultadas estão em [research.md](research.md).

## Complexity Tracking

Nenhuma violação constitucional identificada. O lock e o registro de despacho são necessários para evitar republicação após exclusão e perda/duplicação de trabalho diante de falhas, respectivamente.
