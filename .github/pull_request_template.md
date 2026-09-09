# 📝 Descrição

**Exemplo:** Este pull request adiciona a autenticação do usuário no sistema, alterando as funções X e Y para o suporte dessa nova funcionalidade e adicionando no banco de dados o novo campo W para persistência dos tokens de refresh. Além de melhorias de performance nas funções de autenticação e no tempo de hashing.

# 🔧 Mudanças

* Adicionado funcionalidade de token de refresh e de acesso
* Adicionado middleware para proteger rotas
* Adicionado endpoint para sign-in e sign-out

# 🧪 Como testar

1. Faça uma requisição para `/customer/123`
2. Verifique se a API retorna um erro `401`
3. Faça uma requisição para `/sign-in` com os dados do usuário padrão
4. Tente acessar novamente `/customer/123` e verifique se os dados são retornados corretamente

# 🎯 Checklist

- [x] Meu código segue os padrões do projeto
- [x] Adicionei/atualizei testes
- [x] Atualizei a documentação
- [x] Lints passaram
- [x] Fiz self-review do código

# 🔗 Link da Task

**Exemplo:** https://tasks.com/pr-20