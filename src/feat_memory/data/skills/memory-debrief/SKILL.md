---
name: memory-debrief
summary: "fechar/commitar uma sessão: mover Manifest e changelog/UNRELEASED.md junto com o código, propor ADR a partir do diff e fechar com o teste do agente frio. A mais usada no dia-a-dia."
description: Use quando o usuário sinaliza intenção de commitar, fechar sessão, ou pedir atualização da memória do projeto (frases como "vou commitar", "atualize a memória", "feche a sessão", "debrief", "antes de subir"). Examina o diff, atualiza entradas do Manifest, registra o trabalho no changelog/UNRELEASED.md, e gera proposta de ADR se a sessão produziu decisão arquitetural.
---

# Memory debrief

Quando o usuário sinaliza fim de uma unidade de trabalho — antes de commitar, ao encerrar sessão, ou ao pedir "atualize a memória" / "feche a sessão" / "vou commitar" — execute esta rotina.

Aplica-se proativamente quando você terminou uma unidade coerente (feature, refactor, fix não-trivial) e o usuário ainda não pediu. Nesse caso, sugira antes de propor commit.

## Princípio de concisão

A memória existe para que o próximo agente entenda **o que o projeto faz** e **por que decisões foram tomadas** — não para servir de auditor exaustivo. Cada palavra extra aumenta o custo de recall sem retorno proporcional. **Bias agressivo para brevidade.**

Alvos por artefato:

| Artefato         | Alvo      | Conteúdo                                                |
|------------------|-----------|---------------------------------------------------------|
| Entrada UNRELEASED | ≤ 1 linha | resumo curto, referenciando as F/ADR que toca           |
| Feature F-*      | ≤ 1.5 KB  | `user_value` em 1 frase, 3–4 critérios EARS de 1 linha; corpo dentro do orçamento de prosa do audit (ADR-0050) |
| ADR              | ≤ 1.5 KB  | contexto + decisão + alternativas rejeitadas, todos curtos |

Se passou do alvo, corte. Detalhes mecânicos já vivem no código e na mensagem do commit — não duplique.

## Procedimento

### 1. Examine o que mudou

`git status` + `git diff --staged` (ou `HEAD`). Identifique arquivos tocados, features impactadas (cruze com `.feat-memory/manifest/features/F-*.md::contracts`), e se houve mudança observável de comportamento.

### 2. Atualize features tocadas

Para cada feature cujo código foi tocado:
- `status` se transitou (`proposed` → `in_progress` → `shipped` → `deprecated`)
- `version` se a release mudou
- `acceptance` apenas se o comportamento mudou (ajuste o critério existente; não duplique). Critérios enunciam **observáveis externos, nunca mecanismo** — "usa algoritmo X" é vocabulário de ADR e apodrece quando o mecanismo muda (doutrina do observável, ADR-0050); quando a *maneira* é identidade do produto, ela vira constraint constitucional e o critério vira observável de trajetória
- `metrics` apenas com medição real desta sessão; sem número, sem campo

Se há capacidade nova sem entrada no Manifest, crie uma — formato em "Feature mínima" abaixo. ID = próximo número livre em `manifest/features/`.

### 3. Registre o trabalho no UNRELEASED

O foco em-voo vive em `.feat-memory/changelog/UNRELEASED.md` (ADR-0043) — não há mais `STATE.md` nem comando de checkpoint. Adicione uma **entrada-bullet** sob a seção apropriada (`Adicionado`/`Mudado`/`Corrigido`), **referenciando** as `F-NNNN`/`ADR-NNNN` que a sessão tocou:

```markdown
## Adicionado

- resumo curto do que esta sessão entregou (F-NNNN, ADR-NNNN)
```

O orçamento de retomada da próxima sessão é **derivado** dessas referências (ADR-0043) — por isso toda entrada cita as F/ADR que toca. O arquivo é volátil: edite direto, sem cerimônia.

