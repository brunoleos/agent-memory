"""ADR-0052: roster de skills no bloco AGENTS gerado dos frontmatters.

O template carrega só o token `{SKILLS_ROSTER}`; o texto de cada linha vive
no `summary` do próprio SKILL.md — o roster não consegue driftar porque não
existe cópia."""

from __future__ import annotations

import argparse

from feat_memory import deploy


def _args(target):
    return argparse.Namespace(
        target=str(target), force=False, no_merge=False, no_hooks=True,
        profile=None, cmd="deploy", func=deploy.run,
    )


def test_roster_is_generated_from_skill_summaries():
    roster = deploy._skills_roster()
    # ordem editorial: ciclo de vida
    assert roster.index("memory-deploy") < roster.index("memory-bootstrap")
    assert roster.index("memory-bootstrap") < roster.index("memory-debrief")
    assert roster.index("memory-debrief") < roster.index("memory-pull-brief")
    # cada linha carrega o summary do frontmatter correspondente
    assert "gênese retroativa multi-fonte" in roster
    assert "teste do agente frio" in roster
    assert "reconciliar o UNRELEASED.md" in roster


def test_deployed_agents_block_has_no_token_and_carries_summaries(tmp_project):
    deploy.run(_args(tmp_project))

    text = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")

    assert "{SKILLS_ROSTER}" not in text
    assert "- **`memory-deploy`** —" in text
    assert "- **`memory-debrief`** —" in text
    assert "teste do agente frio" in text


def test_redeploy_roster_is_idempotent(tmp_project):
    deploy.run(_args(tmp_project))
    first = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")

    deploy.run(_args(tmp_project))
    second = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")

    assert first == second
