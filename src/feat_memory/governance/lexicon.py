"""lexicon.py — Nudge de léxico de mecanismo em critérios de aceite.

Doutrina do observável (ADR-0050): critérios de aceite enunciam observáveis
externos; vocabulário de mecanismo é território de ADR. Este módulo deriva um
léxico de termos de mecanismo DOS PRÓPRIOS ADRs — ortogonal por construção:
computado da memória existente a cada audit, sem artefato novo, sem dono,
nada que drifte — e emite Issue de severidade `info` quando um termo aparece
em texto de critério EARS de uma feature ativa.

Heurística com falsos positivos declarados: `info` NUNCA é promovida por
`--strict` (semântica congelada em tests/test_audit_info_severity.py) —
é nudge, jamais gate.

Extração (stdlib puro, F-0046):
- Fontes por ADR (ativos e superseded): tokens das `tags` do frontmatter e
  tokens do título H1 (`# ADR-NNNN · Título`).
- Saliência: token de tag de >=1 ADR, ou token de título de >=2 ADRs.
- Filtros: stopwords pt/en, tokens < 4 chars, tokens puramente numéricos, e
  tokens presentes no AGENTS.md — vocabulário constitucional é sancionado
  por definição (identidade de produto sobe à constituição; a doutrina
  governa lá, não aqui).

Parte de `governance/` (varre a árvore de memória). NÃO é checker de
constraint: o conjunto de checkers do ADR-0028 é fechado; isto é um
indicador do audit com severidade própria.
"""

from __future__ import annotations

import re
from pathlib import Path

from feat_memory.shared import paths as _paths
from feat_memory.shared.parsing import parse_frontmatter
from feat_memory.memory.schemas import EARS_PATTERN_FIELDS, Issue


# Campos EARS de texto livre onde mecanismo costuma vazar.
_EARS_TEXT_FIELDS = sorted({f for fields in EARS_PATTERN_FIELDS.values()
                            for f in fields})

_MIN_TOKEN_LEN = 4

_STOPWORDS = {
    # pt
    "para", "como", "sobre", "entre", "cada", "pela", "pelo", "pelas",
    "pelos", "quando", "onde", "mais", "menos", "ainda", "apenas", "todo",
    "toda", "todos", "todas", "deve", "devem", "sempre", "nunca", "depois",
    "antes", "este", "esta", "estes", "estas", "esse", "essa", "isso",
    "isto", "assim", "então", "entao", "também", "tambem", "pois", "porque",
    "qual", "quais", "seja", "sejam", "foram", "será", "sera", "serão",
    "serao", "estão", "estao", "fica", "ficam", "novo", "nova", "novos",
    "novas", "versão", "versao", "arquivo", "arquivos", "projeto", "sistema",
    # en
    "with", "from", "that", "this", "then", "when", "where", "which",
    "while", "into", "over", "under", "only", "also", "must", "should",
    "shall", "will", "always", "never", "after", "before", "each", "every",
    "some", "none", "more", "less", "than", "them", "they", "have", "been",
    "were", "does", "done", "uses", "used", "using", "make", "makes",
    "made", "file", "files", "version", "system",
}


def _tokenize(text: str) -> set[str]:
    """Tokens alfanuméricos lowercase (unicode), sem numéricos puros."""
    return {
        t for t in re.findall(r"\w+", text.lower(), re.UNICODE)
        if len(t) >= _MIN_TOKEN_LEN and not t.isdigit()
    }


def _adr_title(body: str) -> str:
    """Título do H1 (`# ADR-NNNN · Título`), sem o prefixo de ID."""
    for line in body.splitlines():
        if line.startswith("# "):
            return re.sub(r"^#\s*ADR-\d{4}\s*[·:—-]?\s*", "", line, count=1)
    return ""


def _iter_decision_files() -> list[Path]:
    files: list[Path] = []
    for directory in (_paths.DECISIONS_DIR, _paths.SUPERSEDED_DIR):
        if directory.exists():
            files.extend(
                dp for dp in sorted(directory.glob("[0-9]*.md"))
                if dp.parent == directory
            )
    return files


def extract_mechanism_lexicon() -> dict[str, list[str]]:
    """Deriva o léxico de mecanismo dos ADRs. Retorna {termo: [ADR-ids]}.

    Determinístico: mesma memória → mesmo léxico. O filtro constitucional
    (tokens do AGENTS.md) é aplicado por último, para que promover um termo
    à constituição o retire do nudge no mesmo audit.
    """
    tag_terms: dict[str, set[str]] = {}
    title_terms: dict[str, set[str]] = {}

    for dp in _iter_decision_files():
        try:
            fm, body = parse_frontmatter(dp)
        except ValueError:
            continue
        adr_id = str(fm.get("id") or dp.stem)
        for tag in fm.get("tags") or []:
            for tok in _tokenize(str(tag)):
                tag_terms.setdefault(tok, set()).add(adr_id)
        for tok in _tokenize(_adr_title(body)):
            title_terms.setdefault(tok, set()).add(adr_id)

    salient: dict[str, set[str]] = {}
    for tok, ids in tag_terms.items():
        salient.setdefault(tok, set()).update(ids)
    for tok, ids in title_terms.items():
        if len(ids) >= 2:
            salient.setdefault(tok, set()).update(ids)

    constitution_tokens: set[str] = set()
    if _paths.AGENT.exists():
        constitution_tokens = _tokenize(
            _paths.AGENT.read_text(encoding="utf-8")
        )

    return {
        tok: sorted(ids)
        for tok, ids in salient.items()
        if tok not in _STOPWORDS and tok not in constitution_tokens
    }


def check_mechanism_lexicon() -> list[Issue]:
    """Emite Issue `info` por (feature, termo) quando texto de critério EARS
    de feature ATIVA contém termo do léxico de mecanismo."""
    lexicon = extract_mechanism_lexicon()
    if not lexicon or not _paths.FEATURES_DIR.exists():
        return []

    issues: list[Issue] = []
    for fp in sorted(_paths.FEATURES_DIR.glob("F-*.md")):
        try:
            fm, _ = parse_frontmatter(fp)
        except ValueError:
            continue
        criteria = fm.get("acceptance") or []
        if not isinstance(criteria, list):
            continue
        # Vocabulário de capacidade da própria feature (name + user_value) é
        # declarado, não vazado — isento por feature: "supersede" no aceite
        # de supersede-reconciliation é o domínio dela, não mecanismo alheio.
        own_vocab = _tokenize(
            f"{fm.get('name', '')} {fm.get('user_value', '')}"
        )
        seen: set[str] = set()
        for criterion in criteria:
            if not isinstance(criterion, dict):
                continue
            cid = criterion.get("id", "?")
            text_tokens = _tokenize(" ".join(
                str(criterion.get(f, "")) for f in _EARS_TEXT_FIELDS
            ))
            for term in sorted((text_tokens & set(lexicon)) - own_vocab):
                if term in seen:
                    continue
                seen.add(term)
                sources = ", ".join(lexicon[term][:3])
                issues.append(Issue(
                    fp.name, "info",
                    f"critério {cid}: termo de mecanismo '{term}' "
                    f"(vocabulário de ADR: {sources}) em texto de aceite — "
                    f"mecanismo é território de ADR; prefira observáveis "
                    f"externos (doutrina do observável, ADR-0050)",
                ))
    return issues
