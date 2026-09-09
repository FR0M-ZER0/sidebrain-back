# Convenções de Código — SideBrain Backend

## Nomenclatura de métodos — `repositories`

Para operações de CRUD tradicional, utilizar: `list`, `get`, `create`, `update`, `delete`.

Quando a operação envolver um campo ou domínio diferente da entidade principal, especificá-lo no nome do método:

```python
list_by_purchase_id(...)  # listar users pelo id da purchase
update_email(...)  # atualizar apenas o campo email
```

## Nomenclatura de arquivos

Todo arquivo deve ser prefixado com o nome do domínio + a camada correspondente:

```
models/user_model.py
models/purchase_model.py
repositories/user_repository.py
repositories/purchase_repository.py
schemas/user_schema.py
services/user_service.py
routers/v1/user_router.py
```

Exceções: `core` e `utils` não seguem esse padrão.

### `utils/`

Arquivos organizados por tipo de função utilitária:

```
utils/formatters.py
utils/parsers.py
utils/validators.py
```

## Nomenclatura de métodos — `services` e rotas

Seguem o mesmo padrão do `repository`, prefixado/sufixado pelo domínio:

```python
list_user(...)
get_user(...)
create_user(...)
update_user(...)
delete_user(...)

list_users_by_purchase_id(...)  # segue a mesma regra de especificidade do repository
```

## Paginação

Toda resposta de listagem (`list_*`) deve seguir o formato paginado:

```json
{
  "data": [],
  "page": 1,
  "page_size": 20,
  "total_items": 100,
  "total_pages": 5
}
```

## Respostas de erro — Problem Details

Erros devem seguir o padrão [RFC 9457 (Problem Details)](https://www.rfc-editor.org/rfc/rfc9457):

```json
{
  "type": "https://minha-api.com/errors/validation-error",
  "title": "Erro de validação",
  "status": 422,
  "detail": "Um ou mais campos são inválidos.",
  "errors": [
    { "field": "email", "message": "Formato inválido" },
    { "field": "cpf",   "message": "CPF obrigatório" }
  ]
}
```

## Schemas

Todo schema deve ocultar os nomes de campos vindos do banco de dados, utilizando:

```python
model_config = ConfigDict(from_attributes=True, populate_by_name=True)
```