Ao lançar uma versão, `feat-memory release` congela o `UNRELEASED.md` em `changelog/<VERSION>.md`, commita e cria a tag `v<VERSION>` (ADR-0042/0045). O bump de `VERSION` continua per-commit; o `UNRELEASED` reinicia vazio. Release é gatilho de amostragem adversarial: rode `feat-memory sample --event release` e execute os prompts de refutação (ADR-0050) — é a camada que verifica a *verdade semântica* dos critérios, que o audit (referencial) não cobre.

### 4. Decida sobre ADR

Critério: se um contribuidor lendo o commit em 6 meses precisaria de explicação para entender a escolha, é ADR. Se cabe na mensagem do commit, não é. Nunca para refactor mecânico, rename, ou fix óbvio.

`feat-memory propose-adr --staged` gera draft em `.feat-memory/decisions/proposals/`. Preencha em três seções curtas (formato em "ADR mínimo" abaixo). Mova para `decisions/` só após revisão humana; atualize `affects_features`.

**Superseding um ADR existente.** Quando esta sessão marca um ADR com `status: superseded` (e adiciona `superseded_by` apontando para o novo), mova o arquivo para `.feat-memory/decisions/superseded/` via `git mv` (ADR-0023, F-0019). IDs continuam resolvíveis pelo crosscheck e citáveis por `superseded_by` em ADRs novos; o move desonera o INDEX principal. Sem subcomando — operação manual.

**Propagação do supersede (ADR-0050, F-0044).** Superseder não é evento silencioso: o próximo `feat-memory audit` lista todo artefato vivo que ainda cita o ADR antigo. Para cada citador, **revise o conteúdo** (a citação continua verdadeira sob a decisão nova?) e então: atualize a citação, ou registre o path em `reconciled:` do ADR que supersede (acknowledgment de citação histórica legítima). Nunca reconheça sem revisar — o checklist prova que a revisão aconteceu, não a substitui. Feche o ciclo rodando `feat-memory sample --event supersede`: os prompts de refutação cobrem o que o checklist referencial não cobre (critérios que citam o ADR *novo* mas mantêm semântica velha).

**Supersede parcial (ADR-0040).** Se a decisão nova invalida só **parte** de um ADR, não deixe o base meio-válido (parte obsoleta + parte vigente no mesmo arquivo é ambíguo). Marque o base **inteiro** como `superseded` e divida em ADRs novos: um com a decisão nova, outro(s) re-afirmando a parte que continua válida. O `superseded_by` do base lista **todos** os sucessores. Assim todo ADR vigente é verdadeiro por inteiro.

### 5. Valide

`feat-memory audit --strict --no-index`. Drift = caminho em `contracts` virou inválido ou arquivo removido sem deprecar a feature.

Em branch destinada a merge em `main`: `feat-memory audit --check-collisions origin/main`. Em colisão de ID, renumere o local (renomear arquivo + atualizar `id` no frontmatter + referências cruzadas). ADRs já mesclados na destino nunca renumeram.

### 6. Apresente o resumo

Antes de commitar: features atualizadas (IDs), a entrada registrada no `changelog/UNRELEASED.md`, status do ADR, resultado do audit.

### 7. Telemetria

```bash
feat-memory record debrief_run features=F-NNNN[,F-NNNN]
```

Local-only, falha não bloqueia (F-0014, ADR-0017).

### 8. Retrospectiva e triagem de ideias (ADR-0047, ADR-0048)

Feche com uma **retrospectiva inline** — não persista a narrativa, só reflita na conversa: o que foi entregue (escopo + magnitude), bugs diagnosticados, achados (arquiteturais/processuais) e um **resumo honesto** (o que funcionou, o que custou mais do que devia, qual o risco residual).

Se a sessão produziu **ideias para o futuro** (uma capacidade, uma decisão a tomar, uma melhoria do sistema de agentes), aplique **ask-before-register** e **trie** pelo tipo:

