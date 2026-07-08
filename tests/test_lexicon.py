"""F-0046 / ADR-0050: nudge de léxico de mecanismo em critérios de aceite.

Léxico derivado dos próprios ADRs (ortogonal: nada novo a manter); match em
texto EARS de features ativas emite `info` — nunca promovido por --strict.
"""

from __future__ import annotations

import argparse

from feat_memory.governance import audit, lexicon


def _seed_base(root, *, agent_extra="") -> None:
    am = root / ".feat-memory"
    (root / "AGENTS.md").write_text(
        "---\nschema_version: 2\nproject: x\nconstraints: []\n"
        "references: {}\nbudgets: {}\n---\n\n"
        f"Constituição do projeto. {agent_extra}\n", encoding="utf-8",
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


def _write_adr(root, num, *, tags="", title="decisão"):
    path = root / ".feat-memory" / "decisions" / f"{num}-adr-{num}.md"
    path.write_text(
        f"---\nid: ADR-{num}\ndate: 2026-01-01\nstatus: accepted\n"
        f"tags: [{tags}]\n---\n\n# ADR-{num} · {title}\n",
        encoding="utf-8",
    )


def _write_feature(root, *, response, name="render-graph",
                   user_value="renderiza o grafo"):
    path = (root / ".feat-memory" / "manifest" / "features"
            / "F-0001-render-graph.md")
    path.write_text(
        "---\nid: F-0001\nname: " + name + "\nstatus: proposed\n"
        "user_value: " + user_value + "\ncontracts: {}\n"
        "acceptance:\n"
        "  - {id: A1, pattern: event, trigger: \"nós são inseridos\", "
        f"response: \"{response}\"}}\n"
        "---\n",
        encoding="utf-8",
    )


def _info_issues(result):
    return [i for i in result["issues"]
            if i["severity"] == "info" and "termo de mecanismo" in i["message"]]


def test_tag_term_in_criterion_emits_info(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _write_adr(root, "0001", tags="atrator, forcas")
    _write_feature(root, response="posiciona os nós pelo atrator central")

    result = audit.run_audit(write_indices=False)

    found = _info_issues(result)
    assert len(found) == 1
    assert "'atrator'" in found[0]["message"]
    assert "ADR-0001" in found[0]["message"]


def test_title_term_requires_two_adrs(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _write_adr(root, "0001", title="modelo de gravidade contínua")
    _write_feature(root, response="usa gravidade nas arestas")

    assert _info_issues(audit.run_audit(write_indices=False)) == []

    _write_adr(root, "0002", title="gravidade substituída por molas")
    found = _info_issues(audit.run_audit(write_indices=False))
    assert len(found) == 1
    assert "'gravidade'" in found[0]["message"]


def test_constitution_vocabulary_is_sanctioned(audit_with_tmp_root):
    """Termo presente no AGENTS.md sai do léxico — identidade promovida à
    constituição é governada lá, não nudgada aqui."""
    root = audit_with_tmp_root
    _seed_base(root, agent_extra="A identidade do produto é o atrator.")
    _write_adr(root, "0001", tags="atrator")
    _write_feature(root, response="posiciona os nós pelo atrator central")

    assert _info_issues(audit.run_audit(write_indices=False)) == []


def test_feature_own_vocabulary_is_exempt(audit_with_tmp_root):
    """Termo no name/user_value da própria feature é capacidade declarada."""
    root = audit_with_tmp_root
    _seed_base(root)
    _write_adr(root, "0001", tags="atrator")
    _write_feature(root, response="posiciona os nós pelo atrator central",
                   name="atrator-layout", user_value="layout por atrator")

    assert _info_issues(audit.run_audit(write_indices=False)) == []


def test_stopwords_and_short_tokens_never_enter_lexicon(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _write_adr(root, "0001", tags="para, uso, sempre, x1")
    _write_feature(root, response="para uso sempre que x1 existir")

    assert _info_issues(audit.run_audit(write_indices=False)) == []


def test_one_info_per_feature_term_pair(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _write_adr(root, "0001", tags="atrator")
    path = (root / ".feat-memory" / "manifest" / "features"
            / "F-0001-render-graph.md")
    path.write_text(
        "---\nid: F-0001\nname: render-graph\nstatus: proposed\n"
        "user_value: renderiza\ncontracts: {}\n"
        "acceptance:\n"
        "  - {id: A1, pattern: event, trigger: \"atrator liga\", "
        "response: \"atrator move\"}\n"
        "  - {id: A2, pattern: ubiquitous, requirement: \"atrator estável\"}\n"
        "---\n",
        encoding="utf-8",
    )

    assert len(_info_issues(audit.run_audit(write_indices=False))) == 1


def test_strict_never_blocks_on_lexicon_infos(audit_with_tmp_root, capsys):
    """Integração: audit --strict com infos presentes → exit 0 (nudge,
    jamais gate)."""
    root = audit_with_tmp_root
    _seed_base(root)
    _write_adr(root, "0001", tags="atrator")
    _write_feature(root, response="posiciona os nós pelo atrator central")

    args = argparse.Namespace(
        cmd="audit", json=False, no_index=True, strict=True,
        check_collisions=None, check_staleness=None, path=None,
        func=audit.run,
    )
    rc = audit.run(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "nudge(s) heurístico(s)" in out


def test_lexicon_extraction_is_deterministic(audit_with_tmp_root):
    root = audit_with_tmp_root
    _seed_base(root)
    _write_adr(root, "0001", tags="atrator, mola")
    _write_adr(root, "0002", tags="colisao")

    assert (lexicon.extract_mechanism_lexicon()
            == lexicon.extract_mechanism_lexicon())
