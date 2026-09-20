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

## Monitoramento das tasks

Rode o comando abaixo para abrir a interface do flower e monitorar o andamento das tasks:
```bash
uv run celery -A sidebrain_back.core.celery_app flower
```

## 📄 Documentação extra
Para verificar as padronizações usadas neste projeto, bem como demais documentações, visite o nosso [repositório principal](https://github.com/FR0M-ZER0/Sidebrain)

## Trilhas

As trilhas autenticadas estão disponíveis em `/api/v1/tracks`. A credencial
Bearer identifica o proprietário; `userId` não é aceito nos requests.

- `POST /api/v1/tracks` cria uma trilha.
- `GET /api/v1/tracks` lista trilhas ativas com `page` e `page_size`.
- `GET /api/v1/tracks/{track_id}` retorna a hierarquia filtrada.
- `PATCH /api/v1/tracks/{track_id}` atualiza título e/ou descrição.
- `DELETE /api/v1/tracks/{track_id}` realiza exclusão lógica e retorna `204`.

Falhas usam Problem Details com `type`, `title`, `status` e `detail`; erros de
validação também incluem `errors` por campo.

## Geração incremental de conteúdo

Ao atingir 80% das Lessons ativas de um Step, o serviço pode enfileirar a task
`tasks.prepare_next_step_content` para preparar o próximo Step em background.
A task recebe somente `step_id`, usa o contexto da Track e dos Steps anteriores,
valida o payload do provedor e persiste Lessons, Quizzes e Missions em uma
transação única. Locks de linha e a guarda de conteúdo ativo evitam duplicação;
falhas transitórias têm retry limitado.

## Quizzes

O gerenciamento autenticado de quizzes está disponível em cinco endpoints:

- `POST /api/v1/lessons/{lesson_id}/quizzes` cria um quiz na aula.
- `GET /api/v1/lessons/{lesson_id}/quizzes` lista quizzes ativos com `page` e
  `page_size`. 
- `GET /api/v1/quizzes/{quiz_id}` consulta um quiz e todas as suas respostas.
- `PUT /api/v1/quizzes/{quiz_id}` substitui somente a pergunta.
- `DELETE /api/v1/quizzes/{quiz_id}` realiza exclusão lógica e retorna `204`.

A lista usa o envelope `data`, `page`, `page_size`, `total_items` e
`total_pages`. Quizzes expõem `id`, `lesson_id`, `question` e `answers`; cada
resposta expõe `id`, `user_id`, `text` e `rate`. Nomes físicos do banco,
timestamps e flags de exclusão não fazem parte da resposta direta.

Recursos inexistentes, excluídos, pertencentes a outra pessoa ou contidos em
uma hierarquia excluída retornam o mesmo `404`, sem revelar ownership. O fluxo
segue `router -> service -> repository -> model`. Consulte o
[contrato completo](./specs/SDB-51-quiz-management/contracts/quizzes.md).
