"""version_check.py — Notice soft quando consumer está desatualizado em MAJOR.

Lê `.feat-memory/.meta.yaml::version` e compara a `feat_memory.__version__`.
Só notifica quando o MAJOR difere ("upgrade quando doer", ADR-0050/0051 —
amortece o nudge original do ADR-0022: a tool não deve induzir cadência de
upgrade; diferenças de minor/patch são silenciosas).

Subcomando: `feat-memory version-check` (standalone, para CI/scripts).
Integração: `governance.audit::run` invoca após `print_report` e imprime
na stderr (não muda exit code — soft, ADR-0008).

Disable via `.meta.yaml::version_check_enabled: false`.

Parte de `governance/`. Importa apenas de `shared/` e `feat_memory.__version__`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from feat_memory import __version__
from feat_memory.shared import paths as _paths
from feat_memory.shared.parsing import read_meta


NOTICE_TEMPLATE = (
    "ℹ feat-memory CLI {cli} vs deployed {deployed} — MAJOR diferente\n"
    "  upgrade quando doer: re-rode `feat-memory deploy .` quando um release\n"
    "  note resolver uma dor sua, não por existir versão nova (ADR-0050/0051)."
)

UP_TO_DATE_TEMPLATE = "✓ feat-memory compatível (CLI v{cli})"


def _major(version: str) -> str | None:
    """Componente MAJOR de um semver ('2.5.0' → '2'); None se não-parseável."""
    head = str(version).strip().lstrip("v").split(".", 1)[0]
    return head if head.isdigit() else None


def consumer_version_notice(root: Path) -> str | None:
    """Retorna texto do notice se o MAJOR das versões difere, ou None.

    Casos onde retorna None (fail-soft):
    - `.meta.yaml` ausente (consumer pré-v0.6, ou root inválido)
    - `meta.get("version")` ausente ou vazio
    - `meta.get("version_check_enabled") is False`
    - MAJOR igual (diferenças de minor/patch são silenciosas — "upgrade
      quando doer", ADR-0050/0051)
    - Versão deployed não-parseável (fail-soft: sem notice espúrio)
    """
    meta = read_meta(root)
    if not meta:
        return None
    if meta.get("version_check_enabled") is False:
        return None
    deployed = meta.get("version")
    if not deployed:
        return None
    deployed_major = _major(str(deployed))
    if deployed_major is None:
        return None
    if deployed_major == _major(str(__version__)):
        return None
    return NOTICE_TEMPLATE.format(cli=__version__, deployed=deployed)


def _print_notice(text: str) -> None:
    """Imprime na stderr (amarelo com isatty, plain em CI)."""
    if sys.stderr.isatty():
        print(f"\033[33m{text}\033[0m", file=sys.stderr)
    else:
        print(text, file=sys.stderr)


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "version-check",
        help="Notice se a versão do CLI difere de .feat-memory/.meta.yaml::version "
             "(soft, sempre exit 0; ADR-0022)",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    _paths._init_paths()
    notice = consumer_version_notice(_paths.ROOT)
    if notice:
        _print_notice(notice)
    else:
        print(UP_TO_DATE_TEMPLATE.format(cli=__version__))
    return 0
