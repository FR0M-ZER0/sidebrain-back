# Contrato HTTP — Estatísticas do Usuário

Prefixo da API: `/api/v1`.

## Consultar o próprio resumo

`GET /api/v1/users/me/statistics`

Retorna as estatísticas do usuário autenticado. Não aceita identificador de
usuário, parâmetros de consulta ou corpo. Exige
`Authorization: Bearer <token>`.

### Resposta `200 OK`

```json
{
  "xp": 1250,
  "missionsCompleted": 12,
  "position": 3,
  "badgesUnlocked": 4,
  "currentDayStreak": 7
}
```

| Campo | Tipo | Regra |
| --- | --- | --- |
| `xp` | integer | Total da consulta existente do ranking; mínimo `0` |
| `missionsCompleted` | integer | Total da consulta existente do ranking; mínimo `0` |
| `position` | integer | Posição global existente do ranking; mínimo `1` |
| `badgesUnlocked` | integer | Contagem de progressos `done` associados a badges ativos; mínimo `0` |
| `currentDayStreak` | integer | Sequência registrada se a atividade mais recente ocorreu hoje ou ontem em UTC; caso contrário `0` |

### Regras

- XP, missões concluídas e posição devem ser idênticos aos valores do perfil e
  do ranking para o mesmo estado de dados.
- Usuários ativos sem progresso recebem zero nas quatro contagens; a posição
  permanece determinada pelo ranking existente, inclusive entre usuários com
  zero XP.
- `idle`, `in_progress`, conquistas sem progresso e badges removidos não são
  contabilizados como desbloqueados.
- Uma sequência com data de atividade anterior ao dia UTC imediatamente
  anterior é apresentada como zero; a consulta não altera o valor armazenado.
- A resposta não contém e-mail, credenciais, identificador de usuário ou dados
  de terceiros.
- A operação é somente de leitura e não recalcula conquistas.

### Erros

- `401 Unauthorized`: credencial ausente, inválida ou expirada; formato Problem
  Details e desafio Bearer conforme o padrão existente.
- `404 Not Found`: usuário autenticado não encontrado como ativo na consulta
  do ranking; formato Problem Details.

As respostas seguem os handlers e o formato Problem Details (RFC 9457) adotados
pela API.
