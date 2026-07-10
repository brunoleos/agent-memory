---
id: F-0047
name: proposed-staleness-nudge
status: shipped
introduced: 2026-07-10
version: 3.1.0
user_value: >
  Prospecção ganha relógio: features proposed esquecidas ficam visíveis no
  audit como nudge informativo, impedindo que o Manifest acumule backlog
  aspiracional que ninguém promove nem descarta.
contracts:
  api:
    - src/feat_memory/governance/audit.py::validate_proposed_staleness
  tests:
    - tests/test_proposed_staleness.py
acceptance:
  - {id: A1, pattern: event, trigger: "o audit roda num projeto com feature proposed cujo último commit tem mais de 90 dias e cujo ID não aparece no UNRELEASED nem no ideas.md", response: "um issue de severidade info nomeando o arquivo e a idade aparece no resultado, sugerindo promover, reescopar ou descartar"}
  - {id: A2, pattern: state, state: "o ID da feature proposed é citado numa entrada-bullet do UNRELEASED ou no texto do ideas.md", response: "nenhum issue de apodrecimento é emitido para ela"}
  - {id: A3, pattern: ubiquitous, requirement: "features in_progress, shipped e deprecated nunca recebem o nudge de apodrecimento de prospecção"}
  - {id: A4, pattern: unwanted, trigger: "a feature proposed nunca foi commitada (idade desconhecida)", response: "nenhum issue é emitido (fail-soft)"}
depends_on: []
decisions: [ADR-0052]
---
