# Arquitetura — SideBrain Backend

## Visão geral

API construída em **FastAPI**, organizada em camadas por responsabilidade. O fluxo de dependência segue a direção:

```
routers → services → repositories → models
             ↓           ↓
          schemas      tasks
```

`core` é transversal e pode ser utilizado por qualquer camada.

## Estrutura de diretórios

```
sidebrain_back/
├── core/           # Configurações e infraestrutura compartilhada
├── models/         # Entidades de domínio / ORM (ex.: SQLAlchemy)
├── repositories/    # Acesso e persistência de dados
├── routers/
│   └── v1/          # Endpoints da API, versionados
├── schemas/         # Contratos de entrada/saída (Pydantic)
├── services/        # Regras de negócio e orquestração
├── tasks/           # Tarefas assíncronas (Celery)
└── utils/          # Funções auxiliares puras, sem estado e sem dependências de infraestrutura

tests/
├── unit/            # Testes unitários
└── integration/     # Testes de integração
```

## Responsabilidade das camadas

### `core/`
Código de uso geral e transversal: configuração da aplicação (settings), conexão com banco de dados, autenticação/segurança, exceções customizadas, logging e middlewares. Não deve depender de nenhuma outra camada da aplicação.

### `utils/`
Funções auxiliares puras (ex.: formatação, parsing, conversão de dados). Diferem de `core` por não lidar com infraestrutura ou configuração — apenas lógica utilitária sem estado, reutilizável por qualquer camada.

### `models/`
Definição das entidades de domínio/persistência (ex.: modelos ORM). Representam a estrutura dos dados no banco. Não contêm lógica de negócio.

### `schemas/`
Modelos Pydantic para validação e serialização de entrada/saída da API (request/response). Desacoplados dos `models`, evitando expor a estrutura interna do banco diretamente na API.

### `repositories/`
Camada de acesso a dados. Encapsula queries e operações de persistência sobre os `models`, isolando a lógica de negócio de detalhes de ORM/SQL.

### `services/`
Regras de negócio e orquestração de operações. Consome `repositories`, aplica validações e lógica de domínio, e retorna dados já prontos para os `routers`. Quando uma operação precisa ser executada de forma assíncrona/em background, dispara uma task em `tasks/` ao invés de executá-la de forma síncrona.

### `tasks/`
Tarefas assíncronas executadas via **Celery** (ex.: envio de e-mails, processamento de arquivos, jobs agendados/periódicos, integrações externas demoradas). Consomem `services` para reaproveitar a lógica de negócio já validada, evitando duplicar regras entre o fluxo síncrono da API e o processamento assíncrono. Não contêm regra de negócio própria — apenas orquestram a execução em background e tratam preocupações específicas de Celery (retries, idempotência, serialização de argumentos, timeouts).

### `routers/v1/`
Camada de apresentação HTTP. Define os endpoints, recebe/valida requests via `schemas`, delega a lógica para `services` e retorna as respostas. Versionamento explícito em `v1` permite evolução da API sem quebrar clientes existentes.

## Regras de dependência

- `routers` **não** acessam `repositories`, `models` ou `tasks` diretamente — sempre passam por `services`.
- `services` **não** conhecem detalhes de HTTP (requests/responses) — trabalham com `schemas`/objetos de domínio.
- `services` podem disparar `tasks` (via `.delay()`/`.apply_async()`), mas não devem depender do resultado de forma síncrona/bloqueante.
- `tasks` **não** contêm regra de negócio — delegam para `services`; podem depender de `core` (ex.: configuração do broker/backend do Celery), mas não devem ser importadas por `repositories`, `models` ou `schemas`.
- `repositories` **não** contêm regra de negócio — apenas acesso a dados.
- `core` não depende de nenhuma outra camada.
- `utils` não depende de nenhuma outra camada e não deve conter lógica de negócio ou acesso a infraestrutura.

## Injeção de dependência

A composição entre camadas é feita via `Depends` do FastAPI, evitando instanciamento direto e facilitando testes (mock/override de dependências).

