"""schemas.py — Validação de schema dos quatro artefatos da metodologia.

`validate_agent`, `validate_state`, `validate_feature`, `validate_decision`
recebem um path e retornam (frontmatter, list[Issue]). Schemas seguem
ADR-0002 (constraints hard/soft) e ADR-0003 (acceptance EARS).

`Issue` é o tipo de violação compartilhado com `governance.audit` (que
adiciona métricas, drift e cross-check sobre essa base).

Parte de `memory/`. Importa apenas de `shared/`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from feat_memory.shared.parsing import parse_frontmatter
from feat_memory.shared import paths as _paths


FEATURE_FILE_RE = re.compile(r"^F-\d{4}-[a-z0-9-]+\.md$")
DECISION_FILE_RE = re.compile(r"^\d{4}-[a-z0-9-]+\.md$")
# Canônico X.Y.Z (alinhado ao `version` de features); prefixo `v` aceito
# por compatibilidade com os ADRs da gênese (v0.3.0), que usaram `vX.Y.Z`.
SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+$")

VALID_FEATURE_STATUS = {"proposed", "in_progress", "shipped", "deprecated"}
VALID_DECISION_STATUS = {"proposed", "accepted", "superseded", "deprecated"}

# Palavras de "balde de changelog" — tokens que, no NOME de uma feature, são um
# sinal de alta precisão de que ela empacota várias coisas em vez de nomear UMA
# capacidade (ADR-0035). Lista deliberadamente curta e inequívoca: nenhuma
# capacidade real se chama "polish"/"misc"/"various". A coesão de conteúdo (vários
# critérios sem relação) NÃO é checada — é ruidosa e cabe ao julgamento humano
# via litmus nas skills de autoria; aqui só o tell mecânico confiável é bloqueado.
CHANGELOG_NAME_WORDS = {
    "polish", "misc", "miscellaneous", "various", "assorted", "tweaks",
    "sundry", "melhorias", "diversos", "variados",
}

# Campos obrigatórios por artefato — fonte única, consumida tanto pelos
# `validate_*` quanto pelo gerador de referência de schema (schema_reference.py).
AGENT_REQUIRED = ["schema_version", "project", "constraints", "references", "budgets"]
STATE_REQUIRED = ["schema_version", "updated_at", "active_features"]
FEATURE_REQUIRED = ["id", "name", "status", "user_value", "contracts", "acceptance"]
DECISION_REQUIRED = ["id", "date", "status"]

# Campos reconhecidos-porém-opcionais — puramente documentais (os `validate_*`
# não os exigem). Existem para o gerador de referência listar o vocabulário
# completo de cada artefato sem que o agente precise ler schemas.py.
FEATURE_OPTIONAL = [
    "version", "owner", "introduced", "depends_on", "decisions", "metrics",
]
DECISION_OPTIONAL = [
    "version", "supersedes", "superseded_by", "affects_features", "related", "tags",
]

EARS_PATTERN_FIELDS: dict[str, set[str]] = {
    "ubiquitous": {"requirement"},
    "event":      {"trigger", "response"},
    "state":      {"state", "response"},
    "optional":   {"feature", "response"},
    "unwanted":   {"trigger", "response"},
    "complex":    {"requirement"},
}

DEFAULT_STATE_BUDGET = 4096


@dataclass
class Issue:
    artifact: str
    severity: str  # "error" | "warning" | "info"
    message: str
    # "info" nunca é promovida por `audit --strict` (ADR-0050): é o canal de
    # nudges heurísticos (ex.: léxico de mecanismo) que jamais bloqueiam commit.


def validate_agent(path: Path) -> tuple[dict, list[Issue]]:
    issues: list[Issue] = []
    if not path.exists():
        return {}, [Issue("AGENTS.md", "error", "arquivo ausente")]
    try:
        fm, _ = parse_frontmatter(path)
    except ValueError as e:
        return {}, [Issue("AGENTS.md", "error", str(e))]
    for key in AGENT_REQUIRED:
        if key not in fm:
            issues.append(Issue("AGENTS.md", "error", f"campo ausente: {key}"))
    return fm, issues


def validate_state(path: Path, max_bytes: int) -> tuple[dict, list[Issue]]:
    issues: list[Issue] = []
    if not path.exists():
        return {}, [Issue("STATE.md", "error", "arquivo ausente")]
    size = path.stat().st_size
    if size > max_bytes:
        issues.append(Issue(
            "STATE.md", "error",
            f"tamanho {size}B excede orçamento de {max_bytes}B",
        ))
    try:
        fm, _ = parse_frontmatter(path)
    except ValueError as e:
        return {}, [Issue("STATE.md", "error", str(e))]
    for key in STATE_REQUIRED:
        if key not in fm:
            issues.append(Issue("STATE.md", "error", f"campo ausente: {key}"))
    return fm, issues


def _collect_contract_paths(contracts: dict) -> list[str]:
    paths: list[str] = []
    for key in ("api", "schemas", "tests"):
        val = contracts.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            paths.append(val)
        elif isinstance(val, list):
            paths.extend(str(p) for p in val)
        elif isinstance(val, dict):
            paths.extend(str(p) for p in val.values())
    return paths


def validate_ears_criterion(name: str, idx: int,
                            criterion: dict) -> list[Issue]:
    issues: list[Issue] = []
    cid = criterion.get("id", f"#{idx}")
    pattern = criterion.get("pattern")

    if not pattern:
        issues.append(Issue(
            name, "error",
            f"acceptance[{cid}]: campo 'pattern' ausente "
            f"(esperado: {sorted(EARS_PATTERN_FIELDS)})",
        ))
        return issues

    if pattern not in EARS_PATTERN_FIELDS:
        issues.append(Issue(
            name, "error",
            f"acceptance[{cid}]: pattern inválido '{pattern}' "
            f"(esperado: {sorted(EARS_PATTERN_FIELDS)})",
        ))
        return issues

    required = EARS_PATTERN_FIELDS[pattern]
    for field in required:
        value = criterion.get(field)
        if not value or not str(value).strip():
            issues.append(Issue(
                name, "error",
                f"acceptance[{cid}]: pattern={pattern} requer '{field}' "
                f"não-vazio",
            ))

    return issues


def validate_feature(path: Path) -> tuple[dict, list[Issue]]:
    issues: list[Issue] = []
    name = path.name
    if not FEATURE_FILE_RE.match(name):
        issues.append(Issue(name, "error", "nome inválido (esperado F-NNNN-slug.md)"))
    try:
        fm, _ = parse_frontmatter(path)
    except ValueError as e:
        return {}, [Issue(name, "error", str(e))]

    for key in FEATURE_REQUIRED:
        if key not in fm:
            issues.append(Issue(name, "error", f"campo ausente: {key}"))

    status = fm.get("status")
    if status and status not in VALID_FEATURE_STATUS:
        issues.append(Issue(name, "error", f"status inválido: {status}"))

    # Guard anti-changelog (ADR-0035): o Manifest é por capacidade. Um nome com
    # token de balde ("polish", "misc", …) é sinal de alta precisão de feature
    # guarda-chuva — bloqueia. A coesão de conteúdo fica para o litmus humano.
    fname = fm.get("name")
    if fname:
        tokens = {t for t in str(fname).lower().replace("_", "-").split("-") if t}
        bucket = tokens & CHANGELOG_NAME_WORDS
        if bucket:
            issues.append(Issue(
                name, "error",
                f"nome de feature tem token de changelog {sorted(bucket)}: o "
                f"Manifest é por capacidade nomeável, não por lote de release — "
                f"divida em features reais ou registre bugfix/cleanup no git "
                f"(ADR-0035)",
            ))

    # Só features que afirmam estar construídas (in_progress/shipped) sofrem
    # o check de existência de contracts (ADR-0044). Em `proposed` o código
    # ainda não existe (alvo pretendido); em `deprecated` o código pode ter
    # sido removido (sumiço esperado) — em ambos, path inexistente não é drift.
    # (`proposed` era `planned` antes do ADR-0047 unificar o vocabulário.)
    contracts = fm.get("contracts") or {}
    if status not in ("proposed", "deprecated"):
        for p in _collect_contract_paths(contracts):
            file_part = p.split("::")[0]
            if not (_paths.ROOT / file_part).exists():
                issues.append(Issue(name, "warning", f"drift: caminho inexistente: {p}"))

    acceptance = fm.get("acceptance") or []
    if not isinstance(acceptance, list):
        issues.append(Issue(name, "error", "acceptance deve ser uma lista"))
    else:
        for idx, criterion in enumerate(acceptance):
            if not isinstance(criterion, dict):
                issues.append(Issue(
                    name, "error",
                    f"acceptance[#{idx}]: deve ser um objeto (mapping)",
                ))
                continue
            issues.extend(validate_ears_criterion(name, idx, criterion))

    return fm, issues


def validate_decision(path: Path) -> tuple[dict, list[Issue]]:
    issues: list[Issue] = []
    name = path.name
    if not DECISION_FILE_RE.match(name):
        issues.append(Issue(name, "error", "nome inválido (esperado NNNN-slug.md)"))
    try:
        fm, _ = parse_frontmatter(path)
    except ValueError as e:
        return {}, [Issue(name, "error", str(e))]

    for key in DECISION_REQUIRED:
        if key not in fm:
            issues.append(Issue(name, "error", f"campo ausente: {key}"))

    status = fm.get("status")
    if status and status not in VALID_DECISION_STATUS:
        issues.append(Issue(name, "error", f"status inválido: {status}"))

    # `version` é opcional em ADRs (release em que a decisão foi aceita —
    # simétrico ao version de features). Reconhecido e validado quando
    # presente; nunca exigido. ADR-0027.
    version = fm.get("version")
    if version is not None and not SEMVER_RE.match(str(version)):
        issues.append(Issue(
            name, "error",
            f"version inválido: {version!r} "
            f"(esperado X.Y.Z, prefixo 'v' opcional, ou ausente)",
        ))

    return fm, issues
