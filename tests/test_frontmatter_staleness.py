"""Testes do detector de frontmatter stale (F-0040) e do check no audit."""

from __future__ import annotations

from feat_memory.shared.frontmatter import detect_stale_frontmatter


def test_clean_frontmatter_has_no_findings():
    fm = {
        "references": {
            "manifest_index": "./.feat-memory/manifest/INDEX.md",
            "unreleased": "./.feat-memory/changelog/UNRELEASED.md",
            "methodology": "https://github.com/x/feat-memory/blob/v2.5.0/METHODOLOGY.md",
        },
        "budgets": {"resumption_max_bytes": 12288},
    }
    assert detect_stale_frontmatter(fm, "2.5.0") == []


def test_local_methodology_path_is_not_flagged():
    fm = {"references": {"methodology": "./METHODOLOGY.md"}}
    assert detect_stale_frontmatter(fm, "2.5.0") == []


def test_detects_agent_memory_paths():
    fm = {"references": {"manifest_index": "./.agent-memory/manifest/INDEX.md"}}
    out = detect_stale_frontmatter(fm, "2.5.0")
    assert len(out) == 1 and ".agent-memory/" in out[0]


def test_detects_legacy_state_key_and_budget():
    fm = {
        "references": {"state": "./.feat-memory/STATE.md"},
        "budgets": {"state_max_bytes": 4096},
    }
    out = detect_stale_frontmatter(fm, "2.5.0")
    joined = " ".join(out)
    assert "references.state" in joined
    assert "state_max_bytes" in joined


def test_detects_outdated_methodology_version():
    fm = {"references": {
        "methodology": "https://github.com/x/feat-memory/blob/v0.1.0/METHODOLOGY.md"}}
    out = detect_stale_frontmatter(fm, "2.5.0")
    assert len(out) == 1 and "v0.1.0" in out[0] and "2.5.0" in out[0]


def test_matching_methodology_version_is_clean():
    fm = {"references": {
        "methodology": "https://github.com/x/feat-memory/blob/v2.5.0/METHODOLOGY.md"}}
    assert detect_stale_frontmatter(fm, "2.5.0") == []


def test_handles_missing_or_malformed_sections():
    assert detect_stale_frontmatter({}, "2.5.0") == []
    assert detect_stale_frontmatter({"references": None}, "2.5.0") == []
    assert detect_stale_frontmatter({"references": "oops"}, "2.5.0") == []
