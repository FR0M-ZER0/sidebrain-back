# Modelo de dados: mentoria por IA

Este é o desenho lógico proposto; nomes físicos e migração devem seguir os modelos existentes. Referência: [spec.md](spec.md).

## Entidades

### Autorização de mentoria

- `user_id`: dono autenticado; uma autorização corrente por usuário e finalidade.
- `notice_version`, `granted_at`, `revoked_at` opcional: versão aceita, data do aceite e eventual revogação. Aviso versionado identifica destinatário, finalidade e categorias de dados.
- Estados derivados: ausente, ativa para a versão corrente, revogada ou desatualizada. Aceitar a versão corrente ativa; revogar impede novas chamadas; alterar substancialmente o aviso torna a autorização anterior insuficiente.
- Não armazenar mensagens, conteúdo de trilha nem credenciais no registro. Autorizar novamente requer aceite explícito; não fazer concessão implícita.

### Conversa

- `id`, `user_id`, `track_id`, `created_at`, `updated_at`; trilha fixa e de propriedade do usuário na criação e no uso.
- Uma trilha própria pode ter muitas conversas; acesso e exclusão sempre filtram por `user_id`. Não permitir alteração do `track_id`.
- Ordenar listagem por `updated_at` e desempatar por `id`. O conteúdo das mensagens é armazenado apenas nas mensagens, não em título, sumário, logs ou cache.

### Mensagem

- `id`, `conversation_id`, `sequence`, `role` (`student` ou `mentor`), `content`, `created_at`.
- Conteúdo não vazio e limitado a 4.000 caracteres por mensagem do estudante; resposta completa validada antes de persistir. `(conversation_id, sequence)` é único; numeração monotônica define ordem estável.
- Cada resposta do mentor pertence a uma geração; restrição única por geração impede publicação duplicada. Mensagens de gerações falhas não geram resposta parcial.

### Geração de orientação

- `id`, `conversation_id`, `student_message_id`, `status`, `created_at`, `updated_at`, contagem de tentativas, `error_code` sanitizado; chave de idempotência do cliente por conversa.
- Estados: `queued → processing → completed | failed`; falha transitória pode retornar a `queued`, com limite de tentativas. Estado terminal não retrocede. Nova tentativa explícita cria nova geração associada à mesma mensagem, preservando idempotência por chave.
- No máximo uma geração não terminal por conversa. Restrição transacional também impede duas respostas para a mesma geração. Chaves repetidas com o mesmo payload retornam a mesma operação; payload diferente gera conflito.
- Um registro de despacho persistente, contendo só identificadores e estado, permite reenfileirar operações `queued` após falha entre commit e publicação. Entrega duplicada é segura; não se promete exatamente uma chamada externa.
- Registrar identificador único da tentativa, prazo de processamento e estado de envio, sem conteúdo. Após expiração de `processing`, um reconciliador usa atualização condicional pelo identificador da tentativa: se ainda não houver reserva de envio, retorna a `queued` com retries limitados ou marca `failed`; se houver reserva inconclusiva, marca `failed` e mantém o bloqueio de envio até a reserva ser resolvida. Tentativa antiga não pode publicar nem alterar uma geração recuperada.

### Reserva de envio e bloqueio de privacidade

- Registro durável sem conteúdo, com `user_id`, `generation_id`, identificador único da tentativa e estado `in_flight` ou `finished`; uma tentativa só pode chamar o provedor após gravar `in_flight` e confirmar o commit.
- Um estado persistente por usuário bloqueia novas reservas durante revogação ou exclusão. Mudanças desse estado e criação de reservas são serializadas transacionalmente por usuário. O lock consultivo de sessão complementa essa coordenação, mas sua perda não elimina a reserva.
- A tentativa marca `finished` somente depois de sua chamada local encerrar e não poder mais iniciar ou continuar envio; então revalida autorização, existência e identificador da tentativa antes de publicar. Uma tentativa com resultado inválido ou expirada não publica.
- Se o processo ou a conexão falhar com reserva `in_flight`, ela permanece inconclusiva. Não removê-la automaticamente por timeout ou mera perda de lock; o processamento e o envio ficam bloqueados até comprovação operacional de que o processo original foi encerrado e não pode voltar a enviar. Após essa comprovação, o reconciliador ou operador autorizado encerra a reserva sem conteúdo e mantém a geração `failed`, permitindo retry explícito.

### Contexto de aprendizagem

Objeto transitório, não persistido como cópia: campos pertinentes da trilha própria, progresso e avaliações com vínculo verificável à mesma trilha e mensagens recentes da conversa. Aplicar orçamento configurável de contexto e priorizar a mensagem atual; não inventar dados ausentes nem usar outras conversas. Evitar cache global ou persistência de prompt.

## Integridade, exclusão e concorrência

- FKs e índices para dono, trilha, conversa e sequência; migração Alembic reversível estruturalmente. Exclusão de conteúdo é irreversível e downgrade não o recupera.
- Usar lock consultivo de sessão por usuário em conexão dedicada, compartilhado por envios, exclusão e revogação em todos os processos, sem transação aberta durante o I/O. Revogação/exclusão primeiro bloqueiam novas reservas em estado durável e aguardam reservas existentes; se não puderem provar seu encerramento, respondem `503` sem confirmar a operação e mantêm o bloqueio. Após resolver as reservas, nova tentativa conclui a operação e invalida trabalhos pendentes. A perda do lock impede publicação, mas não é tratada como prova de que o envio terminou.
- A exclusão não desfaz dados já recebidos pelo fornecedor; essa limitação deve constar no aviso e na política operacional. Chamadas pendentes posteriores à confirmação verificam novamente a existência e autorização e não enviam nem publicam.
- Remover fisicamente mensagens, gerações e despachos vinculados à conversa; tarefas atrasadas não encontram a geração e encerram sem efeito. Exclusão de todo o histórico deve serializar também novas criações desse usuário e cobrir todas as suas trilhas.
- O caminho de exclusão/retirada também deve tratar sumários, caches, logs e armazenamento de resultados da task: a implementação não deve criá-los com conteúdo.
- O impacto da exclusão de uma trilha ou conta deve ser integrado ao fluxo existente: impedir geração e apagar conteúdos de mentoria correspondentes, sem manter órfãos ou republicar mensagens. Revisar o comportamento de deleção existente antes da migração.
