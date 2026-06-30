"""Testes end-to-end do `feat-memory deploy <target>`."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pytest

from feat_memory import deploy
from feat_memory.shared.parsing import parse_frontmatter


def _args(target: Path | str, *, force: bool = False, no_merge: bool = False,
          no_hooks: bool = True, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        target=str(target),
        force=force,
        no_merge=no_merge,
        no_hooks=no_hooks,
        dry_run=dry_run,
        cmd="deploy",
        func=deploy.run,
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    """Mapa relpath→bytes de todo arquivo sob root, exceto o .git/."""
    snap: dict[str, bytes] = {}
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.relative_to(root).parts:
            snap[str(p.relative_to(root))] = p.read_bytes()
    return snap


# --- dry-run --------------------------------------------------------------

def test_dry_run_on_fresh_project_writes_nothing(tmp_project, capsys):
    rc = deploy.run(_args(tmp_project, dry_run=True))
    out = capsys.readouterr().out

    assert rc == 0
    # Nenhum artefato foi criado.
    assert not (tmp_project / "AGENTS.md").exists()
    assert not (tmp_project / "CLAUDE.md").exists()
    assert not (tmp_project / ".feat-memory").exists()
    assert not (tmp_project / "skills").exists()
    assert not (tmp_project / ".gitignore").exists()
    # Mas reporta o que faria, no condicional.
    assert "[DRY-RUN]" in out
    assert "criaria: AGENTS.md" in out
    assert "Nada foi escrito" in out


def test_dry_run_after_deploy_is_byte_identical(tmp_project):
    """Garantia anti-mutação: um dry-run sobre um projeto já deployado não
    altera um único byte (cobre a classe 'guard de escrita esquecido')."""
    assert deploy.run(_args(tmp_project)) == 0
    before = _snapshot(tmp_project)

    assert deploy.run(_args(tmp_project, dry_run=True)) == 0
    after = _snapshot(tmp_project)

    assert after == before


def test_dry_run_reports_in_sync_after_deploy(tmp_project, capsys):
    deploy.run(_args(tmp_project))
    capsys.readouterr()  # descarta a saída do deploy real

    deploy.run(_args(tmp_project, dry_run=True))
    out = capsys.readouterr().out

    # Skills idênticas não geram falsa mudança; meta sempre muda (timestamp).
    assert "já em dia: memory-deploy" in out
    assert "atualizaria: .feat-memory/.meta.yaml" in out


def test_dry_run_warns_about_stale_frontmatter(tmp_project, capsys):
    """#1: o dry-run sinaliza frontmatter stale que o deploy não corrige."""
    (tmp_project / "AGENTS.md").write_text(
        "---\n"
        "schema_version: 2\n"
        "project: t\n"
        "references:\n"
        "  state: ./.agent-memory/STATE.md\n"
        "  methodology: https://github.com/x/feat-memory/blob/v0.1.0/METHODOLOGY.md\n"
        "budgets:\n"
        "  state_max_bytes: 4096\n"
        "---\n\n# T\n",
        encoding="utf-8",
    )
    deploy.run(_args(tmp_project, dry_run=True))
    out = capsys.readouterr().out

    assert "⚠ frontmatter desatualizado" in out
    assert "aviso(s) de frontmatter para corrigir à mão" in out
    # E não escreveu nada no frontmatter.
    assert "state: ./.agent-memory/STATE.md" in (tmp_project / "AGENTS.md").read_text(
        encoding="utf-8")


def test_dry_run_detects_env_already_done(tmp_project, capsys):
    """#2: após um deploy real com hooks, o dry-run reporta já-instalado/
    já-configurado em vez de super-reportar configuraria/instalaria."""
    deploy.run(_args(tmp_project, no_hooks=False))
    capsys.readouterr()

    deploy.run(_args(tmp_project, no_hooks=False, dry_run=True))
    out = capsys.readouterr().out

    assert "já configurado: merge.ours.driver" in out
    assert "já instalado: pre-commit" in out
    assert "configuraria" not in out
    assert "instalaria" not in out


