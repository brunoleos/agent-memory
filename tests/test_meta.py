"""Testes do arquivo `.feat-memory/.meta.yaml` (F-0010, ADR-0013; profile
e schema_version 2 em F-0042/ADR-0050)."""

from __future__ import annotations

import argparse

import pytest
import yaml

from feat_memory import __version__, deploy
from feat_memory.governance import audit
from feat_memory.shared.parsing import resolve_profile


def _args(target, profile=None):
    return argparse.Namespace(
        target=str(target),
        force=False,
        no_merge=False,
        no_hooks=True,
        profile=profile,
        cmd="deploy",
        func=deploy.run,
    )


def _read_meta_dict(target):
    meta_path = target / ".feat-memory" / ".meta.yaml"
    return yaml.safe_load(meta_path.read_text(encoding="utf-8"))


def test_deploy_writes_meta_yaml(tmp_project):
    deploy.run(_args(tmp_project))
    meta_path = tmp_project / ".feat-memory" / ".meta.yaml"
    assert meta_path.is_file()

    data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert data["version"] == __version__
    assert "deployed_at" in data
    assert data["deployed_at"].endswith("+00:00")
    # cli_path removido em ADR-0034 (caminho local versionado, sem leitor)
    assert "cli_path" not in data
    assert data["telemetry_enabled"] is True


def test_deploy_meta_has_documentation_header(tmp_project):
    deploy.run(_args(tmp_project))
    meta_path = tmp_project / ".feat-memory" / ".meta.yaml"
    text = meta_path.read_text(encoding="utf-8")
    assert text.startswith("# Metadata de instalação do feat-memory.")
    assert "ADR-0013" in text


def test_redeploy_overwrites_meta_with_fresh_timestamp(tmp_project):
    deploy.run(_args(tmp_project))
    meta_path = tmp_project / ".feat-memory" / ".meta.yaml"
    first = yaml.safe_load(meta_path.read_text(encoding="utf-8"))

    deploy.run(_args(tmp_project))
    second = yaml.safe_load(meta_path.read_text(encoding="utf-8"))

    assert first["version"] == second["version"]
    # deployed_at deve ter sido recalculado (ainda que iguais por timestamp grosso)
    assert "deployed_at" in second


def test_read_meta_returns_dict_when_present(tmp_project):
    deploy.run(_args(tmp_project))
    data = audit.read_meta(tmp_project)
    assert data is not None
    assert data["version"] == __version__
    assert data["schema_version"] == 2


def test_read_meta_returns_none_when_absent(tmp_path):
    """Consumidor pré-v0.6 não tem .meta.yaml — não deve quebrar."""
    assert audit.read_meta(tmp_path) is None


def test_read_meta_raises_on_corrupt_yaml(tmp_project):
    meta_path = tmp_project / ".feat-memory" / ".meta.yaml"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text("not: valid: yaml: [unclosed", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML inválido"):
        audit.read_meta(tmp_project)


# --- profile (F-0042, ADR-0050) -------------------------------------------


def test_virgin_deploy_defaults_to_core(tmp_project):
    """A1: deploy sem --profile num target virgem grava profile core."""
    deploy.run(_args(tmp_project))
    assert _read_meta_dict(tmp_project)["profile"] == "core"


def test_profile_full_flag_persists(tmp_project):
    """deploy --profile full grava full no .meta.yaml."""
    deploy.run(_args(tmp_project, profile="full"))
    assert _read_meta_dict(tmp_project)["profile"] == "full"


def test_redeploy_without_flag_preserves_full(tmp_project):
    """A2: re-deploy sem --profile preserva o perfil já gravado (anti-clobber)."""
    deploy.run(_args(tmp_project, profile="full"))
    deploy.run(_args(tmp_project))
    assert _read_meta_dict(tmp_project)["profile"] == "full"


def test_redeploy_with_flag_switches_profile(tmp_project):
    """Flag explícita vence o perfil gravado — é o mecanismo de troca."""
    deploy.run(_args(tmp_project, profile="full"))
    deploy.run(_args(tmp_project, profile="core"))
    assert _read_meta_dict(tmp_project)["profile"] == "core"


def test_redeploy_pre_v3_meta_upgrades_to_full(tmp_project):
    """Instalação pré-v3 (meta sem profile) re-deployada sem flag recebe
    full — preserva o comportamento efetivo que ela já tinha; core é só
    para adoções novas (ADR-0050)."""
    am = tmp_project / ".feat-memory"
    am.mkdir(parents=True, exist_ok=True)
    (am / ".meta.yaml").write_text(
        "schema_version: 1\nversion: 2.5.0\n"
        "deployed_at: 2026-06-30T00:00:00+00:00\ntelemetry_enabled: true\n",
        encoding="utf-8",
    )
    deploy.run(_args(tmp_project))
    data = _read_meta_dict(tmp_project)
    assert data["profile"] == "full"
    assert data["schema_version"] == 2


# --- resolve_profile (governança) ------------------------------------------


def test_resolve_profile_fallback_full_when_meta_absent(tmp_path):
    assert resolve_profile(tmp_path) == "full"


def test_resolve_profile_reads_core(tmp_project):
    deploy.run(_args(tmp_project, profile="core"))
    assert resolve_profile(tmp_project) == "core"


def test_resolve_profile_fallback_full_on_invalid_value(tmp_project):
    am = tmp_project / ".feat-memory"
    am.mkdir(parents=True, exist_ok=True)
    (am / ".meta.yaml").write_text("profile: turbo\n", encoding="utf-8")
    assert resolve_profile(tmp_project) == "full"


def test_resolve_profile_fallback_full_on_corrupt_yaml(tmp_project):
    am = tmp_project / ".feat-memory"
    am.mkdir(parents=True, exist_ok=True)
    (am / ".meta.yaml").write_text("not: valid: yaml: [unclosed", encoding="utf-8")
    assert resolve_profile(tmp_project) == "full"
