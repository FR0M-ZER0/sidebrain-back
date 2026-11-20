# Modelo de dados — SDB-112

Nenhuma tabela ou coluna nova é necessária. O resumo é uma projeção transitória
composta por consultas às entidades existentes.

## Projeção pública: UserStatistics

| Campo | Tipo | Fonte e regra |
| --- | --- | --- |
| `xp` | inteiro `>= 0` | Valor da consulta individual existente do ranking |
| `missionsCompleted` | inteiro `>= 0` | Valor da consulta individual existente do ranking |
| `position` | inteiro `>= 1` | Posição da consulta individual existente do ranking |
| `badgesUnlocked` | inteiro `>= 0` | Contagem dos progressos `done` do usuário autenticado para badges ativos |
| `currentDayStreak` | inteiro `>= 0` | Valor de `DayStreak` se atualizado hoje ou ontem em UTC; zero se ausente ou expirado |

O contrato não inclui identificador, nome, e-mail ou qualquer campo de outro
usuário. A projeção não é persistida.

## Entidades de origem

### User

- A identidade vem exclusivamente do usuário autenticado.
- Usuários removidos logicamente não possuem entrada válida no ranking e
  resultam no `404` já adotado por esse fluxo.
- Os dados do usuário não são copiados para a resposta de estatísticas.

### MissionProgress e Mission

- XP e quantidade de missões concluídas são fornecidos pelo repositório de
  ranking existente.
- Somente missões ativas em estado concluído (`done`) participam, segundo a
  regra já implementada para o ranking.
- Nenhum cálculo de XP ou conclusão será duplicado neste recurso.

### BadgeProgress e Badge

- Relação: um progresso pertence a um usuário e a um badge.
- Somente progressos do usuário autenticado com status `done` associados a um
  badge ativo são contados.
- `idle`, `in_progress`, ausência de progresso e badge removido contribuem com
  zero.
- A leitura não recalcula, cria ou altera progressos.

### DayStreak

- Existe no máximo um registro de sequência por usuário.
- `dst_value` representa o valor já registrado; `dst_updated_at` identifica o
  último dia de atividade, interpretado em UTC conforme o fluxo existente.
- A leitura retorna o valor armazenado quando `dst_updated_at` cai na data UTC
  corrente ou na data UTC anterior. Um registro mais antigo é apresentado como
  zero, sem limpar ou atualizar o registro.

## Ciclo de vida e consistência

1. A identidade autenticada determina o usuário.
2. A consulta do ranking retorna posição, XP e missões concluídas numa projeção
   única e autoritativa.
3. Consultas read-only obtêm a contagem de conquistas desbloqueadas e o registro
   de sequência do usuário.
4. O serviço valida a atualidade da sequência por uma data UTC de referência e
   monta a projeção pública.
5. Se o usuário não estiver disponível no ranking, o serviço responde com o
   erro de recurso não encontrado; nenhum estado é alterado.

Não há transições de estado nessa operação e nenhuma migration está prevista.
