# feat-memory

Memória persistente para agentes LLM como CLI Python. Instale com `pipx`, rode `feat-memory deploy <projeto>`, e peça ao agente para configurar.

## O que é isso

Quatro artefatos versionados que dão a um agente LLM tudo que ele precisa para retomar trabalho em um projeto sem reler todo o código a cada sessão. Cada artefato responde uma pergunta diferente, com um ciclo de mutação diferente.

| Artefato | Pergunta | Mutação |
|---|---|---|
| `AGENTS.md` | Sob quais regras construímos? | Rara |
| `.feat-memory/manifest/` | O que existe hoje no sistema? | Append-only |
| `.feat-memory/changelog/` | O que está em voo / o que shippou? | UNRELEASED editável; releases imutáveis |
| `.feat-memory/decisions/` | Por que escolhemos assim? | Imutável + supersede |

A instalação tem dois perfis (ADR-0050): **core** (default em adoção nova) instala a espinha — constituição, decisions, `changelog/UNRELEASED.md` e features finas; **full** adiciona a operação completa de changelog e orçamento de prosa maior. Re-deploy preserva o perfil escolhido.

## Instalação

Instale a CLI uma vez na sua máquina (a partir do clone do projeto):

```bash
git clone https://github.com/brunoleos/feat-memory.git ~/dev/feat-memory
pipx install -e ~/dev/feat-memory
```

A flag `-e` é editable install: o binário `feat-memory` no seu PATH lê o código direto do clone, então `git pull` no clone atualiza a CLI imediatamente em todos os projetos. Detalhes desse modo estão em [USER_GUIDE.md](USER_GUIDE.md).

Em qualquer projeto consumidor, rode:

```bash
feat-memory deploy /caminho/do/projeto
```

Isso monta `AGENTS.md`, `CLAUDE.md`, `.feat-memory/changelog/UNRELEASED.md`, `.feat-memory/manifest/`, `.feat-memory/decisions/`, `.feat-memory/ideas.md`, `skills/`, `.gitattributes`, e instala o pre-commit hook — no perfil `core` por default (`--profile full` para a operação completa de changelog).

Depois, abra uma sessão com seu agente preferido (Claude Code, Cursor, ou outro que reconheça `AGENTS.md`) e peça:

```text
instale a metodologia neste projeto
```

A skill `memory-deploy` detecta se o projeto é greenfield (novo, pouco código) ou legacy (com história substancial). Em greenfield, ela apenas executa o deploy mecânico — identidade, restrições, convenções e demais conteúdos específicos do projeto são autoria do mantenedor humano, escritos diretamente no `AGENTS.md` quando ele decidir que vale registrar.

Para projetos legacy, a skill conduz adicionalmente gênese retroativa multi-fonte com revisão humana entre as fases: evidências trianguladas (testes, telas, docs, código, deps; git secundário), Manifest de features finas a partir das capacidades, ADRs a partir das decisões, e `changelog/UNRELEASED.md` inicial vazio. A skill nunca escreve no corpo da `AGENTS.md` fora do bloco delimitado por sentinelas — esse bloco é gerenciado mecanicamente pelo `feat-memory deploy`.

## Comportamento com arquivos pré-existentes

O `feat-memory deploy` é idempotente em todas as superfícies que ele instala. A `AGENTS.md` carrega um bloco delimitado por sentinelas markdown:

```markdown
<!-- >>> feat-memory >>> -->
## feat-memory
[instruções de uso da metodologia, refrescadas a cada deploy]
<!-- <<< feat-memory <<< -->
```

Quando o `AGENTS.md` já existe, o deploy só toca o conteúdo entre essas sentinelas — todo o resto (frontmatter, seções específicas do projeto, comentários do usuário) é preservado. Quando ainda não existe, o template completo é escrito (frontmatter scaffold + bloco). O `CLAUDE.md` (redirect mínimo `@AGENTS.md`) é copiado se ausente e deixado quieto se existe.

O `.feat-memory/changelog/UNRELEASED.md` segue semântica diferente: como o conteúdo dele é volátil por construção, não há valor real em mesclar. Se já existe, é simplesmente pulado — o deploy nunca sobrescreve conteúdo do usuário nele (regra do postmortem ADR-0051).

