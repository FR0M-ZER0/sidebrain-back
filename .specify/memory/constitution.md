<!--
Sync Impact Report
- Version change: scaffold sem versão -> 1.0.0
- Modified principles: nenhum; os cinco princípios foram definidos pela primeira vez
- Added sections: Padrões Técnicos e Arquiteturais; Fluxo de Desenvolvimento e Gates de Qualidade
- Removed sections: nenhuma
- Follow-up TODOs: confirmar a data original de ratificação em TODO(RATIFICATION_DATE)
-->

# SideBrain Backend Constitution

## Core Principles

### I. Qualidade de Código e Clean Code
O código MUST ser legível, coeso e explícito, com nomes que expressem intenção,
funções pequenas e interfaces claras. Cada alteração MUST remover duplicação
acidental, evitar efeitos colaterais desnecessários e manter o comportamento
testável. A complexidade adicional MUST ser justificada por uma necessidade
concreta do domínio ou da infraestrutura. Essa regra reduz custo de manutenção e
torna defeitos mais fáceis de localizar.

### II. Responsabilidade Única e Coesão
Cada módulo, classe, função e endpoint MUST possuir uma responsabilidade
principal, com uma única razão dominante para mudança. Regras de negócio MUST
permanecer nos serviços ou no domínio apropriado; acesso a dados MUST permanecer
nos repositórios; modelos MUST representar dados sem conter regras de negócio.
Essa separação mantém as unidades substituíveis e reduz o acoplamento.

### III. Separação Clara de Camadas
As dependências MUST seguir `routers -> services -> repositories -> models`.
Routers MUST lidar apenas com HTTP e composição de dependências; services MUST
ser independentes de detalhes HTTP; repositories MUST encapsular persistência;
schemas MUST definir os contratos de entrada e saída sem expor modelos internos.
`core` e `utils` MUST permanecer independentes das camadas de negócio, conforme
as responsabilidades descritas em `docs/architecture.md`.

### IV. Testes e Contratos Verificáveis
Toda mudança MUST incluir ou atualizar testes no nível adequado: testes unitários
para regras isoladas, testes de integração para persistência e composição entre
camadas, e testes de contrato para endpoints e schemas públicos. Uma mudança de
contrato MUST explicitar compatibilidade ou migração. A suíte relevante MUST
passar antes da integração da alteração, porque comportamento não verificado não
é considerado concluído.

### V. Simplicidade e Evolução Segura
Implementações MUST preferir a solução mais simples que satisfaça o requisito,
sem abstrações especulativas. Alterações incompatíveis MUST usar uma nova versão
de API ou um plano de migração explícito; versões existentes MUST permanecer
estáveis enquanto houver consumidores suportados. Erros públicos MUST seguir
Problem Details (RFC 9457), e falhas relevantes MUST ser observáveis por meio de
mensagens estruturadas e contexto suficiente para diagnóstico.

## Padrões Técnicos e Arquiteturais

O projeto MUST seguir FastAPI, Pydantic, SQLAlchemy, Alembic, Pytest e `uv` nos
papéis já definidos pelo repositório. A injeção de dependências MUST usar
`Depends` quando houver composição entre camadas. Arquivos e símbolos MUST seguir
`docs/code_conventions.md`, incluindo nomenclatura de métodos, paginação,
schemas configurados com `from_attributes=True` e respostas de erro em Problem
Details. Migrações MUST ser versionadas e reversíveis quando tecnicamente
possível; alterações de banco MUST ser acompanhadas por testes pertinentes.

## Fluxo de Desenvolvimento e Gates de Qualidade

Cada alteração MUST passar por revisão do impacto arquitetural, execução dos
testes relevantes e lint antes de ser integrada. O fluxo mínimo de validação é
`uv run ruff check .` e `uv run pytest`, além de migrações ou verificações
específicas quando a alteração tocar banco, contratos ou infraestrutura. A
revisão MUST rejeitar dependências indevidas entre camadas, lógica duplicada sem
justificativa e mudanças sem cobertura compatível com o risco.

## Governance
<!-- Example: Constitution supersedes all other practices; Amendments require documentation, approval, migration plan -->

Esta constituição é normativa para decisões de arquitetura e qualidade. Uma
alteração MUST descrever o princípio afetado e atualizar a documentação ou os
testes necessários. Emendas exigem proposta registrada, revisão pelos
responsáveis pelo projeto e atualização deste documento no mesmo changeset da
mudança de governança. A conformidade MUST ser verificada em cada revisão e nos
gates automatizados disponíveis; exceções MUST registrar escopo, justificativa,
risco e prazo de revisão.

A versão segue SemVer para governança: MAJOR remove ou redefine uma regra de
forma incompatível; MINOR adiciona princípio ou orientação material; PATCH
esclarece texto sem alterar obrigações. A data de última alteração MUST refletir
a emenda mais recente.

**Version**: 1.0.0 | **Ratified**: 2026-09-11 | **Last Amended**: 2026-09-11
