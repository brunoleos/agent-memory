"""parsing.py — Parsers compartilhados de YAML frontmatter e .meta.yaml.

`parse_frontmatter` lê markdown com frontmatter `---`-delimitado.
`read_meta` lê o `.feat-memory/.meta.yaml` do consumidor.

ADR-0021: parte de `shared/`, sem dependências do projeto. Antes desta
separação, viviam em `audit.py` mas eram chamados por archive, telemetry,
changelog, propose-adr, migrate. Mover aqui quebra o acoplamento.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _yaml():
    """Importa PyYAML preguiçosamente com mensagem de erro acionável.

    Adiar o import até a primeira chamada evita que `feat-memory --help`
    pague o custo de carregar a lib.
    """
    try:
        import yaml as _y
    except ImportError:
        print(
            "ERRO: PyYAML é uma dependência obrigatória.\n\n"
            "Instale com um dos comandos abaixo:\n"
            "  pip install pyyaml\n"
            "  pip3 install pyyaml\n"
            "  python -m pip install pyyaml\n\n"
            "Em ambientes com gerenciamento de pacotes do sistema "
            "(Debian/Ubuntu recente),\n"
            "use --break-system-packages se necessário ou um virtualenv:\n"
            "  pip install --break-system-packages pyyaml",
            file=sys.stderr,
        )
        sys.exit(1)
    return _y


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Extrai YAML frontmatter de um arquivo markdown."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    yaml = _yaml()
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML inválido em {path}: {e}") from e
    body = text[end + 5:]
    return fm, body


def read_meta(root: Path) -> dict | None:
    """Lê `.feat-memory/.meta.yaml` no consumidor.

    Retorna o dict YAML ou `None` se o arquivo não existe (consumidor
    instalado antes de v0.6.0). Schema definido em ADR-0013. Tolerância
    a ausência é deliberada — chamadores degradam graciosamente.
    """
    path = root / ".feat-memory" / ".meta.yaml"
    if not path.exists():
        return None
    yaml = _yaml()
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML inválido em {path}: {e}") from e


VALID_PROFILES = {"core", "full"}


def resolve_profile(root: Path) -> str:
    """Perfil efetivo do consumidor para fins de governança (ADR-0050).

    Lê `profile` do `.meta.yaml`. Fallback `full` em todos os caminhos de
    degradação (meta ausente, campo ausente, valor inválido, YAML corrompido):
    uma instalação pré-v3 não pode ganhar warnings novos de repente só porque
    a CLI avançou — `core` é opt-in gravado pelo deploy, nunca inferido
    ("upgrade quando doer").
    """
    try:
        meta = read_meta(root) or {}
    except ValueError:
        return "full"
    profile = str(meta.get("profile") or "").strip().lower()
    return profile if profile in VALID_PROFILES else "full"
