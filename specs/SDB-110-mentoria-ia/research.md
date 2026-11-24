# Pesquisa: mentoria por IA

**Data**: 2026-11-18 | **Spec**: [spec.md](spec.md)

## Decisões

### Execução da orientação

- **Decisão**: gerar respostas em tarefa Celery, com estado persistido no banco e consulta autenticada pelo cliente; a tarefa recebe apenas identificadores, não texto ou contexto no broker.
- **Justificativa**: chamadas externas podem demorar; `docs/architecture.md` exige tasks para integrações externas demoradas. Mensagens privadas não devem aparecer em argumentos, logs nem resultados do broker.
- **Alternativas**: chamada HTTP bloqueante, que contraria a arquitetura para operações demoradas; SSE, que não é necessário para o MVP e não elimina a necessidade de persistir estados.

### Contexto e isolamento

- **Decisão**: montar um contexto mínimo e limitado à trilha selecionada e ao histórico da própria conversa; usar apenas registros de propriedade comprovada e avaliações comprovadamente ligadas à trilha. Ausência de associação confiável significa omissão, nunca consulta por usuário ou assunto como aproximação.
- **Justificativa**: a spec proíbe dados de outras trilhas e exige fundamentação honesta; isolar o contexto também reduz exposição.
- **Alternativas**: contexto global do usuário ou cache compartilhado de respostas personalizados, ambos rejeitados por risco de vazamento e mistura de dados.
- **Evidências do repositório**: `track_repository.py` verifica dono/trilha ativa, mas o carregamento geral de `Quiz.answers` não filtra explicitamente o autor; criar projeção específica com filtros também em `Answer.ans_user_id`, exclusões em cada nível e caminho `Answer → Quiz → Lesson → Step → Track`, conforme `step_summary_repository.py`. Não enviar a hierarquia integral.
- Avaliação só é vinculável pelo caminho `Track.trk_generation_request_id → GenerationRequest.assessment_id → KnowledgeAssessment`, verificando ambos os donos. Avaliação `skipped` com nível inicial não é medição. Trilhas legadas podem não ter vínculo; nesses casos omitir avaliação.

### Autorização específica

- **Decisão**: fornecer aviso versionado com categorias de dados, finalidade e destinatário configurado; registrar aceite explícito associado ao usuário e à versão. Antes de cada envio, verificar autorização válida; ausência, revogação ou mudança material do aviso bloqueiam novos envios. A revogação não apaga conversas automaticamente.
- **Justificativa**: a spec exige informação e autorização antes do primeiro envio; versão e revogação são escolhas de desenho para impedir uso de aceite obsoleto.
- **Alternativas**: presumir aceite no cadastro, ou solicitar em toda mensagem, rejeitadas por não serem específicas ou por atrito desnecessário.

### Exclusão e concorrência

- **Decisão**: exclusão física transacional das mensagens e respostas; exclusão única ou de todo o histórico do usuário. Complementar o lock consultivo por usuário com reserva de envio durável e bloqueio de privacidade transacional, conforme [data-model.md](data-model.md). Sem transação aberta durante o I/O; revogação/exclusão não confirmam enquanto uma reserva não estiver comprovadamente encerrada. Fila e resultados não contêm dados da conversa.
- **Justificativa**: soft delete não atende ao esclarecimento do usuário. Uma chamada já iniciada ao fornecedor não pode ser desfeita. Perda de conexão libera o lock sem necessariamente encerrar o processo ou o envio; a reserva sobrevive à perda e privilegia segurança em detrimento de disponibilidade, inclusive com intervenção operacional se necessário.
- **Alternativas**: exclusão lógica ou confiar apenas no cancelamento da task, rejeitadas por não garantirem remoção nem prevenção de republicação.

### Falhas e idempotência

- **Decisão**: persistir operação antes do despacho, com identificação estável, uma geração ativa por conversa, recuperação de pendências não despachadas e deduplicação transacional. Para `processing` abandonado, reconciliar por prazo e identificador único da tentativa; reserva inconclusiva resulta em falha e bloqueio até confirmação do encerramento do processo. Usar timeout e retries limitados; permitir retry explícito somente após resolução, sem resposta parcial.
- **Justificativa**: entrega da fila e envio ao provedor podem falhar ou repetir; impedir duplicação de publicações sem prometer exatamente uma chamada externa.
- **Alternativas**: transação aberta durante chamada remota ou confiança na entrega única da fila, rejeitadas por bloqueios prolongados e falhas de recuperação.

### Qualidade da mentoria

- **Decisão**: prompt dedicado de orientação, validação de saída estruturada e avaliação com amostras das métricas SC-001 a SC-006; somente uma saída completa validada é publicada.
- **Justificativa**: a instrução ao modelo não garante resultados; validação estrutural e avaliação humana são complementares, não equivalem a garantia semântica.
- **Alternativas**: usar gerador de trilha inalterado ou tratar teste de esquema como prova da qualidade pedagógica, rejeitadas por escopo e confiabilidade.
- **Evidências do repositório**: `core/llm_client.py` fornece cliente síncrono OpenAI/Groq; `quiz_evaluation_service.py` separa instruções e dados não confiáveis, e `knowledge_assessment_generator.py` ilustra timeout/validação. Usar o cliente no worker, com injeção e timeout; não copiar chamada síncrona em handler assíncrono. `ai_memory_service.py` e `generation_memory_service.py` armazenam artefatos globais e não são apropriados para dados privados. O RAG pode usar LLM e embeddings externos; fica fora deste escopo inicial, evitando envios indiretos antes do aceite.

## Referências e limitações

- `docs/architecture.md`, `docs/code_conventions.md`, `pyproject.toml` e `.specify/memory/constitution.md`.
- [Celery: tasks, idempotência, timeout e dados sensíveis](https://docs.celeryq.dev/en/stable/userguide/tasks.html).
- [PostgreSQL: locks e transações](https://www.postgresql.org/docs/current/explicit-locking.html).
- [FastAPI: segurança](https://fastapi.tiangolo.com/tutorial/security/).
- O MCP Context7 não estava disponível; foram consultadas as documentações oficiais em seu lugar. Elas descrevem versões correntes, que devem ser conferidas contra as versões instaladas antes da implementação.
- Retenção legal e obrigações do fornecedor são decisões operacionais/jurídicas fora da spec; não presumir exceção legal nem declarar conformidade automática. A ativação em produção depende de política documentada e validada.
