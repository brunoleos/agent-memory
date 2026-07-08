---
id: F-0046
name: mechanism-lexicon-nudge
status: shipped
introduced: 2026-07-08
version: 3.0.0
user_value: >
  Vocabulário de mecanismo vazando para critérios de aceite — a causa-raiz do
  incidente que motivou a doutrina do observável — fica visível no audit como
  nudge informativo, derivado dos próprios ADRs, sem nunca bloquear commit.
contracts:
  api:
    - src/feat_memory/governance/lexicon.py::extract_mechanism_lexicon
    - src/feat_memory/governance/lexicon.py::check_mechanism_lexicon
  tests:
    - tests/test_lexicon.py
acceptance:
  - {id: A1, pattern: event, trigger: "um token das tags de um ADR (ou dos títulos de dois ou mais ADRs) aparece em texto de critério EARS de feature ativa", response: "um issue de severidade info nomeando o termo, o critério e os ADRs de origem aparece no resultado do audit"}
  - {id: A2, pattern: ubiquitous, requirement: "issues do nudge nunca alteram o exit code do audit, mesmo sob --strict"}
  - {id: A3, pattern: state, state: "o termo também aparece no AGENTS.md ou no name/user_value da própria feature", response: "nenhum issue é emitido para aquele termo (vocabulário sancionado)"}
  - {id: A4, pattern: ubiquitous, requirement: "no máximo um issue por par (feature, termo) por execução"}
  - {id: A5, pattern: ubiquitous, requirement: "o relatório humano resume os infos numa única linha; o detalhe completo sai no audit --json"}
depends_on: []
decisions: [ADR-0050]
---
