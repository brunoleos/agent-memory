"""Conteúdo metodológico crítico das skills empacotadas (F-0039, ADR-0046).

Garante que a memory-debrief carrega o ritual de retrospectiva + captura de
sugestões e registra no UNRELEASED, e que a bootstrap lê o layout novo.
Pega regressão: uma skill voltar a citar o layout legado quebra o consumidor.
"""

from __future__ import annotations

from importlib.resources import files


def _skill(name: str) -> str:
    return (files("feat_memory") / "data" / "skills" / name / "SKILL.md").read_text(
        encoding="utf-8"
    )


def test_debrief_has_retrospective_and_ideas_triage():
    text = _skill("memory-debrief")
    assert "Retrospectiva" in text
    assert "ideas.md" in text


def test_debrief_registers_in_unreleased():
    assert "UNRELEASED" in _skill("memory-debrief")


def test_bootstrap_reads_unreleased_and_ideas_fallback():
    text = _skill("memory-bootstrap")
    assert "UNRELEASED" in text
    assert "ideas.md" in text


# --- reforma v3 (ADR-0050): doutrinas nas skills ---------------------------


def test_debrief_ends_with_cold_agent_test():
    """A pergunta final de todo debrief é o teste do agente frio."""
    text = _skill("memory-debrief")
    assert "agente frio" in text
    assert "por que não X?" in text


def test_debrief_carries_observable_doctrine():
    text = _skill("memory-debrief")
    assert "observáveis externos" in text
    assert "mecanismo é território de ADR" in text


def test_debrief_propagates_supersede_and_samples():
    text = _skill("memory-debrief")
    assert "reconciled" in text
    assert "feat-memory sample --event supersede" in text
    assert "feat-memory sample --event release" in text


def test_deploy_genesis_forbids_readme_transcription():
    text = _skill("memory-deploy")
    assert "frontmatter-only" in text
    assert "Nunca transcreva prosa de README" in text


def test_deploy_genesis_carries_observable_doctrine():
    text = _skill("memory-deploy")
    assert "observáveis externos" in text
    assert "observáveis de trajetória" in text


def test_every_skill_declares_a_summary():
    """O roster do bloco AGENTS é gerado do campo `summary` de cada skill
    (fonte única mecânica, ADR-0052) — skill sem summary quebra o roster."""
    for name in ("memory-deploy", "memory-bootstrap",
                 "memory-debrief", "memory-pull-brief"):
        text = _skill(name)
        assert text.startswith("---\n")
        frontmatter = text.split("---", 2)[1]
        assert "summary:" in frontmatter, f"{name} sem summary no frontmatter"
