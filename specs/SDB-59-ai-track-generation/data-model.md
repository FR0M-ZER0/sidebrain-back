# Modelo de Dados: Geração de Trilhas com IA

## Modelos internos de geração

### LearningContext

- `goal`: objetivo textual obrigatório.
- `topic`: tópico textual obrigatório.
- `knowledge_level`: nível identificado opcional, limitado a `StepLevelEnum`.
- `assessment_answers`: respostas da avaliação opcionais; texto e classificação necessários para orientar a geração, sem criar registros `Answer`.

### GeneratedTrack

- `title`: texto obrigatório, 1-255 caracteres após normalização.
- `description`: texto obrigatório no resultado, dentro do limite de texto do domínio.
- `steps`: coleção não vazia e completa, ordenada por `position`.

### GeneratedStep

- `position`: inteiro positivo, único e contíguo.
- `level`: valor de `StepLevelEnum`, seguindo a estratégia de progressão sem níveis indevidos ou duplicação.
- `title`: texto obrigatório, 1-255 caracteres.
- `lessons`: preenchido somente quando `position == 1`.
- `mission`: no máximo uma; permitida somente na primeira etapa e apenas quando a estratégia indicar.

### GeneratedLesson

- `position`: inteiro positivo, único e contíguo dentro da etapa.
- `title`: texto obrigatório, 1-255 caracteres.
- `text`: texto obrigatório e não vazio.
- `quiz`: exatamente um quiz para a lição inicial, conforme a estratégia.

### GeneratedQuiz

- `question`: texto obrigatório e não vazio.
- Não contém respostas; respostas dependem da interação do usuário.

### GeneratedMission

- `title`: texto obrigatório, 1-255 caracteres.
- `difficulty`: `MissionDifficultyEnum`.
- `xp_reward`: inteiro positivo dentro do limite do domínio.
- `criteria`: `MissionCriteriaEnum`.
- `criteria_value`: inteiro positivo compatível com o critério.

## Persistência

```text
Track (trk_generation_request_id UNIQUE, trk_user_id, title, description)
└── Step[] (level, title, status=idle)
    ├── Lesson[] (title, text, position, status=idle)
    │   └── Quiz[] (question)
    └── Mission? (title, difficulty, xp_reward, criteria, criteria_value)
```

`trk_generation_request_id` é a chave idempotente recebida pela task, gerada por
uma migration reversível e não exposta em schemas públicos. A restrição UNIQUE
impede duas trilhas para o mesmo pedido.

A geração inicial não cria `Answer`, `Feedback`, `MissionProgress` ou
`LessonFile`. IDs físicos, timestamps de auditoria e flags de exclusão são
responsabilidade dos modelos ORM e não fazem parte dos schemas internos da IA.

## Regras de validação e transição

1. Contexto obrigatório e identificador de solicitação válido são validados antes da chamada à IA.
2. A resposta JSON é validada integralmente antes do primeiro `session.add`/flush.
3. Todas as etapas devem existir na ordem esperada; somente a posição 1 pode conter lições, quizzes ou missão.
4. Lições da primeira etapa precisam ter posições únicas e contíguas; cada uma recebe um quiz quando a estratégia o exigir.
5. Campos textuais vazios, enum inválido, valores numéricos fora do domínio e missão incompatível rejeitam o resultado.
6. Em pedido já concluído, retorna-se a trilha associada; em pedido pendente, o acompanhamento reutiliza a task registrada pelo fluxo existente.
7. Falha de IA, validação, conflito de idempotência ou persistência não deixa entidades da geração parcialmente gravadas.
