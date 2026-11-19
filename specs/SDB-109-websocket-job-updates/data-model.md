# Dados e transições do acompanhamento

## Escopo de acesso

Um ticket e uma inscrição representam a tupla `(user_id, channel, resource_id)`. Validar o formato, normalizar UUIDs e autorizar o par canônico antes de emitir. Fazer nova leitura na inscrição e imediatamente antes de cada envio de `job.updated`, inclusive o primeiro. Reutilizar a identidade autenticada do usuário e verificar que a conta continua acessível. Usar consultas curtas em sessão nova por leitura, com predicados de posse e exclusão lógica no próprio acesso aos dados. Se o vínculo deixar de existir, a resposta pública é idêntica à de um recurso inexistente.

| Canal | Chave pública | Condição de acesso ao snapshot |
|---|---|---|
| `track_generation` | UUID da solicitação | `GenerationRequest.user_id` corresponde ao titular. Em sucesso, a trilha resultante pertence ao mesmo usuário e está ativa. |
| `assessment` | UUID do diagnóstico | `KnowledgeAssessment.kas_user_id` corresponde ao titular. Carregar somente a projeção pública das perguntas. |
| `step_preparation` | ID de tarefa recebido no aceite, string opaca não vazia | Registro pertence ao titular, origem e destino pertencem à trilha ativa desse usuário, ambas as etapas estão acessíveis e o prazo de consulta está vigente. |
| `step_summary` | Dois UUIDs unidos por um único `:`, na ordem trilha e etapa | Etapa ativa pertence exatamente à trilha informada, ativa e do titular. Exigir uma geração identificável ou sumário legado disponível. |

## Dados por duração e origem

**Ticket.** Valor confidencial entregue só na emissão. A chave Redis usa prefixo do ambiente e hash do segredo. Valor contém os três campos do escopo. Emissão inicia TTL de 60 s. Consumo atômico ou expiração removem a chave. Uma inscrição aceita conserva apenas o escopo.

**Inscrição.** Estado em memória no processo ASGI que atende o socket. Guardar o escopo, fase de inscrição, sinal de releitura e identidade do último snapshot público enviado (incluir revisão para sumário). Uma segunda mensagem idêntica mantém o mesmo consumidor. Um único escritor serializa atualizações, erros e fechamento. Liberar referência, sinal e tarefas auxiliares em `finally`, inclusive após falha no envio. O listener compartilhado pertence ao processo e fecha no `lifespan`; suas inscrições locais pertencem às conexões.

**Solicitação de trilha e diagnóstico.** Usar as tabelas `generation_request` e `knowledge_assessment` e as relações existentes. A transação que confirma conteúdo e estado terminal também gera a notificação. Para o diagnóstico, recuperar as perguntas e alternativas na ordem de domínio. O schema de saída seleciona os campos permitidos, inclusive para o diagnóstico já respondido.

**Preparação de etapa (nova tabela).** Uma linha por tarefa, com `task_id` chave primária, `user_id`, `track_id`, `source_step_id`, `target_step_id` com referências às entidades, `status`, `created_at` e `finished_at` UTC com fuso. Várias tarefas podem apontar para a mesma etapa. Restringir estados, unicidade do ID e a presença de `finished_at` exatamente nos estados terminais. Indexar `finished_at` de terminais para limpeza. Autorizar enquanto `finished_at IS NULL` ou o relógio do banco indicar instante estritamente anterior a `finished_at + 24 horas`. Filtrar mesmo antes de qualquer limpeza física. Leituras, retries e reconexão preservam o instante original.

**Geração de sumário (nova tabela).** Uma linha por `step_id` (PK/FK), com `generation` inteiro crescente positivo e `status` restrito a `pending | completed | failed`. Dono e trilha derivam da etapa. O texto canônico continua em `Step.stp_summary`. O erro público fixo deriva do estado de falha. Manter apenas a tentativa vigente. Um `UPSERT` atômico por etapa incrementa a geração e grava `pending` em uma transação curta, confirmada antes do cálculo. Esta reserva define a ordem dos inícios concorrentes. Para uma etapa anterior à migração, interpretar texto existente sem linha de geração como conclusão legada. Não inferir uma pendência de texto nulo.

## Transições e invariantes dos produtores

| Operação | Transição persistida | Regra de confirmação |
|---|---|---|
| Trilha | `pending → succeeded / failed` | Condicionar transição ao estado não terminal. Confirmar a criação e o vínculo da trilha antes de disponibilizar o sucesso. Aceitar reentrega idempotente. |
| Diagnóstico | `pending → generated / skipped / failed`, depois `generated → completed` no fluxo de resposta | Perguntas e estado `generated` ficam visíveis juntos. `generated`, `skipped` e `completed` encerram a espera das perguntas. |
| Preparação | `pending → completed / failed` | Usar o mesmo ID no registro e em `apply_async(task_id=...)`. Gravar o terminal uma única vez. Conteúdo gerado ou já presente resulta em sucesso após confirmação. Alvo inativo impede entrega por perda de acesso. |
| Sumário | Nova geração → `pending`; mesma geração → `completed / failed` | No sucesso, obter a linha da geração com bloqueio, conferir revisão e estado e gravar texto e terminal na mesma transação. Se outra geração tomou seu lugar, descartar a escrita e o aviso. Na falha, após rollback, aplicar a mesma condição em transação curta. |

O fluxo de quiz deve reservar a revisão em sessão independente **antes** de adquirir bloqueios de escrita conflitantes. Calcular usando a sessão que enxerga a resposta recém-criada. O sucesso do sumário participa do commit da resposta, progresso e XP. Se a transação do quiz falhar depois do cálculo, tratar a revisão vigente como falha após rollback. A resposta HTTP de cada pedido explícito continua refletindo o resultado daquela chamada.

Para preparação, persistir o vínculo antes de entregar trabalho ao broker. O worker recupera pelo ID reservado, valida o destino e grava conteúdo e conclusão na mesma transação. Uma falha de despacho confirmada encerra a preparação, respeitando o erro HTTP vigente. Se a entrega for incerta, reconciliar/repetir o despacho com o mesmo ID e tornar o consumo idempotente por bloqueio do registro e verificação do estado terminal. Uma reentrega jamais reinicia o prazo.

## Migração e reversão

Adicionar as duas tabelas e os gatilhos de aviso em revisão Alembic, com `downgrade` que remove os gatilhos, a função de notificação e as tabelas novas. Preservar os estados de trilha, as perguntas e a coluna de sumário existentes. Aplicar a migração antes de subir os novos processos. Validar ida e volta em banco descartável com dados anteriores à mudança, incluindo sumário existente e IDs de preparação sem vínculo demonstrável. [Pesquisa](research.md) · [Contrato público](contracts/job-updates.md)
