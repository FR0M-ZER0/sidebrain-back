# Pesquisa: Geração de Trilhas com IA

## Cliente e formato da IA

**Decision:** Reutilizar `sidebrain_back.core.groq_client.get_groq_client` e solicitar uma resposta JSON estruturada. O conteúdo será desserializado em schemas Pydantic internos antes de qualquer acesso ao banco.

**Rationale:** O projeto já centraliza a criação do cliente Groq. A resposta estruturada permite validar campos obrigatórios, enums, limites e a regra de que apenas a primeira etapa contém conteúdo detalhado. O SDK expõe `response_format` e exceções separadas para conexão, rate limit e erros de status.

**Alternatives considered:** Criar um segundo cliente foi rejeitado por duplicar configuração. Aceitar texto livre e extrair campos por regex foi rejeitado por ser frágil e permitir persistência parcial.

## Retry da task

**Decision:** Classificar erros de conexão, timeout e rate limit como transitórios e usar `self.retry`/configuração de retry do Celery com `max_retries=3`, backoff e jitter. Erros de resposta inválida, erro permanente do provedor e falha de validação não serão repetidos automaticamente.

**Rationale:** O requisito fixa três tentativas totais. O retry fica limitado ao perímetro da chamada externa; a persistência só começa depois da resposta validada. A task deve aceitar reexecução sem criar duplicatas.

**Alternatives considered:** Repetir toda a task após qualquer exceção foi rejeitado porque pode repetir gravações. Retries infinitos foram rejeitados por ocultar indisponibilidade do provedor.

## Idempotência

**Decision:** Receber um `request_id` estável na task e persistir esse identificador em uma coluna única e não exposta de `Track`. Antes de chamar a IA, o serviço procura uma trilha já associada; se encontrada, retorna o resultado existente. Concorrência é protegida pela restrição única e tratamento de conflito.

**Rationale:** O modelo atual não possui associação durável entre task e trilha; usar apenas o ID efêmero do Celery não sobrevive a reentrega ou reinício do worker. A chave persistida satisfaz a reutilização exigida e torna a operação idempotente.

**Alternatives considered:** Usar somente o backend de resultados do Celery foi rejeitado por depender de retenção e não proteger a persistência. Aceitar duplicatas e deduplicar depois foi rejeitado por violar o requisito de não criar trilhas duplicadas.

## Transação e persistência

**Decision:** O repositório receberá uma `AsyncSession` e criará Track, Steps, Lessons, Quizzes e, quando aplicável, Mission dentro de `async with session.begin()`. A resposta inteira será validada antes do bloco transacional; qualquer exceção causa rollback integral.

**Rationale:** `AsyncSession.begin()` fornece commit automático ao sair com sucesso e rollback em erro. O repositório preserva a separação de camadas e pode montar relações ORM sem expor IDs físicos aos schemas internos.

**Alternatives considered:** Fazer commits por entidade foi rejeitado porque deixa trilhas parciais. Colocar queries no task foi rejeitado por violar a arquitetura existente.

## Escopo de conteúdo

**Decision:** O prompt pedirá todas as etapas na ordem da estratégia e conteúdo detalhado somente para a etapa de posição 1. O validador rejeitará posições duplicadas, níveis fora da progressão, conteúdo em etapas posteriores e missão duplicada; lições terão posição única e ordenada.

**Rationale:** A regra é verificável antes da persistência e evita gasto de tokens e armazenamento futuro. Os enums existentes (`StepLevelEnum`, `MissionDifficultyEnum`, `MissionCriteriaEnum`) são a fonte de domínio.

**Alternatives considered:** Gerar todas as lições antecipadamente foi rejeitado pelo FR-009. Inferir a ordem no serviço foi rejeitado porque ocultaria uma resposta inválida da IA.

## Observabilidade e resultado

**Decision:** A task retornará um payload serializável com status de sucesso/falha e o identificador lógico da trilha quando concluída. Logs estruturados registrarão `request_id`, task id e categoria do erro, sem prompt completo, credenciais ou detalhes internos do provedor.

**Rationale:** O fluxo de acompanhamento precisa distinguir conclusão de falha tratável, enquanto a constituição exige diagnóstico sem vazamento de dados internos.

**Alternatives considered:** Propagar exceções brutas do SDK foi rejeitado porque expõe detalhes de infraestrutura e não produz um contrato estável.
