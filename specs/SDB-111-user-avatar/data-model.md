# Modelo de dados — SDB-111

## Avatar

Tabela `avatar`, mantida por migração e arquivos versionados:

| Campo | Tipo | Regras |
|---|---|---|
| `avt_slug` | `VARCHAR(64)` | chave primária, obrigatório, imutável |
| `avt_name` | `VARCHAR(100)` | obrigatório |
| `avt_image_path` | `VARCHAR(255)` | obrigatório, caminho relativo servido por `/static` |
| `avt_is_active` | `BOOLEAN` | obrigatório, default `true` |
| `avt_created_at` | `DATETIME` | obrigatório, default do banco |

O catálogo inicial contém os slugs `cat`, `dog`, `fox`, `bear`, `rabbit`,
`panda`, `owl`, `penguin`, `lion` e `turtle`, com nomes em português e uma
imagem correspondente. O registro default é um recurso estático (`default.png`),
não uma opção selecionável nem um registro ativo do catálogo.

## Perfil do usuário

Adicionar ao modelo `user`:

| Campo | Tipo | Regras |
|---|---|---|
| `usr_avatar_slug` | `VARCHAR(64)` nullable | foreign key para `avatar.avt_slug`, `SET NULL` no delete |

O campo permanece nulo para usuários atuais e quando a seleção é removida.
Somente slugs ativos são aceitos pelo serviço no momento da seleção; a leitura
não falha se um registro anteriormente selecionado for desativado.

## Representação de API

`AvatarResponse` contém `slug`, `name` e `imageUrl`, uma URL relativa como
`/static/avatars/cat.png`.

`UserMeResponse` passa a conter `avatar: AvatarResponse`. Para perfil sem
seleção ou com avatar inativo, o valor é:
`{ "slug": "default", "name": "Avatar padrão", "imageUrl": "/static/avatars/default.png" }`.

## Transições

1. **Sem seleção → ativo:** slug ativo; persiste o slug e retorna a imagem.
2. **Ativo → outro ativo:** valida o novo slug e substitui somente a referência.
3. **Ativo → sem seleção:** `avatar: null`; persiste `NULL` e retorna default.
4. **Ativo → desativado:** o usuário mantém a referência, mas a leitura resolve
   para default.
5. **Ausente no payload:** não executa transição de avatar.
