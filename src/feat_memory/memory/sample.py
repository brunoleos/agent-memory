"""sample.py — Amostragem adversarial de critérios de aceite (F-0045).

O audit garante integridade referencial; a verdade SEMÂNTICA dos critérios —
o modo de falha "revisado-e-escapou", que nenhum checker determinístico
cobre — é responsabilidade desta camada (ADR-0050): sorteamos features
ponderadas por risco e emitimos prompts de REFUTAÇÃO para um agente LLM
executar. A ferramenta detecta e pergunta; o julgamento fica fora do core
(mesmo padrão do `propose-adr --prompt`).

Risco de uma feature ativa:
- +2 por ADR citado (`decisions:`) com status superseded;
- +1 por ADR citado cujo último commit é mais novo que o da feature
  (o racional mudou depois do registro — candidato a apodrecimento).

Gatilho recomendado: por EVENTO (supersede, release) — nunca por commit;
custo de LLM concentra onde o risco se concentra. Sempre exit 0: amostrar
é convite, não gate.

Subcomando: `feat-memory sample [path] [--count N] [--seed S]
[--event supersede|release]`.
"""

from __future__ import annotations

import argparse
import random
import subprocess
from pathlib import Path

from feat_memory.shared import paths as _paths
from feat_memory.shared.parsing import parse_frontmatter


PROMPT_TEMPLATE = """\
Você é um verificador ADVERSARIAL de memória de projeto (feat-memory).

Sua missão é REFUTAR — não confirmar — os critérios de aceite abaixo.
Verificador que quer confirmar, confirma; parta da hipótese de que o
critério apodreceu e procure no código a evidência de que ele NÃO é mais
verdade. Contexto do sorteio: feature com risco {score} ({reasons}).

## Alvo

Feature: {fid} · {fname}
Arquivo:  {fpath}
ADRs citados: {decisions}

## Critérios a refutar

{criteria}

## Instruções

1. Para CADA critério, exercite o comportamento descrito contra o código
   atual (leia o código, rode o que der) e produza um veredito:
   - REFUTADO: o critério não é mais verdade — cite arquivo/linha/evidência.
   - CONFIRMADO: sobreviveu à tentativa de refutação — cite a evidência que
     te impediu de refutar.
   - INCONCLUSIVO: não foi possível verificar — diga exatamente o que falta.
2. FALHE RUIDOSAMENTE: se não conseguir provar que o critério ainda vale,
   o veredito é REFUTADO ou INCONCLUSIVO — nunca um CONFIRMADO por cortesia.
3. Critério que enuncia MECANISMO em vez de observável externo: aponte como
   achado próprio (doutrina do observável, ADR-0050), mesmo se confirmado.
4. Reporte os vereditos ao mantenedor; um REFUTADO alimenta a condição de
   falsificação pré-registrada do ADR-0050.
"""


