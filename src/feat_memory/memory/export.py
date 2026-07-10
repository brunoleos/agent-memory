"""export.py — Superfície estruturada do Manifest para adapters (F-0048).

`feat-memory features` lista as features; `--json` emite o dump completo
(frontmatter inteiro, acceptance incluído) para consumo programático —
adapters (BDD ou não) deixam de parsear markdown na mão (ADR-0052).

Read-only por construção: nunca escreve, sempre exit 0. A fronteira do
ADR-0052 vale aqui: exportamos o contrato; geração de plano, tasks, código
ou step definitions é território do adapter/harness, nunca desta CLI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from feat_memory.shared import paths as _paths
from feat_memory.shared.parsing import parse_frontmatter


def collect_features(root: Path, include_archive: bool = False) -> list[dict]:
    """Frontmatter completo de cada feature, com path repo-relativo e origem."""
    out: list[dict] = []

    def _load(directory: Path, archived: bool) -> None:
        if not directory.exists():
            return
        for fp in sorted(directory.glob("F-*.md")):
            try:
                fm, _ = parse_frontmatter(fp)
            except ValueError:
                continue  # malformada já é error do audit; export é read-only
            if not fm.get("id"):
                continue
            rel = fp.resolve()
            fm["file"] = (
                rel.relative_to(root.resolve()).as_posix()
                if rel.is_relative_to(root.resolve()) else fp.name
            )
            fm["archived"] = archived
            out.append(fm)

    _load(_paths.FEATURES_DIR, archived=False)
    if include_archive:
        _load(_paths.ARCHIVE_DIR, archived=True)
    return out


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "features",
        help="Lista as features do Manifest; --json emite o dump estruturado "
             "completo para adapters (read-only, exit 0; ADR-0052)",
    )
    p.add_argument("path", type=str, nargs="?", default=None,
                   help="raiz do projeto (default: detecta do diretório atual)")
    p.add_argument("--json", action="store_true",
                   help="dump JSON completo (frontmatter + acceptance)")
    p.add_argument("--all", action="store_true",
                   help="inclui as features arquivadas")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve() if getattr(args, "path", None) else None
    _paths._init_paths(root)
    features = collect_features(_paths.ROOT,
                                include_archive=getattr(args, "all", False))
    if getattr(args, "json", False):
        print(json.dumps({"features": features},
                         ensure_ascii=False, indent=2, default=str))
    else:
        for fm in features:
            marker = " [archive]" if fm.get("archived") else ""
            print(f"{fm.get('id')}  {fm.get('status', '?'):<12} "
                  f"{fm.get('name', '')}{marker}")
        if not features:
            print("(nenhuma feature no Manifest)")
    return 0