| Tipo de ideia | Destino |
|---|---|
| Capacidade nova do produto | Feature `proposed` em `manifest/features/` |
| Decisão de arquitetura | ADR `proposed` em `decisions/proposals/` |
| Evolução do sistema de agentes (skill/regra/doc-gap) | aplica direto, ou registra em `.feat-memory/ideas.md` |
| Ainda cru / indeciso | `.feat-memory/ideas.md` (funil do futuro) até amadurecer |

Pergunte ao usuário **resolver agora** / **adiar** (entra no `ideas.md`) / **descartar** — nunca persista silenciosamente; duplicata de uma ideia já listada é só um bump de `occ`. **Na dúvida sobre o tipo, devolva a bifurcação ao usuário em vez de decidir sozinho.** O `ideas.md` é o estágio cru do pipeline (ideia → `proposed` → realizando → realizado) e o fallback de retomada quando o `UNRELEASED` está vazio.

### 9. Teste do agente frio — a pergunta final de todo debrief

Antes de encerrar, responda honestamente: **"um agente frio, chegando amanhã só com a memória, responderia 'por que não X?' para as alternativas que esta sessão rejeitou?"** A pergunta não é "documentei?" — é se a memória previne a re-litigação. Se a resposta é não, o que falta é quase sempre um ADR curto com a alternativa rejeitada e o motivo (a seção mais valiosa de um ADR). Registre agora, enquanto o porquê está fresco — é exatamente o conteúdo que nenhuma outra fonte (código, git, README) consegue expressar (ADR-0050).

## Feature mínima

```yaml
---
id: F-NNNN
name: kebab-slug
status: in_progress
introduced: YYYY-MM-DD
version: X.Y.Z
user_value: Uma frase do que o usuário/agente ganha. Sem prosa de justificativa.
contracts:
  api: src/.../modulo.py::funcao_principal
  tests: tests/test_modulo.py
acceptance:
  - {id: A1, pattern: event, trigger: "comando X é invocado", response: "faz Y e devolve Z"}
  - {id: A2, pattern: ubiquitous, requirement: "invariante curta"}
depends_on: [F-NNNN]
decisions: [ADR-NNNN]
---
```

Sem corpo, a menos que registre algo que a frontmatter não comporta (trade-off não óbvio, link a issue externa). **Não duplique `user_value` numa seção "Comportamento" no body.** O audit avisa quando o corpo excede o orçamento do perfil (core: 10 linhas não-vazias; full: 40) — a feature é registro ortogonal, não documento (ADR-0050).

Mantenha ≤ 4 critérios. Se está escrevendo `response: >` com 3 linhas YAML, ou condense para 1 linha, ou quebre em dois critérios menores. Se precisa enumerar todo caso de erro, está auditando — não documentando recall.

**Critérios enunciam observáveis externos — mecanismo é território de ADR.** "Retorna sem sobreposição após estabilizar" é observável; "usa atrator central" é mecanismo e apodrece quando o mecanismo muda. Maneira que é identidade do produto vira constraint constitucional + observáveis de trajetória nos critérios (nunca nomes de algoritmo). O audit emite nudge `info` quando vocabulário de ADR aparece em critério (F-0046).

### Teste de uma capacidade (aplique ANTES de gravar qualquer feature)

O Manifest é por **capacidade**, não por lote de release. Antes de escrever uma feature, passe-a por estes quatro filtros — se falhar em qualquer um, **divida em features reais ou deixe de fora**:

