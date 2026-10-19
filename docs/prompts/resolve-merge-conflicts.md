# Prompt para resolução de conflitos de merge

Use o texto abaixo como instrução para o agente responsável por fazer merge de `dev` na branch atual e resolver conflitos:

```text
Faça merge de `dev` na branch atual e resolva cuidadosamente quaisquer conflitos resultantes. O objetivo é atualizar a branch atual com `dev`; não faça merge da branch atual em `dev`.

## Prepare o merge

1. Identifique a branch atual com `git branch --show-current`. Se ela for `dev`, pare e informe que não há uma branch de funcionalidade distinta para atualizar.
2. Inspecione `git status`, os commits recentes e as diferenças entre a branch atual e `dev`. Leia as instruções aplicáveis do repositório.
3. Preserve todo o trabalho do usuário. Se a árvore de trabalho tiver alterações não commitadas, não as descarte, sobrescreva, guarde em stash ou inclua em commits. Determine se o merge pode prosseguir com segurança sem interferir nelas; caso contrário, pare e explique o que precisa ser resolvido primeiro.
4. Confirme que a referência local de `dev` está disponível e atualizada em relação à branch `dev` pretendida. Faça fetch somente se necessário e permitido pelo fluxo de trabalho do repositório; nunca troque de branch nem atualize a própria `dev`.

## Faça o merge e resolva os conflitos

1. Inicie um merge de `dev` na branch atual usando o fluxo de trabalho Git normal do repositório.
2. Para cada arquivo com conflito, inspecione a versão base e as versões de ambas as branches, além do código relevante ao redor e das convenções do projeto. Entenda a intenção de ambas as alterações antes de resolver o conflito.
3. Resolva cada conflito de forma a obter o resultado combinado correto. Preserve os comportamentos válidos de ambas as branches quando forem compatíveis. Se um conflito exigir escolher quais comportamentos ou alterações manter e não for possível determinar a escolha correta a partir do código e do contexto da tarefa, pause antes de resolvê-lo e pergunte ao usuário o que ele deseja manter. Apresente opções claras e executáveis (por exemplo, manter a versão da branch atual, manter a versão de `dev` ou combinar ambas quando viável), explique o impacto de cada uma e marque uma opção como **Recomendada**, com uma breve justificativa. Aguarde a escolha do usuário antes de aplicar essa resolução; não adivinhe nem trate a recomendação como aprovação.
4. Não escolha `ours` ou `theirs` às cegas, remova marcadores de conflito sem conciliar o conteúdo ou faça alterações não relacionadas. Não use comandos destrutivos como `git reset --hard` nem descarte alterações do usuário.
5. Após resolver os conflitos, verifique se não restam marcadores de conflito nos arquivos afetados, inspecione o diff completo do merge e execute os testes, o lint ou as verificações de build apropriados. Corrija apenas os problemas introduzidos pelo merge e informe quaisquer verificações que falharem ou não puderem ser executadas.
6. Prepare explicitamente para commit apenas os arquivos cujos conflitos você resolveu; não use comandos abrangentes como `git add -A`. Mantenha intactos os arquivos que o Git já preparou como resultados de merge sem conflitos e, em seguida, conclua o merge usando o fluxo normal de continuação de merge do repositório. Não faça amend nem reescreva commits existentes e não faça push.

## Informe o resultado

Informe se o merge foi concluído, quais arquivos exigiram resolução de conflitos, o hash do commit de merge caso tenha sido criado, as verificações executadas e seus resultados, além de quaisquer problemas ou impedimentos restantes.
```
