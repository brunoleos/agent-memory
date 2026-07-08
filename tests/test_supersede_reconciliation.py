"""F-0044 / ADR-0050: propagação de supersede com acknowledgment por arquivo.

Quando um ADR é superseded, citadores vivos do ID antigo geram warning até
serem listados em `reconciled:` do ADR que supersede (ou atualizarem a
citação). Referencial por construção — cobre o modo "nunca-revisitado".
"""

from __future__ import annotations

from feat_memory.governance import audit
from feat_memory.memory.schemas import validate_decision


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
    (am / "decisions" / "superseded").mkdir(parents=True, exist_ok=True)


def _write_decision(dirpath, num, *, status="accepted", supersedes=None,
                    superseded_by=None, reconciled=None, body=""):
    fields = [
        f"id: ADR-{num}", "date: 2026-01-01", f"status: {status}",
    ]
    if supersedes:
        fields.append(f"supersedes: [{', '.join(supersedes)}]")
    if superseded_by:
        fields.append(f"superseded_by: {superseded_by}")
    if reconciled is not None:
        items = ", ".join(reconciled)
        fields.append(f"reconciled: [{items}]")
    path = dirpath / f"{num}-decision-{num}.md"
    path.write_text(
        "---\n" + "\n".join(fields) + "\n---\n\n"
        f"# ADR-{num} · decisão {num}\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def _write_feature(root, body):
    path = (root / ".feat-memory" / "manifest" / "features"
            / "F-0001-sample-capability.md")
    path.write_text(
        "---\nid: F-0001\nname: sample-capability\nstatus: proposed\n"
        "user_value: exemplo\ncontracts: {}\nacceptance: []\n---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    return path


def _reconciliation_issues(result):
    return [i for i in result["issues"] if "sem reconciliação" in i["message"]]


def _setup_supersede_pair(root, *, reconciled=None):
    """ADR-0001 superseded por ADR-0002 (que declara supersedes)."""
    decisions = root / ".feat-memory" / "decisions"
    _write_decision(decisions / "superseded", "0001",
                    status="superseded", superseded_by="ADR-0002")
    _write_decision(decisions, "0002", supersedes=["ADR-0001"],
                    reconciled=reconciled)


def test_live_citer_without_ack_warns(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _setup_supersede_pair(root)
    _write_feature(root, "Deriva do modelo do ADR-0001.")

    result = audit.run_audit(write_indices=False)

    found = _reconciliation_issues(result)
    assert len(found) == 1
    assert "ADR-0001" in found[0]["message"]
    assert "ADR-0002" in found[0]["message"]
    assert "F-0001" in found[0]["artifact"]


def test_ack_in_reconciled_silences(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _setup_supersede_pair(
        root,
        reconciled=[".feat-memory/manifest/features/F-0001-sample-capability.md"],
    )
    _write_feature(root, "Deriva do modelo do ADR-0001.")

    result = audit.run_audit(write_indices=False)

    assert _reconciliation_issues(result) == []


def test_superseder_is_auto_exempt(audit_with_tmp_root):
    """O ADR que supersede cita o antigo por definição (supersedes/corpo) —
    nunca gera warning sobre si mesmo."""
    root = audit_with_tmp_root
    _seed_base(root)
    decisions = root / ".feat-memory" / "decisions"
    _write_decision(decisions / "superseded", "0001",
                    status="superseded", superseded_by="ADR-0002")
    _write_decision(decisions, "0002", supersedes=["ADR-0001"],
                    body="Substitui o ADR-0001 no corpo também.")

    result = audit.run_audit(write_indices=False)

    assert _reconciliation_issues(result) == []


def test_other_live_adr_citing_old_warns(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _setup_supersede_pair(root)
    decisions = root / ".feat-memory" / "decisions"
    _write_decision(decisions, "0003",
                    body="Referencia histórica ao ADR-0001 sem reconciliar.")

    result = audit.run_audit(write_indices=False)

    found = _reconciliation_issues(result)
    assert len(found) == 1
    assert "0003" in found[0]["artifact"]


def test_archive_and_superseded_are_exempt(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _setup_supersede_pair(root)
    archive = root / ".feat-memory" / "manifest" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "F-0002-old-capability.md").write_text(
        "---\nid: F-0002\nname: old-capability\nstatus: deprecated\n"
        "user_value: histórico\ncontracts: {}\nacceptance: []\n---\n\n"
        "Construída sob o ADR-0001.\n",
        encoding="utf-8",
    )

    result = audit.run_audit(write_indices=False)

    assert _reconciliation_issues(result) == []


def test_unreleased_citing_old_warns(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _setup_supersede_pair(root)
    (root / ".feat-memory" / "changelog" / "UNRELEASED.md").write_text(
        "---\nschema_version: 1\n---\n\n# Não-lançado\n\n"
        "- retomando o modelo do ADR-0001 (F-0001)\n",
        encoding="utf-8",
    )

    result = audit.run_audit(write_indices=False)

    found = _reconciliation_issues(result)
    # 1 do UNRELEASED; o crosscheck de F-0001 inexistente é outro issue.
    assert any("UNRELEASED" in i["artifact"] for i in found)


def test_no_superseded_adrs_no_scan(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    decisions = root / ".feat-memory" / "decisions"
    _write_decision(decisions, "0002")
    _write_feature(root, "Cita o ADR-0002 vigente — nenhum warning.")

    result = audit.run_audit(write_indices=False)

    assert _reconciliation_issues(result) == []


# --- validate_decision: forma e frescor do reconciled ----------------------


def test_reconciled_must_be_list_of_strings(audit_with_tmp_root, tmp_path):
    path = tmp_path / "0009-bad-reconciled.md"
    path.write_text(
        "---\nid: ADR-0009\ndate: 2026-01-01\nstatus: accepted\n"
        "reconciled: not-a-list\n---\n", encoding="utf-8",
    )
    _, issues = validate_decision(path)
    assert any("reconciled deve ser uma lista" in i.message
               and i.severity == "error" for i in issues)


def test_reconciled_stale_path_warns(audit_with_tmp_root, tmp_path):
    path = tmp_path / "0009-stale-reconciled.md"
    path.write_text(
        "---\nid: ADR-0009\ndate: 2026-01-01\nstatus: accepted\n"
        "reconciled: [caminho/que/nao/existe.md]\n---\n", encoding="utf-8",
    )
    _, issues = validate_decision(path)
    assert any("acknowledgment stale" in i.message
               and i.severity == "warning" for i in issues)