def test_dry_run_footer_splits_file_and_env_scopes(tmp_project, capsys):
    """#3: o rodapé separa arquivos de ações de ambiente (não mistura escopos)."""
    deploy.run(_args(tmp_project, no_hooks=False, dry_run=True))
    out = capsys.readouterr().out

    # Projeto fresco: arquivos + ambiente, ambos contados e rotulados.
    assert "arquivo(s)" in out
    assert "ação(ões) de ambiente" in out


def test_deploy_creates_all_artifacts(tmp_project):
    rc = deploy.run(_args(tmp_project))
    assert rc == 0

    for path in (
        tmp_project / "AGENTS.md",
        tmp_project / "CLAUDE.md",
        tmp_project / ".feat-memory" / "changelog" / "UNRELEASED.md",
        tmp_project / ".feat-memory" / "ideas.md",
        tmp_project / ".gitattributes",
        tmp_project / ".gitignore",
    ):
        assert path.is_file(), f"esperado: {path}"

    assert (tmp_project / ".feat-memory" / "manifest" / "features").is_dir()
    assert (tmp_project / ".feat-memory" / "decisions" / "proposals").is_dir()
    assert (tmp_project / "skills" / "memory-deploy" / "SKILL.md").is_file()
    assert (tmp_project / "skills" / "memory-bootstrap" / "SKILL.md").is_file()
    assert (tmp_project / "skills" / "memory-debrief" / "SKILL.md").is_file()
    assert (tmp_project / "skills" / "memory-pull-brief" / "SKILL.md").is_file()


def test_deploy_migrates_legacy_agent_memory_layout(tmp_project):
    """Consumidor no layout antigo: deploy migra .agent-memory/ → .feat-memory/."""
    old = tmp_project / ".agent-memory" / "manifest" / "features"
    old.mkdir(parents=True)
    (tmp_project / ".agent-memory" / "STATE.md").write_text(
        "# old state\n", encoding="utf-8")

    rc = deploy.run(_args(tmp_project))
    assert rc == 0
    assert not (tmp_project / ".agent-memory").exists()
    assert (tmp_project / ".feat-memory" / "STATE.md").is_file()
    # STATE preservado (deploy não sobrescreve STATE existente)
    assert "old state" in (tmp_project / ".feat-memory" / "STATE.md").read_text(
        encoding="utf-8")


def test_migrate_legacy_layout_is_noop_when_already_new(tmp_project):
    (tmp_project / ".feat-memory").mkdir()
    migrated = deploy.migrate_legacy_layout(tmp_project)
    assert migrated is False
    assert (tmp_project / ".feat-memory").is_dir()


def test_migrate_legacy_layout_does_not_clobber_existing(tmp_project):
    """Se ambos existem, não sobrescreve o novo — deixa o legado p/ revisão."""
    (tmp_project / ".agent-memory").mkdir()
    (tmp_project / ".feat-memory").mkdir()
    (tmp_project / ".feat-memory" / "marker").write_text("keep", encoding="utf-8")

    migrated = deploy.migrate_legacy_layout(tmp_project)
    assert migrated is False
    assert (tmp_project / ".feat-memory" / "marker").read_text(
        encoding="utf-8") == "keep"
    assert (tmp_project / ".agent-memory").exists()


def test_migrate_legacy_layout_handles_rename_error(tmp_project, monkeypatch):
    """Erro de rename (lock/permissão) → avisa e retorna False, sem traceback cru."""
    (tmp_project / ".agent-memory").mkdir()

    def _boom(self, *a, **k):
        raise OSError("arquivo travado")

    monkeypatch.setattr(Path, "rename", _boom)
    assert deploy.migrate_legacy_layout(tmp_project) is False
    # não destruiu o legado ao falhar
    assert (tmp_project / ".agent-memory").exists()


