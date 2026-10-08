# Contrato de memória da IA

Não são criados endpoints públicos. Os contratos existentes recebem campos
aditivos e continuam aceitando as mesmas requisições.

## Campos públicos aditivos

### Progresso de Track

`GET /api/v1/tracks/generations/{request_id}` e o evento `generation` do SSE
podem retornar:

```json
{
  "request_id": "uuid",
  "status": "succeeded",
  "track_id": "uuid",
  "error_code": null,
  "source": "cache"
}
```

`source` é `ai`, `cache` ou `null` para histórico sem origem registrada.

### Detalhe de Assessment

`GET /api/v1/assessments/{assessment_id}` pode retornar:

```json
{
  "assessment_id": "uuid",
  "status": "generated",
  "source": "cache"
}
```

Os demais campos permanecem inalterados. Clientes antigos devem ignorar
`source`.

## Contrato interno de canonicalização

Entrada: objetivo/tópico/assunto não vazio, nível quando aplicável, respostas
normalizadas quando aplicável, `prompt_version`, provider e model.

Saída:

```json
{
  "fingerprint_version": "v1",
  "content_type": "track",
  "canonical_context": {},
  "fingerprint": "sha256-64-lowercase"
}
```

Aliases são exatos após canonicalização. Não existe fallback fuzzy.

## Contrato interno de cache

- `lookup(fingerprint, content_type)` retorna somente `ready` e payload que
  passe novamente pelo schema de conteúdo.
- `reserve(...)` é idempotente e respeita a constraint única e a lease.
- `publish_ready(...)` grava payload validado, metadados e transição atômica.
- `release_failed(...)` registra falha sem payload reutilizável.
- Erros de lookup/lock/persistência são miss observável e permitem IA; não são
  erro HTTP público.

## Contrato de clonagem

### Track

`GeneratedTrack` é materializado com novos IDs para Track, Step, Lesson, Quiz e
Mission, owner atual e estados iniciais vazios. Respostas, feedbacks, logins,
badges, streaks e progressos não são copiados.

### Assessment

`GeneratedAssessmentPayload` é materializado com novo Assessment, Question e
Alternative. Chaves corretas são usadas somente na persistência necessária;
respostas, score, submissão e progresso começam vazios.

## Compatibilidade e erros

Requests inválidas continuam usando validação existente e Problem Details
RFC 9457. Não há alteração de status HTTP nem de nomes de rotas. Fingerprints
anteriores continuam consultáveis, mas não são confundidos com a versão atual.
