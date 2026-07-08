"""Testes de F-0018 / ADR-0022: notificação ao consumidor sobre desatualização."""

from __future__ import annotations

import argparse

import pytest

from feat_memory import __version__
from feat_memory.governance import version_check
from feat_memory.shared import paths as _paths


# --- helpers -------------------------------------------------------------


def _seed_meta(root, *, version: str = "0.7.0",
               version_check_enabled: bool | None = None) -> None:
    am = root / ".feat-memory"
    am.mkdir(parents=True, exist_ok=True)
    extra = ""
    if version_check_enabled is not None:
        extra = f"\nversion_check_enabled: {str(version_check_enabled).lower()}"
    (am / ".meta.yaml").write_text(
        f"schema_version: 1\n"
        f"version: {version}\n"
        f"deployed_at: 2026-05-05T00:00:00+00:00\n"
        f"cli_path: /tmp/feat-memory{extra}\n",
        encoding="utf-8",
    )


# --- consumer_version_notice ---------------------------------------------


def test_notice_when_major_differs(tmp_project):
    """A1: MAJOR diferente → notice com ambas + sugestão 'quando doer'."""
    _seed_meta(tmp_project, version="0.5.0")
    notice = version_check.consumer_version_notice(tmp_project)
    assert notice is not None
    assert __version__ in notice
    assert "0.5.0" in notice
    assert "feat-memory deploy" in notice
    assert "quando doer" in notice


def test_no_notice_when_versions_match(tmp_project):
    """A2: versões iguais → None."""
    _seed_meta(tmp_project, version=__version__)
    assert version_check.consumer_version_notice(tmp_project) is None


def test_no_notice_when_same_major_minor_differs(tmp_project):
    """ADR-0050/0051: mesmo MAJOR, minor/patch diferentes → silencioso
    ("upgrade quando doer" — a tool não induz cadência de upgrade)."""
    major = str(__version__).split(".", 1)[0]
    _seed_meta(tmp_project, version=f"{major}.998.7")
    assert version_check.consumer_version_notice(tmp_project) is None


def test_no_notice_when_deployed_version_unparseable(tmp_project):
    """Versão deployed não-semver → fail-soft, sem notice espúrio."""
    _seed_meta(tmp_project, version="banana")
    assert version_check.consumer_version_notice(tmp_project) is None


def test_no_notice_when_meta_absent(tmp_path):
    """A3: sem .meta.yaml → None (consumer pré-v0.6, fail-soft)."""
    assert version_check.consumer_version_notice(tmp_path) is None


def test_no_notice_when_meta_lacks_version_field(tmp_project):
    """meta.yaml sem campo `version` → None (fail-soft)."""
    am = tmp_project / ".feat-memory"
    am.mkdir(parents=True, exist_ok=True)
    (am / ".meta.yaml").write_text(
        "schema_version: 1\ndeployed_at: 2026-05-05T00:00:00+00:00\n",
        encoding="utf-8",
    )
    assert version_check.consumer_version_notice(tmp_project) is None


def test_no_notice_when_disabled_via_meta(tmp_project):
    """A4: version_check_enabled: false → None mesmo se versões diferem."""
    _seed_meta(tmp_project, version="0.5.0", version_check_enabled=False)
    assert version_check.consumer_version_notice(tmp_project) is None


def test_notice_emitted_when_explicitly_enabled(tmp_project):
    """version_check_enabled: true não suprime quando há diff (default-on equivalent)."""
    _seed_meta(tmp_project, version="0.5.0", version_check_enabled=True)
    notice = version_check.consumer_version_notice(tmp_project)
    assert notice is not None


# --- run() subcommand ---------------------------------------------------


def test_run_prints_notice_on_diff(tmp_project, capsys, monkeypatch):
    """A5: subcomando standalone imprime notice quando há diff."""
    _seed_meta(tmp_project, version="0.5.0")
    monkeypatch.setattr(_paths, "ROOT", None, raising=False)
    monkeypatch.chdir(tmp_project)

    rc = version_check.run(argparse.Namespace())

    assert rc == 0
    captured = capsys.readouterr()
    assert "0.5.0" in captured.err
    assert __version__ in captured.err


def test_run_prints_up_to_date_when_match(tmp_project, capsys, monkeypatch):
    """A5: sem diff, imprime 'atualizado' na stdout, exit 0."""
    _seed_meta(tmp_project, version=__version__)
    monkeypatch.setattr(_paths, "ROOT", None, raising=False)
    monkeypatch.chdir(tmp_project)

    rc = version_check.run(argparse.Namespace())

    assert rc == 0
    captured = capsys.readouterr()
    assert "compatível" in captured.out
    assert __version__ in captured.out


def test_run_always_exits_zero(tmp_project, monkeypatch):
    """A6: exit 0 sempre — soft, ADR-0008 fail-open preservado."""
    _seed_meta(tmp_project, version="0.5.0")
    monkeypatch.setattr(_paths, "ROOT", None, raising=False)
    monkeypatch.chdir(tmp_project)
    assert version_check.run(argparse.Namespace()) == 0


# --- audit integration --------------------------------------------------


def test_audit_emits_notice_when_versions_differ(tmp_project, capsys, monkeypatch):
    """A1: audit imprime notice na stderr quando versões diferem, sem mudar exit code."""
    from feat_memory.governance import audit

    am = tmp_project / ".feat-memory"
    am.mkdir(parents=True, exist_ok=True)
    _seed_meta(tmp_project, version="0.5.0")
    (tmp_project / "AGENTS.md").write_text(
        "---\nschema_version: 1\nproject: x\nconstraints: []\n"
        "references: {}\nbudgets: {}\n---\n", encoding="utf-8",
    )
    (am / "STATE.md").write_text(
        "---\nschema_version: 2\nupdated_at: 2026-05-05T00:00:00Z\n"
        "active_features: []\n---\n", encoding="utf-8",
    )

    monkeypatch.setattr(_paths, "ROOT", tmp_project, raising=False)
    monkeypatch.setattr(_paths, "AGENT", tmp_project / "AGENTS.md", raising=False)
    monkeypatch.setattr(_paths, "CLAUDE", tmp_project / "CLAUDE.md", raising=False)
    monkeypatch.setattr(_paths, "STATE", am / "STATE.md", raising=False)
    monkeypatch.setattr(_paths, "MANIFEST_DIR", am / "manifest", raising=False)
    monkeypatch.setattr(_paths, "FEATURES_DIR", am / "manifest" / "features", raising=False)
    monkeypatch.setattr(_paths, "ARCHIVE_DIR", am / "manifest" / "archive", raising=False)
    monkeypatch.setattr(_paths, "DECISIONS_DIR", am / "decisions", raising=False)
    monkeypatch.setattr(_paths, "SUPERSEDED_DIR", am / "decisions" / "superseded", raising=False)
    monkeypatch.setattr(_paths, "PROPOSALS_DIR", am / "decisions" / "proposals", raising=False)

    args = argparse.Namespace(
        cmd="audit", json=False, no_index=True, strict=False,
        check_collisions=None, check_staleness=None, func=audit.run,
    )
    rc = audit.run(args)

    captured = capsys.readouterr()
    # exit 0 (sem violações) — notice não muda exit code
    assert rc == 0
    # Notice impresso na stderr
    assert "0.5.0" in captured.err
    assert __version__ in captured.err


# --- CLI surface --------------------------------------------------------


def test_subcommand_registered(capsys):
    from feat_memory import cli
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "version-check" in out
