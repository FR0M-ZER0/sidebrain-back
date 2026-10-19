# Prompt para criação de branch

Use o texto abaixo como instrução para o agente responsável por criar uma nova branch:

```text
Crie uma nova branch local com base na versão mais recente da branch `dev` do remote apropriado. O usuário fornece apenas o ID da task; consulte os dados dela pelo MCP do Jira no espaço Sidebrain e gere o nome da branch no formato `tipo/sdb-XX-descricao-task`.

## Identifique a task

1. Identifique o ID da task fornecido pelo usuário no formato `SDB-XX` ou `sdb-XX`, em que `XX` é o número da task com um ou mais dígitos, como `sdb-1` ou `sdb-10`. Se estiver ausente ou inválido, solicite um ID válido; não invente nem deduza o identificador.
2. Consulte a task pelo MCP do Jira no espaço Sidebrain, usando o ID informado. Leia o título, o tipo e a descrição disponíveis para entender o objetivo da tarefa e gerar um nome condizente.
3. Se o MCP do Jira estiver indisponível ou não for possível obter os dados da task, peça ao usuário que escreva o nome da task e seu ID. Aguarde essas informações antes de gerar a branch; não invente os dados ausentes.
4. Confirme que o ID retornado pelo Jira ou informado junto com o nome corresponde ao ID solicitado. Se houver divergência, peça esclarecimento antes de continuar.

## Gere e valide o nome da branch

1. Gere o nome no formato obrigatório `tipo/sdb-XX-descricao-task`. O ID deve aparecer imediatamente após o tipo e a barra, sempre em minúsculas, seguido de um hífen e da descrição.
2. Escolha um tipo condizente com o objetivo da task, como `feat` para funcionalidade, `fix` para correção, `docs` para documentação, `refactor` para refatoração, `test` para testes ou `chore` para manutenção. Use os dados do Jira ou, no fluxo alternativo, o nome fornecido pelo usuário. Se não houver contexto suficiente para escolher o tipo ou descrever a tarefa, solicite esclarecimento.
3. Gere uma descrição curta e fiel à task, em português, usando letras minúsculas sem acentos, números e hífens entre palavras, sem espaços ou caracteres especiais. Inicie a descrição com um verbo na forma `cria`, `corrige` ou `adiciona`, em vez de `criar`, `corrigir` ou `adicionar`. Por exemplo: `feat/sdb-1-cria-cadastro-usuario` ou `fix/sdb-10-corrige-validacao-email`.
4. Valide o nome gerado com `git check-ref-format --branch <branch-name>` e confira se ele segue o formato obrigatório. Se for inválido, ajuste a descrição e valide novamente, preservando o ID da task e o tipo apropriado.
5. Inspecione a branch atual, os remotes configurados e o resultado de `git status`. Revise as alterações preparadas para commit, as não preparadas e os arquivos não rastreados para saber o que deve ser preservado.
6. Verifique se já existe uma branch local ou remota com o nome gerado, consultando também o remote para não depender apenas de referências locais desatualizadas. Se existir, não a redefina, sobrescreva ou reutilize. Informe o conflito e peça orientação para ajustar a descrição, mantendo o formato obrigatório e o ID da task.

## Atualize a referência remota de `dev`

1. Identifique o remote apropriado do repositório (use o remote da branch upstream da branch atual quando estiver claramente configurado; caso contrário, use `origin` se ele for o único remote apropriado). Se houver ambiguidade sobre o remote correto, pergunte ao usuário qual usar.
2. Sempre faça fetch da versão mais recente de `dev` desse remote antes de criar a branch e verifique a referência de rastreamento remoto resultante, como `<remote>/dev`. Não presuma que as referências locais já estão atualizadas.
3. Se a branch local `dev` existir, compare seu commit com o da referência `<remote>/dev` recém-atualizada para verificar se ela está sincronizada, atrasada, adiantada ou divergente em relação ao remote. Informe qualquer diferença; se a branch local não existir, use diretamente a referência remota atualizada.
4. Não faça checkout, pull, reset ou qualquer outra atualização da branch local `dev` ou de sua árvore de trabalho. O fetch da referência remota não deve alterar arquivos na árvore de trabalho. Use sempre a referência `<remote>/dev` recém-atualizada como base da nova branch, independentemente do estado da `dev` local.
5. Se o fetch falhar ou não for possível verificar a branch remota `dev`, pare sem criar a branch e informe o problema.

## Crie a branch com segurança

1. Crie a nova branch a partir da referência de rastreamento remoto de `dev` obtida pelo fetch, não da branch atual. Por exemplo, use `git switch -c <branch-name> <remote>/dev` quando for seguro trocar de branch.
2. Preserve todas as alterações preexistentes na árvore de trabalho, incluindo arquivos preparados para commit, não preparados e não rastreados. Não edite, prepare para commit, descarte, guarde em stash, inclua em commits ou sobrescreva essas alterações.
3. Se a árvore de trabalho não estiver limpa, não troque a branch em uso, pois isso poderia carregar ou interferir no trabalho existente. Crie apenas a referência da branch a partir de `<remote>/dev` (por exemplo, `git branch <branch-name> <remote>/dev`) e mantenha a branch atual e todos os arquivos intactos. Informe ao usuário que a branch foi criada, mas não foi feito checkout dela.
4. Se a troca de branch sobrescrever ou causar conflito com algum arquivo existente, não a force. Mantenha a branch atual e os arquivos intactos; se apropriado, mantenha apenas a referência da branch recém-criada e informe ao usuário que não foi feito checkout dela.
5. Não faça push da nova branch.

## Verifique e informe

- Verifique se a nova branch aponta para o mesmo commit da referência `<remote>/dev` obtida pelo fetch.
- Se foi seguro trocar de branch, verifique se a nova branch está em uso. Caso contrário, verifique se a branch original continua em uso e se as alterações na árvore de trabalho foram preservadas.
- Informe o ID e o nome da task, a origem dos dados (Jira ou usuário), o nome da nova branch, o remote e o commit usados como base, o resultado da verificação de atualização de `dev`, se foi feito checkout da nova branch e quaisquer alterações preservadas na árvore de trabalho ou impedimentos.
```
