"""frontmatter.py — Detecção de frontmatter stale no AGENTS.md do consumidor.

O `deploy` refresca o bloco entre sentinelas mas **nunca** toca o frontmatter
(`references`/`budgets`), que é human-owned. Após renames de layout (STATE.md
removido na 2.0.0; `.agent-memory/`→`.feat-memory/`) o frontmatter de um
consumidor pode ficar apontando para artefatos mortos sem nada sinalizar — foi
o ponto-cego que mordeu da 2.2.x em diante. Este detector é a fonte única usada
pelo `deploy`/`deploy --dry-run` (aviso no momento do upgrade) e pelo `audit`
(warning durável a cada commit). Ver F-0040.
"""

from __future__ import annotations

import re

_METH_VERSION_RE = re.compile(r"/blob/v?(\d+\.\d+\.\d+)/")


def detect_stale_frontmatter(fm: dict, current_version: str) -> list[str]:
    """Achados de staleness no frontmatter (mensagens; lista vazia = ok).

    Marca: paths em `.agent-memory/` (layout legado), chave `references.state`
    (STATE.md removido na 2.0.0), `budgets.state_max_bytes` (idem), e URL de
    `references.methodology` cuja tag de versão diverge de `current_version`.
    Um `methodology` sem tag de versão (ex.: path local `./METHODOLOGY.md`) é
    ignorado — nada a comparar.
    """
    findings: list[str] = []
    refs = fm.get("references")
    refs = refs if isinstance(refs, dict) else {}
    budgets = fm.get("budgets")
    budgets = budgets if isinstance(budgets, dict) else {}

    for key, val in refs.items():
        if isinstance(val, str) and ".agent-memory/" in val:
            findings.append(
                f"references.{key} aponta para .agent-memory/ (layout legado) "
                "— troque por .feat-memory/"
            )

    if "state" in refs:
        findings.append(
            "references.state é legado (STATE.md removido na 2.0.0) — troque por "
            "`unreleased: ./.feat-memory/changelog/UNRELEASED.md`"
        )

    if "state_max_bytes" in budgets:
        findings.append(
            "budgets.state_max_bytes é legado (STATE.md removido na 2.0.0) — remova"
        )

    meth = refs.get("methodology")
    if isinstance(meth, str):
        m = _METH_VERSION_RE.search(meth)
        if m and m.group(1) != current_version:
            findings.append(
                f"references.methodology aponta para v{m.group(1)}, mas a versão "
                f"atual é {current_version} — atualize a URL"
            )

    return findings
