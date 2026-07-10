---
id: ADR-0052
date: 2026-07-10
status: accepted
version: 3.1.0
supersedes: null
superseded_by: null
affects_features: [F-0047, F-0048, F-0049]
related: [ADR-0041, ADR-0044, ADR-0047, ADR-0050]
tags: [positioning, manifest, microspec, bdd, prospection, sdd, methodology]
---

# ADR-0052 · Microspec: contrato observável bidirecional — sem workflow, com tomadas BDD

## Contexto

A reforma v3 (ADR-0050) rebaixou a feature de documento a registro e endureceu os
critérios (observáveis, EARS validado). Isso deixou o Manifest funcionalmente
próximo de uma camada de especificação — e levantou três perguntas de identidade:
viramos um SDD kit? somos um "BDD agêntico"? a microspec é só registro do feito,
ou também prospecção do que virá? A frase "descritivo, não aspiracional" da
METHODOLOGY (anterior ao `proposed` unificado do ADR-0047) contradizia o próprio
schema. Este ADR fecha o conceito.

## Decisão

**A microspec é um contrato observável por capacidade — nunca um driver de
workflow.** Ela nasce **bottom-up** (destilada no debrief do trabalho feito) ou
**top-down** (prospectada do funil como feature `proposed` com EARS completos,
antes de qualquer código). Nos dois casos é o mesmo artefato e a mesma
disciplina: observáveis externos, sem mecanismo (ADR), sem porquê (ADR), sem
plano (efêmero, ADR-0041). A doutrina do observável é o que torna a prospecção
segura: critério livre de mecanismo escrito cedo é promessa testável, não design
prematuro cristalizado.

Decisões operacionais:

1. **Prospecção por split** (não por marcador): promessa nova sobre capacidade
   existente vira feature `proposed` própria com `depends_on` — zero schema
   novo; a invariante anti-mentira fica estrutural (critério em feature
   `in_progress`/`shipped` é sempre afirmação viva, refutável pelo sample).
2. **Anti-apodrecimento de `proposed`**: feature `proposed` sem referência em
   UNRELEASED/`ideas.md` por 90+ dias gera issue `info` — nudge de higiene,
   nunca gate (ADR-0024). Prospecção sem relógio viraria backlog JIRA-ificado.
3. **Relação com BDD, com escopo exato**: o Manifest opera como um "BDD
   agnóstico de linguagem" onde o agente substitui o glue code (step
   definitions) e a amostragem adversarial substitui o CI — **sem herdar a
   garantia determinística** (BDD roda 100% dos cenários por build; nós
   refutamos amostra ponderada por evento) **nem o workflow** outside-in.
   EARS enuncia regras; concretude de exemplos é território Gherkin — quem tem
   `.feature` aponta via `contracts.tests`, nunca copia (ortogonalidade).
4. **Adapter-readiness, dois degraus**: (a) export estruturado
   (`feat-memory features --json`) para qualquer adapter consumir sem parsear
   markdown; (b) binding referencial por critério — teste que cita o token
   `F-NNNN-AN` conta como cobertura daquele critério (grep, agnóstico,
   sem execução), evoluindo o `manifest_coverage` de arquivo para critério.
5. **Fronteira dura**: o feat-memory termina onde a microspec termina. Não gera
   plano, não decompõe tasks, não implementa a partir da spec, não executa
   testes, não gera step definitions — plan/task são competência do harness
   (que os faz bem) e execução é competência do toolchain do consumidor.

## Procedência de evidência

- Desenvolvimento contra microspecs funcionou em n=1 nas condições mais
  amigáveis (repo da própria tool, agente-autor, design pré-decidido em debate;
  sessão v3): evidência fraca-porém-real de viabilidade, não de generalidade.
- Limites observados na mesma sessão: microspec opera na granularidade de
  capacidade — a reforma v3 inteira não coube em nenhuma spec, coube num plano
  efêmero (o nível que os SDD kits cobrem e nós deliberadamente não).
- A contradição "descritivo, não aspiracional" × `status: proposed` é textual e
  verificável (METHODOLOGY §Manifest vs ADR-0047).

## Alternativas rejeitadas

- **`pending: true` por critério**: granularidade fina ao custo de schema novo
  + estado a policiar; adiado (não rejeitado) — promove-se se o split brigar
  com a granularidade na prática.
- **Camada de execução BDD no core**: exige glue por linguagem/framework —
  contra C1/C2 e os precedentes de rejeição (pytest-cov, feature flags); o elo
  faltante é binding, não execução (que já existe no toolchain do consumidor).
- **Adotar Gherkin como notação**: EARS (regras) e Gherkin (exemplos) são
  camadas complementares; trocar a notação perderia os patterns validáveis sem
  ganhar a executabilidade (que depende de glue, não de sintaxe).
- **Campo `examples:` por critério e adapter de referência**: adiados para o
  funil — só com demanda validada / consumidor BDD real.
- **Identidade "operacionalização agêntica do BDD"**: infla (reivindica a
  garantia mecânica que trocamos por portabilidade) e enxuga (amputa
  constitution, decisions e changelog — os eixos de valor comprovado).
