"""binding.py — Binding referencial critério↔teste (F-0049, ADR-0052).

Convenção opt-in: um teste que cita o token `F-NNNN-AN` (em comentário,
docstring, nome, tag Cucumber `@F-NNNN-AN`, …) declara cobrir aquele critério
de aceite. A detecção é grep com word-boundary, case-insensitive, restrita
aos arquivos listados em `contracts.tests` da própria feature — referencial
puro: presença de citação, nunca execução (a execução é do toolchain do
consumidor; a fronteira do ADR-0052 vale aqui).

Consumidores: `audit` (métrica de cobertura por critério) e `sample`
(anota no prompt de refutação quais critérios têm teste declarado).
"""

from __future__ import annotations

import re
from pathlib import Path

from feat_memory.shared import paths as _paths


def _test_paths(contracts: dict) -> list[str]:
    """Entradas de `contracts.tests`, normalizadas para lista de strings.

    Espelha as formas aceitas por `schemas._collect_contract_paths`:
    str, lista ou mapa (ex.: {unit: ..., e2e: ...}).
    """
    tests = (contracts or {}).get("tests")
    if tests is None:
        return []
    if isinstance(tests, dict):
        return [str(t) for t in tests.values() if t]
    if isinstance(tests, (list, tuple)):
        return [str(t) for t in tests if t]
    return [str(tests)]


def criterion_bindings(fm: dict) -> dict[str, list[str]]:
    """{criterion_id: [paths de teste que citam o token F-NNNN-AN]}.

    Só critérios com `id` entram; arquivos de teste inexistentes são
    ignorados (a existência é assunto do drift check, não daqui).
    """
    fid = str(fm.get("id") or "")
    criteria = fm.get("acceptance") or []
    if not fid or not isinstance(criteria, list):
        return {}

    texts: dict[str, str] = {}
    for entry in _test_paths(fm.get("contracts") or {}):
        file_part = entry.split("::")[0]
        path = _paths.ROOT / file_part
        if path.exists() and file_part not in texts:
            try:
                texts[file_part] = path.read_text(encoding="utf-8")
            except OSError:
                continue

    out: dict[str, list[str]] = {}
    for criterion in criteria:
        if not isinstance(criterion, dict) or not criterion.get("id"):
            continue
        cid = str(criterion["id"])
        pattern = re.compile(
            rf"\b{re.escape(fid)}-{re.escape(cid)}\b", re.IGNORECASE
        )
        out[cid] = [p for p, text in texts.items() if pattern.search(text)]
    return out


def coverage_summary(features: list[dict]) -> dict:
    """Cobertura por critério agregada sobre features ativas.

    `adopted` = existe ao menos um binding no repo — abaixo disso a métrica
    é exibida como não-adotada (convenção é opt-in; 0% não é dívida).
    """
    total = 0
    bound = 0
    for fm in features:
        bindings = criterion_bindings(fm)
        total += len(bindings)
        bound += sum(1 for paths in bindings.values() if paths)
    return {"total": total, "bound": bound, "adopted": bound > 0}
