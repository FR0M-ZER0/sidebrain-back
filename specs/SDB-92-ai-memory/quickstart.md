# Quickstart de validação — SDB-92

## Pré-requisitos

- Python >=3.11, `uv`, PostgreSQL, Redis e variáveis do `.env`.
- Dependências instaladas com `uv sync`.
- Banco atualizado com `uv run alembic upgrade head`.

## Validação estática e suíte

```bash
uv run ruff check .
uv run pytest
```

Resultado esperado: lint sem erros e todos os testes existentes e novos
passando.

## Cenários de unidade

```bash
uv run pytest tests/unit -k "memory or fingerprint or normalization or alias"
```

Verificar que caixa, acentos, Unicode combinado, whitespace e pontuação
produzem o mesmo valor canônico; `INGLÊS` e `ingles` resolvem para
`lingua inglesa`; níveis, respostas, modelo e `prompt_version` diferentes
produzem fingerprints diferentes.

## Cenário de contrato de Track e SSE

```bash
uv run pytest tests/contract -k "track or generation"
```

Criar uma request válida, concluir a geração e repetir o mesmo contexto com
outro usuário. O mock do provedor deve registrar uma chamada, a segunda
resposta deve conter `source=cache`, o SSE deve emitir esse campo e a Track
clonada deve possuir IDs e ownership novos.

## Cenário de contrato de Assessment

```bash
uv run pytest tests/contract -k "assessment"
```

Criar avaliações equivalentes para dois usuários. O segundo resultado deve
reutilizar perguntas/alternativas sem compartilhar IDs, respostas, score ou
status de conclusão.

## Cenários de integração

```bash
uv run pytest tests/integration -k "memory or generation or assessment"
```

Executar requests concorrentes para o mesmo fingerprint e verificar no banco
uma entrada `GenerationCache` `ready`, no máximo uma chamada ao provedor e
nenhum registro parcial. Repetir com lock/lookup indisponível e com
`AI_MEMORY_ENABLED=false`: a geração deve terminar com `source=ai`.

## Invalidação e regressão

Alterar `GROQ_MODEL` ou `GROQ_PROMPT_VERSION` entre duas solicitações e
confirmar fingerprints/cache distintos. Ler requests legados sem
`source`/cache e confirmar que continuam válidos. Validar downgrade da
migration em banco descartável quando houver teste de migrations.

Os campos e entidades esperados estão detalhados em
[data-model.md](data-model.md) e [contracts/ai-memory.md](contracts/ai-memory.md).