def test_deploy_creates_claude_subagent(tmp_project):
    """B2: deploy projeta o subagent de governança em .claude/agents/."""
    rc = deploy.run(_args(tmp_project))
    assert rc == 0

    agent = tmp_project / ".claude" / "agents" / "memory-debrief.md"
    assert agent.is_file(), f"esperado subagent em {agent}"

    fm, body = parse_frontmatter(agent)
    assert fm["name"] == "memory-debrief"
    # Wrapper fino: pré-carrega a skill homônima (fonte única da lógica).
    assert "memory-debrief" in (fm.get("skills") or [])
    # Comportamento "pede permissão antes de commitar" mora no corpo.
    assert "commit" in body.lower()


def test_deploy_subagent_is_idempotent(tmp_project):
    """Redeploy sobrescreve sem duplicar (conteúdo de metodologia)."""
    deploy.run(_args(tmp_project))
    rc = deploy.run(_args(tmp_project))
    assert rc == 0
    agents_dir = tmp_project / ".claude" / "agents"
    assert sorted(p.name for p in agents_dir.glob("*.md")) == ["memory-debrief.md"]


def test_deploy_is_idempotent(tmp_project):
    deploy.run(_args(tmp_project))
    rc = deploy.run(_args(tmp_project))
    assert rc == 0

    gitignore = (tmp_project / ".gitignore").read_text(encoding="utf-8")
    # Bloco de sentinelas não pode duplicar em re-execuções
    assert gitignore.count("# >>> feat-memory >>>") == 1
    assert gitignore.count("# <<< feat-memory <<<") == 1
    assert ".feat-memory-deploy/" in gitignore


def test_deploy_appends_methodology_block_to_existing_agent_md(tmp_project):
    """AGENTS.md já existente recebe o bloco com sentinelas anexado."""
    custom = "# Constituição custom do meu projeto\n\n## Identidade\n\nFoo.\n"
    (tmp_project / "AGENTS.md").write_text(custom, encoding="utf-8")

    rc = deploy.run(_args(tmp_project))
    assert rc == 0

    content = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")
    # Conteúdo original preservado
    assert "# Constituição custom do meu projeto" in content
    assert "## Identidade" in content
    assert "Foo." in content
    # Bloco com sentinelas anexado
    assert "<!-- >>> feat-memory >>> -->" in content
    assert "<!-- <<< feat-memory <<< -->" in content
    assert "## feat-memory" in content
    # Sem fila de merge gerada (mecanismo legado removido)
    assert not (tmp_project / ".feat-memory-deploy").exists()


def test_deploy_redeploy_is_idempotent_on_block(tmp_project):
    """Re-deploy refresca o bloco sem duplicar e sem tocar conteúdo do usuário."""
    deploy.run(_args(tmp_project))
    # Usuário adiciona seção própria fora do bloco
    extra = "\n## Identidade\n\nProjeto teste.\n"
    agent_md = tmp_project / "AGENTS.md"
    agent_md.write_text(
        agent_md.read_text(encoding="utf-8") + extra, encoding="utf-8"
    )

    deploy.run(_args(tmp_project))

    final = agent_md.read_text(encoding="utf-8")
    # Seção do usuário preservada
    assert "## Identidade" in final
    assert "Projeto teste." in final
    # Bloco aparece exatamente uma vez (não duplica)
    assert final.count("<!-- >>> feat-memory >>> -->") == 1
    assert final.count("<!-- <<< feat-memory <<< -->") == 1


def test_deploy_force_overwrites_existing(tmp_project):
    custom = "# meu custom\n"
    (tmp_project / "AGENTS.md").write_text(custom, encoding="utf-8")

    rc = deploy.run(_args(tmp_project, force=True))
    assert rc == 0

    new_content = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")
    assert new_content != custom
    assert "Constituição" in new_content  # vem do template


