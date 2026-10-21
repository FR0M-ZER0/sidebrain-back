# Prompt para resumo das alterações da branch atual

Use o texto abaixo como instrução para o agente responsável por resumir as alterações do projeto na branch Git atual:

```text
Analise e resuma as alterações do projeto associadas à branch atual. Não modifique arquivos, prepare alterações para commit, crie commits ou faça push.

## Identifique a branch e o ponto de comparação

1. Execute `git branch --show-current` e `git status --short`.
2. Se a branch atual for exatamente `main`, `dev` ou `hml`, avise claramente no início da resposta: "Esta não é uma branch de funcionalidade; a branch atual é `<branch>`." Continue com o resumo das alterações quando houver um ponto de comparação relevante disponível.
3. Use sempre `dev` como branch de comparação, independentemente da branch upstream rastreada pela branch atual. Identifique a referência local ou remota de `dev` disponível (por exemplo, `dev` ou `origin/dev`) e informe qual foi usada. Se nenhuma referência de `dev` estiver disponível, informe isso e peça ao usuário que a forneça ou faça fetch dela; não substitua silenciosamente a branch base por outra.

## Inspecione todas as alterações relevantes

1. Revise todo o intervalo de commits desde a base de merge entre a branch atual e `dev` até `HEAD`, incluindo as mensagens dos commits e o diff agregado. Essa comparação deve ser feita com `dev` para que alterações já compartilhadas pelas duas branches não sejam contabilizadas como específicas da branch atual.
2. Inspecione também a árvore de trabalho: diffs das alterações preparadas e não preparadas para commit, nomes dos arquivos alterados e arquivos não rastreados. Inspecione o conteúdo dos arquivos não rastreados quando necessário para descrevê-los com precisão.
3. Diferencie as alterações commitadas da branch das alterações não commitadas da árvore de trabalho. Não atribua alterações preexistentes aos commits da branch nem as omita do relatório.
4. Leia o código e a documentação relevantes para entender o contexto. Resuma o comportamento real ou o objetivo das alterações, em vez de apenas repetir mensagens de commit ou listar nomes de arquivos.

## Apresente o relatório

1. Comece pelo nome da branch atual e pela referência de `dev` e base de merge utilizadas. Inclua o aviso de que não se trata de uma branch de funcionalidade quando aplicável.
2. Agrupe alterações relacionadas em tópicos concisos e compreensíveis e cite os caminhos dos arquivos relevantes.
3. Separe as alterações commitadas das não commitadas e identifique as alterações preparadas e não preparadas para commit e os arquivos não rastreados, quando houver.
4. Mencione verificações somente se elas tiverem sido realmente executadas durante esta tarefa. Não afirme que verificações passaram com base em suposições ou execuções anteriores.
5. Informe claramente quaisquer limitações, como a ausência de uma referência de `dev`, e evite afirmar que o resumo está completo quando não tiver sido possível estabelecer a comparação.
```