- **`repositories`**: expostos como providers (ex.: `get_user_repository`), recebendo a sessão de banco via `Depends` de `core` (ex.: `get_db`).
- **`services`**: recebem seus `repositories` via `Depends`, ao invés de instanciá-los diretamente.
- **`routers`**: recebem os `services` via `Depends`, nunca instanciam `repositories` ou `services` manualmente.
- **`tasks`**: como o worker Celery roda fora do ciclo de requisição do FastAPI, `Depends` não se aplica diretamente. Cada task abre sua própria sessão de banco (via helper de `core`) e instancia o `service`/`repository` necessário manualmente dentro do corpo da task, mantendo o mesmo encadeamento de camadas.

Exemplo do encadeamento (síncrono):

```python
# repositories/user_repository.py
def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


# services/user_service.py
def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repository)


# routers/v1/users.py
@router.get("/users/{id}")
def get_user(id: int, service: UserService = Depends(get_user_service)):
    return service.get_user(id)
```

Exemplo do encadeamento (assíncrono, via Celery):

```python
# services/user_service.py
class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def request_report(self, user_id: int) -> None:
        # dispara a task ao invés de gerar o relatório de forma síncrona
        generate_user_report_task.delay(user_id)


# tasks/user_tasks.py
from core.celery_app import celery_app
from core.database import session_scope
from repositories.user_repository import get_user_repository
from services.user_service import get_user_service


@celery_app.task(name="tasks.generate_user_report")
def generate_user_report_task(user_id: int) -> None:
    with session_scope() as db:
        service = get_user_service(get_user_repository(db))
        service.generate_report(user_id)
```

Cada provider (`get_*`) deve residir junto à sua respectiva classe (ex.: `get_user_repository` em `repositories/user_repository.py`), mantendo a definição da dependência próxima à implementação.

### Gerenciamento de trilhas

Os endpoints versionados de trilhas ficam em `routers/v1/track_router.py` e
delegam para `TrackService`, que usa `TrackRepository` com `AsyncSession`.
Listagens e detalhes filtram ownership e exclusão lógica, carregando a árvore
com `selectinload`; respostas públicas são definidas em `schemas/track_schema.py`.

Quando o progresso de um Step alcança 80% das Lessons ativas, `TrackService`
calcula o próximo Step elegível e enfileira
`tasks.prepare_next_step_content` sem aguardar o provedor externo. A task abre
sua própria sessão, valida o contexto e persiste Lesson, Quiz e Mission em uma
transação atômica, usando lock de linha e retry limitado para preservar
idempotência e consistência.

### Gerenciamento de quizzes

Os cinco endpoints de quiz ficam em `routers/v1/quiz_router.py` e mantêm o
fluxo `router -> service -> repository -> model`: o router valida HTTP e
autenticação, `QuizService` aplica as regras e controla a transação,
`QuizRepository` executa as consultas e `Quiz`/`Answer` representam a
persistência.

Criação e listagem usam a Lesson da URL; detalhe, atualização e exclusão usam o
Quiz da URL. Toda consulta autorizada atravessa `Lesson -> Step -> Track`,
exige que os pais estejam ativos e filtra `Track.trk_user_id` pelo usuário
atual. Inexistência, exclusão lógica e ownership incompatível são ocultados
sob o mesmo `404`.

A listagem aceita `page` e `page_size` e retorna `data`, `page`, `page_size`,
`total_items` e `total_pages`. Quizzes são ordenados por atualização e ID
decrescentes; Answers, por criação e ID crescentes. `selectinload` agrupa o
carregamento das Answers e também preserva a composição
`Lesson -> Quiz[] -> Answer[]` nas respostas de Track sem N+1.

Os schemas públicos convertem os nomes físicos `qui_*` e `ans_*` em `id`,
`lesson_id`, `question`, `answers`, `user_id`, `text` e `rate`. O DELETE é
lógico e terminal: preserva as linhas de Quiz e Answer e não aciona cascata
física. Consulte o
[contrato HTTP](../specs/SDB-51-quiz-management/contracts/quizzes.md) para os
cinco endpoints e seus códigos de resposta.

## Versionamento de API

Novas versões (`v2`, `v3`, ...) devem ser adicionadas como novos módulos em `routers/`, preservando versões anteriores enquanto necessário para compatibilidade.
