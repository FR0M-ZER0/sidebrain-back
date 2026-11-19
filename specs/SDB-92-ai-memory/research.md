# Pesquisa — SDB-92 Memória determinística da IA

## Decisões

### Cache global separado das instâncias de usuário

- **Decisão**: criar `GenerationCache` global e imutável, armazenando o payload
  canônico validado em JSON; materializar uma nova Track ou KnowledgeAssessment
  para cada usuário.
- **Racional**: `Track` e `KnowledgeAssessment` atuais possuem ownership,
  estados, soft delete, respostas, feedbacks e progresso. Compartilhá-los
  diretamente contaminaria dados de usuários e permitiria mutação do cache.
- **Alternativas consideradas**: transformar `Track` em entidade global
  (mistura template com progresso); copiar somente IDs (quebra FKs e
  ownership); serializar fora do banco (perde transações e constraints).

### Fingerprint canônico e versionado

- **Decisão**: normalizar Unicode com NFKD, remover diacríticos, aplicar
  `casefold`, trim, colapsar whitespace e remover pontuação periférica; aplicar
  aliases exatos após a normalização; gerar SHA-256 de JSON ordenado contendo
  `fingerprint_version`, `content_type`, contexto canônico, nível, respostas
  normalizadas quando aplicável, `prompt_version`, `provider` e `model`.
  `assessment_id` não entra na chave quando não altera o conteúdo.
- **Racional**: entradas equivalentes produzem a mesma chave, enquanto mudanças
  de contrato, prompt ou modelo criam nova entrada sem reescrever históricos.
- **Alternativas consideradas**: similaridade semântica (não determinística);
  hash do texto original (não resolve caixa/acentos/aliases); IDs de usuário
  na chave (impediria reuso).

### Aliases curados versionáveis

- **Decisão**: tabela `TopicAlias` com alias normalizado único, tópico
  canônico normalizado e versão; carga inicial via migration/seed. Não haverá
  CRUD público.
- **Racional**: `ingles -> lingua inglesa` é determinístico e auditável;
  aliases desconhecidos não podem ser inferidos.
- **Alternativas consideradas**: dicionário em código (não auditável);
  busca fuzzy (não determinística).

### Concorrência por lease e unicidade persistente

- **Decisão**: `GenerationCache` terá estados `pending`, `ready` e `failed`,
  `lease_owner` e `lease_expires_at`, além de constraint única no fingerprint
  e tipo. O worker reserva/renova a lease em transação curta com `FOR UPDATE`;
  a chamada ao provedor ocorre fora da transação. Redis pode fornecer lock
  distribuído curto, mas sua ausência é tratada como miss. Conflito de
  constraint relê o vencedor e aguarda/reusa.
- **Racional**: `FOR UPDATE` e `ON CONFLICT` são suportados pelo SQLAlchemy
  2.0/PostgreSQL; a constraint é a garantia permanente e a lease expira após
  crash, sem manter lock de banco durante chamada externa.
- **Alternativas consideradas**: manter lock durante a IA (timeout e bloqueio);
  somente Redis (sem unicidade persistente); duplicatas temporárias (viola
  FR-010).

### Escopo do conteúdo reutilizado

- **Decisão**: a memória cobre a geração inicial dos fluxos atuais de Track e
  Assessment. Conteúdo incremental de Steps futuros continua por usuário e não
  recebe fingerprint próprio nesta versão.
- **Racional**: a especificação limita o escopo a trilhas e avaliações e os
  Steps posteriores são gerados sob demanda.
- **Alternativas consideradas**: cachear cada Step futuro (feature própria);
  cachear somente títulos (não economiza a chamada que gera o payload).

### Fallback e configuração

- **Decisão**: `AI_MEMORY_ENABLED` desliga lookup, lock e gravação sem alterar
  requests ou respostas; falha do cache faz fallback para IA com `source=ai`;
  payload inválido nunca entra no cache; falha ao materializar a instância
  desfaz a transação e falha a geração.
- **Racional**: cache é otimização, não dependência funcional, atendendo
  FR-012/FR-013.
- **Alternativas consideradas**: erro público quando Redis/cache falha
  (indisponibilidade indevida); publicar payload parcial (corrupção).

### Progresso e observabilidade

- **Decisão**: adicionar `source: ai | cache | None` ao progresso, SSE e
  detalhe da avaliação. Logs registram tipo, fingerprint, hit/miss, lock e
  chamadas evitadas, sem payload, tokens ou PII.
- **Racional**: preserva polling e compatibilidade de clientes antigos.
- **Alternativas consideradas**: novo stream global de cache (novo contrato);
  payload integral em logs (risco de exposição).

## Evidências consultadas

- `src/sidebrain_back/services/track_service.py`,
  `src/sidebrain_back/tasks/generate_track_task.py` e
  `src/sidebrain_back/services/generation_service.py`: request assíncrono,
  commit antes do Celery e materialização em transação.
- `src/sidebrain_back/services/knowledge_assessment_service.py` e
  `knowledge_assessment_generator.py`: fingerprint atual e payload de cinco
  perguntas.
- `src/sidebrain_back/routers/v1/track_router.py`: SSE por polling de request.
- Modelos de Track e Assessment: ownership, cascatas e constraints atuais.
- SQLAlchemy 2.0: `AsyncSession.begin`, `Select.with_for_update` e PostgreSQL
  `ON CONFLICT`.
- FastAPI: response models e streaming de eventos SSE.
