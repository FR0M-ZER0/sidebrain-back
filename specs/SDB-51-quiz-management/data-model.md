# Data Model: Gerenciamento de Quizzes

## Quiz

| Campo físico | Campo público | Regra |
|---|---|---|
| `qui_id` | `id` | UUID gerado pelo banco; somente resposta |
| `qui_lesson_id` | `lesson_id` | FK obrigatória; determinada pela URL e nunca aceita no body |
| `qui_question` | `question` | string obrigatória com 1–1.000 caracteres após `strip()` |
| `qui_updated_at` | não exposto no response direto | controlado pelo sistema; ordena listagens e muda em update/delete |
| `qui_is_deleted` | não exposto | `false` em consultas normais |
| `qui_deleted_at` | não exposto | `null` enquanto ativo; preenchido no soft delete |

Requests de criação e atualização contêm somente `question` e rejeitam campos
extras. O response direto usa aliases Pydantic e não expõe os nomes `qui_*`.

Schemas planejados: `QuizCreateRequest`, `QuizUpdateRequest`, `QuizResponse` e
`AnswerResponse`. A coleção usa `PaginatedResponse[QuizResponse]`, preservando o
envelope genérico normativo do projeto.

## Answer

| Campo físico | Campo público | Regra |
|---|---|---|
| `ans_id` | `id` | UUID da resposta existente |
| `ans_question_id` | não exposto | FK interna para Quiz; associação representada pelo aninhamento |
| `ans_user_id` | `user_id` | UUID escalar do autor da resposta |
| `ans_text` | `text` | texto da resposta |
| `ans_rate` | `rate` | `good`, `perfect`, `wrong` ou `almost_got_it` |
| `ans_created_at` | não exposto no response direto | ordenação crescente, com `ans_id` como desempate |
| `ans_updated_at` | não exposto no response direto | auditoria interna |

Answer é somente leitura nesta feature. Quiz sem respostas é serializado com
`answers: []`.

## Relações e acesso

```text
User 1 ─── N Track 1 ─── N Step 1 ─── N Lesson 1 ─── N Quiz 1 ─── N Answer
```

- A Lesson deve existir, não estar excluída e pertencer a uma Step e Track
  ativas do usuário autenticado.
- O status da Lesson não restringe operações de quiz.
- Consulta direta e mutações do Quiz aplicam os mesmos joins e filtros de acesso.
- Todas as Answers do Quiz autorizado são retornadas; o ownership é aplicado ao
  conteúdo superior, não a `ans_user_id`.
- A hierarquia de Track mantém filtros de soft delete em Track, Step, Lesson e
  Quiz e compõe `Lesson -> Quiz[] -> Answer[]`.

## Ordenação

- Listagem paginada e `Lesson.quizzes`: `qui_updated_at DESC`, depois
  `qui_id DESC`.
- `Quiz.answers`: `ans_created_at ASC`, depois `ans_id ASC`.
- A ordem é definida no SQL/mapeamento para ser idêntica em consultas diretas e
  hierárquicas.

## Estados e transições

```text
criação
  -> ativo (qui_is_deleted=false, qui_deleted_at=null)

ativo --PUT--> ativo
  question normalizada; qui_updated_at atualizado

ativo --DELETE--> excluído
  qui_is_deleted=true
  qui_deleted_at=qui_updated_at=instante atual

excluído -> estado terminal nesta API
```

O soft delete não altera nem remove Answers. Um Quiz excluído, ou cujo pai
Track/Step/Lesson esteja excluído, não pode ser listado, consultado, atualizado
ou excluído novamente.

## Paginação e consultas

- Defaults: `page=1`, `page_size=20`; limites: `page >= 1` e
  `1 <= page_size <= 100`.
- Envelope: `data`, `page`, `page_size`, `total_items`, `total_pages`.
- Página além do total retorna `data: []` com metadados consistentes.
- A listagem usa uma consulta de validação da Lesson, uma de total, uma de
  quizzes paginados e uma para o lote de Answers; a quantidade de queries não
  cresce por item.
- Detalhe e responses após mutação carregam Answers antes da serialização, sem
  lazy I/O sob `AsyncSession`.

## Compatibilidade da hierarquia existente

O response direto de quiz é mínimo e sem timestamps. O schema histórico de
Track mantém seus timestamps já publicados por meio de extensões dos schemas
canônicos de Quiz e Answer; ele é ampliado, sem remoções, para incluir
`lesson_id` no Quiz e `user_id` em Answer. Ambos usam nomes de negócio e nunca
expõem flags de exclusão.
