---
schema_version: 2
project: nome-do-projeto
stack:
  language: python>=3.10
  architecture: hexagonal
  primary_db: postgres
constraints:
  - id: C1
    severity: hard
    rule: "Pydantic obrigatório para schemas de borda"
  - id: C2
    severity: hard
    rule: "Nenhuma PII em logs externos"
  - id: C3
    severity: soft
    rule: "Docstrings obrigatórias em funções públicas"
references:
  manifest_index: ./.feat-memory/manifest/INDEX.md
  unreleased: ./.feat-memory/changelog/UNRELEASED.md
  decisions_index: ./.feat-memory/decisions/INDEX.md
  methodology: https://github.com/brunoleos/feat-memory/blob/v{VERSION}/METHODOLOGY.md
  skills: ./skills/
budgets:
  resumption_max_bytes: 12288
---

# Constituição do projeto

<!-- Espaço para seções específicas do projeto, escritas pelo mantenedor
humano se e quando achar útil: ## Identidade, ## Restrições não-negociáveis,
## Convenções de código, etc. O feat-memory nunca escreve essas seções —
adicione-as e mantenha-as fora do bloco delimitado abaixo. -->

<!-- >>> feat-memory >>> -->
## feat-memory

Sessões começam por `.feat-memory/changelog/UNRELEASED.md` (trabalho em voo) e `.feat-memory/manifest/INDEX.md` (mapa de capacidades). Detalhes de uma feature ficam em `.feat-memory/manifest/features/F-NNNN-*.md`. Decisões arquiteturais em `.feat-memory/decisions/`. O histórico de releases vive em `.feat-memory/changelog/<tag>.md`. A metodologia completa está documentada no repositório do feat-memory: <https://github.com/brunoleos/feat-memory/blob/v{VERSION}/METHODOLOGY.md>.

Doutrina do observável: critérios de aceite enunciam observáveis externos, nunca mecanismo (mecanismo é território de ADR); quando o "como" é identidade do produto, ele vive aqui na constituição como constraint, e desce aos critérios só como observáveis de trajetória. Features são registros ortogonais — frontmatter com aceites e ponteiros; prosa que reafirma outra fonte drifta.

Este bloco é refrescado a cada `feat-memory deploy`. Não edite diretamente — mudanças aqui são sobrescritas no próximo redeploy. Conteúdo específico do projeto vai fora das marcações HTML que delimitam este bloco.

### Skills disponíveis

As skills em `skills/` orientam os fluxos críticos. Leia o `SKILL.md` de cada uma antes de executá-la — o frontmatter traz os triggers de ativação e as instruções autoritativas (fonte única; não duplicadas aqui). Roster (gerado dos `summary` das skills a cada deploy):

{SKILLS_ROSTER}

### Como retomar trabalho

A constituição é carregada automaticamente. Em seguida, você deve carregar `.feat-memory/changelog/UNRELEASED.md` para descobrir o trabalho em voo. O conjunto ativo de features e ADRs é **derivado** das referências `F-NNNN`/`ADR-NNNN` nas entradas-bullet do UNRELEASED (ADR-0043) — apenas esses precisam ser expandidos no contexto inicial; carregar o Manifest inteiro ou todos os ADRs viola o orçamento de retomada. UNRELEASED vazio = nada em voo (veja o último release em `changelog/INDEX.md`).
<!-- <<< feat-memory <<< -->
