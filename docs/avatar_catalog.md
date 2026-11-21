# Catálogo de avatares

O catálogo é mantido pelo backend. Cada opção possui um slug imutável, nome,
estado de ativação e um arquivo em `src/sidebrain_back/static/avatars/`.

## Catálogo inicial

| Slug | Nome | Arquivo |
|---|---|---|
| `cat` | Gato | `cat.png` |
| `dog` | Cachorro | `dog.png` |
| `fox` | Raposa | `fox.png` |
| `bear` | Urso | `bear.png` |
| `rabbit` | Coelho | `rabbit.png` |
| `panda` | Panda | `panda.png` |
| `owl` | Coruja | `owl.png` |
| `penguin` | Pinguim | `penguin.png` |
| `lion` | Leão | `lion.png` |
| `turtle` | Tartaruga | `turtle.png` |

`default.png` é usado quando o perfil não possui avatar ou quando a opção
selecionada foi desativada.

## Adicionar ou desativar

Para adicionar uma opção, inclua o arquivo de imagem no diretório estático e um
registro com slug imutável na migração Alembic. O seed inicial usa
`ON CONFLICT DO NOTHING`, portanto reaplicações não sobrescrevem alterações
operacionais.

Para desativar uma opção, aplique uma migração que defina
`avatar.avt_is_active` como `false`. Não remova o registro: usuários que ainda
possuem a referência continuarão válidos e receberão `default.png` no perfil.
Opções inativas deixam de aparecer em `GET /api/v1/avatars` e não podem ser
selecionadas novamente.
