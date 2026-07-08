"""F-0043 / ADR-0050: orçamento de prosa do corpo de features por perfil.

A feature é registro ortogonal (frontmatter); prosa no corpo é onde memória
paralela se acumula. core: 10 linhas não-vazias; full: 40. Warning normal
(promovível sob --strict). Archive é isento (história imutável).
"""

from __future__ import annotations

from feat_memory.memory import schemas
from feat_memory.memory.schemas import PROSE_BUDGET_BY_PROFILE, validate_feature


def _write_feature(dirpath, n_body_lines, *, blank_every=0,
                   name="F-0100-sample-capability.md"):
    dirpath.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(n_body_lines):
        lines.append(f"linha de prosa {i}")
        if blank_every and (i + 1) % blank_every == 0:
            lines.append("")
    path = dirpath / name
    path.write_text(
        "---\n"
        "id: F-0100\n"
        "name: sample-capability\n"
        "status: proposed\n"
        "user_value: registro de exemplo\n"
        "contracts: {}\n"
        "acceptance: []\n"
        "---\n\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return path


def _prose_issues(issues):
    return [i for i in issues if "orçamento de prosa" in i.message]


def test_body_over_core_limit_warns(tmp_path):
    path = _write_feature(tmp_path, 12)
    _, issues = validate_feature(path, prose_limit=PROSE_BUDGET_BY_PROFILE["core"],
                                 profile="core")
    found = _prose_issues(issues)
    assert len(found) == 1
    assert found[0].severity == "warning"
    assert "12 linhas" in found[0].message
    assert "core" in found[0].message


def test_same_body_clean_under_full_limit(tmp_path):
    path = _write_feature(tmp_path, 12)
    _, issues = validate_feature(path, prose_limit=PROSE_BUDGET_BY_PROFILE["full"],
                                 profile="full")
    assert _prose_issues(issues) == []


def test_body_over_full_limit_warns(tmp_path):
    path = _write_feature(tmp_path, 45)
    _, issues = validate_feature(path, prose_limit=PROSE_BUDGET_BY_PROFILE["full"],
                                 profile="full")
    assert len(_prose_issues(issues)) == 1


def test_no_limit_means_no_check(tmp_path):
    path = _write_feature(tmp_path, 200)
    _, issues = validate_feature(path)
    assert _prose_issues(issues) == []


def test_blank_lines_do_not_count(tmp_path):
    # 9 linhas de prosa intercaladas com vazias: não-vazias <= 10 → limpo.
    path = _write_feature(tmp_path, 9, blank_every=1)
    _, issues = validate_feature(path, prose_limit=10, profile="core")
    assert _prose_issues(issues) == []


def test_frontmatter_only_feature_is_always_clean(tmp_path):
    path = _write_feature(tmp_path, 0)
    _, issues = validate_feature(path, prose_limit=10, profile="core")
    assert _prose_issues(issues) == []


# --- integração: run_audit resolve o perfil e aplica o limite --------------


def _seed_minimal_memory(root, *, profile: str) -> None:
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
        f"schema_version: 2\nversion: 0.0.0\nprofile: {profile}\n",
        encoding="utf-8",
    )


def test_audit_applies_core_limit(audit_with_tmp_root):
    from feat_memory.governance import audit

    root = audit_with_tmp_root
    _seed_minimal_memory(root, profile="core")
    _write_feature(root / ".feat-memory" / "manifest" / "features", 12)

    result = audit.run_audit(write_indices=False)

    assert result["metrics"]["profile"] == "core"
    msgs = [i["message"] for i in result["issues"]
            if "orçamento de prosa" in i["message"]]
    assert len(msgs) == 1


def test_audit_full_profile_tolerates_short_rationale(audit_with_tmp_root):
    from feat_memory.governance import audit

    root = audit_with_tmp_root
    _seed_minimal_memory(root, profile="full")
    _write_feature(root / ".feat-memory" / "manifest" / "features", 12)

    result = audit.run_audit(write_indices=False)

    assert result["metrics"]["profile"] == "full"
    assert all("orçamento de prosa" not in i["message"]
               for i in result["issues"])


def test_audit_archive_exempt_from_prose_budget(audit_with_tmp_root):
    from feat_memory.governance import audit

    root = audit_with_tmp_root
    _seed_minimal_memory(root, profile="core")
    _write_feature(root / ".feat-memory" / "manifest" / "archive", 50)

    result = audit.run_audit(write_indices=False)

    assert all("orçamento de prosa" not in i["message"]
               for i in result["issues"])
