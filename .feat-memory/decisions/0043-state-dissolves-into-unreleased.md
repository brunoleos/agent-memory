---
id: ADR-0043
date: 2026-06-26
status: accepted
version: 2.0.0
supersedes: [ADR-0018, ADR-0019]
superseded_by: null
reconciled: [.feat-memory/decisions/0041-no-persistent-specs.md]
affects_features: [F-0036, F-0037]
related: [ADR-0018, ADR-0019, ADR-0016]
tags: [state, changelog, unreleased, resumption, methodology]
---

# ADR-0043 · STATE dissolve em changelog/UNRELEASED.md; retomada derivada

## Contexto

O event-sourcing de checkpoints (ADR-0018/0019) falhou na prática: parou em v0.11.0, os corpos ficaram vazios, o `STATE.md` virou hand-maintained por 14 releases, e rodar `checkpoint`/`state-rebuild` clobbera o STATE curado. A causa-raiz é o STATE conflar duas naturezas opostas: foco-atual (volátil) e história (append-only).

## Decisão

`STATE.md` sai. O "em-voo" vira **`changelog/UNRELEASED.md`** — entradas Keep-a-Changelog onde cada bullet referencia as `F`/`ADR` que toca. O **orçamento de retomada é 100% derivado** dessas referências (sem lista `active_*` hand-maintained — era exatamente a que stale-ava); o "Next" é derivado (fechar o unreleased; vazio → backlog da Fase 2). Aposenta `checkpoints/` e os comandos `checkpoint`/`state-rebuild`. **Ao ser aceito, este ADR supersede ADR-0018 e ADR-0019 (total) e parcialmente o ADR-0016** (o gate de frescor STATE-específico morre; o conceito pode re-homar no UNRELEASED) — caso de uso da regra ADR-0040. A preocupação válida do 0018 ("não perder nuance ao reescrever") é re-homada no git + nos arquivos imutáveis de changelog.

## Alternativas rejeitadas

- **Blindar o event-sourcing** (gate de drift + backfill): dobra a cerimônia empiricamente abandonada; conserta sintoma, não causa.
- **Manter STATE hand-edited sem detecção:** é o status quo que apodreceu.
- **Lista `active_*` explícita no UNRELEASED:** é a listinha hand-maintained que stale-ava; derivar das refs a elimina.
