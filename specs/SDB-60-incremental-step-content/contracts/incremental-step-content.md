# Contract: Geração incremental de conteúdo de Steps

## Natureza do contrato

Este é um contrato interno de task assíncrona, não um endpoint HTTP público. O objetivo é preparar o próximo Step da Track sem bloquear a operação principal de atualização do progresso.

## Tarefa

- Nome: `tasks.prepare_next_step_content`
- Entrada: `step_id` (UUID do Step alvo) e contexto de geração derivado da Track e Steps predecessores
- Saída: sucesso sem conteúdo novo se o Step já estiver pronto; falha observável com retry ou erro definitivo, conforme a política da task

## Regras de entrada

- O `step_id` deve apontar para um Step existente e ativo.
- O sistema deve validar que o Step pertence à Track correta e que o contexto mínimo está disponível.
- Nenhum `user_id` é necessário na assinatura da task.
- O conteúdo fornecido pelo provedor não pode decidir IDs, flags de exclusão, estados ou timestamps.

## Regras de saída

- Em caso de sucesso: `Lesson[]`, `Quiz[]` e `Mission[]` são persistidos como uma unidade atômica.
- Em caso de idempotência: se o Step já possui conteúdo ativo completo ou uma geração equivalente em andamento, a task é encerrada sem novos registros.
- Em caso de falha transitória: a task pode ser repetida até o limite configurado.
- Em caso de falha permanente: a task registra erro sem retry infinito.

## Erros previstos

- Conteúdo inválido ou incompatível com enums e relacionamentos
- Falha de transação ou persistência
- Indisponibilidade temporária do provedor
- Falha permanente de configuração ou credenciais indisponíveis

## Observações

- Não há endpoint HTTP novo nesta feature.
- A resposta pública permanece inalterada até que o conteúdo seja consumido pelo fluxo normal da trilha.
