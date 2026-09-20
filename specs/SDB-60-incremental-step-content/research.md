# Research: Geração incremental de conteúdo de Steps

## Decisão 1: threshold e cálculo do progresso

**Decision**: O cálculo de progresso usa somente Lessons ativas do Step alvo, contabilizando o total de Lessons ativas e a proporção concluídas, com critério inclusivo em 80% (`>= 80`).

**Rationale**: A especificação já define esse threshold como valor fixo e o cálculo precisa ser consistente com a regra de soft delete e com a ausência de dependência de API externa durante a atualização de progresso. Isso elimina ambiguidades em execução e permite testes determinísticos.

**Alternatives considered**: 
- Incluir Lessons excluídas logicamente ou passos inativos: rejeitado porque contradiz a regra de “somente Lessons ativas” e permite falsa aceleração de progresso.
- Usar threshold estritamente maior que 80%: rejeitado porque a feature define 80% como limite inclusivo e a regra precisa ser testável.

## Decisão 2: seleção do próximo Step elegível

**Decision**: O próximo Step candidato deve pertencer à mesma Track, estar ativo, não possuir conteúdo gerado elegível e ser o primeiro seguindo a ordem da Track/Step existente; a seleção deve ocorrer sem bloquear a requisição atual.

**Rationale**: A regra reduz risco de conteúdo incoerente e garante que a etapa seguinte seja a mais próxima disponível na sequência de estudo, preservando a ordem sem exigir UX ou endpoint novo.

**Alternatives considered**:
- Selecionar qualquer Step em qualquer Track: rejeitado porque quebra o escopo e pode gerar contexto incoerente.
- Gerar conteúdo para o próximo passo quando não existir relação ou quando o Step já possuir conteúdo parcial: rejeitado porque a feature exige idempotência e segurança contra duplicação.

## Decisão 3: execução assíncrona e idempotência

**Decision**: A tarefa de geração será disparada por Celery/async task já utilizado pelo projeto e deve verificar rapidamente se o Step alvo já possui conteúdo completo ou execução equivalente em andamento antes de chamar o provedor.

**Rationale**: O projeto já usa Celery para processamento assíncrono com retry e logs estruturados; a feature deve reutilizar esse padrão e manter o request responsável por progresso sem bloquear por IA externa.

**Alternatives considered**:
- Gerar em sincronismo na rota de progresso: rejeitado porque viola a exigência de não aguardar provedor externo e aumenta latência percebida.
- Criar nova API pública ou novos schemas HTTP: rejeitado porque o requisito exige “nenhum endpoint novo” nesta feature.

## Decisão 4: transação, persistência e rollback

**Decision**: A persistência de Lessons/Quizzes/Missions deve ocorrer em uma única transação de banco, com validação estrutural prévia e rollback completo em qualquer falha de persistência.

**Rationale**: Isso preserva a consistência da Track e evita conteúdo parcial visível em caso de erro ou resposta inválida. A regra também alinha com a constituição e com modelos de persistência existentes no backend.

**Alternatives considered**:
- Persistir por partes e apagar erros depois: rejeitado porque deixa estado inconsistente e exige lógica de compensação mais complexa.
- Aceitar conteúdo parcial em caso de falha transitória: rejeitado porque a feature exige zero dados parciais.

## Decisão 5: retry e observabilidade

**Decision**: Falhas transitórias do provedor seguem retry limitado com logs do tipo de falha e tentativa atual, enquanto falhas permanentes encerram a execução sem loop infinito ou expor segredos.

**Rationale**: A arquitetura do projeto já usa `max_retries`, `retry_backoff` e logs com contexto. O padrão reduz risco de degradação e facilita diagnóstico sem preencher logs com credenciais.

**Alternatives considered**:
- Retry infinito: rejeitado por risco operacional e pela exigência de limite finito.
- Registrar credenciais ou payloads sensíveis: rejeitado pela política de segurança e observabilidade mínima.

## Conclusão

Os pontos de decisão foram resolvidos no escopo da feature e não exigem novos esclarecimentos antes do planejamento. O desenho continua compatível com o projeto existente e com as regras de arquitetura, idempotência, observabilidade e segurança do backend.
