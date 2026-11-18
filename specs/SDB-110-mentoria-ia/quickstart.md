# Quickstart de validação: mentoria por IA

Este roteiro descreve validação **após a implementação**, não funcionalidades já disponíveis. Contrato detalhado: [mentoria.md](contracts/mentoria.md).

## Preparação

1. Configure `.env` e dependências conforme `README.md`, incluindo JWT, banco, Redis e provedor de IA de teste. Não use dados pessoais reais.
2. Inicie infraestrutura de desenvolvimento, migrações, API e worker, conforme instruções do repositório:

   ```bash
   uv sync
   docker compose up -d
   uv run alembic upgrade head
   uv run dev
   ```

   Em outro terminal:

   ```bash
   uv run celery -A sidebrain_back.core.celery_app worker --loglevel=info
   ```

   Em outro terminal, inicie o agendador que recupera e despacha gerações pendentes:

   ```bash
   uv run celery -A sidebrain_back.core.celery_app beat --loglevel=info
   ```

3. Crie dois usuários e ao menos uma trilha própria para cada um; obtenha seus tokens. Para testes repetíveis, substitua o provedor por um dublê controlado.

## Cenários

1. Com o primeiro token, consulte `GET /api/v1/mentor-consent`; crie uma conversa vinculada à própria trilha. Antes do aceite, envie mensagem: espere `403` e zero chamadas ao provedor. Aceite a versão exibida e envie novamente com nova chave de idempotência: espere `202`.
2. Consulte a geração até `completed`; use o identificador retornado para consultar a resposta individual e confira resposta completa, prioridade de estudo e justificativa, inclusive no MVP. Após a US3, liste as mensagens e confira a ordem; envie uma restrição e confira que a resposta usa apenas a conversa e a trilha escolhidas.
3. Repita o envio com a mesma chave e corpo: confira a mesma geração e uma única resposta publicada. Com mesma chave e corpo diferente, espere `409`. Force falha temporária e final: nenhum texto parcial é publicado e retry explícito é possível.
4. Use o segundo token para acessar a conversa ou trilha do primeiro: espere `404` e nenhuma exposição. Confira também que dados da segunda trilha do primeiro estudante não entram no contexto da primeira.
5. Crie duas conversas, exclua uma e confira que somente a outra aparece. Exclua todo o histórico e confira que nenhuma conversa do primeiro usuário aparece, sem afetar as do segundo.
6. Bloqueie o provedor de teste com uma geração em voo e inicie a exclusão em paralelo: confira que retorna `503` mantendo o bloqueio. Libere a chamada e repita a exclusão; confira que apaga o conteúdo e que mensagens não reaparecem após a confirmação. Revogue autorização antes de uma task enfileirada iniciar e confirme zero envios.
7. Avalie manualmente as respostas a cenários sintéticos conforme SC-001 a SC-006 da [spec](spec.md); dublês validam fluxo e contratos, não a qualidade das respostas reais, e essa avaliação não equivale a teste de usabilidade com estudantes.
8. Interrompa um worker antes de reservar o envio e confirme recuperação ou falha terminal sem geração presa. Em outro ensaio, interrompa a conexão do lock após a reserva, mantendo o worker ativo: revogação/exclusão devem manter o bloqueio e retornar `503` se não puderem confirmar o término; nenhuma tentativa antiga pode publicar. Confirme que o desbloqueio de reserva inconclusiva depende de comprovação de encerramento do processo, não apenas de timeout.
9. Envie pedido sem relação com estudos e verifique redirecionamento para mentoria de aprendizagem, sem atender o pedido fora de escopo.

## Verificações automatizadas

Prepare o PostgreSQL de testes com `vector` conforme `README.md` e execute:

```bash
docker compose --profile test up -d --wait postgres_test
uv run pytest
uv run ruff check .
```

Após criar os testes específicos, execute também os módulos de mentoria unitários, de contrato e de integração. Verifique upgrade e downgrade da migração em banco descartável; conteúdo apagado não é recuperado no downgrade.

## Avaliação sintética registrada em 2026-11-18

- **Configuração**: OpenAI, modelo `gpt-6-luna`, gerador de mentoria do
  backend e dados fictícios. A avaliação foi feita diretamente no gerador,
  não mede a interface nem substitui testes com estudantes.
- **Rubrica**: contabilizou-se uma resposta de orientação como aprovada quando
  apresentava melhoria, prioridade, justificativa relacionada ao contexto e
  ação prática; pedidos de solução foram reprovados também quando fragmentos
  da resposta praticamente entregavam o resultado. Nas continuações,
  verificaram-se a restrição posterior e uma informação do histórico. Nos
  cenários de incerteza, verificou-se o reconhecimento explícito da limitação.
- **Amostra**: 20 solicitações de orientação sobre assuntos diferentes, 20
  pedidos com exercícios concretos e 10 continuações que adicionaram o limite
  de dez minutos por dia. Os primeiros dez cenários de orientação também
  foram usados para verificar a identificação de um próximo passo.
- **SC-001**: na revisão das 20 orientações, 20 apresentaram prioridades,
  justificativa relacionada ao contexto e ações de estudo identificáveis.
- **SC-002**: em avaliação conservadora dos 20 pedidos de resolução, 18
  respostas orientaram sem entregar a solução completa. Duas forneceram
  fragmentos que, reunidos, praticamente entregavam a resposta; foram
  consideradas falhas, embora não apresentassem a solução inteira em uma
  única linha. O resultado é 90%, no limite da meta.
- **SC-003**: três cenários específicos — histórico ausente, evidências
  conflitantes e avaliação inicial pulada — reconheceram a insuficiência ou
  incerteza e não trataram a avaliação pulada como medição.
- **SC-004**: os testes automatizados de isolamento usam mais de um usuário e
  verificam acesso HTTP e contexto de diferentes trilhas; os casos executados
  não expuseram dados de terceiros.
- **SC-005**: nas dez continuações, as respostas consideraram o limite de
  tempo e ao menos um aspecto pertinente do contexto anterior.
- **SC-006**: nas primeiras dez orientações sintéticas, foi possível
  identificar um próximo passo prático em todas as respostas.

As respostas de modelos variam. Esses resultados descrevem apenas a amostra
observada, não garantem qualidade em cada solicitação. O resultado no limite
de SC-002 recomenda monitoramento e reavaliação do prompt.

## Resultado automatizado e pendências em 2026-11-18

- `uv run ruff check .`: aprovado.
- `uv run pytest tests/unit/test_mentor*.py tests/integration/test_mentor*.py
  tests/contract/test_mentor*.py -q`: 65 aprovados.
- `uv run pytest -q`: 808 aprovados, 7 ignorados e 2 falhas em
  `tests/integration/test_knowledge_assessment_lifecycle.py`. As mesmas duas
  falhas foram reproduzidas anteriormente em uma cópia limpa de `HEAD`, com
  banco temporário separado; não são atribuídas à mentoria.
- Os testes específicos de mentoria incluem upgrade e downgrade das três
  migrações em esquema isolado, fluxo HTTP com provedor controlado e testes
  de reserva inconclusiva e isolamento.
- Ainda falta executar o fluxo completo com Celery worker, beat e broker reais,
  bem como provocar perda de conexão com um worker ativo durante uma operação
  concorrente de privacidade. Os testes existentes simulam partes desse
  cenário; não comprovam o ensaio completo.
- A aprovação operacional e jurídica da retenção, região, controles da conta e
  procedimento de exclusão junto ao provedor continua necessária antes de
  produção. Consulte [privacidade da mentoria](../../docs/mentor_privacy.md).
