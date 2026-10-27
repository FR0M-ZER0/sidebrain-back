# Modelo de dados — SDB-86

## Mission

Recurso de objetivo de aprendizagem persistido em `mission`.

| Campo público | Campo persistido | Tipo | Regras |
|---|---|---|---|
| `id` | `msn_id` | UUID | Identificador gerado pelo banco |
| `stepId` | `msn_step_id` | UUID | Obrigatório na criação; imutável na atualização |
| `title` | `msn_title` | string | 1–255 caracteres após trim; não pode ser vazio |
| `difficulty` | `msn_difficulty` | `MissionDifficultyEnum` | Deve ser um valor conhecido |
| `xpReward` | `msn_xp_reward` | inteiro | Não negativo |
| `criteria` | `msn_criteria` | `MissionCriteriaEnum` | Deve ser um valor conhecido |
| `criteriaValue` | `msn_criteria_value` | inteiro | Positivo |
| `updatedAt` | `msn_updated_at` | datetime | Atualizado em mutações |
| (interno) | `msn_is_deleted` | boolean | Filtrado nas consultas públicas |
| (interno) | `msn_deleted_at` | datetime opcional | Preenchido no soft delete |
| `missionProgresses` | relação `mission_progress` | lista | Somente registros do usuário autenticado |

## MissionProgress

Entidade somente de leitura nesta feature. A relação é filtrada por
`mpg_user_id` e não permite criação, atualização, pontuação, mudança de status
ou exclusão nos endpoints de Mission.

Campos públicos da composição: `id`, `status`, `finishedIn`, `score` e
`updatedAt`.

## Step e Track

- `Step` possui `stp_track_id` e só é acessível quando não está excluído.
- `Track` define o ownership via `trk_user_id` e também deve estar ativo.
- A autorização efetiva é `user -> Track -> Step -> Mission`.

## Relações e transições

```text
Track 1 ── N Step 1 ── N Mission 1 ── N MissionProgress
```

Estados públicos de Mission:

```text
ativa --DELETE--> excluída logicamente
```

Uma missão em estado excluído não retorna em listagem ou consulta e não pode
ser atualizada ou excluída novamente. A exclusão não remove
`MissionProgress`.

## Validações de entrada

- `MissionCreate`: exige `title`, `difficulty`, `xpReward`, `criteria` e
  `criteriaValue`; rejeita campos extras e `stepId` no body.
- `MissionUpdate`: todos os campos editáveis são opcionais, mas ao menos um deve
  ser enviado; rejeita payload vazio, campos extras e `stepId`.
- `title` é normalizado com trim.
- Erros de schema devem resultar em Problem Details `422`.