def test_deploy_no_merge_skips_existing_without_queueing(tmp_project):
    custom = "# meu custom\n"
    (tmp_project / "AGENTS.md").write_text(custom, encoding="utf-8")

    rc = deploy.run(_args(tmp_project, no_merge=True))
    assert rc == 0

    # Conteúdo preservado
    assert (tmp_project / "AGENTS.md").read_text(encoding="utf-8") == custom
    # Sem fila de merge gerada
    assert not (tmp_project / ".feat-memory-deploy" / "merge-queue").exists()


def test_deploy_invalid_target_returns_error(tmp_path):
    rc = deploy.run(_args(tmp_path / "nao-existe"))
    assert rc == 1


def test_deploy_target_must_be_directory(tmp_path):
    file_path = tmp_path / "arquivo.txt"
    file_path.write_text("conteudo")
    rc = deploy.run(_args(file_path))
    assert rc == 1


def test_deploy_reaches_audit_step(tmp_project, capsys):
    """Mesmo sem o binário no PATH, o header da auditoria deve aparecer."""
    deploy.run(_args(tmp_project))
    out = capsys.readouterr().out
    assert "Auditoria inicial:" in out


@pytest.mark.skipif(
    shutil.which("feat-memory") is None,
    reason="feat-memory binary not on PATH; audit subprocess não pode rodar",
)
def test_deploy_audit_subprocess_succeeds(tmp_project, capsys):
    """Quando o binário está no PATH, a auditoria deve rodar sem warnings."""
    deploy.run(_args(tmp_project))
    out = capsys.readouterr().out
    assert "AVISO: 'feat-memory' não encontrado" not in out
    assert "auditoria retornou" not in out  # só aparece se rc != 0


def test_deploy_substitutes_version_in_agent_md(tmp_project):
    """O placeholder {VERSION} deve ser substituído pela versão atual."""
    from feat_memory import __version__
    deploy.run(_args(tmp_project))
    content = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")
    assert "{VERSION}" not in content
    assert f"v{__version__}/METHODOLOGY.md" in content


def test_deploy_injects_frontmatter_into_legacy_agent_md(tmp_project):
    """AGENTS.md em prosa, sem frontmatter, recebe o esqueleto injetado.

    Regressão (ADR-0029): antes, deploy só anexava o bloco com sentinelas e
    deixava o arquivo sem schema_version/project/..., fazendo a auditoria
    falhar com conformidade 0.00 logo após adoção legacy.
    """
    prose = "# Constituição do projeto\n\nSomos uma SPA vanilla JS.\n"
    (tmp_project / "AGENTS.md").write_text(prose, encoding="utf-8")

    rc = deploy.run(_args(tmp_project))
    assert rc == 0

    content = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")
    # Frontmatter foi prependido (arquivo começa com ---)
    assert content.startswith("---\n")
    fm, _ = parse_frontmatter(tmp_project / "AGENTS.md")
    for field in ("schema_version", "project", "constraints", "references",
                  "budgets"):
        assert field in fm, f"campo obrigatório ausente após injeção: {field}"
    # Prosa do mantenedor preservada, abaixo do frontmatter
    assert "Somos uma SPA vanilla JS." in content
    # Bloco da metodologia também presente
    assert "<!-- >>> feat-memory >>> -->" in content


def test_deploy_does_not_inject_frontmatter_when_present(tmp_project):
    """AGENTS.md que já tem frontmatter não recebe um segundo bloco."""
    existing = (
        "---\nschema_version: 2\nproject: meu-proj\nconstraints: []\n"
        "references: {}\nbudgets: {}\n---\n\n# Const\n\nProsa.\n"
    )
    (tmp_project / "AGENTS.md").write_text(existing, encoding="utf-8")

    deploy.run(_args(tmp_project))

    content = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")
    # Exatamente um frontmatter (uma abertura `---` no topo + um fechamento)
    assert content.startswith("---\n")
    assert content.count("\n---\n") == 1
    assert "project: meu-proj" in content
    assert "TODO-nome-do-projeto" not in content


