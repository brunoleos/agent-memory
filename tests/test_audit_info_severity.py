"""ADR-0050: severidade `info` é o canal de nudges heurísticos — nunca
promovida por `audit --strict`, nunca muda exit code.

Congela a semântica de promoção do --strict (audit.run): só `warning` é
promovido a error. Um refactor que passe a promover `info` quebra estes
testes antes de quebrar o pre-commit de um consumidor.
"""

from __future__ import annotations

import argparse

from feat_memory.governance import audit


METRICS_STUB = {
    "schema_compliance": 1.0,
    "constraint_conformance": {"checked": 0, "pass": True, "violations": 0},
    "state_freshness_hours": None,
    "manifest_coverage": 1.0,
    "manifest_drift": [],
    "manifest_velocity": {
        "shipped_last_30d": 0,
        "in_progress_open": 0,
        "deprecated_still_referenced": 0,
    },
    "decision_health": {
        "accepted": 0,
        "superseded": 0,
        "supersession_ratio": 0,
        "stale_over_180d": 0,
    },
}


def _issue(severity: str) -> dict:
    return {"artifact": "x.md", "severity": severity, "message": "m"}


def _run(monkeypatch, issues: list[dict], *, strict: bool) -> int:
    monkeypatch.setattr(
        audit, "run_audit", lambda **kw: {"metrics": METRICS_STUB, "issues": issues}
    )
    args = argparse.Namespace(
        cmd="audit", json=True, no_index=True, strict=strict,
        check_collisions=None, check_staleness=None, path=None, func=audit.run,
    )
    return audit.run(args)


def test_info_not_promoted_by_strict(monkeypatch):
    assert _run(monkeypatch, [_issue("info")], strict=True) == 0


def test_info_is_silent_without_strict(monkeypatch):
    assert _run(monkeypatch, [_issue("info")], strict=False) == 0


def test_warning_promoted_by_strict(monkeypatch):
    """Controle: a promoção de warning continua existindo."""
    assert _run(monkeypatch, [_issue("warning")], strict=True) == 1


def test_warning_not_promoted_without_strict(monkeypatch):
    assert _run(monkeypatch, [_issue("warning")], strict=False) == 0


def test_error_blocks_regardless(monkeypatch):
    assert _run(monkeypatch, [_issue("error")], strict=False) == 1
    assert _run(monkeypatch, [_issue("error")], strict=True) == 1


def test_mixed_info_and_warning_under_strict(monkeypatch):
    """Só o warning conta na promoção; o info não engorda o exit."""
    rc = _run(monkeypatch, [_issue("info"), _issue("warning")], strict=True)
    assert rc == 1  # por causa do warning, não do info


def test_report_segregates_info_count(capsys):
    """print_report exibe contagem por severidade e a nota sobre info."""
    result = {
        "metrics": METRICS_STUB,
        "issues": [_issue("info"), _issue("warning")],
    }
    audit.print_report(result)
    out = capsys.readouterr().out
    assert "1 warning" in out
    assert "1 info" in out
    assert "nunca promovido por --strict" in out


def test_report_states_referential_scope(capsys):
    """O cabeçalho do report declara o escopo real da garantia (ADR-0050)."""
    audit.print_report({"metrics": METRICS_STUB, "issues": []})
    out = capsys.readouterr().out
    assert "integridade referencial" in out
    assert "não verdade semântica" in out