As skills em `skills/` são sempre reescritas a cada deploy, porque elas são conteúdo de metodologia (não de usuário). Se você quiser uma skill customizada, copie-a para um nome diferente (`skills/memory-debrief` → `skills/my-debrief`) — a versão renomeada é preservada. O `.gitattributes` segue a mesma lógica via bloco com sentinelas: o que estiver fora do bloco é preservado, o bloco em si é refrescado.

A flag `--force` reescreve `AGENTS.md` e `CLAUDE.md` inteiros a partir do template, descartando conteúdo do usuário fora do bloco. A flag `--no-merge` pula a refresh do bloco em `AGENTS.md`/`CLAUDE.md` existentes (útil em CI onde nenhuma modificação é desejada).

## Versionamento e atualizações

O pacote tem versionamento semântico em `VERSION` (lido pelo `pyproject.toml`) e histórico de releases em [.feat-memory/changelog/INDEX.md](.feat-memory/changelog/INDEX.md) (um arquivo imutável por tag, ADR-0042). Cada release publicada em <https://github.com/brunoleos/feat-memory/releases> corresponde a uma tag `vX.Y.Z`. Para descobrir a versão instalada, rode `feat-memory --version` ou `pipx list | grep feat-memory`.

Em editable install, atualizar é simplesmente `git pull` no clone:

```bash
cd ~/dev/feat-memory
git pull
```

A CLI passa a refletir a versão nova imediatamente em todos os projetos consumidores. Para fixar em uma tag específica:

```bash
cd ~/dev/feat-memory
git fetch --tags
git checkout v0.3.0
```

Para reaplicar templates e skills em um projeto consumidor após upgrade, rode `feat-memory deploy <projeto>` novamente — ele é idempotente: refresca o bloco com sentinelas em `AGENTS.md` (preservando todo o resto), atualiza skills e `.gitattributes`, garante a entrada em `.gitignore`, e reinstala o pre-commit hook.

Quando o pacote estiver publicado na PyPI (planejado), o caminho de instalação para usuários finais será `pipx install feat-memory` (sem `-e`), e atualização será `pipx upgrade feat-memory`.

## Modo programático

Em CI ou automação sem intervenção humana, o `feat-memory deploy` pode ser invocado direto sem passar pela skill. Em ambientes onde refresh do bloco não é desejada, use `--no-merge`.

```bash
feat-memory deploy <projeto>                 # padrão: perfil core (novo) ou o já gravado; refresca bloco em AGENTS.md
feat-memory deploy <projeto> --profile full  # operação completa de changelog + orçamento de prosa maior
feat-memory deploy <projeto> --no-merge      # pula AGENT/CLAUDE existentes (sem refresh do bloco)
feat-memory deploy <projeto> --force         # reescreve AGENT/CLAUDE inteiros do template
feat-memory deploy <projeto> --no-hooks      # pula instalação de git hooks
feat-memory deploy <projeto> --dry-run       # mostra o que mudaria sem escrever nada
```

A escolha entre skill e comando direto reflete os dois modos de uso. Para humanos adotando a metodologia em um projeto real, a skill é o caminho (em legacy ela faz a gênese retroativa de ADRs e Manifest, que o comando direto não faz). Para automação que apenas precisa da estrutura mecânica, o comando direto basta.

## Portabilidade

Todas as ferramentas estão escritas em Python 3.10 ou superior, sem dependência de shell scripts. O pacote roda em Linux, macOS e Windows nativamente, sem necessidade de WSL ou outras camadas de compatibilidade. A única dependência externa é PyYAML, declarada em `pyproject.toml` e instalada automaticamente pelo `pipx`.

## Estrutura do pacote

