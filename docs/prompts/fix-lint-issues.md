# Prompt para resolução de problemas de lint

Use o texto abaixo como instrução para o agente responsável por resolver problemas de lint neste repositório:

```text
Resolva os problemas de lint apontados pela configuração do ESLint deste repositório. Corrija as causas dos problemas no código, preservando o comportamento esperado e todo o trabalho existente do usuário.

## Inspecione e diagnostique

1. Inspecione `git status` e os diffs relevantes antes de fazer alterações. Preserve as alterações preexistentes e não relacionadas do usuário; não as descarte, sobrescreva, prepare para commit ou inclua em commits.
2. Execute `npm run lint` e revise a saída completa. Identifique os arquivos afetados e entenda cada violação de regra em seu contexto antes de editar.

## Resolva os problemas

1. Faça as menores alterações que resolvam corretamente as violações apontadas, mantendo o comportamento da aplicação intacto e seguindo os padrões do código ao redor.
2. Remova importações e declarações que realmente não são utilizadas. Para avisos sobre dependências de React Hooks, determine as dependências corretas e ajuste a estrutura do código, se necessário; não suprima a regra nem adicione dependências às cegas.
3. Não desative nem enfraqueça regras do ESLint, adicione exclusões genéricas ou use comentários de supressão no código apenas para fazer o lint passar. Use uma supressão de escopo restrito somente quando uma limitação real tornar a regra inaplicável e documente o motivo ao lado dela.
4. Não faça refatorações não relacionadas nem altere a configuração de lint, a menos que a tarefa exija isso especificamente. Se um diagnóstico parecer ser um falso positivo ou não puder ser resolvido sem alterar o comportamento esperado, explique o problema e consulte o usuário antes de fazer uma alteração arriscada.

## Verifique e informe

1. Execute `npm run lint` novamente após as alterações. Revise o diff para confirmar que ele contém apenas as alterações necessárias para resolver os problemas de lint.
2. Se as alterações puderem afetar o comportamento em tempo de execução, execute os testes relevantes ou as verificações de build disponíveis no repositório. Não afirme que as verificações passaram se elas não foram executadas.
3. Informe os arquivos alterados, os tipos de problemas de lint resolvidos, as verificações executadas e seus resultados, além de quaisquer diagnósticos ou impedimentos restantes.
```
