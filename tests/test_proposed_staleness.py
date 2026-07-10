"""F-0047 / ADR-0052: anti-apodrecimento de prospecção.

Feature `proposed` velha (>90d) sem referência em UNRELEASED/ideas.md gera
nudge `info` — higiene, nunca gate. Prospecção sem relógio vira backlog.
"""

from __future__ import annotations

import os
import subprocess

from feat_memory.governance import audit


OLD_DATE = "2026-01-01T00:00:00"


def _seed_base(root) -> None:
    am = root / ".feat-memory"
    (root / "AGENTS.md").write_text(
        "---\nschema_version: 2\nproject: x\nconstraints: []\n"
        "references: {}\nbudgets: {}\n---\n", encoding="utf-8",
    )
    (am / "changelog").mkdir(parents=True, exist_ok=True)
    (am / "changelog" / "UNRELEASED.md").write_text(
        "---\nschema_version: 1\n---\n\n# Não-lançado\n", encoding="utf-8",
    )
    (am / ".meta.yaml").write_text(
        "schema_version: 2\nversion: 0.0.0\nprofile: full\n", encoding="utf-8",
    )
    (am / "manifest" / "features").mkdir(parents=True, exist_ok=True)
    (am / "decisions").mkdir(parents=True, exist_ok=True)


def _write_feature(root, num, *, status="proposed"):
    path = (root / ".feat-memory" / "manifest" / "features"
            / f"F-{num}-capability-{num}.md")
    path.write_text(
        f"---\nid: F-{num}\nname: capability-{num}\nstatus: {status}\n"
        f"user_value: valor {num}\ncontracts: {{}}\nacceptance: []\n---\n",
        encoding="utf-8",
    )
    return path


def _commit_dated(root, path, date=OLD_DATE):
    env = {**os.environ,
           "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    subprocess.run(["git", "-C", str(root), "add", str(path)],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed"],
                   check=True, capture_output=True, env=env)


def _staleness_issues(result):
    return [i for i in result["issues"]
            if "sem referência em UNRELEASED/ideas" in i["message"]]


def test_old_unreferenced_proposed_gets_info(audit_with_tmp_root):
    """Binding: F-0047-A1."""
    root = audit_with_tmp_root
    _seed_base(root)
    path = _write_feature(root, "0001")
    _commit_dated(root, path)

    found = _staleness_issues(audit.run_audit(write_indices=False))

    assert len(found) == 1
    assert found[0]["severity"] == "info"
    assert "promova, reescope ou descarte" in found[0]["message"]


def test_referenced_in_unreleased_is_silent(audit_with_tmp_root):
    """Binding: F-0047-A2."""
    root = audit_with_tmp_root
    _seed_base(root)
    path = _write_feature(root, "0001")
    _commit_dated(root, path)
    (root / ".feat-memory" / "changelog" / "UNRELEASED.md").write_text(
        "---\nschema_version: 1\n---\n\n# Não-lançado\n\n"
        "- retomando a prospecção (F-0001)\n",
        encoding="utf-8",
    )

    assert _staleness_issues(audit.run_audit(write_indices=False)) == []


def test_mentioned_in_ideas_is_silent(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    path = _write_feature(root, "0001")
    _commit_dated(root, path)
    (root / ".feat-memory" / "ideas.md").write_text(
        "# Ideias\n\n## refinar-prospeccao\n- contexto: evoluir F-0001\n",
        encoding="utf-8",
    )

    assert _staleness_issues(audit.run_audit(write_indices=False)) == []


def test_recent_proposed_is_silent(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    path = _write_feature(root, "0001")
    subprocess.run(["git", "-C", str(root), "add", str(path)],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed"],
                   check=True, capture_output=True)

    assert _staleness_issues(audit.run_audit(write_indices=False)) == []


def test_uncommitted_proposed_is_silent(audit_with_tmp_root):
    """Idade desconhecida (nunca commitada) → fail-soft, sem nudge.
    Binding: F-0047-A4."""
    root = audit_with_tmp_root
    _seed_base(root)
    _write_feature(root, "0001")

    assert _staleness_issues(audit.run_audit(write_indices=False)) == []


def test_old_shipped_is_silent(audit_with_tmp_root):
    """O relógio é só de prospecção — shipped velho não é apodrecimento.
    Binding: F-0047-A3."""
    root = audit_with_tmp_root
    _seed_base(root)
    path = _write_feature(root, "0001", status="shipped")
    _commit_dated(root, path)

    assert _staleness_issues(audit.run_audit(write_indices=False)) == []