```text
feat-memory/                         # clone do projeto na sua máquina
├── pyproject.toml                    # metadados do pacote
├── README.md                         # este arquivo
├── USER_GUIDE.md                     # manual prático para usuários
├── METHODOLOGY.md                    # doutrina completa
├── FUTURE_IMPROVEMENTS.md            # roadmap de extensões
├── VERSION                           # versão semântica atual (lida por pyproject)
├── src/
│   └── feat_memory/                 # pacote Python (3 subpacotes, ADR-0021)
│       ├── __init__.py
│       ├── cli.py                    # entrypoint: feat-memory ...
│       ├── deploy.py                 # subcomando deploy (top-level)
│       ├── data/                     # package data compartilhado (vai no wheel)
│       │   ├── templates/            # AGENTS.md, CLAUDE.md, ideas.md, .gitattributes
│       │   ├── skills/               # memory-deploy, memory-bootstrap, memory-debrief, memory-pull-brief
│       │   └── agents/               # subagents (Claude Code)
│       ├── shared/                   # utilitários sem deps do projeto
│       │   ├── paths.py              # lazy-init de ROOT e paths derivados
│       │   ├── parsing.py            # parse_frontmatter, read_meta, resolve_profile
│       │   └── frontmatter.py        # detecção de frontmatter stale
│       ├── memory/                   # artefatos canônicos + ciclo de vida
│       │   ├── schemas.py            # validação de schema (EARS, orçamento de prosa)
│       │   ├── indexing.py           # geração de INDEX.md
│       │   ├── archive.py            # subcomando archive
│       │   ├── changelog.py          # subcomando release + UNRELEASED
│       │   ├── propose_adr.py        # subcomando propose-adr
│       │   ├── sample.py             # subcomando sample (refutação adversarial)
│       │   ├── schema_reference.py   # subcomando schema
│       │   └── migrate.py            # subcomando migrate
│       └── governance/              # enforcement, métricas, telemetria, hooks
│           ├── audit.py              # subcomando audit
│           ├── constraints.py        # checkers declarativos de constraints
│           ├── lexicon.py            # nudge de léxico de mecanismo (info)
│           ├── telemetry.py          # subcomandos record / log
│           ├── check_staleness.py    # check-staleness-staged
│           ├── check_doc_sync.py     # check-doc-sync-staged
│           ├── check_version_bump.py # check-version-bump-staged
│           ├── version_check.py      # subcomando version-check
│           ├── install_hooks.py      # helper de instalação de hooks
│           └── data/hooks/           # pre-commit
├── tests/                            # suite pytest
└── examples/                         # exemplos pedagógicos (não vão no wheel)
    ├── manifest/features/F-0001-vector-similarity-search.md
    ├── decisions/0001-record-architecture-decisions.md
    └── decisions/0002-cosine-similarity-default.md
```

## Estrutura final no project root

Depois da instalação, o seu repositório tem isto. Os artefatos versionados em Git são `AGENTS.md`, `CLAUDE.md`, `.feat-memory/` (changelog, ideas, manifest, decisions, .meta.yaml), `skills/`, `.gitattributes`, e o bloco em `.gitignore`.

```text
seu-projeto/
├── .gitignore                        # contém bloco com regras feat-memory
├── .gitattributes                    # bloco com sentinelas (regras de merge)
├── AGENTS.md                          # constituição (com bloco feat-memory delimitado por sentinelas)
├── CLAUDE.md                         # redirect para AGENTS.md (Claude Code)
├── skills/
│   ├── memory-deploy/SKILL.md
│   ├── memory-bootstrap/SKILL.md
│   ├── memory-debrief/SKILL.md
│   └── memory-pull-brief/SKILL.md
├── .feat-memory/
│   ├── .meta.yaml                    # versão deployada + perfil (core|full)
│   ├── ideas.md                      # funil de ideias cruas
│   ├── changelog/
│   │   ├── UNRELEASED.md             # trabalho em voo (volátil)
│   │   └── (X.Y.Z.md imutáveis a cada release — perfil full)
│   ├── manifest/
│   │   ├── INDEX.md                  # gerado por feat-memory audit
│   │   └── features/
│   │       └── (vazio até primeira feature)
│   └── decisions/
│       ├── INDEX.md                  # gerado por feat-memory audit
│       ├── proposals/                # drafts de feat-memory propose-adr
│       └── (vazio até primeiro ADR)
└── (seu código de sempre)
```

## Operação diária

