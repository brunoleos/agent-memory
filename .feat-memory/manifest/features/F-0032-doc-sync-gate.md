---
id: F-0032
name: doc-sync-gate
status: shipped
introduced: 2026-06-06
version: 1.1.0
user_value: >
  O pre-commit hook bloqueia commits que tocam código sem mover nenhum artefato
  de doc (.feat-memory/STATE.md, manifest/ ou decisions/), tornando o movimento
  conjunto documentação↔código uma garantia mecânica em vez de disciplina.
contracts:
  api:
    - src/feat_memory/governance/check_doc_sync.py::staged_block_reason
    - src/feat_memory/governance/check_doc_sync.py::run
  tests:
    - tests/test_check_doc_sync.py
  hooks:
    - src/feat_memory/governance/data/hooks/pre-commit
acceptance:
  - {id: A1, pattern: event, trigger: "o staging toca código sem nenhum artefato de doc (STATE/manifest/decisions) staged", response: "`check-doc-sync-staged` retorna exit 1 e o pre-commit bloqueia o commit, com remediação (/memory-debrief ou --no-verify)"}
  - {id: A2, pattern: event, trigger: "o staging toca código E inclui qualquer um de STATE.md, manifest/** ou decisions/**", response: "exit 0 — a doc acompanhou, commit liberado"}
  - {id: A3, pattern: ubiquitous, requirement: "tests/, docs/, .claude/, README e nomes não-código (heurística `_is_code_path`) não contam como código e nunca disparam o gate sozinhos"}
  - {id: A4, pattern: unwanted, trigger: "não há repositório Git", response: "fail-soft — não bloqueia (a fail-open de binário-ausente fica no hook, ADR-0008)"}
depends_on: []
decisions: [ADR-0037]
---

# F-0032 · doc-sync-gate

Gate hard que fecha a porta do drift no boundary de commit. Complementa — não
substitui — o aviso soft `check-staleness-staged` (F-0013, ADR-0016): o soft nudga
para o STATE, este garante que *algum* artefato de doc (STATE **ou** manifest **ou**
decisions) se moveu junto com o código. Reusa `_is_code_path` (audit) e `_staged_paths`
(check_staleness) para coerência de heurística. Segue o padrão de guard hard dentro de
hook fail-open já estabelecido por `check-version-bump-staged` (ADR-0020). O que ele
garante é **movimento conjunto** doc↔código no boundary de commit — integridade
referencial, não verdade semântica do conteúdo movido (ADR-0050).
