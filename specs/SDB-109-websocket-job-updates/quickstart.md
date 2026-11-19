# Validar os quatro canais após a implementação

Use um banco descartável, dois usuários de teste e processos separados para API e worker. Os comandos interativos abaixo usam PowerShell. Os cenários com barreiras, falhas e relógio controlado pertencem à suíte de integração planejada.

## Subir o ambiente

Na raiz, configure o `.env` conforme `.env.example` e o README. Preencha as credenciais locais, um segredo JWT válido e a configuração do provedor para executar a geração real. O cenário de diagnóstico dispensado também funciona sem chamar o provedor. [Setup do repositório](../../README.md)

```powershell
uv sync
docker compose up -d postgres redis
docker compose exec postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"'
uv run alembic upgrade head
uv run dev
```

Em outro terminal, subir o worker. No Windows local, acrescentar `--pool=solo`.

```powershell
uv run celery -A sidebrain_back.core.celery_app worker --loglevel=info
```

## Testar um diagnóstico do início à reconexão

Em um terceiro terminal, usar as credenciais de uma conta de teste existente. Para observar primeiro `pending`, fazer a chamada e abrir a inscrição antes de iniciar o worker.

```powershell
$api = 'http://localhost:8080/api/v1'
$conta = Get-Credential -Message 'Credenciais da conta de teste (e-mail e senha)'
$login = @{ email = $conta.UserName; password = $conta.GetNetworkCredential().Password } | ConvertTo-Json
$auth = Invoke-RestMethod -Method Post -Uri "$api/auth/login" -ContentType 'application/json' -Body $login
$headers = @{ Authorization = "Bearer $($auth.accessToken)" }

function Iniciar-Operacao($caminho, $dados) {
    $opcoes = @{ Method = 'Post'; Uri = "$api/$caminho"; Headers = $headers }
    if ($null -ne $dados) {
        $opcoes.ContentType = 'application/json'
        $opcoes.Body = $dados | ConvertTo-Json -Compress
    }
    Invoke-RestMethod @opcoes
}

function Acompanhar-Job($canal, $id) {
    $escopo = @{ channel = $canal; resource_id = [string]$id }
    $credencial = Iniciar-Operacao 'auth/ws-ticket' $escopo
    $inscricao = @{ type = 'subscribe'; channel = $canal; resource_id = [string]$id }
    Write-Host 'Envie esta mensagem quando o cliente WebSocket abrir:'
    Write-Host ($inscricao | ConvertTo-Json -Compress)
    uv run python -m websockets "ws://localhost:8080/api/v1/ws?ticket=$($credencial.ticket)"
}

$diagnostico = Iniciar-Operacao 'assessments' @{ subject = 'Frações'; skip = $true }
Acompanhar-Job 'assessment' $diagnostico.assessment_id
```

Colar a inscrição impressa no prompt WebSocket e pressionar Enter. Com o worker ativo, o resultado esperado é `completed` com `questions: []`. Sair do cliente e executar novamente a última linha. O helper emite outro ticket e a primeira atualização já traz o resultado concluído. Repetir com outro assunto e `skip = $false` para verificar as cinco perguntas com quatro alternativas públicas.

## Testar trilha, preparação e sumário

Executar as chamadas uma de cada vez. Após o terminal da trilha, copiar o `track_id` recebido. Para a preparação aceita, usar uma etapa própria com pelo menos 80% das lições ativas concluídas e uma próxima etapa elegível. Para o sumário, pode-se usar qualquer etapa própria ativa da trilha.

```powershell
$pedido = Iniciar-Operacao 'tracks' @{ goal = 'Resolver problemas com frações'; topic = 'Matemática' }
Acompanhar-Job 'track_generation' $pedido.request_id
```

```powershell
$trilha = Read-Host 'UUID da trilha própria'
$etapa = Read-Host 'UUID da etapa de origem'
$caminho = "tracks/$trilha/steps/$etapa"
$preparo = Iniciar-Operacao "$caminho/prepare-next" $null
if ($preparo.status -eq 'accepted') { Acompanhar-Job 'step_preparation' $preparo.task_id }
$sumario = Iniciar-Operacao "$caminho/summary" $null
Acompanhar-Job 'step_summary' ("${trilha}:${etapa}")
```

Conferir `succeeded` e a trilha já consultável, a preparação `completed` com o ID recebido, e o texto de sumário igual ao da resposta HTTP quando houver só uma geração. Repetir a preparação com uma etapa inelegível e conferir `skipped` sem `task_id`. [Corpos, status e erros esperados por canal](contracts/job-updates.md)

## Ensaios de aceite automatizados

Usar fixtures de provedor e canais de sincronização nos testes para controlar o instante do commit ou provocar falhas. Executar os seguintes comandos na implementação com Redis e PostgreSQL de teste ativos.

