"""install_hooks.py — Instala os Git hooks no projeto consumidor.

Chamado pelo deploy via install_hooks.install(target). Idempotente.
Os hooks ficam em src/feat_memory/data/hooks/ e são acessados via
importlib.resources (funciona em editable e wheel install).
"""

from __future__ import annotations

import shutil
import stat
from importlib.resources import as_file, files
from pathlib import Path


def _plan(target: Path):
    """Plano de instalação: lista (nome, status, src_entry, dst).

    status ∈ {'novo','atualizar','já instalado'}. Retorna None se `target`
    não é repositório Git. Permite que `deploy --dry-run` reporte com a mesma
    fidelidade dos arquivos ('já instalado' quando o hook já bate byte-a-byte).
    """
    git_dir = target / ".git"
    if not git_dir.exists():
        return None

    hooks_dst = git_dir / "hooks"
    hooks_src = files("feat_memory.governance") / "data" / "hooks"

    plan = []
    for entry in sorted(hooks_src.iterdir(), key=lambda e: e.name):
        if not entry.is_file():
            continue
        dst = hooks_dst / entry.name
        if not dst.exists():
            status = "novo"
        else:
            try:
                same = (dst.read_text(encoding="utf-8")
                        == entry.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                same = False
            status = "já instalado" if same else "atualizar"
        plan.append((entry.name, status, entry, dst))
    return plan


def install(target: Path, dry_run: bool = False) -> int:
    """Copia hooks do pacote para <target>/.git/hooks/. Idempotente.

    Hooks idênticos viram no-op ('já instalado'). Sob `dry_run`, não escreve.
    Retorna o número de hooks que (seriam) instalados/atualizados.
    """
    plan = _plan(target)
    if plan is None:
        print("  pulado (não é repositório Git)")
        return 0

    if not dry_run:
        (target / ".git" / "hooks").mkdir(parents=True, exist_ok=True)

    changes = 0
    for hook_name, status, entry, dst in plan:
        if status == "já instalado":
            print(f"  já instalado: {hook_name}")
            continue
        if not dry_run:
            with as_file(entry) as src_path:
                shutil.copy2(src_path, dst)
                current = dst.stat().st_mode
                dst.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        if status == "novo":
            verb = "instalaria" if dry_run else "instalado"
        else:
            verb = "atualizaria" if dry_run else "atualizado"
        print(f"  {verb}: {hook_name}")
        changes += 1

    if changes and not dry_run:
        print("  Para desabilitar temporariamente um commit: git commit --no-verify")
    return changes
