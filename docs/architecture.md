# Arquitetura — SideBrain Backend

## Visão geral

API construída em **FastAPI**, organizada em camadas por responsabilidade. O fluxo de dependência segue a direção:

```
routers → services → repositories → models
             ↓
          schemas
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
Regras de negócio e orquestração de operações. Consome `repositories`, aplica validações e lógica de domínio, e retorna dados já prontos para os `routers`.

### `routers/v1/`
Camada de apresentação HTTP. Define os endpoints, recebe/valida requests via `schemas`, delega a lógica para `services` e retorna as respostas. Versionamento explícito em `v1` permite evolução da API sem quebrar clientes existentes.

## Regras de dependência

- `routers` **não** acessam `repositories` ou `models` diretamente — sempre passam por `services`.
- `services` **não** conhecem detalhes de HTTP (requests/responses) — trabalham com `schemas`/objetos de domínio.
- `repositories` **não** contêm regra de negócio — apenas acesso a dados.
- `core` não depende de nenhuma outra camada.
- `utils` não depende de nenhuma outra camada e não deve conter lógica de negócio ou acesso a infraestrutura.

## Injeção de dependência

A composição entre camadas é feita via `Depends` do FastAPI, evitando instanciamento direto e facilitando testes (mock/override de dependências).

- **`repositories`**: expostos como providers (ex.: `get_user_repository`), recebendo a sessão de banco via `Depends` de `core` (ex.: `get_db`).
- **`services`**: recebem seus `repositories` via `Depends`, ao invés de instanciá-los diretamente.
- **`routers`**: recebem os `services` via `Depends`, nunca instanciam `repositories` ou `services` manualmente.

Exemplo do encadeamento:

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

Cada provider (`get_*`) deve residir junto à sua respectiva classe (ex.: `get_user_repository` em `repositories/user_repository.py`), mantendo a definição da dependência próxima à implementação.

## Versionamento de API

Novas versões (`v2`, `v3`, ...) devem ser adicionadas como novos módulos em `routers/`, preservando versões anteriores enquanto necessário para compatibilidade.