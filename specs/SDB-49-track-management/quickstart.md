# Quickstart de Validação

## Pré-requisitos

- Python >= 3.11, `uv` e Docker instalados.
- Arquivo `.env` configurado.
- PostgreSQL disponível pelo compose.

## Preparação

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
```

## Validações automatizadas

```bash
uv run pytest tests/unit tests/integration tests/contract
uv run ruff check .
```

Os testes devem sobrescrever `get_db` e `get_current_user` para controlar sessão e usuários sem depender de login real. Testes de integração devem usar PostgreSQL, pois UUID e ENUM são específicos do banco configurado.

## Cenários mínimos

1. Criar uma trilha sem descrição e confirmar `201`, título, proprietário do contexto e timestamps.
2. Criar com título ausente, vazio e acima de 255 caracteres; confirmar `422` e ausência de persistência.
3. Listar com `page=1&page_size=20`; confirmar somente trilhas ativas do usuário, envelope e totais.
4. Consultar uma trilha com árvore completa; confirmar etapas, lições, arquivos, feedbacks, quizzes/respostas, missões e apenas o progresso do usuário atual.
5. Consultar UUID inválido, trilha de outro usuário e trilha excluída; confirmar `422` ou `404` sem vazamento.
6. Atualizar título/descrição; confirmar `200`, preservação em payload inválido e atualização de auditoria.
7. Excluir; confirmar `204`, `deleted_at` preenchido e ausência em listagem/detalhe.
8. Instrumentar o engine e confirmar que a quantidade de consultas da leitura cresce por relação agrupada, não por item filho.

## Execução manual

```bash
uv run dev
```

Abrir `http://localhost:8080/docs`, fornecer uma credencial válida e executar os cinco endpoints de [contracts/tracks.md](contracts/tracks.md). O resultado esperado é idempotente para consultas e não expõe dados entre usuários.
