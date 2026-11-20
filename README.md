# API do Sidebrain

## 🚀 Tecnologias

- **FastAPI**: Framework web moderno e de alta performance para construção de APIs
- **Pydantic**: Validação de dados e serialização via modelos tipados
- **SQLAlchemy**: ORM para comunicação com o banco de dados
- **pgvector**: Extensão do PostgreSQL para armazenamento e busca de vetores
- **uv**: Gerenciador de pacotes e ambientes Python, rápido e moderno
- **Uvicorn**: Servidor ASGI para execução da aplicação FastAPI
- **Alembic**: Ferramenta de migração de banco de dados para SQLAlchemy
- **Pytest**: Framework para escrita e execução de testes

## 🏗️ Arquitetura

Veja mais sobre nossa arquitetura [aqui](./docs/architecture.md)

## ⚙️ Rodando o projeto

1. O projeto faz uso do Husky para gerenciar os hooks do git, bem como do `commitlint`. Instale essas dependências rodando:
```bash
npm i
```

2. Instale as dependências do projeto, usando
```bash
uv sync
```

3. Crie o arquivo .env e preencha as variáveis:
```bash
cp .env.example .env
```

4. Inicie os serviços necessários, incluindo PostgreSQL, Redis e RabbitMQ:
```bash
docker compose up -d
```

5. Habilite a extensão `vector` no banco da aplicação (uma vez por banco):
```bash
docker compose exec postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"'
```

6. Rode as migrações:
```bash
uv run alembic upgrade head
```

7. Rode a API em ambiente dev usando:
```bash
uv run dev
```

8. Em outro terminal, rode o worker das tasks do Celery usando:
```bash
uv run celery -A sidebrain_back.core.celery_app worker --loglevel=info
```

9. Em outro terminal, rode o worker de notificações:
```bash
uv run notifications-worker
```

10. Para processar e recuperar solicitações de mentoria, inicie também o
agendador Celery em outro terminal:

```bash
uv run celery -A sidebrain_back.core.celery_app beat --loglevel=info
```

Se estiver utilizando os dados padrões no .env para o servidor, ele estará disponível em `http://localhost:8080` e a documentação interativa em [http://localhost:8080/docs](http://localhost:8080/docs).

## Testes

Os testes de integração usam um PostgreSQL exclusivo com a extensão `vector`.
Configure as variáveis `TEST_POSTGRES_*` no `.env`, conforme `.env.example`.
A porta padrão desse banco é `5434` e deve estar livre no host.

```bash
docker compose --profile test up -d --wait postgres_test
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

O `conftest.py` usa essas configurações para conectar ao banco de testes,
aplica as migrations e isola os dados da fixture `db_session` por rollback.

Para executar apenas os testes unitários e de contrato:

```bash
uv run pytest tests/unit tests/contract
```

Os cinco testes de aceitação HTTP exigem uma API em execução e a variável
`AUTH_CONSUMER_BASE_URL`; sem ela, são ignorados automaticamente.

## Monitoramento das tasks

Rode o comando abaixo para abrir a interface do flower e monitorar o andamento das tasks:
```bash
uv run celery -A sidebrain_back.core.celery_app flower
```

## Prompts para agentes

Para usar o [prompt de criação de pull request](./docs/prompts/create-pr.md),
é necessário ter o **GitHub CLI (`gh`) instalado** e autenticado com uma conta
que tenha acesso ao repositório.

Siga as [instruções oficiais de instalação](https://cli.github.com/) e, em
seguida, verifique a instalação e faça a autenticação:

```bash
gh --version
gh auth login
gh auth status
```

## 📄 Documentação extra
Para verificar as padronizações usadas neste projeto, bem como demais documentações, visite o nosso [repositório principal](https://github.com/FR0M-ZER0/Sidebrain)