1. **Uma frase, sem "e"/";" juntando assuntos.** Consegue dizer o `user_value` numa frase sem emendar coisas distintas? Se enumera ("faz X; também Y; e Z"), são várias features.
2. **Critérios coesos.** Todos os `acceptance` testam **a mesma** capacidade de ângulos diferentes? Se A1 e A2 falam de assuntos sem relação, você empacotou um changelog.
3. **Nome = substantivo de capacidade.** O `name` diz *o que o sistema faz* (`schema-reference`, `cli-path-uniformity`), não uma palavra de processo (`polish`, `misc`, `various`, `fixes`, `updates`). O audit **bloqueia** nomes-balde (ADR-0035) — mas ele só pega o tell óbvio; a coesão dos itens 1–2 é seu julgamento.
4. **É capacidade ou faxina?** Bugfix, refactor mecânico, fix cosmético, remoção de dead-code **não viram feature** — vão pro git history (e ADR se for decisão). Agrupar várias faxinas numa "feature guarda-chuva" é o anti-padrão que gerou o changelog-disfarçado-de-feature.

Cobertura honesta > cobertura inflada: é melhor uma faxina ficar só no git do que virar uma entrada de Manifest que mente sobre ser capacidade.

**EARS — patterns e campos obrigatórios:**

| pattern      | campos                  | uso                          |
|--------------|-------------------------|------------------------------|
| `ubiquitous` | `requirement`           | invariante sempre ativa      |
| `event`      | `trigger`, `response`   | estímulo → resposta          |
| `state`      | `state`, `response`     | comportamento condicional    |
| `optional`   | `feature`, `response`   | flag/parâmetro opcional      |
| `unwanted`   | `trigger`, `response`   | erro / proteção defensiva    |
| `complex`    | `requirement`           | combinação — evite, prefira quebrar |

## ADR mínimo

```markdown
---
id: ADR-NNNN
date: YYYY-MM-DD
status: accepted
supersedes: null
superseded_by: null
affects_features: [F-NNNN]
related: [ADR-NNNN]
tags: [tag1, tag2]
---

# ADR-NNNN · título curto

## Contexto

Qual problema forçou a decisão. 1–2 frases. Não recapitule arquitetura — só o que torna a escolha não-óbvia.

## Decisão

O que decidiu e o porquê dominante. Embuta trade-offs aqui ("aceitamos custo X para ganhar Y"). Um parágrafo, eventualmente lista curta de bullets se a decisão tem partes distintas.

## Alternativas rejeitadas

(opcional) Só as que pareceriam óbvias para quem não viveu a sessão. Uma linha cada — nome + motivo seco.
```

**Sem seção "Consequências" separada** — o que importa, embuta na Decisão; o resto recupera do código e do diff. **Sem listas "Positivas:" / "Negativas:" exaustivas.**

## O que evitar

- **Inventar features** para preencher Manifest. Sem capacidade nomeável, sem entrada.
- **Feature guarda-chuva / changelog.** Empacotar várias mudanças de um lote (fixes + cleanup + cosmético) numa só feature. Passe pelo "Teste de uma capacidade" — divida ou deixe no git.
- **Inventar métricas.** Sem medição desta sessão, mantenha valor anterior ou remova o campo.
- **Entrada de UNRELEASED prolixa.** Uma linha referenciando as F/ADR basta; o detalhe vai no código e no commit.
- **Duplicar frontmatter no body** de feature ou ADR.
- **Forçar ADR** para mudança mecânica.
- **Promover drafts** de `decisions/proposals/` para `decisions/` sem revisão humana.
- **Persistir specs / planos longos.** O registro durável de uma sessão é ADR + Feature, não um design doc paralelo; planejamento é efêmero (conversa/plan mode). Proponha ADRs e stubs de feature cedo, ambos como `proposed`, para a retomada não depender de plano efêmero (ADR-0041).
- **Rename/remoção sem varredura exaustiva.** Ao renomear ou remover um artefato/comando, **não** enumere as referências de cabeça — faça `grep -rn` de todas as formas do símbolo em todo o repo (src/tests/skills/templates/hooks/docs) e leve a **zero** referências ativas (re-grep no fim). É o método contra o ponto-cego "stale-on-cutover" (ADR-0049).
