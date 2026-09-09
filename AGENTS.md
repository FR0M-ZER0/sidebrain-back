# AGENTS.md

Instruções para agentes de IA que forem ler, gerar ou modificar código neste repositório.

## Contexto do projeto

API em **FastAPI**. Antes de qualquer alteração, consultar:

- [`architecture.md`](./docs/architecture.md) — camadas, estrutura de diretórios, fluxo de dependências e injeção de dependência via `Depends`.
- [`code_conventions.md`](./docs/code_conventions.md) — nomenclatura de métodos, arquivos, paginação, formato de erros e schemas.

Essas convenções são normativas: qualquer código gerado deve segui-las sem exceção.

## Setup e execução

```bash
# instalar dependências
uv sync

# subir a aplicação
uv run dev

# lint
uv run ruff check .

# rodar os testes
uv run pytest
```

## Servidores MCP

Se o usuário enviar o ID da task do Jira (SDB-x, onde x é o número da task, exemplo: SDB-1), utilize o MCP do Jira e procure os dados da task no espaço do Sidebrain.

Além disso, utilize o MCP do Context7 para buscar a documentação atualizada de frameworks e bibliotecas.

**Sempre responda em português brasileiro.**