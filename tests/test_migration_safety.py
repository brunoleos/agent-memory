"""ADR-0051: operações destrutivas sobre artefatos de memória exigem prova
de preservação de conteúdo.

Postmortem: a migração de changelog 2.x destruiu o UNRELEASED de um consumidor
porque era write-through sem backup e sem teste que asserisse a sobrevivência
do conteúdo. Estes testes fixam a regra para as superfícies destrutivas vivas:
`freeze_unreleased` (release) e os scaffolds idempotentes do deploy.
"""

from __future__ import annotations

from feat_memory.memory import changelog


def _seed_unreleased(root, body_lines: list[str]) -> None:
    changelog.ensure_scaffold(root)
    changelog.unreleased_path(root).write_text(
        "---\nschema_version: 1\n---\n\n# Não-lançado\n\n"
        + "\n".join(body_lines) + "\n",
        encoding="utf-8",
    )


def test_freeze_preserves_full_unreleased_body(tmp_path):
    """Cada linha de conteúdo do usuário sobrevive no arquivo congelado —
    inclusive prosa fora de bullet, que não conta como ref ativa mas é
    conteúdo do usuário do mesmo jeito."""
    body_lines = [
        "## Adicionado",
        "- entrega com detalhe insubstituível (F-0001, ADR-0001)",
        "nota em prosa solta que só existe aqui",
        "- outra entrega (F-0002)",
    ]
    _seed_unreleased(tmp_path, body_lines)

    target = changelog.freeze_unreleased(tmp_path, "9.9.9", "2026-07-08")

    frozen = target.read_text(encoding="utf-8")
    for line in body_lines:
        assert line in frozen, f"linha perdida no freeze: {line!r}"


def test_freeze_resets_unreleased_only_after_persisting(tmp_path):
    """O reset do UNRELEASED é aceitável porque o conteúdo já migrou —
    o par (congelado contém tudo, UNRELEASED = template) é a invariante."""
    _seed_unreleased(tmp_path, ["- algo em voo (F-0003)"])

    changelog.freeze_unreleased(tmp_path, "9.9.9", "2026-07-08")

    up = changelog.unreleased_path(tmp_path).read_text(encoding="utf-8")
    assert up == changelog.UNRELEASED_TEMPLATE


def test_freeze_refuses_to_overwrite_existing_release(tmp_path):
    """Releases são imutáveis: freeze sobre versão existente falha em vez de
    sobrescrever (proteção contra perda por re-execução)."""
    import pytest

    _seed_unreleased(tmp_path, ["- primeira (F-0001)"])
    changelog.freeze_unreleased(tmp_path, "9.9.9", "2026-07-08")
    _seed_unreleased(tmp_path, ["- segunda (F-0002)"])

    with pytest.raises(FileExistsError):
        changelog.freeze_unreleased(tmp_path, "9.9.9", "2026-07-09")


def test_ensure_scaffold_never_overwrites_existing_unreleased(tmp_path):
    """Scaffold idempotente: UNRELEASED existente jamais é tocado —
    a classe de bug do postmortem (recriação silenciosa) fica proibida."""
    changelog.ensure_scaffold(tmp_path)
    up = changelog.unreleased_path(tmp_path)
    up.write_text("conteúdo do usuário que não pode sumir\n", encoding="utf-8")

    changelog.ensure_scaffold(tmp_path)

    assert up.read_text(encoding="utf-8") == (
        "conteúdo do usuário que não pode sumir\n"
    )
