---
id: ADR-0051
date: 2026-07-08
status: accepted
version: 3.0.0
supersedes: null
superseded_by: null
affects_features: []
related: [ADR-0042, ADR-0043, ADR-0049, ADR-0050]
tags: [postmortem, migration, changelog, data-loss, upgrade, governance]
---

# ADR-0051 · Postmortem: migração de changelog 2.x destruiu um UNRELEASED — migração destrutiva exige backup e teste de preservação

## Contexto

Durante a adoção da série 2.x num projeto consumidor (tensegrams), a migração de
layout do changelog (introduzida na 1.9.0, cutover na 2.0.0, removida na 2.3.0 —
F-0037) **perdeu o conteúdo do `changelog/UNRELEASED.md`** do consumidor, que
precisou ser reconstruído manualmente a partir do git log.

Causa técnica: a migração era **write-through destrutiva** — removia os artefatos
legados (`CHANGELOG.md`, `STATE.md`, `checkpoints/`) e semeava um `UNRELEASED.md`
novo, sem backup do estado anterior e sem teste que garantisse a preservação de
conteúdo de ponta a ponta. Fatores agravantes: `UNRELEASED.md` é `merge=ours` (perda
não aparece como conflito) e `deploy_changelog` pula o arquivo quando já existe (a
recriação pós-perda parecia "sucesso"). A causa-raiz de método é irmã da do
ADR-0049: mudanças estruturais raciocinadas em vez de verificadas mecanicamente.

Para uma ferramenta cujo produto é **confiança na memória**, perder memória do
consumidor num upgrade é o equivalente a um banco perder um depósito — default da
própria tese.

## Decisão

1. **Toda migração destrutiva de artefato de memória exige backup prévio** do
   conteúdo tocado (cópia `.bak` no próprio diretório ou preservação integral no
   arquivo destino) — o conteúdo do usuário nunca é o custo da conveniência da tool.
2. **Toda migração exige teste de preservação de conteúdo**: dado um artefato
   populado, o pipeline (migração, freeze, re-deploy) deve provar que cada linha de
   conteúdo do usuário sobrevive em algum artefato resultante.
3. **Disciplina de upgrade** (implementada junto ao ADR-0050): o consumer notice
   passa a soar apenas em diferença de MAJOR, com linguagem "upgrade quando doer" —
   a tool para de induzir a cadência de upgrade que multiplicou a exposição a este
   bug (5 upgrades em 3 semanas no consumidor).

## Alternativas rejeitadas

- **"Migração testada já basta"**: os testes da época cobriam o caminho feliz do
  layout, não a preservação de conteúdo; a classe de bug só apareceu no dogfood do
  cliente. Preservação precisa ser asserção explícita, não consequência esperada.
- **Nunca mais migrar automaticamente**: inviabiliza evolução de layout; o remédio é
  backup + prova, não paralisia.
