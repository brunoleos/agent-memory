---
id: F-0041
name: frontmatter-staleness-warning
status: shipped
introduced: 2026-06-30
version: 2.5.0
user_value: O deploy e o audit avisam quando o frontmatter do AGENTS.md (references/budgets) ficou stale — paths .agent-memory/ legados, chave state:, state_max_bytes, ou URL de methodology numa versão antiga — já que o deploy refresca o bloco mas nunca toca o frontmatter.
contracts:
  api: src/feat_memory/shared/frontmatter.py::detect_stale_frontmatter
  tests: tests/test_frontmatter_staleness.py
acceptance:
  - {id: A1, pattern: event, trigger: "deploy/deploy --dry-run encontra frontmatter com marcador legado", response: "emite ⚠ por achado instruindo correção manual; não altera o frontmatter"}
  - {id: A2, pattern: event, trigger: "audit roda com frontmatter stale", response: "emite warning por achado (artifact AGENTS.md), durável a cada commit via pre-commit"}
  - {id: A3, pattern: ubiquitous, requirement: "methodology sem tag de versão (ex.: path local ./METHODOLOGY.md) não vira falso-positivo"}
depends_on: [F-0040]
decisions: [ADR-0049]
---

Fecha do lado do consumidor o ponto-cego que recorreu da 2.2.x: o frontmatter é human-owned (o deploy não o reescreve, cf. ADR-0029), então paths/URLs legados passavam silenciosos. O detector é fonte única reusada por deploy e audit (ADR-0049, varredura mecânica em vez de revisão de cabeça).