```powershell
docker compose --profile test up -d --wait postgres_test
uv run ruff check .
uv run pytest tests/contract tests/integration tests/unit
uv run pytest
```

| Ensaio | Como provocar e o que verificar |
|---|---|
| Autorização e sigilo | Enviar Bearer inválido, canal desconhecido e chave inválida. Comparar 401/422/404 no formato Problem Details. Confrontar recurso de B, UUID inexistente, etapa de outra trilha e exclusão lógica. Verificar que os 404 têm o mesmo corpo. Examinar chaves de todo o JSON de diagnóstico e logs para confirmar sigilo de gabaritos e credenciais. |
| Ticket exclusivo | Em duas réplicas, disputar o mesmo ticket em paralelo. Exigir exatamente um upgrade. Tentar sem ticket, após consumo e aos 60 s. Manter um socket aberto além desse prazo e entregar normalmente o resultado. |
| Estados | Parametrizar sucesso e falha dos quatro produtores. Introduzir falha recuperável seguida de sucesso e esgotamento de tentativas. Em cada caso definitivo conferir um terminal público e coerência com o resultado confirmado no banco. Incluir diagnóstico respondido e dispensado, preparação com conteúdo já presente e sumário legado. |
| Corridas e retomada | Confirmar uma mudança antes do LISTEN, entre registro local e leitura, durante a leitura e durante o envio. Aguardar o terminal em todos os casos. Duplicar aviso e inscrição. Repetir com socket fechado durante o commit e novo ticket depois. |
| Corridas do sumário | Iniciar A, depois B. Concluir B e só então concluir ou falhar A. Verificar B no socket, após reconexão e no GET do sumário. Repetir invertendo escritores (POST/quiz) e com rollback da resposta do quiz. |
| Retenção | Para sucesso e falha, ajustar o instante de conclusão da fixture. Até 23h59min59s, emitir ticket e ler o terminal. Aos 24h, esperar 404 na emissão e `job.error` na inscrição com ticket emitido imediatamente antes do limite. Verificar que a reconexão não renova o prazo. |
| Revogação e isolamento | Inscrever usuários distintos no mesmo canal. Revogar acesso após o ticket e, em outro teste, depois do primeiro snapshot. Na próxima tentativa de envio, exigir somente o erro genérico e fechamento da conexão afetada. Enviar inscrição divergente e malformada e conferir a correlação original do erro. |
| Limpeza e falha de infraestrutura | Fechar normalmente, interromper o transporte com o job pendente, falhar o envio e derrubar a conexão LISTEN. Conferir zero consumidores, vínculos e tarefas daquele socket após cada caso. O job deve poder terminar. Abrir nova inscrição após a recuperação. |
| Latência | Com worker real e provedor determinístico, registrar no mesmo relógio de teste os instantes de aceitação, commit observado e recepção. Obter ao menos 100 amostras por canal e tipo de entrega. Calcular p95 separadamente para snapshot e terminal, com alvo de até 2 s em cada conjunto. |
| Compatibilidade e migração | Rodar os contratos vigentes de trilhas, diagnóstico, etapas e quiz. Testar migração e reversão em banco descartável com dados anteriores, e reentrega de mensagens Celery anteriores à ativação. |

Na homologação, repetir a conexão com `wss://` pelo proxy público, com duas réplicas e worker em processo separado. Confirmar que nenhuma query com ticket aparece nos logs de acesso e repetir a retomada roteando o cliente para outra réplica. [Requisitos de publicação](contracts/job-updates.md)

## Evidências da implementação

Validação local executada em 18/11/2026 com PostgreSQL de teste na porta
5434 e Redis local:

- o executável `uv` não estava no `PATH` desta sessão; foi usado o ambiente
  existente com `.venv\Scripts\python.exe -m ...`, equivalente aos comandos
  `uv run ...` abaixo;

- `alembic upgrade head`: concluído, incluindo `sdb109jobupdates`;
- `ruff check src migrations/versions/sdb109_job_updates.py tests`: aprovado;
- testes focados de contrato, ticket, listener e regressões dos produtores:
  aprovados;
- suíte completa final com diretório temporário local: `754 passed, 7 skipped`
  em 38,84 s;
- ciclo de migração `downgrade e6f7a8b9c0d1` seguido de `upgrade head`:
  aprovado.

O primeiro ensaio completo no sandbox encontrou apenas restrição de acesso ao
diretório temporário do usuário e bloqueio do download inicial do vocabulário
`tiktoken`. A repetição com `--basetemp` dentro do projeto e cache local do
`tiktoken` passou integralmente.

O ensaio de homologação permanece pendente: este ambiente não possui URL,
credenciais nem acesso ao proxy/duas réplicas de homologação. Portanto ainda
não há evidência local para `wss`, roteamento entre réplicas ou inspeção dos
logs do proxy.
