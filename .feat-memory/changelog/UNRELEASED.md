---
schema_version: 1
---

# Não-lançado

Trabalho concluído mas ainda não tagueado. Cada entrada referencia as
features e decisões que toca (`F-NNNN` / `ADR-NNNN`); o orçamento de
retomada é derivado dessas referências. Vazio = nada em voo.

## Adicionado

- ADR de posicionamento da microspec: contrato observável bidirecional (registro e prospecção), sem workflow, com tomadas BDD (ADR-0052)
- Anti-apodrecimento de prospecção: proposed >90d sem referência em UNRELEASED/ideas gera nudge info (F-0047, ADR-0052)
- `feat-memory features --json`: export estruturado do Manifest para adapters, read-only (F-0048, ADR-0052)

## Mudado

- METHODOLOGY §Manifest: "descritivo, não aspiracional" corrigido para o modelo bidirecional — prospecção legítima via feature `proposed` com split (ADR-0052)

## Corrigido
