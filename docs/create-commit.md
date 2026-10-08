# Prompt para criação de commits

Use o texto abaixo como instrução para o agente responsável por criar os commits:

```text
Analise as alterações desta tarefa e crie os commits necessários, seguindo rigorosamente as instruções abaixo.

## Identifique a task

1. Consulte o nome da branch atual com `git branch --show-current`.
2. Extraia da branch o identificador da task no formato `SDB-XX` e normalize-o para minúsculas, no formato `sdb-XX` (por exemplo, `SDB-10` vira `sdb-10`). O número pode ter um ou mais dígitos.
3. Use esse identificador como o escopo de todos os commits, imediatamente após o tipo, conforme o Conventional Commits: `tipo(sdb-XX): descrição`.
4. Se a branch não tiver um identificador SDB inequívoco, não invente nem deduza um ID. Não crie commits; informe o problema e peça o identificador correto.

## Faça commits atômicos

- Examine `git status`, o diff completo e os arquivos alterados antes de preparar commits.
- Agrupe as alterações em commits pequenos, coesos e independentes: cada commit deve representar uma única mudança lógica e poder ser entendido e revisado isoladamente.
- Crie commits separados para mudanças que atendam a objetivos diferentes. Não faça um único commit abrangente quando houver mudanças independentes.
- Mantenha juntas as alterações que dependem umas das outras para formar uma unidade funcional. Não fragmente uma mudança de forma artificial apenas para aumentar o número de commits.
- Inclua somente alterações pertencentes a esta tarefa. Preserve alterações preexistentes ou não relacionadas; não as descarte, sobrescreva ou inclua nos commits.
- Faça o stage de forma explícita, selecionando apenas os arquivos ou trechos relacionados ao commit em questão.

## Siga Conventional Commits

- Use o formato `tipo(sdb-XX): descrição`, sempre com o ID real extraído da branch.
- Escolha um tipo que represente corretamente a mudança, por exemplo: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `perf` ou `chore`.
- Escreva a descrição em português, no imperativo, de forma breve e específica; comece com letra minúscula e não termine com ponto.
- Exemplo: `feat(sdb-10): adiciona validação ao formulário de cadastro`.
- Para uma mudança incompatível, aplique a convenção de breaking change do Conventional Commits (`!` no cabeçalho e/ou rodapé `BREAKING CHANGE:`), mantendo o escopo da task.

## Antes e depois de commitar

- Confira o conteúdo staged de cada commit para garantir que ele é atômico e não contém arquivos alheios à tarefa.
- Execute verificações apropriadas às alterações quando possível. Não declare que uma verificação passou sem executá-la.
- Crie os commits usando as mensagens definidas. Não faça amend, não reescreva commits existentes e não faça push.
- Ao terminar, informe os hashes, as mensagens de cada commit e as verificações executadas (incluindo resultados ou falhas).
```