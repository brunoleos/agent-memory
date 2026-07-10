# Referência de schema — artefatos do feat-memory

Gerado de `feat_memory.memory.schemas` (fonte única). Não edite à mão — rode `feat-memory schema` ou regenere o doc. Campos não listados como obrigatórios são opcionais.

## AGENTS.md (frontmatter)

- **Obrigatórios:** `schema_version`, `project`, `constraints`, `references`, `budgets`
- `constraints`: lista; cada item tem `id`, `severity` (`hard`|`soft`) e `rule`. Bloco `check` opcional torna a constraint executável no audit (ADR-0028).
- `references`: mapa (`manifest_index`, `state`, `decisions_index`, `methodology`, `skills`).
- `budgets`: ver seção *Budgets* abaixo.

## changelog/UNRELEASED.md (trabalho em voo)

- Entradas-bullet no estilo Keep-a-Changelog (`Adicionado`/`Mudado`/`Corrigido`), cada uma referenciando as `F-NNNN`/`ADR-NNNN` que toca.
- O orçamento de retomada é **derivado** dessas referências (ADR-0043) — não há lista `active_*` hand-maintained. Vazio = nada em voo.
- Sem schema rígido; mantenha enxuto.

> Layout legado: o `STATE.md` foi removido na 2.0.0. Se um repositório ainda o tiver, o audit valida o schema antigo (obrigatórios `schema_version`, `updated_at`, `active_features`; `state_max_bytes`) por retrocompatibilidade.

## Feature (`.feat-memory/manifest/features/F-NNNN-slug.md`)

- **Nome do arquivo:** `^F-\d{4}-[a-z0-9-]+\.md$`
- **Obrigatórios:** `id`, `name`, `status`, `user_value`, `contracts`, `acceptance`
- **Opcionais reconhecidos:** `version`, `owner`, `introduced`, `depends_on`, `decisions`, `metrics`
- `status` ∈ {`deprecated`, `in_progress`, `proposed`, `shipped`}
- `contracts`: mapa com chaves `api`, `schemas`, `tests` (str, lista ou mapa de caminhos reais; `arquivo::símbolo` aceito). Caminho inexistente → `warning` de drift.
- `acceptance`: lista de critérios EARS (ver seção *EARS*).
- Sem limite mecânico de tamanho — mantenha enxuto (uma capacidade, `user_value` em uma frase).
- `name` deve nomear **uma capacidade**, não um lote de release: tokens de changelog (ex.: `polish`, `misc`, `various`) são **bloqueados** (ADR-0035). Coesão de conteúdo é julgamento humano (litmus nas skills).

## Decisão / ADR (`.feat-memory/decisions/NNNN-slug.md`)

- **Nome do arquivo:** `^\d{4}-[a-z0-9-]+\.md$`
- **Obrigatórios:** `id`, `date`, `status`
- **Opcionais reconhecidos:** `version`, `supersedes`, `superseded_by`, `affects_features`, `related`, `tags`, `reconciled`
- `status` ∈ {`accepted`, `deprecated`, `proposed`, `superseded`}
- `version` (opcional): SemVer `^v?\d+\.\d+\.\d+$` (prefixo `v` aceito).

## Critérios de aceitação — patterns EARS

Cada item de `acceptance` tem um `pattern` e os campos exigidos por ele (além de um `id` livre). Campos exigidos por pattern:

| pattern | campos obrigatórios |
|---|---|
| `ubiquitous` | `requirement` |
| `event` | `response`, `trigger` |
| `state` | `response`, `state` |
| `optional` | `feature`, `response` |
| `unwanted` | `response`, `trigger` |
| `complex` | `requirement` |

## Budgets (em `AGENTS.md::budgets`)

- `state_max_bytes` — **legado** (default 4096B): enforced só quando ainda existe um `STATE.md` legado (removido na 2.0.0).
- `resumption_max_bytes` — **advisory**: orçamento de contexto de retomada que o agente respeita ao carregar UNRELEASED/features/ADRs; não há checagem mecânica.
- Orçamento de prosa do corpo de features, por perfil de instalação (ADR-0050): `core` = 10 linhas não-vazias; `full` = 40 linhas não-vazias — acima do limite o audit emite warning (a feature é registro, não documento).