def test_deploy_frontmatter_injection_is_idempotent(tmp_project):
    """Re-deploy não injeta um segundo esqueleto de frontmatter."""
    prose = "# Const\n\nProsa do projeto.\n"
    (tmp_project / "AGENTS.md").write_text(prose, encoding="utf-8")

    deploy.run(_args(tmp_project))
    deploy.run(_args(tmp_project))

    content = (tmp_project / "AGENTS.md").read_text(encoding="utf-8")
    assert content.count("schema_version:") == 1
    assert content.count("<!-- >>> feat-memory >>> -->") == 1


def test_deploy_ideas_refreshes_stale_header_preserves_entries(tmp_project):
    """Defeito 2.2.0: ideas.md migrado mantinha header velho. Deploy refresca o
    header (conteúdo de metodologia) e preserva as entradas do usuário."""
    fm = tmp_project / ".feat-memory"
    fm.mkdir(parents=True, exist_ok=True)
    (fm / "ideas.md").write_text(
        "# Backlog de sugestões\n\nPropostas de evolução do sistema (ADR-0046).\n\n"
        "<!-- Entradas abaixo. -->\n\n## minha-ideia\n\n- **tipo:** produto-capacidade\n",
        encoding="utf-8")
    deploy.run(_args(tmp_project))
    ideas = (fm / "ideas.md").read_text(encoding="utf-8")
    assert "## minha-ideia" in ideas            # entrada do usuário preservada
    assert "funil do futuro" in ideas           # header novo (ADR-0047)
    assert "Backlog de sugestões" not in ideas  # header velho sumiu


def test_deploy_does_not_create_legacy_artifacts(tmp_project):
    """Regressão do cutover 2.0.0: deploy não recria STATE.md/checkpoints/CHANGELOG.md."""
    deploy.run(_args(tmp_project))
    assert not (tmp_project / ".feat-memory" / "STATE.md").exists()
    assert not (tmp_project / ".feat-memory" / "checkpoints").exists()
    assert not (tmp_project / "CHANGELOG.md").exists()


def test_deploy_defaults_to_cwd(tmp_project, monkeypatch):
    """deploy sem target usa o diretório atual (W3, ADR-0033)."""
    monkeypatch.chdir(tmp_project)
    rc = deploy.run(_args("."))
    assert rc == 0
    assert (tmp_project / "AGENTS.md").is_file()
    assert (tmp_project / ".feat-memory" / "changelog" / "UNRELEASED.md").is_file()


def test_deploy_meta_omits_cli_path(tmp_project):
    """meta.yaml não versiona mais cli_path (W6, ADR-0034)."""
    import yaml
    deploy.run(_args(tmp_project))
    data = yaml.safe_load(
        (tmp_project / ".feat-memory" / ".meta.yaml").read_text(encoding="utf-8")
    )
    assert "cli_path" not in data
    assert data["version"]


def test_deploy_cleans_stale_pending_dir(tmp_project):
    """Re-deploy obliterates leftover .feat-memory-deploy/ from prior run."""
    # Simula deploy anterior com merges pendentes
    deploy_dir = tmp_project / ".feat-memory-deploy"
    deploy_dir.mkdir()
    (deploy_dir / "merge-queue").write_text("STALE.md\n")
    (deploy_dir / "pending").mkdir()
    (deploy_dir / "pending" / "STALE.md.new").write_text("conteudo antigo")

    # Run deploy sem AGENT.md customizado (não dispara nova fila)
    deploy.run(_args(tmp_project))

    # Diretório de deploy não deve ter sobrado nada do estado anterior
    assert not (deploy_dir / "merge-queue").exists()
    assert not (deploy_dir / "pending" / "STALE.md.new").exists()
