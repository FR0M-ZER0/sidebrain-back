# Data Model: Gerenciamento de Feedback

## Feedback

| Campo físico | Campo público | Regra |
|---|---|---|
| `fbk_id` | `id` | UUID gerado pelo banco; somente resposta |
| `fbk_lesson_id` | `lesson_id` | FK obrigatória para aula ativa na criação/listagem |
| `fbk_user_id` | `author_id` | FK do usuário autenticado; nunca vem do cliente |
| `fbk_text` | `text` | obrigatório, 1+ caractere após `strip()` |
| `fbk_created_at` | `created_at` | timestamp controlado pelo sistema |
| `fbk_updated_at` | `updated_at` | atualizado em edição/exclusão |
| `fbk_is_deleted` | não exposto | `false` em consultas normais |
| `fbk_deleted_at` | não exposto | preenchido na exclusão lógica |

O schema público usa `from_attributes=True`, `populate_by_name=True` e aliases
para impedir que nomes físicos de armazenamento façam parte do contrato.
Requests aceitam somente `text`; IDs, autoria, datas e flags são rejeitados.

## Relações

```text
User 1 ─── N Feedback N ─── 1 Lesson
                              │
                              └── pertence à hierarquia Step -> Track
```

`Lesson.feedbacks` e `User.feedbacks` são relações ORM bidirecionais. A resposta
de uma aula inclui uma lista de `FeedbackResponse` ativos; feedback não possui
entidades filhas próprias.

## Estados e transições

- Criação: `fbk_is_deleted = false`, `fbk_deleted_at = null`.
- Atualização: somente feedback ativo cujo `fbk_user_id` é o usuário atual;
  altera `fbk_text` e `fbk_updated_at`.
- Exclusão: `false -> true`, preenche `fbk_deleted_at` e `fbk_updated_at`.
- Estado excluído é terminal para esta API: não aparece, não atualiza e não é
  removido novamente.

## Consultas

- Criar/listar valida a aula com `lsn_is_deleted = false`.
- Listar e consultar feedback filtram `fbk_is_deleted = false`.
- A leitura da hierarquia usa `selectinload` filtrado, incluindo todos os
  feedbacks ativos em lote e sem query individual por item.
- A coleção direta segue o envelope `data`, `page`, `page_size`,
  `total_items`, `total_pages`.
