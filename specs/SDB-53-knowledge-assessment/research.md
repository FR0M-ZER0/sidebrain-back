# Pesquisa e Decisoes

## Decisao: Separar service, adapter Groq e task Celery

**Racional:** A arquitetura do projeto reserva regras de negocio para services e tarefas assincronas para orquestracao. O service decide o caminho `skipped`, valida contexto e resultado, enquanto o adapter encapsula o SDK Groq. A task recebe apenas argumentos serializaveis, chama o service e trata retries.

**Alternativas consideradas:** Colocar a chamada Groq diretamente na task foi rejeitado porque mistura integracao, regra de negocio e politica de execucao. Criar repository/model foi rejeitado porque a especificacao declara resultado transitorio e nenhuma persistencia.

## Decisao: Contrato Pydantic estrito com cinco perguntas

**Racional:** `KnowledgeAssessmentResult` tera `assessment_id`, `status`, `level` opcional e `questions`. O status `generated` exige exatamente cinco perguntas; `skipped` exige lista vazia e `level=beginner`. Cada pergunta tera identificador, enunciado e quatro alternativas textuais identificadas e ordenadas. `extra="forbid"` impede respostas externas parcialmente aceitas.

**Alternativas consideradas:** Aceitar quantidade variavel foi rejeitado pelo FR-005. Usar `dict` sem schema foi rejeitado porque impediria bloquear respostas incompletas antes do consumo posterior.

## Decisao: Skip antes da validacao do assunto e do provider

**Racional:** O caminho `skipped` nao precisa de assunto, nao chama Groq e retorna deterministically `beginner`. Quando habilitado, o assunto e normalizado e deve ter entre 1 e 255 caracteres; objetivo e opcional, mas texto vazio e normalizado para ausencia.

**Alternativas consideradas:** Validar sempre o assunto foi rejeitado pelo edge case que da prioridade ao skip. Exigir objetivo foi rejeitado pelo FR-002.

## Decisao: JSON estruturado e modelo configurado pelo ambiente

**Racional:** A chamada usa `client.chat.completions.create` com `model=Env.GROQ_MODEL`, `response_format={"type": "json_object"}`, temperatura baixa e prompt que exige contexto de assunto/objetivo, conhecimento previo e dificuldade variada. O conteudo e parseado e validado como resultado completo.

**Alternativas consideradas:** Parsear texto livre ou markdown foi rejeitado por ser fragiI e permitir conteudo parcial. Fixar o modelo no codigo foi rejeitado porque o repositorio ja externaliza `GROQ_MODEL`.

## Decisao: Retry explicito e limitado para falhas transitorias

**Racional:** Task `bind=True` usa `self.retry` com no maximo 3 retries e backoff crescente para `APIConnectionError`, `APITimeoutError` e `RateLimitError`. Erros de credencial, status definitivo, JSON invalido e falha Pydantic nao entram no retry. O contexto do retry registra task id, tentativa e tipo de falha sem prompt, resposta ou credenciais.

**Alternativas consideradas:** `autoretry_for=(Exception,)` foi rejeitado por repetir erros permanentes indefinidamente ou sem criterio. Nao retryar nada violaria FR-012.

## Decisao: Resultado retornado pelo backend de resultados do Celery

**Racional:** A task retorna `model_dump(mode="json")`, compativel com o serializer JSON ja configurado. O chamador consulta o `AsyncResult` e o fluxo posterior consome o resultado; nao ha endpoint ou TTL novo nesta feature. O `user_id` entra como argumento interno e contexto de log, nao como campo de input publico nem necessariamente no resultado.

**Alternativas consideradas:** Publicar evento ou persistir resultado foram rejeitados por extrapolarem FR-014 e a premissa de transitoriedade.

## Fontes consultadas

- `docs/architecture.md`, `docs/code_conventions.md` e `.specify/memory/constitution.md` do repositorio.
- Documentacao atual do Celery: task vinculada (`bind=True`), `self.retry`, `max_retries`, backoff e separacao de excecoes.
- Documentacao atual do Groq Python: `chat.completions.create`, `response_format`, timeout e excecoes `APIConnectionError`, `APITimeoutError`, `RateLimitError` e `APIStatusError`.
