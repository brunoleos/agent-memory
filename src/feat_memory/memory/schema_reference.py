"""schema_reference.py — Referência de schema gerada de `schemas.py`.

Fonte única: lê as constantes de [schemas.py](schemas.py) e renderiza um Markdown
de uma página com os campos obrigatórios/opcionais de cada artefato, os patterns
EARS, os enums de status, os regexes de nome de arquivo e os budgets. Existe para
que o agente (em qualquer projeto consumidor) descubra o schema sem ler o
código-fonte do feat-memory.

Exposto de duas formas, ambas derivadas da mesma função (zero drift):
- `feat-memory schema` — imprime ao vivo; sempre coerente com o CLI instalado.
- `docs/SCHEMA-REFERENCE.md` — materializado no repo, mantido em sincronia por
  `tests/test_schema_reference.py`.

Parte de `memory/`. Importa apenas de `memory.schemas`.
"""

from __future__ import annotations

import argparse

from feat_memory.memory import schemas as S


def _fields(names: list[str]) -> str:
    return ", ".join(f"`{n}`" for n in names)


def render_schema_reference() -> str:
    """Monta o Markdown da referência a partir das constantes de schemas.py."""
    out: list[str] = []
    w = out.append

    w("# Referência de schema — artefatos do feat-memory")
    w("")
    w("Gerado de `feat_memory.memory.schemas` (fonte única). Não edite à mão — "
      "rode `feat-memory schema` ou regenere o doc. Campos não listados como "
      "obrigatórios são opcionais.")
    w("")

    # AGENTS.md
    w("## AGENTS.md (frontmatter)")
    w("")
    w(f"- **Obrigatórios:** {_fields(S.AGENT_REQUIRED)}")
    w("- `constraints`: lista; cada item tem `id`, `severity` (`hard`|`soft`) e "
      "`rule`. Bloco `check` opcional torna a constraint executável no audit "
      "(ADR-0028).")
    w("- `references`: mapa (`manifest_index`, `state`, `decisions_index`, "
      "`methodology`, `skills`).")
    w("- `budgets`: ver seção *Budgets* abaixo.")
    w("")

    # changelog/UNRELEASED.md (substitui o STATE.md no layout 2.x)
    w("## changelog/UNRELEASED.md (trabalho em voo)")
    w("")
    w("- Entradas-bullet no estilo Keep-a-Changelog (`Adicionado`/`Mudado`/"
      "`Corrigido`), cada uma referenciando as `F-NNNN`/`ADR-NNNN` que toca.")
    w("- O orçamento de retomada é **derivado** dessas referências (ADR-0043) — "
      "não há lista `active_*` hand-maintained. Vazio = nada em voo.")
    w("- Sem schema rígido; mantenha enxuto.")
    w("")
    w(f"> Layout legado: o `STATE.md` foi removido na 2.0.0. Se um repositório "
      f"ainda o tiver, o audit valida o schema antigo (obrigatórios "
      f"{_fields(S.STATE_REQUIRED)}; `state_max_bytes`) por retrocompatibilidade.")
    w("")

    # Feature
    w("## Feature (`.feat-memory/manifest/features/F-NNNN-slug.md`)")
    w("")
    w(f"- **Nome do arquivo:** `{S.FEATURE_FILE_RE.pattern}`")
    w(f"- **Obrigatórios:** {_fields(S.FEATURE_REQUIRED)}")
    w(f"- **Opcionais reconhecidos:** {_fields(S.FEATURE_OPTIONAL)}")
    w(f"- `status` ∈ {{{', '.join(f'`{s}`' for s in sorted(S.VALID_FEATURE_STATUS))}}}")
    w("- `contracts`: mapa com chaves `api`, `schemas`, `tests` (str, lista ou "
      "mapa de caminhos reais; `arquivo::símbolo` aceito). Caminho inexistente → "
      "`warning` de drift.")
    w("- `acceptance`: lista de critérios EARS (ver seção *EARS*).")
    w("- Sem limite mecânico de tamanho — mantenha enxuto (uma capacidade, "
      "`user_value` em uma frase).")
    w("- `name` deve nomear **uma capacidade**, não um lote de release: tokens "
      "de changelog (ex.: `polish`, `misc`, `various`) são **bloqueados** "
      "(ADR-0035). Coesão de conteúdo é julgamento humano (litmus nas skills).")
    w("")

    # Decision / ADR
    w("## Decisão / ADR (`.feat-memory/decisions/NNNN-slug.md`)")
    w("")
    w(f"- **Nome do arquivo:** `{S.DECISION_FILE_RE.pattern}`")
    w(f"- **Obrigatórios:** {_fields(S.DECISION_REQUIRED)}")
    w(f"- **Opcionais reconhecidos:** {_fields(S.DECISION_OPTIONAL)}")
    w(f"- `status` ∈ {{{', '.join(f'`{s}`' for s in sorted(S.VALID_DECISION_STATUS))}}}")
    w(f"- `version` (opcional): SemVer `{S.SEMVER_RE.pattern}` (prefixo `v` aceito).")
    w("")

    # EARS
    w("## Critérios de aceitação — patterns EARS")
    w("")
    w("Cada item de `acceptance` tem um `pattern` e os campos exigidos por ele "
      "(além de um `id` livre). Campos exigidos por pattern:")
    w("")
    w("| pattern | campos obrigatórios |")
    w("|---|---|")
    for pattern, fields in S.EARS_PATTERN_FIELDS.items():
        w(f"| `{pattern}` | {', '.join(f'`{f}`' for f in sorted(fields))} |")
    w("")

    # Budgets
    w("## Budgets (em `AGENTS.md::budgets`)")
    w("")
    w(f"- `state_max_bytes` — **legado** (default {S.DEFAULT_STATE_BUDGET}B): "
      "enforced só quando ainda existe um `STATE.md` legado (removido na 2.0.0).")
    w("- `resumption_max_bytes` — **advisory**: orçamento de contexto de retomada "
      "que o agente respeita ao carregar UNRELEASED/features/ADRs; não há checagem "
      "mecânica.")
    w("- Orçamento de prosa do corpo de features, por perfil de instalação "
      "(ADR-0050): "
      + "; ".join(f"`{profile}` = {limit} linhas não-vazias"
                  for profile, limit in sorted(S.PROSE_BUDGET_BY_PROFILE.items()))
      + " — acima do limite o audit emite warning (a feature é registro, "
      "não documento).")
    w("")

    return "\n".join(out) + "\n"


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "schema",
        help="Imprime a referência de schema dos artefatos (campos, EARS, enums)",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    print(render_schema_reference(), end="")
    return 0
