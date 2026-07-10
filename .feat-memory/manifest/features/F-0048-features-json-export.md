---
id: F-0048
name: features-json-export
status: shipped
introduced: 2026-07-10
version: 3.1.0
user_value: >
  Adapters (BDD ou qualquer outro) consomem o Manifest estruturado por um
  comando em vez de parsear markdown na mão: o contrato completo de cada
  feature, acceptance incluído, sai como JSON read-only.
contracts:
  api:
    - src/feat_memory/memory/export.py::run
    - src/feat_memory/memory/export.py::collect_features
  tests:
    - tests/test_features_export.py
acceptance:
  - {id: A1, pattern: event, trigger: "feat-memory features --json é executado", response: "stdout contém JSON válido com o frontmatter completo de cada feature ativa (acceptance incluído), path repo-relativo e flag archived; exit 0"}
  - {id: A2, pattern: optional, feature: "--all é fornecido", response: "as features do archive entram no dump, marcadas archived: true"}
  - {id: A3, pattern: unwanted, trigger: "o Manifest está vazio ou ausente", response: "JSON válido com lista vazia e exit 0"}
  - {id: A4, pattern: ubiquitous, requirement: "o comando nunca escreve em artefato algum"}
depends_on: []
decisions: [ADR-0052]
---
