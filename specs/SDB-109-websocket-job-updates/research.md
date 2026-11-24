# Pesquisa técnica da SDB-109

## Como consumir um ticket uma única vez?

**Decisão.** Emitir um segredo aleatório de 32 bytes em base64url. Após autenticar o Bearer e autorizar o recurso, guardar usuário, canal e chave canônica no Redis de autenticação com `SET <prefixo>:<sha256(ticket)> <escopo> NX EX 60`. Repetir a geração em caso de colisão. Antes do upgrade, `GETDEL` recupera o escopo e consome o ticket em uma operação. Se a resposta se perder, o cliente solicita outro ticket. Falha do Redis impede autorizar o socket.

**Motivo e alternativas.** A API já usa Redis 7. O TTL limita o segredo mesmo quando o cliente abandona a tela. Um JWT assinado precisaria de armazenamento adicional para invalidar seu segundo uso. Ler e depois apagar em comandos separados permitiria duas conexões concorrentes. [SET](https://redis.io/docs/latest/commands/set/) · [GETDEL](https://redis.io/docs/latest/commands/getdel/)

## Como distribuir mudanças entre processos e recuperar o estado?

**Decisão.** Manter o estado consultável no PostgreSQL 16. Gerar `pg_notify` por gatilhos de migração nos registros de acompanhamento, quando a inserção ou a alteração muda o estado observável. O aviso contém apenas canal e chave canônica do recurso. Usar um canal PostgreSQL fixo com um listener `asyncpg` por processo ASGI que atende inscrições. O callback marca como pendente de releitura cada inscrição local correspondente. O serviço consulta o banco com o usuário da inscrição. Uma notificação nunca autoriza acesso nem contém o resultado.

**Motivo e alternativas.** Trilha e diagnóstico já confirmam resultados no banco. O gatilho acompanha todos os escritores, inclusive o worker, e um rollback descarta o aviso junto com a mudança. Redis Pub/Sub exigiria tratar a falha entre commit e publicação. Uma fila de histórico permitiria replay, mas o cliente solicita o estado atual e pode obtê-lo novamente em uma reconexão. [NOTIFY](https://www.postgresql.org/docs/16/sql-notify.html) · [Semântica de entrega do Redis](https://redis.io/docs/latest/develop/pubsub/)

**Ordem da inscrição.** Aguardar a confirmação de `LISTEN`, registrar o consumidor local e só então ler o estado em uma nova transação. Usar um único emissor por socket. Antes da leitura, limpar o sinal local de releitura. Um aviso durante a consulta ou envio mantém esse sinal ativo para a próxima iteração. Reconsultar ao acordar, conferir acesso e suprimir snapshots já entregues da mesma execução. O receptor de mensagens/desconexões continua ativo mesmo sem tráfego do worker. Se a sessão de escuta cair, sinalizar falha a todas as inscrições afetadas e restabelecer a escuta para novas conexões. [LISTEN](https://www.postgresql.org/docs/16/sql-listen.html)

## Quais estados já existem?

| Fluxo | Evidência no repositório | Decisão e alternativa examinada |
|---|---|---|
| Trilha | `generation_request_repository.py`, `generation_service.py`, `generate_track_task.py` | Projetar a solicitação persistida. Proteger a transição terminal contra atualização tardia ou repetida. Cobrir o esgotamento de `retry(exc=...)`, erros definitivos e reentrega. Confiar só no resultado Celery perderia o vínculo com a transação que cria a trilha. |
| Diagnóstico | `knowledge_assessment_service.py`, `knowledge_assessment_task.py`, `knowledge_assessment_schema.py` | Usar o diagnóstico persistido e o schema público de perguntas ordenadas. A conclusão da geração ocorre em `generated`, antes de o usuário responder. Uma tarefa legada sem `assessment_id` não identifica um diagnóstico público. |
| Próxima etapa | `TrackService.prepare_next_step`, `enqueue_next_step_preparation`, `prepare_next_step_content_task.py` | Reservar o ID Celery e gravar dono, trilha, origem e destino antes do despacho. Um `AsyncResult` desconhecido também pode parecer pendente e não comprova posse. |
| Sumário | `StepService.generate_step_summary`, `QuizService.submit_quiz_answer`, `StepSummaryService.refresh_summary_for_quiz` | Persistir uma revisão crescente por etapa ao admitir a geração. Condicionar à mesma revisão a escrita de `stp_summary` e a transição terminal, inclusive no quiz. Ordenar por hora de conclusão permitiria que uma tentativa antiga sobrescrevesse a atual. |

**Falha de job e falha de transporte.** Uma tentativa transitória mantém `pending`. Depois de rollback, a falha definitiva deve ser persistida em uma transação válida, com código ou mensagem pública, e acordar os inscritos. Um erro ao consultar o snapshot ou perder a sessão de escuta encerra o acompanhamento com `job.error` quando o socket ainda aceita envio. O job continua independente da conexão.

## Como introduzir os dados novos?

**Decisão.** Criar registros apenas para as preparações e as revisões de sumário. Reutilizar a coluna de texto da etapa e os estados das outras duas operações. Uma etapa acessível com sumário anterior à migração tem snapshot concluído. Se ainda não houver solicitação nem texto, o recurso de acompanhamento do sumário está indisponível até o primeiro início.

**Motivo e alternativas.** Copiar o conteúdo dos quatro fluxos para uma tabela de eventos duplicaria perguntas e sumários. Uma preparação legada despachada apenas com o ID da etapa não oferece prova persistida de posse pelo `task_id`. Na ativação, drenar os workers antigos e documentar a janela de transição para IDs anteriores. A restrição de 24 horas vale a partir da primeira conclusão ou falha da preparação rastreada.

O contrato de produto foi conferido com as duas tarefas de origem e com as decisões locais de 18/11/2026. [SDB-109](https://fromzero-api.atlassian.net/browse/SDB-109) · [SDB-104](https://fromzero-api.atlassian.net/browse/SDB-104) · [Especificação](spec.md)
