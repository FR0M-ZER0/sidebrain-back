# Data Model: Gerenciamento de Trilhas

## Track (Trilha)

- `trk_id`: UUID, identificador gerado pelo banco, somente resposta.
- `trk_user_id`: UUID do proprietário autenticado, somente persistência/resposta interna.
- `trk_title`: string obrigatória, 1 a 255 caracteres após normalização; não aceitar vazia.
- `trk_description`: texto opcional; `null` permitido.
- `trk_created_at`, `trk_updated_at`: timestamps de auditoria, somente resposta.
- `trk_is_deleted`, `trk_deleted_at`: estado de exclusão lógica, somente persistência.

Requests de criação e atualização expõem apenas `title` e `description`. O PATCH rejeita título vazio quando enviado e preserva o valor anterior quando o campo não for enviado.

## Hierarquia de leitura

```text
Track
└── Step[]
    ├── Lesson[]
    │   ├── LessonFile[]
    │   ├── Feedback[]
    │   └── Quiz[]
    │       └── Answer[]
    └── Mission[]
        └── MissionProgress[] (somente o usuário autenticado)
```

As respostas usam nomes públicos sem os prefixos físicos do banco (`id`, `title`, `description`, etc.) e schemas Pydantic com `from_attributes=True` e `populate_by_name=True`. Campos `is_deleted` e `deleted_at` dos filhos não são expostos; entidades filhas excluídas são omitidas.

## Relações e filtros

| Relação | Cardinalidade | Filtro de leitura |
|---|---:|---|
| User -> Track | 1:N | `track.user_id = current_user.id`, `track.is_deleted = false` |
| Track -> Step | 1:N | `step.is_deleted = false` |
| Step -> Lesson | 1:N | `lesson.is_deleted = false`, ordem por `position` |
| Step -> Mission | 1:N | `mission.is_deleted = false` |
| Lesson -> LessonFile | 1:N | `lesson_file.is_deleted = false` |
| Lesson -> Feedback | 1:N | `feedback.is_deleted = false` |
| Lesson -> Quiz | 1:N | `quiz.is_deleted = false` |
| Quiz -> Answer | 1:N | respostas ativas conforme regra do contrato |
| Mission -> MissionProgress | 1:N | `progress.user_id = current_user.id` |

A consulta deve usar `selectinload` aninhado, critérios de relação e ordenação estável. A implementação deve testar o número de queries para impedir crescimento proporcional ao número de filhos.

## Estados e transições

- Criação: `is_deleted=false`, `deleted_at=null`.
- Atualização: somente trilha ativa e pertencente ao usuário; atualizar `updated_at`.
- Exclusão: `is_deleted=false -> true`, preencher `deleted_at` e `updated_at`.
- Estado excluído é terminal para esta API: listagem, detalhe, atualização e exclusão retornam `404`.

## Paginação

O envelope de listagem contém `data`, `page`, `page_size`, `total_items` e `total_pages`. Os padrões são `page=1` e `page_size=20`; `page_size` máximo é 100. A resposta vazia mantém metadados consistentes e `total_pages=0` quando `total_items=0`.
