---
schema_version: 2
project: feat-memory
stack:
  language: python>=3.11
  packaging: setuptools (src layout, importlib.resources para package data)
  testing: pytest
  distribution: pipx editable install (PyPI planejado)
constraints:
  - id: C1
    severity: hard
    rule: "Pure Python; sem shell scripts. Tools rodam em Linux, macOS e Windows nativamente."
    check:
      type: forbid_paths
      globs: ["**/*.sh", "**/*.bash"]
  - id: C2
    severity: hard
    rule: "Dependência externa única: pyyaml. Novas dependências exigem ADR."
    check:
      type: dependencies
      manifest: pyproject.toml
      allow: ["pyyaml"]
  - id: C3
    severity: hard
    rule: "O projeto segue a metodologia feat-memory para gestão de agentes LLM."
  - id: C4
    severity: hard
    rule: "Toda documentação em pt-br."
references:
  manifest_index: ./.feat-memory/manifest/INDEX.md
  unreleased: ./.feat-memory/changelog/UNRELEASED.md
  decisions_index: ./.feat-memory/decisions/INDEX.md
  methodology: ./METHODOLOGY.md
  skills: ./skills/
budgets:
  resumption_max_bytes: 12288
---

# Constituição do projeto

## Identidade

`feat-memory` é uma CLI Python que distribui uma metodologia de memória persistente para agentes LLM — quatro artefatos versionados, skills e governança executável. A apresentação completa (o quê, para quem, comandos) está no [README.md](README.md); a doutrina, na [METHODOLOGY.md](METHODOLOGY.md); o roster de subcomandos, em `feat-memory --help` (não o duplique aqui — drifta).

Este repositório é simultaneamente a tool e a metodologia — vale o C3: o projeto segue o próprio protocolo.

## Restrições não-negociáveis

As restrições marcadas como `severity: hard` no frontmatter são auditadas pelo `feat-memory audit` e bloqueiam o build quando violadas. As `soft` geram apenas warning. Mudanças nesta lista exigem ADR.

Constraints podem declarar um bloco `check` opcional que o `feat-memory audit` **executa** contra o repositório, tornando a restrição enforced em vez de só declarativa ([ADR-0028](.feat-memory/decisions/0028-constraints-declarative-checkers.md)). C1 (`forbid_paths` sobre `*.sh`/`*.bash`) e C2 (`dependencies` sobre `pyproject.toml`, allow `pyyaml`) são checadas a cada audit; a violação herda a severity da constraint. C3 e C4 ficam declarativas — não há checker barato e confiável para elas.

A combinação `pure Python` + `pyyaml apenas` é o que torna o `pipx install` trivial em qualquer plataforma. Adicionar shell scripts ou outras dependências fragmenta a superfície de instalação e exige ADR.

## Convenções de código

Observado em refactors recentes (não confirmado como regra dura): módulos da CLI tendem a usar **lazy initialization** — `yaml` importado dentro das funções que precisam, `ROOT` e paths derivados computados sob demanda. Veja [src/feat_memory/governance/audit.py](src/feat_memory/governance/audit.py), [src/feat_memory/memory/propose_adr.py](src/feat_memory/memory/propose_adr.py). Mantém startup barato e desacopla import do CWD.

Templates em `src/feat_memory/data/templates/` usam o token literal `{VERSION}`, substituído em runtime pelo `deploy.py` com a versão do pacote. Não escreva versões hardcoded em templates.

Pre-commit hook é fail-open: se o binário `feat-memory` não está no PATH, emite warning e libera o commit. Documentado em [src/feat_memory/governance/data/hooks/pre-commit](src/feat_memory/governance/data/hooks/pre-commit).

Código, identificadores e nomes de arquivos em inglês; documentação em pt-br (C4).

## Desenvolvimento local

Este repositório é a fonte da tool e ao mesmo tempo um projeto consumidor da metodologia (C3). Para instalar/atualizar a CLI a partir do código local, use **pipx editable install** — é o mecanismo de distribuição formalizado em [ADR-0007](.feat-memory/decisions/0007-distribute-as-pipx-package.md):

```bash
python -m pipx install --force -e .
```

`--force` reinstala se já houver versão pipx-instalada (típico). Após esse comando, mudanças em `src/feat_memory/` aparecem imediatamente em `feat-memory <subcomando>` (editable install) — não é preciso reinstalar a cada edição. Bumps de versão em `VERSION` e mudanças em `pyproject.toml` exigem reinstall para refletir em `feat-memory.__version__`.

Não use `pip install -e .` — colide com o shim do pipx em `~/.local/bin/feat-memory.exe` e produz erro de permissão no Windows.

<!-- >>> feat-memory >>> -->
## feat-memory

Sessões começam por `.feat-memory/changelog/UNRELEASED.md` (trabalho em voo) e `.feat-memory/manifest/INDEX.md` (mapa de capacidades). Detalhes de uma feature ficam em `.feat-memory/manifest/features/F-NNNN-*.md`. Decisões arquiteturais em `.feat-memory/decisions/`. O histórico de releases vive em `.feat-memory/changelog/<tag>.md`. A metodologia completa está documentada no repositório do feat-memory: <https://github.com/brunoleos/feat-memory/blob/v3.0.0/METHODOLOGY.md>.

Doutrina do observável: critérios de aceite enunciam observáveis externos, nunca mecanismo (mecanismo é território de ADR); quando o "como" é identidade do produto, ele vive aqui na constituição como constraint, e desce aos critérios só como observáveis de trajetória. Features são registros ortogonais — frontmatter com aceites e ponteiros; prosa que reafirma outra fonte drifta.

Este bloco é refrescado a cada `feat-memory deploy`. Não edite diretamente — mudanças aqui são sobrescritas no próximo redeploy. Conteúdo específico do projeto vai fora das marcações HTML que delimitam este bloco.

### Skills disponíveis

Quatro skills em `skills/` orientam os fluxos críticos. Leia o `SKILL.md` de cada uma antes de executá-la — o frontmatter traz os triggers de ativação e as instruções autoritativas (fonte única; não duplicadas aqui). Roster:

- **`memory-deploy`** — instalar/adotar a metodologia num projeto: deploy mecânico e, em legacy, gênese retroativa multi-fonte (testes, telas, código, deps; git secundário).
- **`memory-bootstrap`** — retomar uma sessão: carregar o contexto e dar o briefing tático ("onde paramos", "qual o status").
- **`memory-debrief`** — fechar/commitar uma sessão: atualizar Manifest e registrar o trabalho no `changelog/UNRELEASED.md` e propor ADR a partir do diff. A mais usada no dia-a-dia.
- **`memory-pull-brief`** — após `git pull`, brifar o que veio do remote e reconciliar o `UNRELEASED.md`.

### Como retomar trabalho

A constituição é carregada automaticamente. Em seguida, você deve carregar `.feat-memory/changelog/UNRELEASED.md` para descobrir o trabalho em voo. O conjunto ativo de features e ADRs é **derivado** das referências `F-NNNN`/`ADR-NNNN` nas entradas-bullet do UNRELEASED (ADR-0043) — apenas esses precisam ser expandidos no contexto inicial; carregar o Manifest inteiro ou todos os ADRs viola o orçamento de retomada. UNRELEASED vazio = nada em voo (veja o último release em `changelog/INDEX.md`).
<!-- <<< feat-memory <<< -->
