---
id: ADR-0050
date: 2026-07-08
status: accepted
version: 3.0.0
supersedes: null
superseded_by: null
affects_features: [F-0042, F-0043, F-0044, F-0045, F-0046]
related: [ADR-0022, ADR-0028, ADR-0037, ADR-0043, ADR-0047, ADR-0049, ADR-0051]
tags: [methodology, doctrine, profiles, manifest, audit, observability, governance, dogfooding]
---

# ADR-0050 · Reforma v3: doutrinas da ortogonalidade, perfis de deploy e manifest como registro

## Contexto

Uma auditoria conduzida por um agente frio num projeto consumidor real (tensegrams)
encontrou, na mesma sessão, **dois stales de memória com modos de falha distintos**:

1. **F-0002/A4 (consumidor)**: um critério de aceite enunciava o *mecanismo* de
   implementação ("atrator central + separação por collision layers") — vocabulário
   de ADR que vazou para o frontmatter estruturado. Quando o ADR do modelo foi
   superseded, o critério apodreceu junto, **sobreviveu a uma reconciliação que tocou
   o próprio arquivo** (modo "revisado-e-escapou") e contaminou uma sessão de agente
   frio com um axioma falso.
2. **README:191 (consumidor)**: a mesma afirmação velha sobrevivia numa duplicação
   em prosa que ninguém reconciliou (modo "prosa paralela").

O debate de 4 rodadas que se seguiu (auditoria → contra-perícia → tréplica → síntese)
convergiu num diagnóstico que nenhum dos lados tinha sozinho e numa agenda de reforma.
Este ADR é o guarda-chuva da reforma; o postmortem da migração destrutiva é ADR-0051.

## Decisão

### Doutrinas (entram na METHODOLOGY como normas)

- **Memória errada é pior que memória nenhuma.** O objetivo do sistema não é ter
  memória; é ter memória que não mente.
- **Memória paralela ao repo drifta; memória ortogonal não consegue driftar.**
  Artefato que *reafirma* o que código/README já mostram é paralelo — corta. Artefato
  que registra o que o código não pode expressar (IDs, status, porquês, rejeições,
  trabalho em voo) é ortogonal — fica.
- **Doutrina do observável (delimitada).** Critérios de aceite só enunciam
  observáveis externos; mecanismo é território exclusivo de ADR. Quando o "como" é
  identidade do produto, ele sobe à constituição como constraint e desce aos
  critérios apenas como observáveis de trajetória — nunca nomes de algoritmo.
  (Critérios só de estado final são tautológicos e não discriminam.)
- **Disciplina de procedência de evidência.** Todo item de reforma nomeia a
  evidência exata que o prova; um incidente não pode ser alistado como prova de
  itens que ele não prova.

### Mudanças mecânicas

- **Manifest rebaixado de documento a registro ortogonal**: features
  frontmatter-only (id, status, aceites observáveis, ponteiros); corpo em prosa gera
  warning acima do orçamento do perfil (core: 10 linhas não-vazias; full: 40).
- **Perfis de deploy**: `--profile core|full`, default `core` para adoções novas
  (constituição + decisions + UNRELEASED + features finas). `full` adiciona changelog
  completo e orçamento de prosa maior. Perfil gravado em `.meta.yaml`
  (schema_version 2); audit resolve com fallback `full` (instalações pré-v3 não
  ganham warnings novos). Re-deploy preserva o perfil existente.
- **Audit reenquadrado**: o que ele garante é integridade referencial e movimento
  conjunto — não verdade semântica. As mensagens passam a dizer exatamente isso.
- **Propagação de supersede**: ADR superseded gera obrigação de reconciliação por
  arquivo citador vivo; acknowledgment via campo `reconciled: [paths]` no ADR que
  supersede. Referencial (match textual), nunca semântico.
- **Amostragem adversarial** (`feat-memory sample`): prompts de *refutação* de
  critérios, sorteio ponderado por risco (ADRs citados superseded/alterados),
  gatilho por evento (supersede/release). É a camada que cobre o modo
  "revisado-e-escapou" — o único que mecanismo determinístico não cobre.
- **Nudge de léxico de mecanismo**: termos salientes derivados dos próprios ADRs em
  tempo de audit, emitidos como severidade `info` (nunca promovida por `--strict`)
  quando aparecem em texto de critério. Ortogonal por construção: computado da
  memória existente, sem artefato novo.
- **Disciplina de upgrade**: consumer notice só em diferença de MAJOR ("upgrade
  quando doer"), amortecendo o nudge do ADR-0022.
- **Teste do agente frio**: pergunta final de todo debrief — "um agente frio
  responderia 'por que não X?' só com a memória?".

## Procedência de evidência

| Item | Evidência que o prova |
|---|---|
| Doutrina do observável | Incidente F-0002/A4 do tensegrams (mecanismo em critério apodreceu com o mecanismo; sobreviveu a revisão) |
| Doutrina da ortogonalidade + gênese sem prosa | Stale de README:191 do tensegrams (prosa paralela driftou sem reconciliação) |
| Amostragem adversarial | Modo "revisado-e-escapou" do A4 — nenhum checker determinístico o cobre |
| Propagação de supersede | **Não** é provada pelo incidente (que era revisado-e-escapou); justificada por plausibilidade e custo baixo para o modo comum "nunca-revisitado" |
| Perfis de deploy | Assimetria de valor observada no consumidor: ADRs+UNRELEASED alto valor; manifest com prosa e changelog sem cadência, custo sem retorno |
| Disciplina de upgrade + ADR-0051 | 5 upgrades em 3 semanas no consumidor; migração 2.x destruiu um UNRELEASED |
| Reenquadramento do audit | O gate passou com o A4 driftado — a promessa "doc sempre sincronizada" era overclaiming |
| Arbitragem do próprio debate | Sustenta apenas "IDs estáveis + ADRs versionados viabilizam arbitragem" — argumento pelo perfil core, não pelo stack completo (escopo estreitado deliberadamente) |

## Falsificação pré-registrada — a condicional do manifest

Estudo de caso com condição de falsificação pré-registrada (não é experimento
comparativo; n=1 consumidor).

- **Condenação do conceito**: se, com gênese reformada e doutrina do observável em
  vigor, um agente frio absorver contaminação **originada de** um registro de
  feature fino (frontmatter-only, critérios observáveis, ponteiros), o conceito de
  manifest perde o álibi e o perfil `core` reavalia até a exclusão do manifest.
- **Absolvição**: 10 sessões de agente frio OU 3 ciclos de amostragem adversarial
  sem contaminação originada de feature ⇒ o conceito sai da condicional e a
  discussão encerra.
- **Julgamento**: relato do incidente pelo agente consumidor + verificação contra os
  artefatos versionados, com atribuição registrada; atribuição disputada vira rodada
  de arbitragem como a que originou esta reforma.

## Alternativas rejeitadas

- **Deletar o manifest**: o orçamento de retomada (ADR-0043) depende dos IDs
  resolverem; o ledger de status é o registro anti-relitigação; o grafo
  aceite→teste→ADR é o valor único reconhecido pelos dois lados do debate.
- **Emagrecer só a prosa** (reforma original proposta pela auditoria): não teria
  evitado o próprio incidente — o A4 vivia no frontmatter estruturado.
- **Gate semântico de drift** (mapa de "frases-assinatura" por ADR): memória
  paralela vigiando outra; mesma categoria que o incidente condena. Substituído
  pela dupla propagação-referencial + amostragem-adversarial.
- **Checker de constraint para o léxico**: o conjunto de checkers é fechado
  (ADR-0028); o nudge é indicador de audit com severidade própria, não constraint.
