# API do Sidebrain

## 🚀 Tecnologias

- **FastAPI**: Framework web moderno e de alta performance para construção de APIs
- **Pydantic**: Validação de dados e serialização via modelos tipados
- **SQLAlchemy**: ORM para comunicação com o banco de dados
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

4. Inicie o banco de dados para utilização no ambiente de dev:
```bash
docker compose up -d
```

5. Rode as migrações:
```bash
uv run alembic upgrade head
```

6. Por fim, rode a API em ambiente dev usando:
```bash
uv run dev
```

Se estiver utilizando os dados padrões no .env para o servidor, ele estará disponível em `http://localhost:8080` e a documentação interativa em [http://localhost:8080/docs](http://localhost:8080/docs).


## 📄 Documentação extra
Para verificar as padronizações usadas neste projeto, bem como demais documentações, visite o nosso [repositório principal](https://github.com/FR0M-ZER0/Sidebrain)