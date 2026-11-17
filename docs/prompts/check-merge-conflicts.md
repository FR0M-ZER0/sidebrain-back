# Prompt para verificação de conflitos de merge

Use o texto abaixo como instrução para o agente responsável por verificar conflitos de merge entre `dev` e a branch atual:

```text
Verifique se fazer merge de `dev` na branch atual produziria conflitos. Esta é uma tarefa de inspeção somente de leitura: não faça merge, rebase, alterações em arquivos, commits ou push.

## Verifique as branches

1. Identifique a branch atual com `git branch --show-current`. Se ela for `dev`, informe que não há uma branch atual distinta para comparar e pare.
2. Inspecione `git status` e preserve todas as alterações existentes do usuário.
3. Confirme que a branch local `dev` existe e determine se ela está atualizada em relação à referência de `dev` pretendida. Se a branch ou referência necessária estiver indisponível ou desatualizada, explique essa limitação; não presuma silenciosamente que a comparação está atualizada.
4. Compare a branch atual com `dev` usando uma verificação com merge-tree que não altere as branches ou os arquivos, como `git merge-tree --write-tree dev HEAD`. Se a versão instalada do Git não oferecer suporte a essa opção, use uma forma compatível de `git merge-tree` que também não altere as branches ou os arquivos.

## Informe o resultado

- Se houver conflitos, informe-os na conversa. Para cada conflito, identifique o arquivo afetado e resuma as alterações conflitantes usando a saída do merge-tree e os diffs relevantes das branches. Não edite os arquivos nem tente resolver os conflitos.
- Se não houver conflitos, informe que, com base nas referências verificadas, espera-se que o merge de `dev` na branch atual ocorra sem conflitos.
- Mencione claramente qualquer limitação, como uma referência de `dev` indisponível ou desatualizada, um comando Git não suportado ou alterações não commitadas que tornem a comparação incerta.
```