def _last_commit_ts(root: Path, path: Path) -> int | None:
    """Timestamp (epoch) do último commit que tocou `path`; None sem git/commit."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%ct", "--",
             str(path)],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        return int(out) if out.isdigit() else None
    except OSError:
        return None


def _load_decisions() -> dict[str, dict]:
    """{ADR-id: {"status": ..., "path": Path}} de decisions/ + superseded/."""
    out: dict[str, dict] = {}
    for directory in (_paths.DECISIONS_DIR, _paths.SUPERSEDED_DIR):
        if not directory.exists():
            continue
        for dp in sorted(directory.glob("[0-9]*.md")):
            if dp.parent != directory:
                continue
            try:
                fm, _ = parse_frontmatter(dp)
            except ValueError:
                continue
            if fm.get("id"):
                out[str(fm["id"])] = {"status": fm.get("status"), "path": dp}
    return out


def score_feature(fm: dict, fpath: Path, decisions: dict[str, dict],
                  root: Path) -> tuple[int, list[str]]:
    """Risco da feature + razões legíveis (para o prompt e o relatório)."""
    score = 0
    reasons: list[str] = []
    feature_ts = _last_commit_ts(root, fpath)
    for did in fm.get("decisions") or []:
        info = decisions.get(str(did))
        if not info:
            continue
        if info["status"] == "superseded":
            score += 2
            reasons.append(f"{did} superseded")
            continue
        adr_ts = _last_commit_ts(root, info["path"])
        if feature_ts and adr_ts and adr_ts > feature_ts:
            score += 1
            reasons.append(f"{did} mudou depois da feature")
    return score, reasons


def _format_criteria(acceptance: list, bindings: dict | None = None) -> str:
    lines: list[str] = []
    for c in acceptance:
        if not isinstance(c, dict):
            continue
        cid = c.get("id", "?")
        fields = ", ".join(
            f"{k}: {v}" for k, v in c.items() if k not in ("id",)
        )
        bound = (bindings or {}).get(str(cid)) or []
        suffix = f"  [teste declarado: {', '.join(bound)}]" if bound else ""
        lines.append(f"- [{cid}] {fields}{suffix}")
    return "\n".join(lines) or "- (feature sem critérios — achado por si só)"


def collect_candidates(root: Path) -> list[dict]:
    """Features ativas com score/razões, prontas para ordenação."""
    decisions = _load_decisions()
    candidates: list[dict] = []
    if not _paths.FEATURES_DIR.exists():
        return candidates
    for fp in sorted(_paths.FEATURES_DIR.glob("F-*.md")):
        try:
            fm, _ = parse_frontmatter(fp)
        except ValueError:
            continue
        if not fm.get("id"):
            continue
        score, reasons = score_feature(fm, fp, decisions, root)
        candidates.append({
            "id": str(fm["id"]),
            "name": str(fm.get("name", "")),
            "path": fp,
            "fm": fm,
            "acceptance": fm.get("acceptance") or [],
            "decisions": [str(d) for d in (fm.get("decisions") or [])],
            "score": score,
            "reasons": reasons,
        })
    return candidates


def emit_prompts(candidates: list[dict], count: int,
                 seed: int | None, root: Path) -> int:
    """Ordena por risco (desempate seeded), emite até `count` prompts."""
    if not candidates:
        print("Nenhuma feature ativa para amostrar — nada a refutar.")
        return 0
    rng = random.Random(seed)
    ordered = sorted(
        candidates, key=lambda c: (-c["score"], rng.random())
    )
    picked = ordered[:max(count, 0)]
    from feat_memory.memory import binding as _binding
    for i, c in enumerate(picked):
        if i:
            print("\n" + "=" * 72 + "\n")
        rel = c["path"].resolve()
        rel = rel.relative_to(root.resolve()).as_posix() \
            if rel.is_relative_to(root.resolve()) else c["path"].name
        # Binding referencial (F-0049): critério com teste declarado ganha a
        # anotação — o verificador começa rodando o teste citado.
        bindings = _binding.criterion_bindings(c["fm"])
        print(PROMPT_TEMPLATE.format(
            score=c["score"],
            reasons="; ".join(c["reasons"]) or "amostra de rotina, sem sinal",
            fid=c["id"],
            fname=c["name"],
            fpath=rel,
            decisions=", ".join(c["decisions"]) or "(nenhum)",
            criteria=_format_criteria(c["acceptance"], bindings),
        ))
    return 0


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "sample",
        help="Emite prompts de refutação adversarial de critérios de aceite, "
             "ponderados por risco (ADR-0050; sempre exit 0)",
    )
    p.add_argument("path", type=str, nargs="?", default=None,
                   help="raiz do projeto (default: detecta do diretório atual)")
    p.add_argument("--count", type=int, default=3,
                   help="quantas features amostrar (default: 3)")
    p.add_argument("--seed", type=int, default=None,
                   help="semente do desempate (reprodutibilidade)")
    p.add_argument("--event", choices=["supersede", "release"], default=None,
                   help="evento que disparou a amostragem (registrado no "
                        "contexto; o gatilho recomendado é por evento, "
                        "nunca por commit)")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve() if getattr(args, "path", None) else None
    _paths._init_paths(root)
    candidates = collect_candidates(_paths.ROOT)
    if getattr(args, "event", None):
        print(f"(amostragem disparada por evento: {args.event})\n")
    return emit_prompts(candidates, getattr(args, "count", 3),
                        getattr(args, "seed", None), _paths.ROOT)
