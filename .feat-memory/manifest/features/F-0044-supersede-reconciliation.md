---
id: F-0044
name: supersede-reconciliation
status: shipped
introduced: 2026-07-08
version: 3.0.0
user_value: >
  Superseder um ADR deixa de ser um evento silencioso: todo artefato vivo que
  ainda cita o ADR antigo aparece no audit até ser revisado e reconhecido,
  convertendo a propagação de supersede de disciplina em checklist mecânico.
contracts:
  api:
    - src/feat_memory/governance/audit.py::validate_supersede_reconciliation
    - src/feat_memory/memory/schemas.py::validate_decision
  tests:
    - tests/test_supersede_reconciliation.py
acceptance:
  - {id: A1, pattern: event, trigger: "o audit roda num projeto onde um artefato vivo (feature ativa, ADR ativo, AGENTS.md ou UNRELEASED) cita o ID de um ADR superseded", response: "um warning por arquivo citador aparece no relatório, nomeando o ADR antigo e o(s) que o supersedem"}
  - {id: A2, pattern: event, trigger: "o path do citador é adicionado à lista reconciled do ADR que supersede", response: "o warning daquele arquivo desaparece do relatório"}
  - {id: A3, pattern: ubiquitous, requirement: "o ADR que supersede e o próprio arquivo do ADR antigo nunca geram warning de reconciliação"}
  - {id: A4, pattern: ubiquitous, requirement: "manifest/archive/, decisions/superseded/ e releases congelados nunca geram warning de reconciliação"}
  - {id: A5, pattern: unwanted, trigger: "reconciled contém um path que não existe no repositório", response: "warning de acknowledgment stale nomeando o path"}
  - {id: A6, pattern: unwanted, trigger: "reconciled não é uma lista de strings", response: "error de schema no ADR"}
depends_on: []
decisions: [ADR-0050]
---
