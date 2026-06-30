# Ideias — funil do futuro

O lar das **ideias cruas** ainda não triadas: capacidades de produto, decisões em
gestação, e evolução do próprio sistema de agentes. É o estágio cru do pipeline do
futuro (ADR-0047):

    ideia (aqui)  →  proposed (Feature/ADR)  →  in_progress / accepted  →  shipped

Commitado e compartilhado entre agentes — merge normal (acumula entradas de todos),
**não** `merge=ours`. Quando o `changelog/UNRELEASED.md` está vazio (nada em voo), a
`memory-bootstrap` oferece candidatos daqui como próximo foco.

## Triagem — para onde cada ideia vai quando amadurece

| Tipo de ideia | Destino |
|---|---|
| Capacidade nova do produto | Feature `proposed` em `manifest/features/` |
| Decisão de arquitetura do produto | ADR `proposed` em `decisions/proposals/` |
| Evolução do sistema de agentes (skill, regra, doc-gap) | aplica direto (vira skill/regra/ADR de metodologia) |
| Bug/tarefa pontual | seu issue tracker, se houver — **não** é o que este arquivo rastreia |

Disciplina anti-JIRA: itens curtos e **transitórios** — promova (para `proposed`) ou
descarte rápido; não acumule. Uma ideia promovida ou descartada **sai daqui**.

Formato por entrada (uma seção `##` por ideia):

    ## <id-kebab>
    - **tipo:** produto-capacidade | produto-decisao | sistema-agentes | doc-gap
    - **contexto:** 1–2 frases do que motivou
    - **occ:** ocorrências (bump silencioso em duplicata)

<!-- Entradas abaixo. Vazio = sem ideias pendentes. -->
