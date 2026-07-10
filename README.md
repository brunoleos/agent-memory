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

O `feat-memory deploy` é idempotente: em `AGENTS.md` ele só refresca o bloco entre as sentinelas `<!-- >>> feat-memory >>> -->` / `<!-- <<< feat-memory <<< -->` e preserva todo o resto (frontmatter, seções do mantenedor); o `changelog/UNRELEASED.md` nunca é sobrescrito quando existe. A especificação completa — o que é refrescado, preservado ou pulado, e as flags `--force`/`--no-merge` — está na [METHODOLOGY.md](METHODOLOGY.md), seção **Deploy**.

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
│       │   ├── binding.py            # binding critério↔teste (F-NNNN-AN)
│       │   ├── changelog.py          # subcomando release + UNRELEASED
│       │   ├── export.py             # subcomando features (export JSON)
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

Quatro skills cobrem os quatro momentos do uso — o procedimento autoritativo de cada uma vive no seu `SKILL.md`, e o agente descobre os triggers pelo `description` do frontmatter:

- **`memory-deploy`** — adoção inicial, greenfield ou legacy (com gênese retroativa revisada).
- **`memory-bootstrap`** — início de sessão ("onde paramos?").
- **`memory-debrief`** — antes de cada commit relevante; a mais usada.
- **`memory-pull-brief`** — depois de `git pull` que trouxe commits de colegas.

## Comandos úteis

```bash
feat-memory audit                    # valida artefatos + gera índices (--strict no hook/CI)
feat-memory features --json          # export estruturado do Manifest (adapters)
feat-memory sample --event release   # prompts de refutação adversarial (exit 0 sempre)
feat-memory propose-adr --staged     # draft de ADR a partir do diff
feat-memory migrate --limit 200      # pistas para gênese retroativa (legacy)
feat-memory schema                   # referência gerada de campos e patterns EARS
```

O que cada comando garante — e o que deliberadamente não garante — está na [METHODOLOGY.md](METHODOLOGY.md).

## Documentação

A documentação está dividida em três níveis. O [USER_GUIDE.md](USER_GUIDE.md) é o manual prático para usuários, cobrindo instalação, fluxo de trabalho típico, comandos importantes, resolução de problemas comuns, e trabalho em time. Comece por ele se você está adotando a metodologia pela primeira vez.

A doutrina técnica completa está em [METHODOLOGY.md](METHODOLOGY.md), incluindo o esquema de cada artefato, a notação EARS para critérios de aceitação, o protocolo do agente, as métricas de auditoria, o workflow de merge e rebase, e casos de borda. Use-o como referência quando precisa entender por que algo funciona como funciona.

O roadmap está em [FUTURE_IMPROVEMENTS.md](FUTURE_IMPROVEMENTS.md), registrando extensões implementadas (com link reverso para quando foram adicionadas), planejadas (organizadas por horizonte), e explicitamente rejeitadas (com a razão da rejeição registrada).
