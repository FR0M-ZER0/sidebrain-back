# Prompt para criação de pull request

Use o texto abaixo como instrução para o agente responsável por abrir o pull request:

```text
Analise as alterações da branch atual e crie um pull request para o repositório deste projeto, seguindo rigorosamente as instruções abaixo.

## Identifique a task e a branch

1. Consulte a branch atual com `git branch --show-current` e identifique o identificador da task no formato `SDB-XX`.
2. Normalize o identificador para minúsculas no formato `sdb-XX` (por exemplo, `SDB-10` vira `sdb-10`). O número pode ter um ou mais dígitos.
3. Se não houver um identificador SDB inequívoco na branch, não invente nem deduza um ID. Não abra o pull request; informe o problema e peça o identificador correto.
4. Confirme qual é o remote configurado para o repositório usando `git remote -v`. Use o remote definido no projeto (preferencialmente `origin`, quando configurado) e confirme que ele corresponde ao repositório desta cópia de trabalho. Não crie um pull request em outro repositório.

## Prepare o pull request

- Use sempre `dev` como branch de destino (`base`). Não escolha outra branch de destino.
- Use a branch atual como branch de origem (`head`).
- O título deve seguir exatamente o padrão `(sdb-XX): Descrição breve`, usando o ID da task encontrado na branch. Exemplo: `(sdb-10): Adiciona validação ao cadastro`.
- Escreva a descrição em português brasileiro, de forma clara e específica sobre o que foi implementado.
- Antes de criar, consulte os pull requests existentes e verifique se já há um PR aberto para a mesma branch de origem e destino. Se já existir, não crie duplicado; informe o link e o estado do PR existente.

## Siga o template do projeto

- Leia e siga integralmente o arquivo `.github/pull_request_template.md`.
- Preencha todas as seções do template, preservando seus títulos e sua estrutura: `📝 Descrição`, `🔧 Mudanças`, `🧪 Como testar`, `🎯 Checklist` e `🔗 Link da Task`.
- Substitua os exemplos do template por informações reais desta tarefa; não deixe exemplos genéricos ou instruções de preenchimento no corpo final.
- Liste as mudanças relevantes e descreva passos de teste reproduzíveis, sem afirmar testes ou verificações que não foram executados.
- Marque cada item do checklist de acordo com o que foi efetivamente realizado; não marque itens como concluídos sem confirmação.
- Inclua o link real da task SDB na seção correspondente se ele estiver disponível no repositório, na branch ou no contexto da tarefa. Se não estiver disponível, indique isso sem inventar uma URL.

## Crie e confirme o PR

- Revise o diff entre a branch atual e `dev` para que o título e a descrição representem as alterações incluídas.
- Se a branch ainda não estiver publicada no remote configurado, faça push da branch atual para esse remote, sem alterar ou sobrescrever branches alheias.
- Crie o pull request usando o remote/repositório configurado, com `dev` como base e a branch atual como head. Use `gh` para a operação no GitHub.
- Depois da criação, confirme o título, o repositório, a branch de origem e `dev` como destino.
- Ao terminar, informe o link do pull request, seu título e as branches de origem e destino.
```