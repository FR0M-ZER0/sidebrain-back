# Changelog

## [1.1.0](https://github.com/FR0M-ZER0/sidebrain-back/compare/v1.0.0...v1.1.0) (2026-10-28)


### Features

* **sdb-100:** adiciona filtros e recálculo de badges ([7fe23a2](https://github.com/FR0M-ZER0/sidebrain-back/commit/7fe23a2f0091a71c771738e284cf5b5ba4b76265))
* **sdb-100:** adiciona justificativa ao rate do quiz ([291261f](https://github.com/FR0M-ZER0/sidebrain-back/commit/291261f30143092a789e88d6bef7bd920cb9cd78))
* **sdb-100:** adiciona missões mensuráveis às etapas ([5355356](https://github.com/FR0M-ZER0/sidebrain-back/commit/53553568c571c1dd5d0c36232bf19c4859af4482))
* **sdb-100:** adiciona progresso e listagem global de missões ([1631d17](https://github.com/FR0M-ZER0/sidebrain-back/commit/1631d1793c7d70c727c359c7696902ae4154190d))
* **sdb-100:** atualiza badges com atividades do usuário ([73b43f8](https://github.com/FR0M-ZER0/sidebrain-back/commit/73b43f8873f96b69da31c33b3c0ef1b3be47471c))
* **sdb-100:** filtra listagem de trilhas do usuário ([96c60d7](https://github.com/FR0M-ZER0/sidebrain-back/commit/96c60d7af14906713cd7e92322487c17fd863eba))
* **sdb-100:** inclui resumo de XP no perfil ([cc46846](https://github.com/FR0M-ZER0/sidebrain-back/commit/cc468463f344d699945f4f8d2b71421e53e7d4bb))
* **sdb-86:** adiciona endpoints de gerenciamento de missões ([a211bee](https://github.com/FR0M-ZER0/sidebrain-back/commit/a211beed66b5bfba3c686564e94febe32d9c3a19))
* **sdb-87:** adiciona endpoints de badge ([660b3ea](https://github.com/FR0M-ZER0/sidebrain-back/commit/660b3ea923a6409367430d7b133162b8b288035e))
* **sdb-88:** adiciona resumo por etapa ([e150088](https://github.com/FR0M-ZER0/sidebrain-back/commit/e1500883fcc26b015139b406d804cdd251e21ddf))
* **sdb-88:** adiciona tempo de expiração do token como variavel ([f1d2bd1](https://github.com/FR0M-ZER0/sidebrain-back/commit/f1d2bd1f064731c949b1d2c04bcbbb71b1da2713))
* **sdb-88:** expande conteúdo didático das etapas ([5a73544](https://github.com/FR0M-ZER0/sidebrain-back/commit/5a7354473543131e8a42e2654af6b94a0080e8c1))
* **sdb-88:** integra classificador ao sumário da etapa ([9e9a36b](https://github.com/FR0M-ZER0/sidebrain-back/commit/9e9a36b38ae649941421c24f7e9fa81edfee94e9))
* **sdb-88:** limita texto e cita fontes das lições ([0c0a783](https://github.com/FR0M-ZER0/sidebrain-back/commit/0c0a783ae933e70294afb52d035b33f9fc3a1fb3))
* **sdb-88:** seleciona provedor de chat por configuração ([312752d](https://github.com/FR0M-ZER0/sidebrain-back/commit/312752d3dd905eab3e8c8a72335f3f55c5795036))
* **sdb-89:** adiciona pipeline de indexação e busca RAG ([9afce4c](https://github.com/FR0M-ZER0/sidebrain-back/commit/9afce4cfff873480947759cb4887ce3b5fa7b4ea))
* **sdb-89:** adiciona suporte ao pgvector ([049074d](https://github.com/FR0M-ZER0/sidebrain-back/commit/049074d40c4d2dafc0faddf571d6c24a277f8db3))
* **sdb-89:** integra RAG à geração de trilhas ([5b69575](https://github.com/FR0M-ZER0/sidebrain-back/commit/5b695754b691fb25ebeaa3fd4ee2237515ce2779))
* **sdb-90:** adiciona endpoints para gerenciamento do ranking de usuários por xp ([0052e1a](https://github.com/FR0M-ZER0/sidebrain-back/commit/0052e1a74dd804ba29b95c12952ae6c1f278de74))
* **sdb-93:** adiciona funcionalidade para gerar missões por IA ([1240dc7](https://github.com/FR0M-ZER0/sidebrain-back/commit/1240dc7cb1ecb8723a4466a140771b6519b944f1))


### Bug Fixes

* **sdb-100:** corrige geração incremental de conteúdo ([fea7f64](https://github.com/FR0M-ZER0/sidebrain-back/commit/fea7f6416be81fcfbbcd40916f1be07ba8a01f85))
* **sdb-100:** descarta pool async na geração inicial ([a9f132d](https://github.com/FR0M-ZER0/sidebrain-back/commit/a9f132d39b2fd94bfdbda16af5e4d8b6a288894e))
* **sdb-100:** usa dependência correta no ranking ([6d3bc57](https://github.com/FR0M-ZER0/sidebrain-back/commit/6d3bc57fa4c960d29ff1091989573ba4da8f8f80))
* **SDB-81:** corrige configuração de autenticação no CI ([5279554](https://github.com/FR0M-ZER0/sidebrain-back/commit/52795549e664cabf2f1f25a878383e8b48d2e74a))
* **sdb-81:** corrige configuração do banco de testes ([a1c7678](https://github.com/FR0M-ZER0/sidebrain-back/commit/a1c76789b03494e3fb6d964e7fcc2e8f08796690))
* **sdb-81:** corrige estrutura do arquivo de dependências ([706baa7](https://github.com/FR0M-ZER0/sidebrain-back/commit/706baa75a0a128da47276375c7ad71d693af0c99))
* **SDB-81:** corrige validações de autenticação e migração ([fbde83c](https://github.com/FR0M-ZER0/sidebrain-back/commit/fbde83c588aa3b18f7c665eecdec26807526992a))
* **SDB-81:** garante unicidade das falhas no Redis ([86d3a9f](https://github.com/FR0M-ZER0/sidebrain-back/commit/86d3a9fb8da55446df46724c9728865f23677727))
* **SDB-81:** impede troca de senha durante bloqueio ([69b985c](https://github.com/FR0M-ZER0/sidebrain-back/commit/69b985ca7b5158ae69a7626d5bfc130d04de45c1))
* **SDB-81:** resolve conflitos com a dev ([06d515d](https://github.com/FR0M-ZER0/sidebrain-back/commit/06d515d39cca97bfa6f1d79a576ddd76f4955bdc))
* **SDB-81:** valida tipos antes de normalizar usuário ([10e8240](https://github.com/FR0M-ZER0/sidebrain-back/commit/10e8240b7183ceee3638053c8c01ec30f9a649b0))
* **sdb-88:** ajusta chamadas OpenAI ao modelo configurado ([3632a7c](https://github.com/FR0M-ZER0/sidebrain-back/commit/3632a7cb52acf67b2a3332b7d55f14d8508064fa))
* **sdb-88:** destaca tópicos centrais no resumo da etapa ([67468dd](https://github.com/FR0M-ZER0/sidebrain-back/commit/67468ddd1286217c868812bf78d9d3dfde40938d))
* **sdb-88:** ordena etapas pela progressão de nível ([e173c1f](https://github.com/FR0M-ZER0/sidebrain-back/commit/e173c1f2608012fb421a1f57acd0cc4208a73cbc))
* **sdb-88:** reforça validação do conteúdo gerado ([53d0b68](https://github.com/FR0M-ZER0/sidebrain-back/commit/53d0b68a052c90224382cc967f53dae5b41bb686))
* **sdb-88:** remove prefixo genérico do título da trilha ([1cbbbfd](https://github.com/FR0M-ZER0/sidebrain-back/commit/1cbbbfd28089f15389559755744d2c9e1822edb0))
* **sdb-88:** repara coluna de resumo da etapa ([8363d36](https://github.com/FR0M-ZER0/sidebrain-back/commit/8363d36f287c2eeec57a90af832b028bc443610a))

## 1.0.0 (2026-09-29)


### Features

* adiciona arquivo dos servidores mcp ([0165c01](https://github.com/FR0M-ZER0/sidebrain-back/commit/0165c011ade02893b161581c1b62b47a46c48ad1))
* adiciona conexão assíncrona com o banco de dados postgres ([e472e1a](https://github.com/FR0M-ZER0/sidebrain-back/commit/e472e1aac0d426b79ebbc57c3bdbd2bbab8217b3))
* adiciona conexão com o banco de dados ([530c1ab](https://github.com/FR0M-ZER0/sidebrain-back/commit/530c1ab017e9f0ac7269da7776e4d671ec9b4585))
* adiciona enums ([b41e519](https://github.com/FR0M-ZER0/sidebrain-back/commit/b41e51958ac46752585d428c48485658937912ce))
* adiciona hooks do git ([96e1690](https://github.com/FR0M-ZER0/sidebrain-back/commit/96e16905531253961b3553d58a12b60052490feb))
* adiciona migrações do alembic ([549993d](https://github.com/FR0M-ZER0/sidebrain-back/commit/549993d9bd56f6b1319af1196ea95e487b4dde6d))
* adiciona models do projeto ([7806631](https://github.com/FR0M-ZER0/sidebrain-back/commit/780663188a82c9d50ede5de707621069d910a891))
* adiciona o spec-kit ([109b81d](https://github.com/FR0M-ZER0/sidebrain-back/commit/109b81d6919d0c20d3eeebf6f322480b959e6298))
* **sdb-49:** adiciona endpoints de track ([4c9a41d](https://github.com/FR0M-ZER0/sidebrain-back/commit/4c9a41d694a64bc0ecb58fa46acf5580a79ce1d9))
* **sdb-51:** adiciona gerenciamento de quizzes ([d6f56fd](https://github.com/FR0M-ZER0/sidebrain-back/commit/d6f56fd137053b40ff4235b86b455bb491ce2b59))
* **sdb-52:** adiciona endpoints de feedback ([69ad295](https://github.com/FR0M-ZER0/sidebrain-back/commit/69ad295c72fcf4c8e7d811c4c10b58671338e2b1))
* **sdb-52:** adiciona seed.py ([5d81fc4](https://github.com/FR0M-ZER0/sidebrain-back/commit/5d81fc4bead92d230db262217286336bfb2a47ca))
* **sdb-53:** adiciona funcionalidade para obter o nível do usuário ([c1e3c3c](https://github.com/FR0M-ZER0/sidebrain-back/commit/c1e3c3ca1341a4501ecbaa8b42c53a4c7801fde3))
* **sdb-56:** adiciona gerenciamento do nível de conhecimento ([7fe11f3](https://github.com/FR0M-ZER0/sidebrain-back/commit/7fe11f3538b49fbcc8d6f27647538b3e3e07c360))
* **sdb-57:** adiciona gerenciamento de lições ([c8aae93](https://github.com/FR0M-ZER0/sidebrain-back/commit/c8aae93a17d3fcabbe4a77cff1765f7ba9f1816e))
* **sdb-58:** adiciona endpoints de steps ([91f7a6f](https://github.com/FR0M-ZER0/sidebrain-back/commit/91f7a6fe732173e32bbffa74a0a009255ca926d6))
* **sdb-59:** adiciona geracao assincrona de trilhas ([e48c6e5](https://github.com/FR0M-ZER0/sidebrain-back/commit/e48c6e50cc6ad60c8bf134184bb8a57218dab8f4))
* **sdb-60:** gera lições e quizzes ([4b518bb](https://github.com/FR0M-ZER0/sidebrain-back/commit/4b518bb8571b789db88840d9f2b5bedaecae1df8))
* **sdb-64:** adiciona workflow de padroes de desenvovlvimento ([1fbb6a8](https://github.com/FR0M-ZER0/sidebrain-back/commit/1fbb6a8a6d6800430df2e42439711977681a41d2))
* **sdb-64:** Adiciona workflow de padroes de desenvovlvimento ([a90faa6](https://github.com/FR0M-ZER0/sidebrain-back/commit/a90faa64f884617e6ed4737897da66b174e2f8cd))
* **sdb-72:** adiciona client do groq ([fa11568](https://github.com/FR0M-ZER0/sidebrain-back/commit/fa115687147ac1768a2571fb3e821269962095eb))
* **sdb-75:** adiciona chamadas assíncronas às tasks do celery ([800c9f4](https://github.com/FR0M-ZER0/sidebrain-back/commit/800c9f45153f19a7a9fde6f5956cd1322d495619))
* **sdb-75:** adiciona tabela para gerações ([6d468f7](https://github.com/FR0M-ZER0/sidebrain-back/commit/6d468f7ea67f78a7360c5b827198cad53cdbb7eb))
* **sdb-76:** adiciona acompanhamento SSE da geração ([c9267c9](https://github.com/FR0M-ZER0/sidebrain-back/commit/c9267c903b2314df153ec0826fc08386b9ab0209))
* **sdb-76:** avalia respostas de quiz com IA ([08045da](https://github.com/FR0M-ZER0/sidebrain-back/commit/08045dae0da1ba577d6652d3e442404296d1294e))
* **sdb-76:** conclui lição após responder quizzes ([7a81772](https://github.com/FR0M-ZER0/sidebrain-back/commit/7a8177267a3a013e0a274bf85eb4694f2cc252ca))
* **sdb-76:** habilita CORS para todas as origens ([9caec74](https://github.com/FR0M-ZER0/sidebrain-back/commit/9caec74f6d4d3d61d117520ac040673202594323))
* **sdb-76:** persiste ícones de trilha escolhidos pela LLM ([5aff3c1](https://github.com/FR0M-ZER0/sidebrain-back/commit/5aff3c1266ec27f096217c07873c398172e43f60))
* **sdb-76:** propaga avaliacao no fluxo de geracao ([5355ba9](https://github.com/FR0M-ZER0/sidebrain-back/commit/5355ba9c1f2b4e927f621b2b6e05d0a98b85bdab))
* **sdb-76:** vincula avaliacao a geracao de trilha ([e306a58](https://github.com/FR0M-ZER0/sidebrain-back/commit/e306a5821fe6dde374c1e48ee6dda878148b55ac))
* **sdb-77:** adiciona polling da geração de trilhas ([f806f02](https://github.com/FR0M-ZER0/sidebrain-back/commit/f806f025b9cada2033463aabf0a99d89782bdd09))


### Bug Fixes

* corrige erro em que os models utilizavam o nome dos atributos dos enums ([1edbe78](https://github.com/FR0M-ZER0/sidebrain-back/commit/1edbe781b20f486a83667274d22eb86cf72ad52e))
* corrige nomes das classes dos enums ([f9492b6](https://github.com/FR0M-ZER0/sidebrain-back/commit/f9492b6f1a0d223ee93ea9a9b5ce7254eabd256c))
* corrige utilização das variáveis do env que estavam erradas ([df0b414](https://github.com/FR0M-ZER0/sidebrain-back/commit/df0b4146598504c9fa99016f9acbb16cc9a9b1a2))
* **sdb-51:** corrige problemas apontados na revisão ([938d7fe](https://github.com/FR0M-ZER0/sidebrain-back/commit/938d7fe25a8386cf6d0f742f791641b44ec77590))
* **sdb-75:** altera os prompts para gerar os valores conforme os schemas ([487d1c1](https://github.com/FR0M-ZER0/sidebrain-back/commit/487d1c1267052c920b713582e0d2424c872b7fbd))
* **sdb-76:** evita acesso a usuário expirado no fluxo SSE de geração ([94f3705](https://github.com/FR0M-ZER0/sidebrain-back/commit/94f37054d8460890f8967a2544d019e243e72d6a))
* **sdb-76:** persiste falhas permanentes da Groq ([7823a10](https://github.com/FR0M-ZER0/sidebrain-back/commit/7823a1098d036dd1b0d10d628c48c15e0353a824))
