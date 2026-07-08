"""F-0045 / ADR-0050: amostragem adversarial de critérios de aceite.

Sorteio ponderado por risco (ADRs citados superseded/alterados), prompts de
REFUTAÇÃO em stdout, sempre exit 0 — a ferramenta pergunta, o LLM julga.
"""

from __future__ import annotations

import argparse

from feat_memory.memory import sample


def _seed_memory(root) -> None:
    am = root / ".feat-memory"
    (am / "manifest" / "features").mkdir(parents=True, exist_ok=True)
    (am / "decisions" / "superseded").mkdir(parents=True, exist_ok=True)


def _write_adr(root, num, *, status="accepted", superseded=False):
    sub = "decisions/superseded" if superseded else "decisions"
    path = root / ".feat-memory" / sub / f"{num}-adr-{num}.md"
    path.write_text(
        f"---\nid: ADR-{num}\ndate: 2026-01-01\nstatus: {status}\n---\n\n"
        f"# ADR-{num} · decisão\n",
        encoding="utf-8",
    )


def _write_feature(root, num, *, decisions=(), response="comporta-se bem"):
    path = (root / ".feat-memory" / "manifest" / "features"
            / f"F-{num}-capability-{num}.md")
    decs = ", ".join(decisions)
    path.write_text(
        f"---\nid: F-{num}\nname: capability-{num}\nstatus: shipped\n"
        f"user_value: valor {num}\ncontracts: {{}}\n"
        f"decisions: [{decs}]\n"
        "acceptance:\n"
        "  - {id: A1, pattern: event, trigger: \"algo acontece\", "
        f"response: \"{response}\"}}\n"
        "---\n",
        encoding="utf-8",
    )


def _run(root, capsys, **kw) -> tuple[int, str]:
    args = argparse.Namespace(
        cmd="sample", path=str(root), count=kw.get("count", 3),
        seed=kw.get("seed"), event=kw.get("event"), func=sample.run,
    )
    rc = sample.run(args)
    return rc, capsys.readouterr().out


def test_superseded_citation_ranks_first(audit_with_tmp_root, capsys):
    """Feature que cita ADR superseded vem antes das demais no sorteio."""
    root = audit_with_tmp_root
    _seed_memory(root)
    _write_adr(root, "0001", status="superseded", superseded=True)
    _write_adr(root, "0002")
    _write_feature(root, "0001", decisions=("ADR-0002",))
    _write_feature(root, "0002", decisions=("ADR-0001",))

    rc, out = _run(root, capsys, count=1, seed=7)

    assert rc == 0
    assert "F-0002" in out
    assert "F-0001" not in out
    assert "ADR-0001 superseded" in out


def test_seed_makes_output_deterministic(audit_with_tmp_root, capsys):
    root = audit_with_tmp_root
    _seed_memory(root)
    for n in ("0001", "0002", "0003", "0004"):
        _write_feature(root, n)

    _, first = _run(root, capsys, count=2, seed=42)
    _, second = _run(root, capsys, count=2, seed=42)

    assert first == second


def test_prompt_demands_refutation_and_carries_criteria(
        audit_with_tmp_root, capsys):
    root = audit_with_tmp_root
    _seed_memory(root)
    _write_feature(root, "0001", response="retorna top-k ordenado")

    rc, out = _run(root, capsys, count=1, seed=1)

    assert rc == 0
    assert "REFUTAR" in out
    assert "FALHE RUIDOSAMENTE" in out
    assert "retorna top-k ordenado" in out
    assert "[A1]" in out


def test_no_candidates_exits_zero(audit_with_tmp_root, capsys):
    root = audit_with_tmp_root
    _seed_memory(root)

    rc, out = _run(root, capsys)

    assert rc == 0
    assert "nada a refutar" in out


def test_event_flag_is_recorded_in_output(audit_with_tmp_root, capsys):
    root = audit_with_tmp_root
    _seed_memory(root)
    _write_feature(root, "0001")

    rc, out = _run(root, capsys, count=1, seed=1, event="release")

    assert rc == 0
    assert "evento: release" in out


def test_subcommand_registered(capsys):
    import pytest
    from feat_memory import cli
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "sample" in capsys.readouterr().out
