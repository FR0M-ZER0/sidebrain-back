# Resultados de validação da SDB-81

**Data:** 2026-10-14  
**Ambiente:** Windows, Python 3.11, PostgreSQL 16 efêmero, Redis 7 e API local.

## Gates automatizados

| Gate | Resultado |
| --- | --- |
| `ruff check .` | PASS — sem violações |
| suíte `pytest` | PASS — 449 passed, 2 skipped, 2 avisos de dependências |
| testes fundamentais SDB-81 | PASS — 17 passed |
| contratos e services SDB-81 | PASS — 29 passed |
| integração de usuário | PASS — 7 passed antes da ampliação final; casos ampliados incluídos na suíte completa |
| desempenho com 20 clientes | PASS — p95 de 1,046 s; limite de 2 s |
| consumidores do contrato | PASS — 5 de 5 jornadas concluídas |

Os dois skips da suíte completa são cenários condicionados ao ambiente. O
ensaio de autenticação condicionado a `AUTH_PERFORMANCE_BASE_URL` foi executado
separadamente contra a API local e passou.

## Migração

O histórico completo foi aplicado em PostgreSQL vazio até
`f81a1b2c3d4`. Em seguida, `alembic downgrade -1` e novo `upgrade head`
terminaram com sucesso.

Consultas a `information_schema.columns` e `pg_indexes` confirmaram:

- após downgrade: `usr_token_version=0`, índice normalizado `=0`;
- após upgrade: `usr_token_version=1`, índice normalizado `=1`.

As contas e tabelas relacionadas permaneceram no banco durante a reversão.
Também foram inseridas duas contas artificiais que diferiam apenas por caixa e
espaços. O upgrade foi interrompido antes da alteração do esquema com a mensagem
de reconciliação esperada. Após remover somente esses dados artificiais, o
upgrade voltou a passar.

## Cenários funcionais e de segurança

Testes de contrato, unidade, integração e execução local cobriram cadastro,
entrada, perfil, atualização, troca de senha e exclusão lógica. Também foram
verificados JWT adulterado/expirado/incompleto, UUID puro, revogação por versão,
reserva de e-mail de conta excluída, concorrência, Problem Details e headers.

Com Redis real, seis logins inválidos consecutivos retornaram
`[401, 401, 401, 401, 401, 429]`; a sexta resposta trouxe
`Retry-After: 900`. O cadastro usado no ensaio retornou `201` e a limpeza por
exclusão lógica retornou `204`.

## Validação de consumidores

Cinco sessões HTTP independentes executaram cadastro, entrada e consulta do
próprio perfil usando somente o contrato público. Todas as cinco jornadas
passaram, acima do mínimo de quatro definido por SC-007. A execução foi uma
validação técnica automatizada, não uma pesquisa de usabilidade com pessoas.
O registro reproduzível está em `consumer-validation.md` e o teste em
`tests/acceptance/test_auth_consumer_validation.py`.
