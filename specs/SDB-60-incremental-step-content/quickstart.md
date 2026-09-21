# Quickstart: Validação da geração incremental de conteúdo de Steps

## Pré-requisitos

- Ambiente do projeto configurado com `uv`.
- PostgreSQL em execução via Docker Compose ou ambiente equivalente.
- Dependências do backend instaladas com `uv sync`.
- Entidades de Track/Step/Lesson/Mission/Quiz já presentes no banco.

## Cenários executáveis

### 1. Progress threshold é alcançado

1. Criar uma Track com um Step ativo contendo Lessons ativas.
2. Marcar pelo menos 80% delas como concluídas.
3. Executar a lógica de progresso existente.
4. Verificar que a operação original conclui sem bloquear no provedor externo.
5. Confirmar que a task assíncrona do próximo Step foi enfileirada.

### 2. Progress abaixo do threshold

1. Criar uma Track com Step ativo e menos de 80% de Lessons ativas concluídas.
2. Executar a lógica de progresso.
3. Verificar que a geração do próximo Step não é disparada.

### 3. Geração bem-sucedida do próximo Step

1. Selecionar um Step elegível sem conteúdo e com Track contextualizada.
2. Executar a task de geração.
3. Confirmar que a resposta do provedor é validada antes da persistência.
4. Verificar que Lessons, Quizzes e Missions são persistidos com relacionamentos validados e sem criação de `Answer`, `Feedback`, `LessonFile` ou `MissionProgress`.

### 4. Idempotência e concorrência

1. Disparar duas execuções para o mesmo Step quase simultaneamente.
2. Verificar que apenas uma geração persiste conteúdo e a outra termina sem duplicar registros.

### 5. Falha transitória e retry

1. Simular erro do provedor (timeout ou indisponibilidade temporária).
2. Executar a task e confirmar o retry limitado.
3. Verificar que nenhum conteúdo parcial fica persistido.

## Comandos sugeridos

```bash
uv sync
uv run pytest tests/unit tests/integration -q
```

## Resultado esperado

- A atualização de progresso continua responsiva.
- O próximo Step é preparado em background apenas quando o threshold for atingido.
- O conteúdo gerado é consistente, atômico e sem duplicação.
