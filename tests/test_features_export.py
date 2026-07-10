"""F-0048 / ADR-0052: export estruturado do Manifest para adapters.

`feat-memory features --json` emite o frontmatter completo (acceptance
incluído) — read-only, exit 0 sempre.
"""

from __future__ import annotations

import argparse
import json

from feat_memory.memory import export


def _write_feature(root, num, *, archived=False, status="shipped"):
    sub = "archive" if archived else "features"
    d = root / ".feat-memory" / "manifest" / sub
    d.mkdir(parents=True, exist_ok=True)
    (d / f"F-{num}-capability-{num}.md").write_text(
        f"---\nid: F-{num}\nname: capability-{num}\nstatus: {status}\n"
        f"user_value: valor {num}\ncontracts: {{api: src/mod.py::fn}}\n"
        "acceptance:\n"
        "  - {id: A1, pattern: event, trigger: \"algo acontece\", "
        "response: \"responde bem\"}\n"
        "---\n",
        encoding="utf-8",
    )


def _run(root, capsys, **kw) -> tuple[int, str]:
    args = argparse.Namespace(
        cmd="features", path=str(root), json=kw.get("json", False),
        all=kw.get("all", False), func=export.run,
    )
    rc = export.run(args)
    return rc, capsys.readouterr().out


def test_json_dump_carries_full_acceptance(audit_with_tmp_root, capsys):
    """Binding: F-0048-A1."""
    root = audit_with_tmp_root
    _write_feature(root, "0001")

    rc, out = _run(root, capsys, json=True)

    assert rc == 0
    data = json.loads(out)
    (feat,) = data["features"]
    assert feat["id"] == "F-0001"
    assert feat["acceptance"][0]["pattern"] == "event"
    assert feat["acceptance"][0]["response"] == "responde bem"
    assert feat["contracts"]["api"] == "src/mod.py::fn"
    assert feat["file"] == ".feat-memory/manifest/features/F-0001-capability-0001.md"
    assert feat["archived"] is False


def test_archive_only_with_all_flag(audit_with_tmp_root, capsys):
    """Binding: F-0048-A2."""
    root = audit_with_tmp_root
    _write_feature(root, "0001")
    _write_feature(root, "0002", archived=True)

    _, out = _run(root, capsys, json=True)
    assert [f["id"] for f in json.loads(out)["features"]] == ["F-0001"]

    _, out = _run(root, capsys, json=True, all=True)
    data = json.loads(out)["features"]
    assert [f["id"] for f in data] == ["F-0001", "F-0002"]
    assert data[1]["archived"] is True


def test_empty_manifest_is_valid_json_exit_zero(audit_with_tmp_root, capsys):
    """Binding: F-0048-A3."""
    root = audit_with_tmp_root
    (root / ".feat-memory" / "manifest" / "features").mkdir(
        parents=True, exist_ok=True)

    rc, out = _run(root, capsys, json=True)

    assert rc == 0
    assert json.loads(out) == {"features": []}


def test_human_listing_without_json(audit_with_tmp_root, capsys):
    root = audit_with_tmp_root
    _write_feature(root, "0001", status="proposed")

    rc, out = _run(root, capsys)

    assert rc == 0
    assert "F-0001" in out
    assert "proposed" in out


def test_subcommand_registered(capsys):
    import pytest
    from feat_memory import cli
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "features" in capsys.readouterr().out
