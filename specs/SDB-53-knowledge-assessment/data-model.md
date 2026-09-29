# Modelo de Dados da Avaliacao

Os objetos abaixo sao DTOs transitórios, sem tabelas ou migrations.

## AssessmentContext

Entrada interna da task/service.

| Campo | Tipo | Obrigatorio | Regras |
|---|---|---:|---|
| `user_id` | UUID/string serializavel | sim | Vem do contexto autenticado; nao e aceito como dado informado pelo usuario final. |
| `subject` | string | somente se `skip=false` | Trim; 1 a 255 caracteres; nao pode ser vazio. |
| `objective` | string ou null | nao | Trim; vazio normalizado para `null`; limite de 1000 caracteres. |
| `skip` | boolean | sim | Define o caminho sem provider; default `false` no contrato interno se o chamador omitir. |

## KnowledgeQuestion

Pergunta gerada e validada antes de ser exposta.

| Campo | Tipo | Obrigatorio | Regras |
|---|---|---:|---|
| `id` | string | sim | Identificador estavel dentro do resultado, nao vazio. |
| `statement` | string | sim | Enunciado nao vazio. |
| `alternatives` | lista de `KnowledgeAlternative` | sim | Exatamente quatro alternativas, sem texto vazio e sem ids repetidos. |

## KnowledgeAlternative

| Campo | Tipo | Obrigatorio | Regras |
|---|---|---:|---|
| `id` | string | sim | Identificador nao vazio, estavel na pergunta. |
| `text` | string | sim | Texto nao vazio. |

## KnowledgeAssessmentResult

| Campo | Tipo | Obrigatorio | Regras |
|---|---|---:|---|
| `assessment_id` | UUID | sim | Identifica a execucao transitoria. |
| `status` | `generated` ou `skipped` | sim | Controla as invariantes abaixo. |
| `level` | `beginner` ou null | condicional | `beginner` somente quando `status=skipped`; nulo quando gerado. |
| `questions` | lista de `KnowledgeQuestion` | sim | Cinco itens quando `generated`; lista vazia quando `skipped`. |

## Invariantes e estados

- `skipped`: `level=beginner`, `questions=[]`, nenhuma chamada externa.
- `generated`: `level=null`, `len(questions)=5`, todas as perguntas e alternativas validas.
- Nao existe estado parcial publicavel. Falha de parsing, schema ou quantidade impede o retorno do resultado.
- A classificacao definitiva baseada em respostas nao pertence a este modelo nem a esta feature.
- `user_id` e contexto de execucao, nao uma entidade criada ou modificada.
