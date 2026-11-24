# Contrato proposto: mentoria

Base `/api/v1`, JSON, autenticação `Authorization: Bearer <token>` em todas as operações. Identidade vem do token. Identificadores seguem o tipo usado pelos modelos existentes. Campos abaixo usam nomes de negócio; implementação deve manter convenções de schema do projeto.

## Aviso e autorização

- `GET /mentor-consent`: `200` com aviso versionado (por exemplo `3-openai`), finalidade, provedor, categorias de dados, retenção e estado de autorização. As categorias incluem conteúdo de lições e perguntas de quizzes solicitados. Aceites de versões anteriores não autorizam novos envios; o aviso explica que a exclusão local não apaga dados já enviados.
- `PUT /mentor-consent`: corpo `{ "notice_version": "<versão recebida>", "accepted": true }`; `200` com estado vigente. Só aceitar versão corrente e aceite explícito; `false`, versão ausente ou obsoleta retornam `422` ou `409` para versão obsoleta.
- `DELETE /mentor-consent`: `204`, revogação idempotente. Bloqueia novas reservas de envio e aguarda chamadas em andamento; se não for possível confirmar seu término, retorna `503`, mantém o bloqueio e permite nova tentativa. Após `204`, impede novos envios, inclusive de tasks enfileiradas; chamada já iniciada não pode ser desfeita. Histórico permanece disponível até exclusão solicitada.

## Conversas

- `POST /mentor-conversations`: `{ "track_id": "<id>" }` → `201` com `{ "id": "<id>", "track_id": "<id>", "created_at": "...", "updated_at": "..." }`. Trilha deve ser própria e ativa. Criar conversa vazia não chama IA.
- `GET /mentor-conversations?track_id=<id>&page=1&page_size=20`: `200` com `{ "data": [<conversa>], "page": 1, "page_size": 20, "total_items": 1, "total_pages": 1 }`; `track_id` é opcional e filtra apenas trilhas próprias.
- `GET /mentor-conversations/{conversation_id}`: `200` com metadados da conversa própria.
- `GET /mentor-conversations/{conversation_id}/messages?page=1&page_size=20`: `200` com envelope paginado acima e `data` contendo `{ "id": "<id>", "sequence": 1, "role": "student", "content": "...", "created_at": "..." }`, ordenado por `sequence` crescente.
- `DELETE /mentor-conversations/{conversation_id}`: `204` depois de exclusão transacional do conteúdo próprio, sujeito às ressalvas de [data-model.md](../data-model.md). Caso uma reserva de envio não possa ser comprovadamente encerrada, retorna `503`, mantém o bloqueio de novos envios e permite nova tentativa.
- `DELETE /mentor-conversations`: `204` depois de excluir todo o histórico de mentoria do usuário em todas as suas trilhas; não remove trilhas, progresso ou autorização. Aplica o mesmo tratamento `503` para reserva inconclusiva.

## Solicitação e acompanhamento

- `POST /mentor-conversations/{conversation_id}/messages`: cabeçalho obrigatório `Idempotency-Key: <uuid>`, corpo `{ "content": "Como posso melhorar meus estudos?" }`; texto após trim de 1 a 4.000 caracteres.
- `202 Accepted`: `{ "generation_id": "<id>", "message_id": "<id>", "status": "queued" }`. A persistência e reserva de despacho precedem o retorno; o cliente consulta o estado. Repetir chave com mesmo conteúdo retorna a mesma geração; com conteúdo diferente retorna `409`.
- `GET /mentor-conversations/{conversation_id}/generations/{generation_id}`: `200` com `{ "id": "<id>", "message_id": "<id>", "status": "queued|processing|completed|failed", "response_message_id": "<id ou null>", "error_code": "<código sanitizado ou null>" }`. Em `completed`, buscar a resposta pelo endpoint individual abaixo; nunca expor resposta parcial.
- `GET /mentor-conversations/{conversation_id}/messages/{message_id}`: `200` com `{ "id": "<id>", "sequence": 2, "role": "mentor", "content": "...", "created_at": "..." }` para mensagem concluída da conversa própria; `404` para mensagem inexistente, excluída ou inacessível. Disponível no MVP.
- `POST /mentor-conversations/{conversation_id}/generations/{generation_id}/retry`: cabeçalho `Idempotency-Key: <uuid>`; sem corpo. Somente geração `failed` própria pode ser repetida; `202` retorna nova geração associada à mesma mensagem. Mesma chave retorna a mesma nova geração; não duplica a mensagem. Uma geração ativa na conversa implica `409`.
- Sem autorização válida, envio inicial ou retry que dependa de serviço externo retorna `403` com Problem Details `mentor-consent-required`, sem chamar provedor. Criar ou consultar conversas não depende desse aceite.

## Erros e regras

- `401` credencial ausente/inválida; `404` para conversa/trilha/geração/mensagem inexistente, excluída ou de outro usuário, sem distinguir propriedade; `422` entrada inválida; `409` conflito de idempotência, versão ou geração ativa; `503` quando não for possível registrar a solicitação ou concluir com segurança revogação/exclusão.
- Erros seguem RFC 9457 (`application/problem+json`), com `type`, `title`, `status`, `detail` e eventuais erros de validação. Não expor prompt, conteúdo privado, credenciais ou resposta bruta do provedor.
- Apenas uma geração ativa por conversa; geração falha pode ser repetida. Se a fila estiver indisponível após o commit, manter a operação recuperável em `queued`; não retornar sucesso quando o registro não foi persistido.
- `completed` indica resposta completa persistida; `failed` é genérico e permite retry. Repetição de entrega pode causar mais de uma chamada externa, mas não mais de uma resposta publicada para a geração.
- Geração abandonada antes da reserva de envio pode ser recuperada com tentativas limitadas. Se o envio estiver inconclusivo, a geração passa a `failed`, mas o retry não inicia outra chamada até a reserva ser resolvida; retornar `503` enquanto o bloqueio persistir.
- O escopo da leitura é sempre usuário autenticado e trilha fixa; respostas e prompts nunca são reutilizados entre usuários.
