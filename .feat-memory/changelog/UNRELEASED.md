---
schema_version: 1
---

# Não-lançado

Trabalho concluído mas ainda não tagueado. Cada entrada referencia as
features e decisões que toca (`F-NNNN` / `ADR-NNNN`); o orçamento de
retomada é derivado dessas referências. Vazio = nada em voo.

## Adicionado

- ADR guarda-chuva da reforma v3 — doutrinas, procedência de evidência e falsificação pré-registrada da condicional do manifest (ADR-0050)
- Postmortem da migração de changelog 2.x que destruiu um UNRELEASED de consumidor; regra de backup + teste de preservação (ADR-0051)
- Seção "Doutrinas" na METHODOLOGY: memória-errada, ortogonalidade, observável, procedência (ADR-0050)
- Perfis de deploy `--profile core|full`; core default em instalação nova, re-deploy preserva perfil, meta schema v2 (F-0042, ADR-0050)
- Orçamento de prosa no corpo de features por perfil (core 10 / full 40 linhas não-vazias), warning do audit; archive isento (F-0043, ADR-0050)
- Propagação de supersede: citadores vivos de ADR superseded geram warning até acknowledgment por arquivo via `reconciled:` do superseder (F-0044, ADR-0050)
- Nudge de léxico de mecanismo em critérios EARS, derivado dos ADRs, severidade info nunca promovida; report resume infos numa linha (F-0046, ADR-0050)
- `feat-memory sample`: prompts de refutação adversarial ponderados por risco, gatilho por evento, sempre exit 0 (F-0045, ADR-0050)
- Skills reformadas: gênese gera features frontmatter-only sem transcrever README; doutrina do observável na deploy/debrief; propagação de supersede e sample como rituais; teste do agente frio fecha todo debrief (ADR-0050)
- Docs alinhadas à v3: METHODOLOGY (perfis, amostragem adversarial, reconciled, orçamento de prosa), README e USER_GUIDE atualizados do modelo STATE.md pré-2.0 para o changelog vivo — prosa paralela corrigida (ADR-0050, ADR-0051)

## Mudado

- Audit reenquadrado: report e crosscheck declaram integridade referencial e movimento conjunto, não verdade semântica; severidade `info` nova, nunca promovida por `--strict` (ADR-0050)
- Consumer version notice só em diferença de MAJOR, com linguagem "upgrade quando doer" (ADR-0050, ADR-0051)
- Testes de preservação de conteúdo para freeze/scaffold do changelog (ADR-0051)

## Corrigido