As quatro skills cobrem quatro momentos qualitativamente diferentes do uso da metodologia. Cada uma tem triggers próprios e instruções autoritativas no respectivo `SKILL.md`. O agente que entende essas skills (Claude Code via `CLAUDE.md`, Cursor via `AGENTS.md`, e outros) descobre os triggers a partir do `description` no frontmatter de cada skill.

A skill `memory-deploy` cobre a adoção inicial, executada uma única vez por projeto. Ela ativa quando o usuário pede para instalar a metodologia e conduz tanto greenfield quanto legacy, conforme detectado.

A skill `memory-bootstrap` cobre o início de cada sessão de trabalho. Frases como "onde paramos" ou "qual o status" ativam a skill, que carrega o contexto eficientemente e apresenta um briefing tático antes de prosseguir.

A skill `memory-debrief` é a mais usada no dia-a-dia. Frases como "vou commitar" ou "atualize a memória" ativam a skill, que examina o diff, atualiza o Manifest, registra o trabalho no `changelog/UNRELEASED.md`, gera proposta de ADR se necessário, e fecha com o teste do agente frio ("um agente frio responderia 'por que não X?' só com a memória?"). Invoque-a antes de cada commit relevante.

A skill `memory-pull-brief` cobre o quarto momento crítico: depois de `git pull` que trouxe commits de colegas. Frases como "o que veio do pull" ou "brifa as mudanças do main" ativam a skill, que examina o diff trazido, identifica mudanças semânticas em `.feat-memory/manifest/`, `.feat-memory/decisions/` e no bloco metodológico de `AGENTS.md`, e propõe ajustes em `.feat-memory/changelog/UNRELEASED.md` para ressincronizar o foco local. É read-only sobre `.feat-memory/manifest/` e `.feat-memory/decisions/` — esses já vieram corretos do pull.

## Comandos úteis

A auditoria valida todos os artefatos e gera os índices automaticamente. Ela é executada também pelo pre-commit hook em modo strict.

```bash
feat-memory audit                # relatório + índices
feat-memory audit --strict       # warnings viram errors
feat-memory audit --json         # output para CI
```

O gerador de propostas examina o diff atual e detecta sinais de mudança arquitetural não-trivial, gerando draft em `.feat-memory/decisions/proposals/` para revisão. É invocado pela skill `memory-debrief` mas pode ser chamado diretamente.

```bash
feat-memory propose-adr             # examina HEAD~1..HEAD
feat-memory propose-adr --staged    # mudanças staged
feat-memory propose-adr --prompt    # prompt para LLM
```

O detector de candidatos para gênese retroativa é invocado pela skill `memory-deploy` na fase 2 de projetos legacy. Pode ser chamado diretamente para inspeção do histórico.

```bash
feat-memory migrate --limit 200
```

A amostragem adversarial cobre a verdade semântica dos critérios de aceite, que o audit (referencial) não cobre: sorteia features ponderadas por risco e emite prompts de refutação para um agente LLM executar. Gatilho recomendado: após um supersede e a cada release.

```bash
feat-memory sample --event release          # prompts de refutação, exit 0 sempre
feat-memory sample --count 5 --seed 42      # amostra maior, reprodutível
```

## Documentação

A documentação está dividida em três níveis. O [USER_GUIDE.md](USER_GUIDE.md) é o manual prático para usuários, cobrindo instalação, fluxo de trabalho típico, comandos importantes, resolução de problemas comuns, e trabalho em time. Comece por ele se você está adotando a metodologia pela primeira vez.

A doutrina técnica completa está em [METHODOLOGY.md](METHODOLOGY.md), incluindo o esquema de cada artefato, a notação EARS para critérios de aceitação, o protocolo do agente, as métricas de auditoria, o workflow de merge e rebase, e casos de borda. Use-o como referência quando precisa entender por que algo funciona como funciona.

O roadmap está em [FUTURE_IMPROVEMENTS.md](FUTURE_IMPROVEMENTS.md), registrando extensões implementadas (com link reverso para quando foram adicionadas), planejadas (organizadas por horizonte), e explicitamente rejeitadas (com a razão da rejeição registrada).
