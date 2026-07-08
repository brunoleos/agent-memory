# Índice de features arquivadas

Features `shipped` e não referenciadas no `changelog/UNRELEASED.md`, movidas
por `feat-memory archive --apply`. IDs continuam resolvíveis pelo
cross-check; mantenha aqui o registro histórico, sem onerar o INDEX
principal.

| ID | Nome | Status | Versão | ADRs | Depende |
|---|---|---|---|---|---|
| F-0001 | deploy | shipped | 0.3.0 | ADR-0006,ADR-0007,ADR-0011 | — |
| F-0002 | audit | shipped | 0.3.0 | ADR-0002,ADR-0003 | — |
| F-0003 | propose-adr | shipped | 0.3.0 | — | — |
| F-0004 | migrate | shipped | 0.3.0 | — | — |
| F-0005 | pre-commit-hook | shipped | 0.3.0 | ADR-0008 | F-0002 |
| F-0006 | skill-memory-deploy | shipped | 0.4.0 | ADR-0004,ADR-0010,ADR-0011 | F-0001,F-0004 |
| F-0007 | skill-memory-bootstrap | shipped | 0.5.0 | ADR-0004,ADR-0012 | — |
| F-0008 | skill-memory-debrief | shipped | 0.3.0 | ADR-0004 | F-0003 |
| F-0009 | skill-memory-pull-brief | shipped | 0.5.0 | ADR-0004,ADR-0012 | F-0002,F-0007 |
| F-0010 | version-meta | shipped | 0.6.0 | ADR-0013 | F-0001 |
| F-0011 | audit-state-crosscheck | shipped | 0.6.0 | ADR-0014 | F-0002 |
| F-0012 | archive-shipped | shipped | 0.6.0 | ADR-0015 | F-0002,F-0011 |
| F-0013 | hook-staleness-staged | shipped | 0.6.0 | ADR-0016 | F-0005,F-0011 |
| F-0014 | local-telemetry | shipped | 0.6.0 | ADR-0013,ADR-0017 | F-0010 |
| F-0015 | state-from-checkpoints | deprecated | 0.6.0 | ADR-0018,ADR-0019 | F-0008,F-0014 |
| F-0016 | check-version-bump | shipped | 0.6.0 | ADR-0020 | F-0005,F-0011 |
| F-0017 | memory-governance-split | shipped | 0.7.0 | ADR-0021 | F-0001,F-0002 |
| F-0018 | consumer-version-notice | shipped | 0.8.0 | ADR-0022 | F-0010,F-0017 |
| F-0019 | superseded-decisions-folder | shipped | 0.9.0 | ADR-0023 | F-0011 |
| F-0020 | audit-release-status | shipped | 0.10.0 | ADR-0024 | F-0011 |

_Gerado por `feat-memory audit` em 2026-07-08T18:18:59+00:00. Não edite manualmente._
