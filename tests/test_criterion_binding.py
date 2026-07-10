"""F-0049 / ADR-0052: binding referencial critério↔teste.

Convenção opt-in: teste que cita o token `F-NNNN-AN` cobre aquele critério.
Grep com word-boundary, restrito aos arquivos de contracts.tests da própria
feature — presença de citação, nunca execução.
"""

from __future__ import annotations

import argparse

from feat_memory.memory import binding, sample
from feat_memory.governance import audit


def _fm(root, *, tests, criteria=("A1", "A2")):
    return {
        "id": "F-0001",
        "name": "capability",
        "status": "shipped",
        "contracts": {"tests": tests},
        "acceptance": [
            {"id": cid, "pattern": "ubiquitous", "requirement": f"req {cid}"}
            for cid in criteria
        ],
    }


def _write_test_file(root, name, content):
    d = root / "tests"
    d.mkdir(exist_ok=True)
    (d / name).write_text(content, encoding="utf-8")
    return f"tests/{name}"


def test_token_in_test_file_binds_criterion(audit_with_tmp_root):
    """Binding: F-0049-A1."""
    root = audit_with_tmp_root
    path = _write_test_file(root, "test_x.py",
                            "def test_a1():\n    # F-0001-A1\n    pass\n")

    out = binding.criterion_bindings(_fm(root, tests=path))

    assert out["A1"] == ["tests/test_x.py"]
    assert out["A2"] == []


def test_token_match_is_case_insensitive_and_bounded(audit_with_tmp_root):
    """Binding: F-0049-A2."""
    root = audit_with_tmp_root
    path = _write_test_file(root, "test_x.py",
                            "# f-0001-a1 em minúsculas\n"
                            "# F-0001-A22 não é o A2\n")

    out = binding.criterion_bindings(_fm(root, tests=path))

    assert out["A1"] == ["tests/test_x.py"]
    assert out["A2"] == []  # A22 não faz boundary com A2


def test_missing_test_file_yields_unbound_without_error(audit_with_tmp_root):
    """Binding: F-0049-A3."""
    root = audit_with_tmp_root

    out = binding.criterion_bindings(_fm(root, tests="tests/inexistente.py"))

    assert out == {"A1": [], "A2": []}


def test_tests_as_mapping_is_supported(audit_with_tmp_root):
    """contracts.tests em forma de mapa (unit/e2e) — mesma forma aceita
    pelo drift check em schemas._collect_contract_paths."""
    root = audit_with_tmp_root
    unit = _write_test_file(root, "test_unit.py", "# F-0001-A1\n")
    e2e = _write_test_file(root, "test_e2e.py", "# F-0001-A2\n")

    out = binding.criterion_bindings(
        _fm(root, tests={"unit": unit, "e2e": e2e}))

    assert out["A1"] == ["tests/test_unit.py"]
    assert out["A2"] == ["tests/test_e2e.py"]


def test_coverage_summary_not_adopted_when_zero_bindings(audit_with_tmp_root):
    root = audit_with_tmp_root
    path = _write_test_file(root, "test_x.py", "def test_plain():\n    pass\n")

    summary = binding.coverage_summary([_fm(root, tests=path)])

    assert summary == {"total": 2, "bound": 0, "adopted": False}


def test_coverage_summary_counts_bound_criteria(audit_with_tmp_root):
    root = audit_with_tmp_root
    path = _write_test_file(root, "test_x.py", "# F-0001-A1\n")

    summary = binding.coverage_summary([_fm(root, tests=path)])

    assert summary == {"total": 2, "bound": 1, "adopted": True}


_METRICS_STUB = {
    "schema_compliance": 1.0,
    "constraint_conformance": {"checked": 0, "pass": True, "violations": 0},
    "state_freshness_hours": None,
    "manifest_coverage": 1.0,
    "manifest_drift": [],
    "manifest_velocity": {
        "shipped_last_30d": 0, "in_progress_open": 0,
        "deprecated_still_referenced": 0,
    },
    "decision_health": {
        "accepted": 0, "superseded": 0,
        "supersession_ratio": 0, "stale_over_180d": 0,
    },
}


def test_report_shows_dash_when_convention_not_adopted(capsys):
    """Binding: F-0049-A4. Convenção opt-in: 0 bindings não é dívida."""
    metrics = {**_METRICS_STUB,
               "criterion_coverage": {"total": 5, "bound": 0, "adopted": False}}
    audit.print_report({"metrics": metrics, "issues": []})
    out = capsys.readouterr().out

    assert "Cobertura por critério:    —" in out


def test_report_shows_ratio_when_adopted(capsys):
    metrics = {**_METRICS_STUB,
               "criterion_coverage": {"total": 5, "bound": 3, "adopted": True}}
    audit.print_report({"metrics": metrics, "issues": []})
    out = capsys.readouterr().out

    assert "3/5" in out


def test_sample_prompt_annotates_bound_criterion(audit_with_tmp_root, capsys):
    """Binding: F-0049-A5. O prompt de refutação aponta o teste declarado."""
    root = audit_with_tmp_root
    am = root / ".feat-memory"
    (am / "manifest" / "features").mkdir(parents=True, exist_ok=True)
    (am / "decisions").mkdir(parents=True, exist_ok=True)
    _write_test_file(root, "test_cap.py", "# F-0001-A1\n")
    (am / "manifest" / "features" / "F-0001-capability.md").write_text(
        "---\nid: F-0001\nname: capability\nstatus: shipped\n"
        "user_value: valor\ncontracts: {tests: tests/test_cap.py}\n"
        "acceptance:\n"
        "  - {id: A1, pattern: ubiquitous, requirement: \"invariante\"}\n"
        "---\n",
        encoding="utf-8",
    )

    args = argparse.Namespace(cmd="sample", path=str(root), count=1,
                              seed=1, event=None, func=sample.run)
    rc = sample.run(args)
    out = capsys.readouterr().out

    assert rc == 0
    assert "[teste declarado: tests/test_cap.py]" in out
