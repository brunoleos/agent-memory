"""cli.py — Entrypoint da CLI feat-memory.

Despacha argv para o subcomando apropriado. Cada módulo registra seu
próprio subparser via add_subparser(subparsers).
"""

from __future__ import annotations

import argparse
import sys

from feat_memory import __version__, deploy
from feat_memory.memory import (
    archive,
    changelog,
    migrate,
    propose_adr,
    sample,
    schema_reference,
)
from feat_memory.governance import (
    audit,
    check_doc_sync,
    check_staleness,
    check_version_bump,
    telemetry,
    version_check,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="feat-memory",
        description=(
            "Persistent memory methodology for LLM agents.\n\n"
            "Subcomandos agrupados por concern (F-0017, ADR-0021):\n"
            "  Memória:    deploy, audit, propose-adr, migrate, archive,\n"
            "              release, sample, schema\n"
            "  Governança: record, log, version-check,\n"
            "              check-staleness-staged, check-doc-sync-staged,\n"
            "              check-version-bump-staged"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"feat-memory {__version__}",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Subcomandos de memória (artefatos canônicos, ciclo de vida)
    deploy.add_subparser(sub)
    audit.add_subparser(sub)
    propose_adr.add_subparser(sub)
    migrate.add_subparser(sub)
    archive.add_subparser(sub)
    changelog.add_subparser(sub)
    schema_reference.add_subparser(sub)
    sample.add_subparser(sub)

    # Subcomandos de governança (telemetria, hooks, version-check)
    check_staleness.add_subparser(sub)
    check_doc_sync.add_subparser(sub)
    check_version_bump.add_subparser(sub)
    telemetry.add_subparser(sub)
    version_check.add_subparser(sub)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
