# Contrato Interno: CLI de Indexação e Recuperação RAG

A ferramenta é interna para responsáveis/automação de operação. Não cria endpoint HTTP público e não altera contratos de request/response existentes.

## Invocação

```bash
uv run python -m sidebrain_back.rag.rag_cli index --source python-tutorial
uv run python -m sidebrain_back.rag.rag_cli index --all
uv run python -m sidebrain_back.rag.rag_cli reindex --full
uv run python -m sidebrain_back.rag.rag_cli query "Como funciona async/await?" --language javascript
uv run python -m sidebrain_back.rag.rag_cli evaluate --k 8
uv run python -m sidebrain_back.rag.rag_cli evaluate --index --k 8
```

## `index`

- `--source NAME` indexa incrementalmente uma fonte configurada.
- `--all` indexa incrementalmente todas as fontes configuradas.
- Exatamente um dos parâmetros deve ser passado; fonte desconhecida é erro de argumento.
- Falha em documento é contada e não interrompe demais documentos/fontes.

## `reindex`

- `--full` reconstrói as fontes/trechos/embeddings e é obrigatório neste fluxo.
- Sem `--source`, aplica a todas as fontes; `--source NAME` restringe a uma fonte, preservando as demais.
- Se modelo ou dimensão mudaram, a operação deve abranger todas as fontes e rejeitar escopo parcial para não misturar vetores incompatíveis.
- Antes de modificar o índice, valida configuração, credenciais necessárias e compatibilidade do schema/dimensão. A saída avisa que consultas podem ter cobertura parcial durante o rebuild e que uma troca de dimensão exige migration anterior.

## `query`

- Consulta posicional não vazia.
- Filtros opcionais `--language {python,javascript}`, `--level {beginner,intermediate,advanced}`, `--content-type {concept,code_example,reference,tutorial,exercise}` e `--top-k N` (padrão 8, faixa 1–50).
- Emite texto recuperado, título, seção, URL/caminho, idioma, nível, tipo, tags e licença de cada resultado/atribuição.
- Exige `OPENAI_API_KEY` para embedding de consulta; ausência ou falha é mensagem operacional clara sem exibir segredo. No fluxo de geração esta falha é capturada e segue sem referências.

## `evaluate`

- Executa o conjunto local fixo de 20 perguntas, resolve IDs/fontes esperados e calcula recall@k para `--k` especificado (padrão 8).
- `--fixtures` e `--index` são mutuamente exclusivos; o padrão é `--fixtures`.
- Com `--fixtures`, usa documentos/embeddings locais e provider falso; não acessa internet, OpenAI ou Groq e valida cálculo/fluxo de avaliação de forma offline.
- Com `--index`, executa as consultas reais contra índice previamente carregado, usando embeddings de consulta do modelo ativo. Exige `OPENAI_API_KEY`, não faz crawling e registra modelo/dimensão do índice usado.

## Relatório de indexação

Inclui fontes/documentos encontrados, documentos processados/inalterados, chunks produzidos, chunks aproximados/exatos deduplicados, conteúdo excluído por política de licença, falhas por documento, duração e custo estimado quando preço estiver configurado. Não imprime credenciais nem o conteúdo completo dos documentos nos logs.

## Códigos de saída

- `0`: operação concluída sem falhas por documento (consulta pode retornar zero resultados).
- `1`: operação executada, mas houve falhas parciais em documentos/fontes; relatório ainda é emitido.
- `2`: argumentos inválidos, fonte desconhecida ou configuração/schema incompatível.
- `3`: falha fatal de serviço externo ou persistência que impediu finalizar a operação.
