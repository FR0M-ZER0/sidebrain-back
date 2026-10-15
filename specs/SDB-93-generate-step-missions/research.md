# Research: Geração de Missões por IA para Steps

## Estado consultável, ownership e repetição segura

**Decision**: Persistir um registro de geração de missão com ID de task Celery, Step, usuário proprietário, estado, timestamps e código de erro sanitizado. A API consulta este registro e não trata o backend de resultados Celery como fonte pública de estado. Gerar o ID antes de publicar e enviá-lo explicitamente ao Celery. Enquanto o registro estiver `pending` ou `running`, uma repetição do proprietário retorna `202` com o mesmo ID. Estados terminais são `succeeded` e `failed`; uma nova solicitação após falha pode criar uma nova geração.

**Rationale**: O requisito acrescentado no esclarecimento pede consulta com ownership; `AsyncResult` pode reportar `PENDING` também para um ID desconhecido, além de depender do backend e retenção do resultado. O registro da aplicação distingue a solicitação autorizada, permite ocultar registros de outros usuários sob o mesmo 404 e conserva estado/código de falha para consulta. O padrão de geração de Trilhas já persiste estados no banco e captura falhas ao publicar tarefas.

**Alternatives considered**:
- Usar apenas `AsyncResult`: rejeitado por não fornecer por si só um mapeamento persistente e autorizado entre ID da task e usuário/Step, e por a semântica `PENDING` também cobrir IDs inexistentes.
- Armazenar estado apenas no broker/backend de resultados: rejeitado como contrato de longa duração, pois retenção e disponibilidade dependem da configuração operacional e não resolvem ownership.
- Reutilizar o registro de geração de Trilha: rejeitado por misturar domínios e vincular solicitações de missão a um modelo de geração com ciclo de vida e contexto diferentes.

**References**:
- [Celery 5.6 task states](https://docs.celeryq.dev/en/v5.6.3/userguide/tasks.html#built-in-states): estados e metadados de task; o estado `PENDING` também pode representar task desconhecida.
- Repositório local: `src/sidebrain_back/routers/v1/track_router.py` expõe consulta autenticada de progresso; `src/sidebrain_back/services/track_service.py` persiste estado e trata falha ao publicar geração.

## Concorrência e publicação assíncrona

**Decision**: Sob transação curta, bloquear o Step ativo de forma compatível com o fluxo incremental, validar ownership e verificar missões e solicitações ativas; criar o registro `pending` e fazer commit. Publicar a task com o ID previamente atribuído. Se a publicação falhar, marcar a solicitação como `failed` com código estável e responder com erro Problem Details; a próxima chamada poderá tentar novamente. O worker muda para `running`, gera sem manter lock de banco durante a chamada externa e revalida o Step antes da gravação.

**Rationale**: Serializar por Step permite que requisições concorrentes encontrem o mesmo registro ativo sem segurar lock durante o provedor. O desenho espelha o fluxo assíncrono atual e preserva a responsividade HTTP. IDs pré-atribuídos ligam com segurança o estado persistido à task publicada.

**Alternatives considered**:
- Manter uma transação/lock aberta durante a chamada à IA: rejeitado por alongar locks e transações em função de latência externa.
- Confiar somente em deduplicação dentro do worker: rejeitado por ainda publicar e pagar por tarefas concorrentes redundantes.
- Adicionar outbox transacional: não necessário neste escopo, pois o projeto já usa registro persistido, publicação após commit e tratamento explícito de falha no dispatch; reavaliar se uma garantia de entrega entre banco e broker se tornar requisito.

**References**:
- Repositório local: `src/sidebrain_back/tasks/prepare_next_step_content_task.py` segue o padrão de revalidar contexto, evitar conteúdo existente e persistir em transação.
- [SQLAlchemy 2.0 asyncio sessions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html): `AsyncSession.begin()` enquadra transação com commit/rollback; falha deve sair do bloco e provocar rollback.
- Repositório local: `docs/architecture.md` estabelece que tasks abrem sessão própria e orquestram services sem manter dependência do ciclo HTTP.

## Validação e persistência de Mission

**Decision**: Centralizar `GeneratedMission` no schema de geração e aplicá-lo a toda saída da IA (sob demanda, geração inicial e preparação incremental). Rejeitar campos extras, usar os enums de domínio e exigir `xp_reward > 0` e `criteria_value > 0`. Sob demanda, validar que a resposta contém exatamente a quantidade pedida; qualquer quantidade divergente invalida o lote inteiro. Validar todas as missões antes de persistir; gravar pelo `MissionService`/`MissionRepository` e confirmar todas em uma única transação.

**Rationale**: O requisito identifica uma divergência atual entre validadores e demanda reutilização das camadas CRUD. A centralização remove divergência e o pré-validador de lote mais a transação garantem ausência de persistência parcial.

**Alternatives considered**:
- Manter schemas separados para geração inicial e incremental: rejeitado porque já existe divergência de limites e gera manutenção duplicada.
- Inserir diretamente pelo model/repository na task: rejeitado por duplicar regra e contornar o caminho de domínio exigido.
- Aceitar valores zero e tratá-los como “sem recompensa”: rejeitado pelo contrato de negócio explicitado, que exige positividade.

## Falhas e observabilidade

**Decision**: Retry limitado com backoff somente para falhas transitórias do provedor; parsing e validação terminam como falha sem retry. Mapear estados internos da task a `pending`, `running`, `succeeded` e `failed`; não expor traceback, prompt ou resposta bruta. Registrar task ID, Step ID e categoria do erro.

**Rationale**: A API fornece um estado previsível e seguro para o cliente; os detalhes necessários ao diagnóstico permanecem nos logs estruturados.

**Alternatives considered**:
- Expor estado e exceção diretamente do backend Celery: rejeitado por vazar dados de implementação e potencialmente conteúdo sensível.
- Repetir qualquer falha: rejeitado por desperdiçar recursos e repetir respostas determinísticas inválidas.

## Decisões resolvidas

- Estado da task é consultável por ID, limitado ao usuário proprietário.
- Missão da geração inicial é opcional; missão inválida fornecida continua sendo erro, não é silenciosamente descartada.
- Chamadas repetidas enquanto a geração estiver ativa retornam o ID existente.
- Endpoint novo segue o versionamento do repositório (`/v1`); contratos existentes da Trilha e preparação incremental não mudam.
- A entrega das camadas de gerenciamento de Mission é pré-requisito, conforme declarado pela especificação.
