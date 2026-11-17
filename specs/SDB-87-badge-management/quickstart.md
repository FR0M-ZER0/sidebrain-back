# Quickstart de validação

## Pré-requisitos

- Python conforme `.python-version` e dependências sincronizadas.
- PostgreSQL 16 disponível pelo Docker Compose.
- Um usuário persistido e seu UUID para usar como Bearer token.

Na raiz do repositório:

```powershell
uv sync
docker compose up -d
```

## Validação automatizada

Execute os testes específicos depois que a implementação estiver pronta:

```powershell
uv run pytest tests/unit/test_badge_schema.py tests/unit/test_badge_service.py tests/integration/test_badge_lifecycle.py tests/contract/test_badge_contract.py
uv run ruff check .
```

## Cenários end-to-end

1. **Criar e normalizar**
   - Envie `POST /api/v1/badges` autenticado com `name: "  Primeira trilha  "` e valores válidos.
   - Confirme `201`, `name: "Primeira trilha"` e `progress: []`.
2. **Validar regras**
   - Repita o nome com caixa diferente e confirme `409`.
   - Envie `criteria_value: 0`, critério desconhecido, raridade desconhecida e nome vazio; confirme `422` sem novo registro.
3. **Listar e isolar progresso**
   - Crie progresso para dois usuários no mesmo badge.
   - Consulte `GET /api/v1/badges` e `GET /api/v1/badges/{id}` com cada usuário; confirme que cada resposta contém somente seu próprio progresso.
   - Consulte uma página acima do total e confirme `data: []`, `total_items` e `total_pages` corretos.
4. **Atualizar parcialmente**
   - Envie `PATCH /api/v1/badges/{id}` com apenas descrição ou nome.
   - Confirme que os campos omitidos permaneceram inalterados; payload `{}` deve retornar `422`.
5. **Soft delete**
   - Remova o badge e confirme `204`.
   - Confirme `404` em listagem/detalhe/atualização/remoção repetida e valide diretamente no banco que o registro e o progresso continuam presentes.
6. **Autenticação**
   - Repita POST, GET, PATCH e DELETE sem Bearer e confirme `401`, sem alteração no banco.

Os campos e estados esperados estão detalhados em [data-model.md](data-model.md);
os formatos HTTP estão em [contracts/badges.md](contracts/badges.md).
