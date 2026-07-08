"""audit.py — Auditoria dos artefatos de memória + métricas + drift.

Orquestrador. Importa schemas de `memory.schemas` para validar, gera
índices via `memory.indexing`, e adiciona camadas próprias de
governança: cross-check de IDs ativos (F-0011), staleness check
opt-in (F-0011), collision detection pré-merge, métricas de saúde.

Subcomando da CLI: `feat-memory audit`. AGENTS.md fica na raiz do
project root; changelog/, manifest/ e decisions/ ficam em .feat-memory/.

Uso:
    feat-memory audit                       # relatório + índices
    feat-memory audit --json                # output em JSON (CI)
    feat-memory audit --strict              # warnings viram errors
    feat-memory audit --no-index            # só valida
    feat-memory audit --check-collisions origin/main
    feat-memory audit --check-staleness=7   # warning se STATE desatualizado

Saída:
    Exit code 0 se nenhum erro foi encontrado.
    Exit code 1 se houve erro de schema, ou drift em modo --strict.

Parte de `governance/`. ADR-0021 explica por que vive aqui mesmo
importando `memory.schemas`: a direção de dependência importa
(governance ⇒ memory permitido; memory ⇒ governance proibido).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from feat_memory.shared import paths as _paths
from feat_memory.shared.parsing import parse_frontmatter, read_meta
from feat_memory.memory import indexing
from feat_memory.memory.schemas import (
    DEFAULT_STATE_BUDGET,
    Issue,
    validate_agent,
    validate_decision,
    validate_feature,
    validate_state,
)
from feat_memory.governance import constraints as _constraints


# Re-export para compat: outros módulos (e testes) podem ter referências
# a `audit.parse_frontmatter` ou `audit.read_meta`. Mantemos os nomes
# disponíveis nesta superfície durante a migração.
__all__ = [
    "Issue",
    "parse_frontmatter",
    "read_meta",
    "validate_state_crosscheck",
    "validate_state_freshness",
    "validate_release_status",
    "check_constraints",
    "released_versions",
    "STALENESS_WARN_HOURS",
    "_is_code_path",
    "STALENESS_NONCODE_PREFIXES",
    "STALENESS_NONCODE_EXACT",
    "check_collisions",
    "compute_metrics",
    "run_audit",
    "print_report",
    "add_subparser",
    "run",
]

# Acima deste limiar (14 dias), `print_report` destaca o frescor do STATE
# como aviso visual. NÃO vira Issue — staleness no momento do commit é
# responsabilidade (soft, fail-open) de F-0013 `check-staleness-staged`,
# e promover a Issue faria o pre-commit hook (`audit --strict`) bloquear
# o commit, transformando um nudge em coerção. ADR-0024.
STALENESS_WARN_HOURS = 14 * 24

# Re-export: executor dos checkers de constraint (ADR-0028). Vive em
# governance/constraints.py; exposto aqui para os testes e a compat de API.
check_constraints = _constraints.check_constraints


def validate_state_crosscheck(state_fm: dict,
                              features: list[dict],
                              decisions: list[dict]) -> list[Issue]:
    """Verifica que cada ID em active_features/active_decisions existe.

    Não detecta drift de contracts (isso é responsabilidade de
    `validate_feature`); aqui o foco é "memória mentirosa" — o changelog/
    UNRELEASED.md citando IDs que não têm arquivo correspondente. ADR-0014.

    O que este check (e o audit como um todo) garante é integridade
    REFERENCIAL e movimento conjunto doc↔código — não verdade semântica dos
    conteúdos. Um critério de aceite pode estar referencialmente íntegro e
    factualmente apodrecido; essa camada é coberta pela amostragem
    adversarial definida no ADR-0050, não por este gate.

    `features` deve ser a lista combinada de features ativas e
    arquivadas (run_audit faz a união antes de chamar). Cobertura
    histórica completa por F-0012.
    """
    issues: list[Issue] = []
    feature_ids = {f.get("id") for f in features if f.get("id")}
    decision_ids = {d.get("id") for d in decisions if d.get("id")}

    for fid in state_fm.get("active_features") or []:
        if fid not in feature_ids:
            issues.append(Issue(
                "changelog/UNRELEASED.md", "error",
                f"entrada cita {fid} mas nenhum arquivo "
                f"F-NNNN-*.md existe em manifest/features/ ou archive/",
            ))

    for did in state_fm.get("active_decisions") or []:
        if did not in decision_ids:
            issues.append(Issue(
                "changelog/UNRELEASED.md", "error",
                f"entrada cita {did} mas nenhum arquivo "
                f"NNNN-*.md existe em decisions/",
            ))

    return issues


def released_versions(root: Path) -> set[str]:
    """Conjunto de versões já released, derivado do changelog e git tags.

    Fonte de verdade tripla, fail-soft (retorna o que conseguir):
    - Arquivos por-tag `.feat-memory/changelog/<X.Y.Z>.md` (layout novo, ADR-0042).
    - Seções datadas `## [X.Y.Z]` num CHANGELOG.md legado (layout antigo).
    - Tags Git no formato `vX.Y.Z`.

    A união é o que `validate_release_status` confronta contra o campo
    `version` das features. ADR-0024.
    """
    versions: set[str] = set()

    changelog_dir = root / ".feat-memory" / "changelog"
    if changelog_dir.exists():
        for p in changelog_dir.glob("*.md"):
            m = re.match(r"^(\d+\.\d+\.\d+)\.md$", p.name)
            if m:
                versions.add(m.group(1))

    changelog = root / "CHANGELOG.md"
    if changelog.exists():
        try:
            text = changelog.read_text(encoding="utf-8")
        except OSError:
            text = ""
        for m in re.finditer(r"^##\s*\[(\d+\.\d+\.\d+)\]", text, re.MULTILINE):
            versions.add(m.group(1))

    try:
        out = subprocess.check_output(
            ["git", "tag"], text=True, stderr=subprocess.DEVNULL, cwd=root,
        )
        for line in out.splitlines():
            m = re.match(r"^v(\d+\.\d+\.\d+)$", line.strip())
            if m:
                versions.add(m.group(1))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return versions


def validate_release_status(features: list[dict],
                            released: set[str]) -> list[Issue]:
    """Detecta features que mentem sobre o próprio status.

    Uma feature com `status: in_progress` cujo `version` já consta como
    released (CHANGELOG/tag) é drift: o trabalho saiu, mas a memória ainda
    o reporta aberto — foi exatamente assim que F-0010..F-0019 acumularam
    11 features fantasma in_progress após 4 releases. Warning (soft), mas
    promovível por `--strict`: commitar uma feature já-released ainda
    marcada in_progress deve falhar. ADR-0024.

    Fail-soft: sem versões released conhecidas (`released` vazio), não
    emite nada — ausência de CHANGELOG/tags não é sinal.
    """
    issues: list[Issue] = []
    if not released:
        return issues
    for f in features:
        if f.get("status") != "in_progress":
            continue
        ver = f.get("version")
        if ver and str(ver) in released:
            issues.append(Issue(
                "manifest", "warning",
                f"{f.get('id', 'F-????')} declara version {ver} (já "
                f"released) mas status=in_progress; marque shipped e rode "
                f"`feat-memory archive`",
            ))
    return issues


# Paths considerados "código" para staleness check. Tudo que NÃO tem
# um destes prefixos / não é um destes nomes exatos é tratado como
# código (ADR-0014). Lista deliberadamente conservadora.
STALENESS_NONCODE_PREFIXES = (".feat-memory/", "tests/", "docs/", ".claude/")
STALENESS_NONCODE_EXACT = {
    "AGENTS.md", "README.md", "METHODOLOGY.md",
    "USER_GUIDE.md", "FUTURE_IMPROVEMENTS.md", "LICENSE",
    ".gitignore", ".gitattributes",
}


def _is_code_path(path: str) -> bool:
    p = path.replace("\\", "/")
    if p in STALENESS_NONCODE_EXACT:
        return False
    return not any(p.startswith(prefix) for prefix in STALENESS_NONCODE_PREFIXES)


def validate_state_freshness(root: Path, days: int = 7) -> list[Issue]:
    """Detecta sessões que tocaram código sem registrar no changelog/UNRELEASED.md.

    Opt-in via `feat-memory audit --check-staleness[=N]`. Heurística
    descrita em ADR-0014. Fail-soft: sem git ou sem commits no período,
    retorna lista vazia (não promove ausência de histórico a sinal).
    """
    try:
        out = subprocess.check_output(
            ["git", "log", f"--since={days} days ago",
             "--name-only", "--pretty=format:"],
            text=True, stderr=subprocess.DEVNULL, cwd=root,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    touched = {line.strip() for line in out.splitlines() if line.strip()}
    if not touched:
        return []

    unreleased_relpath = ".feat-memory/changelog/UNRELEASED.md"
    unreleased_was_touched = any(
        p.replace("\\", "/") == unreleased_relpath for p in touched
    )
    if unreleased_was_touched:
        return []

    code_files = [p for p in touched if _is_code_path(p)]
    if not code_files:
        return []

    return [Issue(
        "changelog/UNRELEASED.md", "warning",
        f"sem registro há {days}+ dia(s) enquanto código foi commitado "
        f"({len(code_files)} arquivo(s) tocado(s) — ex: "
        f"{sorted(code_files)[0]}); considere /memory-debrief",
    )]


# --- collision detection (pre-merge) ---------------------------------------

def get_id_to_file_map(ref: str, subdir: str) -> dict[str, str]:
    """Mapeia IDs para nomes de arquivos num ref Git."""
    try:
        out = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", ref, subdir],
            text=True, stderr=subprocess.DEVNULL, cwd=_paths.ROOT,
        )
    except subprocess.CalledProcessError:
        return {}

    mapping: dict[str, str] = {}
    for line in out.splitlines():
        name = Path(line).name
        if subdir == ".feat-memory/manifest/features":
            m = re.match(r"^(F-\d{4})-", name)
            if m:
                mapping[m.group(1)] = name
        elif subdir == ".feat-memory/decisions":
            m = re.match(r"^(\d{4})-", name)
            if m:
                mapping[f"ADR-{m.group(1)}"] = name
    return mapping


def check_collisions(base_ref: str) -> list[Issue]:
    """Detecta colisões de IDs entre HEAD atual e o base_ref."""
    issues: list[Issue] = []

    base_features = get_id_to_file_map(base_ref, ".feat-memory/manifest/features")
    head_features = get_id_to_file_map("HEAD", ".feat-memory/manifest/features")
    for fid, head_name in sorted(head_features.items()):
        base_name = base_features.get(fid)
        if base_name and base_name != head_name:
            issues.append(Issue(
                "manifest", "error",
                f"colisão de ID com {base_ref}: {fid} aponta para "
                f"'{head_name}' aqui e '{base_name}' lá "
                f"(renumere antes do merge)",
            ))

    base_adrs = get_id_to_file_map(base_ref, ".feat-memory/decisions")
    head_adrs = get_id_to_file_map("HEAD", ".feat-memory/decisions")
    for aid, head_name in sorted(head_adrs.items()):
        base_name = base_adrs.get(aid)
        if base_name and base_name != head_name:
            issues.append(Issue(
                "decisions", "error",
                f"colisão de ID com {base_ref}: {aid} aponta para "
                f"'{head_name}' aqui e '{base_name}' lá "
                f"(renumere antes do merge)",
            ))

    return issues


# --- metrics ---------------------------------------------------------------

def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _resolve_active_feature_paths(state_fm: dict) -> list[Path]:
    """Resolve IDs de active_features para caminhos de arquivo.

    Busca em FEATURES_DIR e ARCHIVE_DIR (F-NNNN-*.md).
    """
    ids = state_fm.get("active_features") or []
    if not ids:
        return []
    candidates: list[Path] = []
    for d in (_paths.FEATURES_DIR, _paths.ARCHIVE_DIR):
        if d.exists():
            candidates.extend(d.glob("F-*.md"))
    id_set = set(ids)
    return [p for p in candidates
            if re.match(r"^(F-\d{4})-", p.name)
            and p.name.split("-")[1] and f"F-{p.name.split('-')[1]}" in id_set]


def _resolve_active_decision_paths(state_fm: dict) -> list[Path]:
    """Resolve IDs de active_decisions para caminhos de arquivo.

    Busca em DECISIONS_DIR e SUPERSEDED_DIR (NNNN-*.md → ADR-NNNN).
    """
    ids = state_fm.get("active_decisions") or []
    if not ids:
        return []
    candidates: list[Path] = []
    for d in (_paths.DECISIONS_DIR, _paths.SUPERSEDED_DIR):
        if d.exists():
            candidates.extend(p for p in d.glob("[0-9]*.md") if p.parent == d)
    id_set = set(ids)
    result: list[Path] = []
    for p in candidates:
        m = re.match(r"^(\d{4})-", p.name)
        if m and f"ADR-{m.group(1)}" in id_set:
            result.append(p)
    return result


def compute_metrics(state_fm: dict, features: list[dict],
                    decisions: list[dict], issues: list[Issue]) -> dict:
    errors = sum(1 for i in issues if i.severity == "error")

    freshness = None
    updated = _parse_dt(state_fm.get("updated_at"))
    if updated:
        delta = datetime.now(timezone.utc) - updated
        freshness = round(delta.total_seconds() / 3600, 1)

    with_tests = 0
    for f in features:
        tests = (f.get("contracts") or {}).get("tests")
        if not tests:
            continue
        paths = tests if isinstance(tests, list) else [tests]
        if all((_paths.ROOT / str(p).split("::")[0]).exists() for p in paths):
            with_tests += 1
    coverage = round(with_tests / len(features), 2) if features else 1.0

    drift = [i.message for i in issues if i.message.startswith("drift:")]

    now = datetime.now(timezone.utc)
    shipped_30d = 0
    in_progress = 0
    deprecated_referenced = 0
    deprecated_ids = {f.get("id") for f in features
                      if f.get("status") == "deprecated"}

    for f in features:
        if f.get("status") == "shipped":
            intro = _parse_dt(f.get("introduced"))
            if intro and (now - intro).days <= 30:
                shipped_30d += 1
        elif f.get("status") == "in_progress":
            in_progress += 1
        for dep in f.get("depends_on") or []:
            if dep in deprecated_ids and f.get("status") != "deprecated":
                deprecated_referenced += 1

    accepted = sum(1 for d in decisions if d.get("status") == "accepted")
    superseded = sum(1 for d in decisions if d.get("status") == "superseded")
    super_ratio = round(superseded / len(decisions), 2) if decisions else 0.0

    stale = 0
    for d in decisions:
        if d.get("status") != "accepted":
            continue
        date = _parse_dt(d.get("date"))
        if date and (now - date).days > 180:
            stale += 1

    return {
        "schema_compliance": 1.0 if errors == 0 else 0.0,
        "state_freshness_hours": freshness,
        "manifest_coverage": coverage,
        "manifest_drift": drift,
        "manifest_velocity": {
            "shipped_last_30d": shipped_30d,
            "in_progress_open": in_progress,
            "deprecated_still_referenced": deprecated_referenced,
        },
        "decision_health": {
            "accepted": accepted,
            "superseded": superseded,
            "supersession_ratio": super_ratio,
            "stale_over_180d": stale,
        },
        "violations_count": errors,
    }


# --- entry points ----------------------------------------------------------

def run_audit(write_indices: bool = True,
              check_collisions_against: str | None = None,
              check_staleness_days: int | None = None) -> dict:
    all_issues: list[Issue] = []

    agent_fm, issues = validate_agent(_paths.AGENT)
    all_issues.extend(issues)

    # Frontmatter stale: o deploy refresca o bloco mas não toca references/budgets,
    # então paths legados (.agent-memory/, state:, state_max_bytes) ou URL de
    # methodology numa versão antiga passam silenciosos. Warning durável (F-0040).
    from feat_memory.shared.frontmatter import detect_stale_frontmatter
    from feat_memory import __version__ as _fm_version
    for _msg in detect_stale_frontmatter(agent_fm, _fm_version):
        all_issues.append(Issue("AGENTS.md", "warning", _msg))

    # Constitution enforced: executa os checkers declarativos das constraints
    # com bloco `check` (ADR-0028). Violação herda a severity da constraint
    # (hard→error/bloqueia, soft→warning); `check` malformado é error de schema.
    cc = _constraints.check_constraints(agent_fm, _paths.ROOT)
    all_issues.extend(cc["issues"])

    max_state = (agent_fm.get("budgets") or {}).get(
        "state_max_bytes", DEFAULT_STATE_BUDGET
    )
    if _paths.STATE.exists():
        state_fm, issues = validate_state(_paths.STATE, max_state)
        all_issues.extend(issues)
    else:
        # Layout novo (sem STATE.md): o orçamento de retomada é derivado das
        # referências do changelog/UNRELEASED.md (ADR-0043). Mantém o mesmo
        # shape consumido por compute_metrics e validate_state_crosscheck.
        from feat_memory.memory import changelog
        active = changelog.derive_active_refs(_paths.ROOT)
        state_fm = {
            "active_features": active["features"],
            "active_decisions": active["decisions"],
        }

    features: list[dict] = []
    if _paths.FEATURES_DIR.exists():
        for fp in sorted(_paths.FEATURES_DIR.glob("F-*.md")):
            fm, issues = validate_feature(fp)
            all_issues.extend(issues)
            if fm:
                features.append(fm)

    # Features arquivadas (F-0012, ADR-0015).
    archived_features: list[dict] = []
    if _paths.ARCHIVE_DIR.exists():
        for fp in sorted(_paths.ARCHIVE_DIR.glob("F-*.md")):
            fm, issues = validate_feature(fp)
            all_issues.extend(issues)
            if fm:
                archived_features.append(fm)

    decisions: list[dict] = []
    if _paths.DECISIONS_DIR.exists():
        for dp in sorted(_paths.DECISIONS_DIR.glob("[0-9]*.md")):
            if dp.parent != _paths.DECISIONS_DIR:
                continue
            fm, issues = validate_decision(dp)
            all_issues.extend(issues)
            if fm:
                decisions.append(fm)

    # ADRs superseded movidas para decisions/superseded/ (ADR-0023, F-0019).
    superseded_decisions: list[dict] = []
    if _paths.SUPERSEDED_DIR.exists():
        for dp in sorted(_paths.SUPERSEDED_DIR.glob("[0-9]*.md")):
            fm, issues = validate_decision(dp)
            all_issues.extend(issues)
            if fm:
                superseded_decisions.append(fm)

    all_features = features + archived_features
    all_decisions = decisions + superseded_decisions

    # Cross-check de IDs ativos contra arquivos existentes (ADR-0014).
    all_issues.extend(validate_state_crosscheck(state_fm, all_features, all_decisions))

    # Cross-check status vs. release: feature in_progress já released é
    # memória mentirosa (ADR-0024). Default-on, soft, fail-soft sem CHANGELOG/tags.
    all_issues.extend(validate_release_status(all_features, released_versions(_paths.ROOT)))

    # Detecção de colisões pré-merge (opcional)
    if check_collisions_against:
        all_issues.extend(check_collisions(check_collisions_against))

    # Staleness check (opt-in via --check-staleness; ADR-0014).
    if check_staleness_days is not None:
        all_issues.extend(validate_state_freshness(_paths.ROOT, check_staleness_days))

    if write_indices:
        indexing.regenerate_all_indexes(
            _paths.MANIFEST_DIR, _paths.ARCHIVE_DIR,
            _paths.DECISIONS_DIR, _paths.SUPERSEDED_DIR,
            features, archived_features,
            decisions, superseded_decisions,
        )

    metrics = compute_metrics(state_fm, all_features, all_decisions, all_issues)
    metrics["constraint_conformance"] = {
        "checked": cc["checked"],
        "violations": cc["violations"],
        "pass": cc["violations"] == 0,
    }
    return {
        "metrics": metrics,
        "issues": [asdict(i) for i in all_issues],
    }


def print_report(result: dict) -> None:
    m = result["metrics"]
    print("=" * 60)
    print("Relatório de auditoria")
    print("(integridade referencial e movimento conjunto — não verdade semântica)")
    print("=" * 60)
    print(f"Project root:              {_paths.ROOT}")
    print(f"Conformidade de schema:    {m['schema_compliance']:.2f}")
    cc = m.get("constraint_conformance") or {}
    if cc.get("checked"):
        if cc["pass"]:
            print(f"Conformidade constraints:  {cc['checked']} checada(s) — ok")
        else:
            print(f"Conformidade constraints:  {cc['checked']} checada(s) — "
                  f"⚠ {cc['violations']} violação(ões)")
    fresh = m["state_freshness_hours"]
    if fresh is not None and fresh > STALENESS_WARN_HOURS:
        dias = round(fresh / 24)
        print(f"Frescor de estado:         {fresh} h  "
              f"⚠ {dias} dias sem update — rode /memory-debrief")
    else:
        fresh_str = f"{fresh} h" if fresh is not None else "—"
        print(f"Frescor de estado:         {fresh_str}")
    print(f"Cobertura do manifest:     {m['manifest_coverage']:.0%}")
    print(f"Drift detectado:           {len(m['manifest_drift'])} casos")
    print()
    v = m["manifest_velocity"]
    print("Velocity:")
    print(f"  shipped (30d):           {v['shipped_last_30d']}")
    print(f"  em progresso:            {v['in_progress_open']}")
    print(f"  refs a deprecated:       {v['deprecated_still_referenced']}")
    print()
    h = m["decision_health"]
    print("Saúde de decisões:")
    print(f"  accepted:                {h['accepted']}")
    print(f"  superseded:              {h['superseded']} "
          f"(ratio {h['supersession_ratio']})")
    print(f"  > 180 dias sem revisão:  {h['stale_over_180d']}")
    print()

    issues = result["issues"]
    if issues:
        by_sev = {"error": 0, "warning": 0, "info": 0}
        for i in issues:
            by_sev[i["severity"]] = by_sev.get(i["severity"], 0) + 1
        print(f"Issues encontrados: {len(issues)} "
              f"({by_sev['error']} error, {by_sev['warning']} warning, "
              f"{by_sev['info']} info)")
        for i in issues:
            print(f"  [{i['severity']}] {i['artifact']}: {i['message']}")
        if by_sev["info"]:
            print("  (info = nudge heurístico; nunca promovido por --strict)")
    else:
        print("Nenhum issue encontrado.")


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "audit",
        help="Valida artefatos da metodologia e regenera índices",
    )
    p.add_argument("path", nargs="?", default=None,
                   help="raiz do projeto (default: descobre via git/cwd)")
    p.add_argument("--json", action="store_true",
                   help="output em JSON")
    p.add_argument("--no-index", action="store_true",
                   help="não regenerar índices")
    p.add_argument("--strict", action="store_true",
                   help="trata warnings (drift) como errors")
    p.add_argument("--check-collisions", metavar="REF",
                   help="detecta colisões de IDs contra REF "
                   "(ex: origin/main) antes de merge")
    p.add_argument("--check-staleness", nargs="?", const=7, type=int,
                   metavar="DAYS",
                   help="warning se commits dos últimos N dias (default 7) "
                   "tocaram código sem registrar no changelog/UNRELEASED.md (ADR-0014)")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    from pathlib import Path
    root = Path(args.path).resolve() if getattr(args, "path", None) else None
    _paths._init_paths(root)

    result = run_audit(
        write_indices=not args.no_index,
        check_collisions_against=args.check_collisions,
        check_staleness_days=args.check_staleness,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print_report(result)
        # F-0018: notice soft se consumer está desatualizado em relação ao CLI.
        # Não muda exit code (ADR-0022 + ADR-0008 fail-open).
        from feat_memory.governance.version_check import (
            consumer_version_notice, _print_notice,
        )
        notice = consumer_version_notice(_paths.ROOT)
        if notice:
            _print_notice(notice)
            # Guard de upgrade (W5): se a AGENTS.md está sem frontmatter (erros
            # "campo ausente") E o CLI é mais novo que o deploy, o remédio é
            # re-deployar — o deploy >=0.13 injeta o esqueleto de frontmatter
            # (ADR-0029). Liga o sintoma (schema 0.00) à causa/solução.
            missing_fm = any(
                i["artifact"] == "AGENTS.md"
                and str(i["message"]).startswith("campo ausente")
                for i in result["issues"]
            )
            if missing_fm:
                _print_notice(
                    "→ AGENTS.md sem frontmatter e CLI mais novo que o deploy: "
                    "re-rode `feat-memory deploy` para injetar o esqueleto de "
                    "frontmatter (v0.13+)."
                )

    issues = result["issues"]
    errors = sum(1 for i in issues if i["severity"] == "error")
    if args.strict:
        warnings = sum(1 for i in issues if i["severity"] == "warning")
        if warnings:
            print(f"\n[strict] {warnings} warning(s) promovidos a error.",
                  file=sys.stderr)
            errors += warnings
    return 1 if errors else 0
