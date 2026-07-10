"""deploy.py — Deploy idempotente da metodologia em um projeto.

Subcomando da CLI: `feat-memory deploy <target>`. Copia templates,
instala hooks e configura .gitignore/.gitattributes no target.

`--dry-run` reporta o que mudaria (criaria/atualizaria) sem escrever nada —
útil para revisar o efeito de um upgrade antes de commitar. A garantia de
zero-mutação é coberta por teste de regressão (árvore byte-idêntica).

Tanto o deploy quanto o dry-run sinalizam frontmatter stale no AGENTS.md
(paths legados, methodology desatualizada) que o deploy não corrige — o
frontmatter é human-owned (F-0041).

Comportamento por arquivo:
    AGENTS.md            → bloco com sentinelas markdown, refrescado a cada
                            deploy; conteúdo do usuário fora do bloco nunca
                            é tocado
    CLAUDE.md            → copia se ausente; deixa quieto se existe
    .feat-memory/changelog/UNRELEASED.md → pula se existe (volátil)
    skills/              → sempre atualizadas (conteúdo de metodologia)
    .claude/agents/      → subagents do Claude Code, sempre atualizados
                            (wrapper fino que pré-carrega a skill homônima)
    .gitattributes       → bloco com sentinelas, refrescado a cada deploy
    .gitignore           → bloco com sentinelas garantindo .feat-memory-deploy/
    pastas               → cria se não existem
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path

from feat_memory.governance import install_hooks
from feat_memory.shared.frontmatter import detect_stale_frontmatter
from feat_memory.shared.parsing import parse_frontmatter


SENTINEL_BEGIN = "# >>> feat-memory >>>"
SENTINEL_END = "# <<< feat-memory <<<"

# Sentinelas markdown (HTML comments) para o bloco da metodologia em AGENTS.md.
# Diferentes das sentinelas shell-style usadas em .gitignore/.gitattributes
# porque `#` em markdown é heading, não comentário.
MD_SENTINEL_BEGIN = "<!-- >>> feat-memory >>> -->"
MD_SENTINEL_END = "<!-- <<< feat-memory <<< -->"


def _verb(done: str, would: str, dry_run: bool) -> str:
    """Verbo no modo certo: 'criaria' (dry-run) vs 'criado' (aplicado).

    Centraliza a flexão para que toda linha de log do `deploy` fale no
    condicional sob `--dry-run` sem repetir o ternário em cada call site.
    """
    return would if dry_run else done


def _warn_stale_frontmatter(target: Path) -> int:
    """Avisa sobre frontmatter stale no AGENTS.md do consumidor.

    O deploy refresca o bloco entre sentinelas mas **não** toca o frontmatter
    (`references`/`budgets`) — então paths legados ou URL de methodology numa
    versão antiga passariam despercebidos. Read-only (roda igual em dry-run e
    aplicado). Retorna o número de avisos. Ver F-0040.
    """
    dst = target / "AGENTS.md"
    if not dst.exists():
        return 0
    try:
        fm, _ = parse_frontmatter(dst)
    except (ValueError, OSError):
        return 0
    if not fm:
        return 0
    from feat_memory import __version__
    findings = detect_stale_frontmatter(fm, __version__)
    for msg in findings:
        print(f"  ⚠ frontmatter desatualizado: {msg}")
    if findings:
        print("  (o deploy refresca o bloco mas NÃO toca o frontmatter — "
              "corrija à mão)")
    return len(findings)


def _data_path(*parts: str) -> Traversable:
    """Retorna um Traversable em data/<parts>.

    F-0017 / ADR-0021 moveu data/ para o topo do package feat_memory:
    - templates/, skills/  → feat_memory/data/
    - hooks/               → feat_memory.governance/data/

    Esta função roteia automaticamente baseado no primeiro componente.
    """
    if parts and parts[0] == "hooks":
        base = files("feat_memory.governance") / "data"
    else:
        base = files("feat_memory") / "data"
    p = base
    for part in parts:
        p = p / part
    return p


def _copy_resource(src: Traversable, dst: Path) -> None:
    """Copia um arquivo do package data para um path de filesystem."""
    with as_file(src) as src_path:
        shutil.copy2(src_path, dst)


# Ordem editorial do roster (ciclo de vida: adotar → retomar → fechar →
# sincronizar); skills fora da lista entram depois, em ordem alfabética.
_ROSTER_ORDER = ["memory-deploy", "memory-bootstrap", "memory-debrief",
                 "memory-pull-brief"]


def _skills_roster() -> str:
    """Roster gerado dos frontmatters das skills (campo `summary`).

    Fonte única mecânica (ADR-0052): o texto de cada linha vive no próprio
    SKILL.md; o template carrega só o token `{SKILLS_ROSTER}`. Skill sem
    `summary` entra só com o nome (fail-soft) — nunca inventamos resumo.
    """
    from feat_memory.shared.parsing import parse_frontmatter
    entries: dict[str, str] = {}
    skills_root = _data_path("skills")
    for entry in skills_root.iterdir():
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            fm, _ = parse_frontmatter(skill_md)
        except (ValueError, OSError):
            continue
        name = str(fm.get("name") or entry.name)
        summary = str(fm.get("summary") or "").strip()
        entries[name] = (f"- **`{name}`** — {summary}" if summary
                         else f"- **`{name}`**")
    ordered = [n for n in _ROSTER_ORDER if n in entries]
    ordered += sorted(n for n in entries if n not in _ROSTER_ORDER)
    return "\n".join(entries[n] for n in ordered)


def _substitute_tokens(content: str) -> str:
    """Substitui placeholders de template (`{VERSION}`, `{DEPLOY_DATE}`,
    `{SKILLS_ROSTER}`).

    `{VERSION}` → versão atual do pacote (URLs ancoradas na tag da doutrina).
    `{DEPLOY_DATE}` → instante UTC do deploy em ISO-8601, disponível para
    artefatos gerados que precisem de um timestamp real.
    `{SKILLS_ROSTER}` → bullets gerados dos `summary` das skills empacotadas
    (só computado quando o token aparece). Templates sem placeholders passam
    intactos.
    """
    from datetime import datetime, timezone
    from feat_memory import __version__
    content = content.replace("{VERSION}", __version__)
    content = content.replace(
        "{DEPLOY_DATE}", datetime.now(timezone.utc).isoformat()
    )
    if "{SKILLS_ROSTER}" in content:
        content = content.replace("{SKILLS_ROSTER}", _skills_roster())
    return content


def _copy_template(src: Traversable, dst: Path) -> None:
    """Copia um template aplicando `_substitute_tokens`.

    Usado para AGENTS.md/CLAUDE.md.
    """
    dst.write_text(_substitute_tokens(src.read_text(encoding="utf-8")),
                   encoding="utf-8")


def _ensure_frontmatter(existing: str) -> tuple[str, bool]:
    """Prepende um esqueleto de frontmatter se o arquivo não tiver nenhum.

    Em adoção legacy a AGENTS.md já existe — quase sempre uma constituição em
    prosa, sem YAML frontmatter. O deploy só refresca o bloco com sentinelas e
    nunca tocava o topo do arquivo, então a auditoria pós-deploy falhava com
    "campo ausente: schema_version/project/constraints/..." e a conformidade de
    schema ficava 0.00 — exatamente o usuário diligente (que escreveu uma boa
    constituição em prosa) sendo recebido com erros. Aqui fechamos a assimetria
    com greenfield: se não há frontmatter, injetamos o esqueleto mínimo
    (campos mecânicos preenchidos; `project`/`stack`/`constraints` como TODO
    para o mantenedor migrar a prosa). Não é autorar identidade — é dar a mesma
    estrutura que o template greenfield já entrega. Ver ADR-0029.

    A detecção espelha `shared.parsing.parse_frontmatter`: frontmatter é
    reconhecido só quando o arquivo começa exatamente com `---\\n`. Retorna
    (novo_conteúdo, injetou).
    """
    if existing.startswith("---\n"):
        return existing, False
    skeleton_src = _data_path("templates", "AGENTS.frontmatter-skeleton.md")
    if not skeleton_src.is_file():
        # Defensivo: sem o template não injeta, mas não quebra o deploy.
        return existing, False
    skeleton = _substitute_tokens(skeleton_src.read_text(encoding="utf-8"))
    return skeleton.rstrip() + "\n\n" + existing, True


def _replace_sentinel_block(existing: str, payload: str,
                            begin: str = SENTINEL_BEGIN,
                            end: str = SENTINEL_END) -> tuple[str, bool]:
    """Substitui ou insere um bloco delimitado por sentinelas.

    Retorna (novo_conteúdo, mudou). Se o bloco já existir e for idêntico,
    mudou=False. Caso contrário, substitui (ou anexa, se ausente).
    """
    block = f"{begin}\n{payload.rstrip()}\n{end}\n"

    if begin in existing and end in existing:
        # Pega a PRIMEIRA ocorrência da sentinela de abertura e a ÚLTIMA da
        # sentinela de fechamento. Defesa contra menções literais às strings
        # das sentinelas no conteúdo do bloco (raro mas catastrófico).
        before, _, rest = existing.partition(begin)
        _, _, after = rest.rpartition(end)
        if after.startswith("\n"):
            after = after[1:]
        new_content = before + block + after
    else:
        sep = "" if not existing or existing.endswith("\n") else "\n"
        new_content = existing + sep + ("\n" if existing else "") + block

    return new_content, new_content != existing


def _extract_methodology_block(template_text: str) -> str:
    """Extrai o conteúdo entre sentinelas markdown no template AGENTS.md.

    O conteúdo retornado é o que vai entre `<!-- >>> feat-memory >>> -->`
    e `<!-- <<< feat-memory <<< -->` no template (sem as sentinelas em si).
    Usado para refrescar o bloco em arquivos AGENTS.md já existentes sem
    sobrescrever o resto do conteúdo do usuário.
    """
    if MD_SENTINEL_BEGIN not in template_text or MD_SENTINEL_END not in template_text:
        raise ValueError(
            "template AGENTS.md não contém sentinelas markdown feat-memory"
        )
    # Defesa contra menções literais às sentinelas no conteúdo: usa primeira
    # abertura e última fechamento (cf. _replace_sentinel_block).
    _, _, rest = template_text.partition(MD_SENTINEL_BEGIN)
    block, _, _ = rest.rpartition(MD_SENTINEL_END)
    return block.strip()


def deploy_constitution(target: Path, force: bool, merge: bool,
                        dry_run: bool = False) -> tuple[int, int]:
    """Deploy de AGENTS.md (via bloco com sentinelas) e CLAUDE.md.

    Para AGENTS.md, a única mudança que o deploy faz num arquivo existente
    é substituir o bloco delimitado por sentinelas markdown. O resto do
    conteúdo (frontmatter, seções específicas do projeto autoradas pelo
    mantenedor) nunca é tocado. Em arquivo ausente, copia o template
    completo.

    Para CLAUDE.md (redirect mínimo `@AGENTS.md`), copia se ausente e
    deixa quieto se existe — não há merge nem refresh.

    Sob `dry_run`, nada é escrito; só reporta o que mudaria. Retorna
    `(arquivos_mudados, avisos_de_frontmatter)` — o frontmatter não é tocado
    pelo deploy, só sinalizado quando stale.
    """
    print("Constituição (AGENTS.md, CLAUDE.md):")
    changes = 0

    src = _data_path("templates", "AGENTS.md")
    dst = target / "AGENTS.md"
    if not src.is_file():
        print("  ERRO: template ausente no pacote: AGENTS.md", file=sys.stderr)
        sys.exit(1)

    template_text = _substitute_tokens(src.read_text(encoding="utf-8"))

    if not dst.exists():
        if not dry_run:
            dst.write_text(template_text, encoding="utf-8")
        print(f"  {_verb('criado', 'criaria', dry_run)}: AGENTS.md")
        changes += 1
    elif force:
        if not dry_run:
            dst.write_text(template_text, encoding="utf-8")
        print(f"  {_verb('sobrescrito', 'sobrescreveria', dry_run)}: "
              "AGENTS.md (--force)")
        changes += 1
    elif not merge:
        print("  pulado: AGENTS.md (já existe; --no-merge)")
    else:
        block_payload = _extract_methodology_block(template_text)
        existing = dst.read_text(encoding="utf-8")
        existing, fm_added = _ensure_frontmatter(existing)
        had_block = MD_SENTINEL_BEGIN in existing and MD_SENTINEL_END in existing
        new_content, changed = _replace_sentinel_block(
            existing, block_payload,
            begin=MD_SENTINEL_BEGIN, end=MD_SENTINEL_END,
        )
        if changed or fm_added:
            if not dry_run:
                dst.write_text(new_content, encoding="utf-8")
            tail = "" if had_block else " (bloco anexado)"
            print(f"  {_verb('atualizado', 'atualizaria', dry_run)}{tail}: "
                  "AGENTS.md (bloco feat-memory)")
            if fm_added:
                verb = _verb('injetado', 'injetaria', dry_run)
                print(f"  {verb}: AGENTS.md (esqueleto de frontmatter — "
                      "preencha os campos TODO)")
            changes += 1
        else:
            print("  já em dia: AGENTS.md (bloco feat-memory sem mudanças)")

    warnings = _warn_stale_frontmatter(target)

    src = _data_path("templates", "CLAUDE.md")
    dst = target / "CLAUDE.md"
    if not src.is_file():
        print("  ERRO: template ausente no pacote: CLAUDE.md", file=sys.stderr)
        sys.exit(1)

    if not dst.exists():
        if not dry_run:
            _copy_template(src, dst)
        print(f"  {_verb('criado', 'criaria', dry_run)}: CLAUDE.md")
        changes += 1
    elif force:
        if not dry_run:
            _copy_template(src, dst)
        print(f"  {_verb('sobrescrito', 'sobrescreveria', dry_run)}: "
              "CLAUDE.md (--force)")
        changes += 1
    else:
        print("  pulado: CLAUDE.md (já existe)")

    return changes, warnings


META_HEADER = (
    "# Metadata de instalação do feat-memory.\n"
    "#\n"
    "# Regenerado a cada `feat-memory deploy`. Versionado no Git do consumidor\n"
    "# para que ferramentas externas e a própria CLI (audit, telemetria) saibam\n"
    "# contra qual versão a estrutura foi produzida.\n"
    "#\n"
    "# Schema documentado em ADR-0013; `profile` (core|full) em ADR-0050.\n"
    "# Não edite manualmente — re-rode deploy (com --profile para mudar).\n"
    "\n"
)


def _resolve_deploy_profile(target: Path, profile_flag: str | None) -> str:
    """Perfil a gravar no .meta.yaml (ADR-0050).

    Resolução: flag explícita > profile já gravado > default por estado da
    instalação. O default distingue instalação nova de upgrade: target virgem
    (sem .meta.yaml) recebe `core`; instalação pré-v3 (meta sem `profile`)
    recebe `full`, preservando o comportamento efetivo que ela já tinha —
    um re-deploy de rotina nunca rebaixa um consumidor para core.
    """
    if profile_flag:
        return profile_flag
    from feat_memory.shared.parsing import VALID_PROFILES, read_meta
    try:
        meta = read_meta(target)
    except ValueError:
        meta = {}
    if meta is None:
        return "core"
    existing = str(meta.get("profile") or "").strip().lower()
    return existing if existing in VALID_PROFILES else "full"


def deploy_meta(target: Path, dry_run: bool = False,
                profile_flag: str | None = None) -> int:
    """Grava .feat-memory/.meta.yaml com versão, timestamp e perfil.

    Idempotente por construção: cada deploy sobrescreve o arquivo com os
    valores correntes. Schema definido em ADR-0013; `cli_path` removido em
    ADR-0034; `profile` e `schema_version: 2` adicionados em ADR-0050.
    O perfil é resolvido por `_resolve_deploy_profile` (flag > existente >
    default por estado), então re-deploy sem flag preserva a escolha.

    Sob `dry_run`, não escreve. O `.meta.yaml` carrega um `deployed_at` que
    muda a cada deploy, então é sempre reportado como mudança.
    """
    print("Metadata (.feat-memory/.meta.yaml):")

    from datetime import datetime, timezone

    import yaml

    from feat_memory import __version__

    feat_memory_dir = target / ".feat-memory"
    dst = feat_memory_dir / ".meta.yaml"
    existed = dst.exists()
    profile = _resolve_deploy_profile(target, profile_flag)

    if not dry_run:
        data = {
            "schema_version": 2,
            "version": __version__,
            "profile": profile,
            "deployed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "telemetry_enabled": True,
        }
        feat_memory_dir.mkdir(parents=True, exist_ok=True)
        body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
        dst.write_text(META_HEADER + body, encoding="utf-8")

    verb = _verb("atualizado", "atualizaria", dry_run) if existed \
        else _verb("criado", "criaria", dry_run)
    print(f"  {verb}: .feat-memory/.meta.yaml (v{__version__}, profile {profile})")
    return 1


def deploy_changelog(target: Path, dry_run: bool = False) -> int:
    """Cria changelog/UNRELEASED.md em .feat-memory/ (pula se existe).

    Substitui o antigo STATE.md: o foco da sessão e o orçamento de retomada
    vivem nas entradas do UNRELEASED (ADR-0043). Conteúdo volátil — nunca
    sobrescreve um existente. Sob `dry_run`, não escreve.
    """
    from feat_memory.memory import changelog
    print("Changelog vivo (.feat-memory/changelog/UNRELEASED.md):")
    up = changelog.unreleased_path(target)
    if up.exists():
        print("  já existe: .feat-memory/changelog/UNRELEASED.md")
        return 0
    if not dry_run:
        changelog.ensure_scaffold(target)
    print(f"  {_verb('criado', 'criaria', dry_run)}: "
          ".feat-memory/changelog/UNRELEASED.md")
    return 1


_IDEAS_MARKER = "<!-- Entradas"


def _ideas_entries(text: str) -> str:
    """Entradas (`## ...`) de um ideas.md/suggestions.md, sem o cabeçalho."""
    i = text.find(_IDEAS_MARKER)
    if i >= 0:
        eol = text.find("\n", i)
        return text[eol + 1:].strip() if eol >= 0 else ""
    m = re.search(r"^## ", text, re.MULTILINE)
    return text[m.start():].strip() if m else ""


def deploy_ideas(target: Path, dry_run: bool = False) -> int:
    """Cria/refresca .feat-memory/ideas.md — funil do futuro (ADR-0047).

    O **cabeçalho** (descrição + tabela de triagem) é conteúdo de metodologia e
    é refrescado a cada deploy, como o bloco do AGENTS.md; as **entradas** do
    usuário (`## ...`) são preservadas. Sob `dry_run`, não escreve.
    """
    print("Funil do futuro (.feat-memory/ideas.md):")
    fm_dir = target / ".feat-memory"
    dst = fm_dir / "ideas.md"

    header = _substitute_tokens(
        _data_path("templates", "ideas.md").read_text(encoding="utf-8")
    ).rstrip("\n") + "\n"
    entries = _ideas_entries(dst.read_text(encoding="utf-8")) if dst.exists() else ""
    content = header + (f"\n{entries}\n" if entries else "")

    before = dst.read_text(encoding="utf-8") if dst.exists() else None
    if before == content:
        print("  já atualizado: .feat-memory/ideas.md")
        return 0
    if not dry_run:
        fm_dir.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")
    if before is None:
        print(f"  {_verb('criado', 'criaria', dry_run)}: .feat-memory/ideas.md")
    else:
        verb = _verb("header refrescado", "refrescaria o header", dry_run)
        print(f"  {verb}: .feat-memory/ideas.md (entradas preservadas)")
    return 1


def _merge_driver_configured(target: Path) -> bool:
    """True se `merge.ours.driver` já está setado como `true` no repo."""
    try:
        r = subprocess.run(
            ["git", "config", "--get", "merge.ours.driver"],
            cwd=target, capture_output=True, text=True, check=False,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except FileNotFoundError:
        return False


def deploy_gitattributes(target: Path, dry_run: bool = False) -> tuple[int, int]:
    """Deploy do .gitattributes (bloco com sentinelas) + driver de merge.

    Sob `dry_run`, não escreve nem mexe no `git config`. Retorna
    `(arquivos_mudados, ações_de_ambiente)` — o `merge.ours.driver` só conta
    como ação quando ainda não está configurado.
    """
    print("Configuração de merge (.gitattributes):")
    src = _data_path("templates", ".gitattributes")
    dst = target / ".gitattributes"

    if not src.is_file():
        return 0

    payload = src.read_text(encoding="utf-8").strip() + "\n"
    existing = dst.read_text(encoding="utf-8") if dst.exists() else ""
    new_content, changed = _replace_sentinel_block(existing, payload)

    if changed:
        if not dry_run:
            dst.write_text(new_content, encoding="utf-8")
        verb = _verb("atualizado", "atualizaria", dry_run) if existing \
            else _verb("criado", "criaria", dry_run)
        print(f"  {verb}: .gitattributes (bloco feat-memory)")
    else:
        print("  já em dia: .gitattributes (bloco feat-memory sem mudanças)")

    env_changes = 0
    if (target / ".git").exists():
        if _merge_driver_configured(target):
            print("  já configurado: merge.ours.driver")
        elif dry_run:
            print("  configuraria: merge.ours.driver")
            env_changes = 1
        else:
            try:
                subprocess.check_call(
                    ["git", "config", "merge.ours.driver", "true"],
                    cwd=target, stdout=subprocess.DEVNULL,
                )
                print("  configurado: merge.ours.driver")
                env_changes = 1
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("  AVISO: não foi possível configurar merge.ours.driver")

    return (1 if changed else 0), env_changes


def ensure_gitignore(target: Path, dry_run: bool = False) -> int:
    """Garante que paths transientes/locais estão no .gitignore.

    `.feat-memory-deploy/` — diretório transiente do deploy legado.
    `.feat-memory/.telemetry.jsonl` — telemetria local opt-out (F-0014,
    ADR-0017): dado pessoal de adoção do dev, não memória do projeto;
    versionar distribuiria padrões de uso individual. Sob `dry_run`, não escreve.
    """
    print("Gitignore (.feat-memory-deploy/, .telemetry.jsonl ignorados):")
    dst = target / ".gitignore"
    payload = ".feat-memory-deploy/\n.feat-memory/.telemetry.jsonl\n"
    existing = dst.read_text(encoding="utf-8") if dst.exists() else ""
    new_content, changed = _replace_sentinel_block(existing, payload)

    if changed:
        if not dry_run:
            dst.write_text(new_content, encoding="utf-8")
        verb = _verb("atualizado", "atualizaria", dry_run) if existing \
            else _verb("criado", "criaria", dry_run)
        print(f"  {verb}: .gitignore (bloco feat-memory)")
        return 1
    print("  já contém: .gitignore (bloco feat-memory presente)")
    return 0


def check_v03_layout(target: Path) -> bool:
    """Detecta layout v0.3.x na raiz e aborta com instrução de migração.

    Retorna True se layout legado detectado (não pode continuar).
    Retorna False se layout já é novo ou não há Git.
    """
    if not (target / ".git").exists():
        return False

    legacy_paths = ["manifest", "decisions", "STATE.md"]
    tracked = []
    try:
        for p in legacy_paths:
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", p],
                cwd=target, capture_output=True, text=True, check=False,
            )
            if result.returncode == 0:
                tracked.append(p)
    except FileNotFoundError:
        return False

    if not tracked:
        return False

    print()
    print("=" * 60)
    print("ATENÇÃO: layout v0.3.x detectado na raiz do projeto")
    print("=" * 60)
    print()
    print("A partir de v0.4.0, os artefatos de memória ficam em .feat-memory/.")
    print("Os seguintes paths legados foram detectados no Git:")
    for p in tracked:
        print(f"  - {p}/" if p != "STATE.md" else f"  - {p}")
    print()
    print("Execute a migração manual ANTES de prosseguir:")
    print()
    print("  # 1. Crie a nova estrutura")
    print("  mkdir -p .feat-memory/manifest/features")
    print("  mkdir -p .feat-memory/decisions/proposals")
    print()
    print("  # 2. Mova os artefatos (preserva histórico via git mv)")
    if "manifest" in tracked:
        print("  git mv manifest/* .feat-memory/manifest/")
        print("  rmdir manifest")
    if "decisions" in tracked:
        print("  git mv decisions/* .feat-memory/decisions/")
        print("  rmdir decisions")
    if "STATE.md" in tracked:
        print("  git mv STATE.md .feat-memory/STATE.md")
    print()
    print('  # 3. Ajuste .gitattributes (padrões de merge=ours)')
    print('  # As linhas de STATE.md, manifest/INDEX.md, decisions/INDEX.md')
    print('  # devem incluir o prefixo .feat-memory/')
    print()
    print('  git commit -m "chore: migrate to feat-memory v0.4 layout"')
    print()
    print("=" * 60)
    return True


def migrate_legacy_layout(target: Path, dry_run: bool = False) -> bool:
    """Migra o layout legado `.agent-memory/` → `.feat-memory/` (rename do projeto).

    Caminho de upgrade para consumidores que adotaram a metodologia quando ela se
    chamava `agent-memory` (ADR-0036). Idempotente: no-op se já está no layout novo.
    Não-destrutivo: se `.agent-memory/` E `.feat-memory/` coexistem, não sobrescreve
    — deixa o legado para revisão manual e avisa. Retorna True se migrou.

    O `deploy` que chama isto em seguida reinstala o pre-commit hook (passa a chamar
    `feat-memory`) e refresca o bloco em AGENTS.md, completando a transição.

    Sob `dry_run`, detecta e reporta a migração sem renomear (e sem remover o
    diretório transiente legado).
    """
    legacy = target / ".agent-memory"
    current = target / ".feat-memory"

    # Diretório transiente legado do deploy antigo: descartável sempre.
    legacy_deploy = target / ".agent-memory-deploy"
    if legacy_deploy.exists() and not dry_run:
        shutil.rmtree(legacy_deploy, ignore_errors=True)

    if not legacy.is_dir():
        return False

    if dry_run:
        if current.exists():
            print("AVISO: existem .agent-memory/ E .feat-memory/ — reconcilie "
                  "manualmente (o deploy real não vai sobrescrever).")
            return False
        print("Migração de layout: migraria .agent-memory/ → .feat-memory/ "
              "(rename); o plano abaixo assume o layout já migrado.")
        return True

    if current.exists():
        print("AVISO: existem .agent-memory/ E .feat-memory/ — não vou "
              "sobrescrever.")
        print("  Reconcilie manualmente e remova .agent-memory/.")
        return False

    try:
        legacy.rename(current)
    except OSError as e:
        print(f"AVISO: não foi possível migrar .agent-memory/ → .feat-memory/: {e}",
              file=sys.stderr)
        print("  Renomeie o diretório manualmente e rode `feat-memory deploy` de novo.",
              file=sys.stderr)
        return False

    print("Migração de layout: .agent-memory/ → .feat-memory/ (rename para feat-memory)")
    print("  O pre-commit hook será reinstalado para chamar `feat-memory`.")
    print("  Se houver um pacote pipx antigo, remova: pipx uninstall agent-memory")
    return True


def deploy_agents(target: Path, dry_run: bool = False) -> int:
    """Deploy do(s) subagent(s) do Claude Code em .claude/agents/.

    Cada arquivo é um wrapper fino que pré-carrega a skill homônima (fonte
    única da lógica) via o campo `skills:` do frontmatter, dando ao agente um
    contexto isolado. Refresca quando diverge — conteúdo de metodologia, como
    as skills. No-op silencioso se o pacote não traz a pasta agents/. Sob
    `dry_run`, não escreve.
    """
    agents_src = _data_path("agents")
    if not agents_src.is_dir():
        return 0

    print("Subagents (Claude Code):")
    agents_dst = target / ".claude" / "agents"

    changes = 0
    if not dry_run:
        agents_dst.mkdir(parents=True, exist_ok=True)

    for agent_path in sorted(agents_src.iterdir(), key=lambda e: e.name):
        if not (agent_path.is_file() and agent_path.name.endswith(".md")):
            continue
        dst_file = agents_dst / agent_path.name
        src_text = agent_path.read_text(encoding="utf-8")
        existed = dst_file.exists()
        if existed and dst_file.read_text(encoding="utf-8") == src_text:
            print(f"  já em dia: {agent_path.name}")
            continue
        if not dry_run:
            _copy_resource(agent_path, dst_file)
        verb = _verb("atualizado", "atualizaria", dry_run) if existed \
            else _verb("deployado", "deployaria", dry_run)
        print(f"  {verb}: {agent_path.name}")
        changes += 1

    print("  → se .claude/ está no seu .gitignore, rastreie os subagents "
          "(ex.: troque `.claude/` por `.claude/*` + `!.claude/agents/`)")
    return changes


def deploy_skills(target: Path, force: bool, dry_run: bool = False) -> int:
    """Deploy de skills (conteúdo de metodologia; refresca quando diverge).

    Compara o conteúdo antes de escrever: skill idêntica vira no-op ("já em
    dia"), o que torna o `--dry-run` honesto (só reporta o que realmente
    mudaria). Sob `dry_run`, não escreve.
    """
    print("Skills:")
    skills_dst = target / "skills"

    skills_src = _data_path("skills")
    if not skills_src.is_dir():
        print("  AVISO: pasta skills/ ausente no pacote")
        return 0

    changes = 0
    if not dry_run:
        skills_dst.mkdir(parents=True, exist_ok=True)

    for skill_path in sorted(skills_src.iterdir(), key=lambda e: e.name):
        if not skill_path.is_dir():
            continue
        skill_name = skill_path.name
        src_file = skill_path / "SKILL.md"
        dst_dir = skills_dst / skill_name
        dst_file = dst_dir / "SKILL.md"

        if not src_file.is_file():
            print(f"  pulado: {skill_name} (sem SKILL.md no source)")
            continue

        src_text = src_file.read_text(encoding="utf-8")
        existed = dst_file.exists()
        if existed and dst_file.read_text(encoding="utf-8") == src_text:
            print(f"  já em dia: {skill_name}")
            continue

        if not dry_run:
            dst_dir.mkdir(parents=True, exist_ok=True)
            _copy_resource(src_file, dst_file)
        verb = _verb("atualizada", "atualizaria", dry_run) if existed \
            else _verb("deployada", "deployaria", dry_run)
        print(f"  {verb}: {skill_name}")
        changes += 1

    return changes


def create_directories(target: Path, dry_run: bool = False) -> int:
    """Cria estrutura de pastas .feat-memory/manifest/, decisions/, changelog/.

    Sob `dry_run`, não cria nada.
    """
    print("Estrutura de pastas:")
    base = target / ".feat-memory"
    changes = 0
    for rel in ("manifest/features", "decisions/proposals", "changelog"):
        full = base / rel
        if full.exists():
            print(f"  já existe: .feat-memory/{rel}/")
        else:
            if not dry_run:
                full.mkdir(parents=True, exist_ok=True)
                (full / ".gitkeep").touch()
            print(f"  {_verb('criado', 'criaria', dry_run)}: .feat-memory/{rel}/")
            changes += 1
    return changes


def install_git_hooks(target: Path, dry_run: bool = False) -> int:
    """Instala git hooks no target. Sob `dry_run`, só anuncia.

    Retorna o número de hooks que (seriam) instalados/atualizados — hooks
    idênticos não contam ('já instalado').
    """
    print("Git hooks:")
    return install_hooks.install(target, dry_run=dry_run)


def run_audit(target: Path) -> None:
    """Roda primeira auditoria via subprocess (cwd=target)."""
    print("Auditoria inicial:")
    try:
        result = subprocess.run(
            ["feat-memory", "audit"],
            cwd=target, capture_output=True, text=True, check=False,
        )
        for line in result.stdout.splitlines():
            print(f"  {line}")
        if result.returncode != 0:
            print(f"  AVISO: auditoria retornou {result.returncode}")
    except FileNotFoundError:
        print("  AVISO: 'feat-memory' não encontrado no PATH; "
              "pulando auditoria inicial")


def print_next_steps(target: Path) -> None:
    """Imprime próximos passos para o usuário."""
    print("Próximos passos:")
    print(f"  1. Preencha/aprove o frontmatter de {target / 'AGENTS.md'} "
          "(project, stack, constraints) — a skill memory-deploy propõe a partir "
          "do código e você aprova; `feat-memory schema` mostra a forma dos campos")
    print(f"  2. Registre o trabalho em voo em "
          f"{target / '.feat-memory' / 'changelog' / 'UNRELEASED.md'}")
    print("  3. (Opcional) Adicione seções específicas do projeto à AGENTS.md "
          "fora do bloco feat-memory")
    print("  4. Crie sua primeira feature em .feat-memory/manifest/features/ "
          "(`feat-memory schema` lista os campos)")
    print('  5. Faça commit: git add + git commit -m "adopt feat-memory"')


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "deploy",
        help="Instala templates, skills e hooks da metodologia num projeto",
    )
    p.add_argument("target", type=str, nargs="?", default=".",
                   help="caminho para a raiz do projeto consumidor "
                        "(default: diretório atual)")
    p.add_argument("--force", action="store_true",
                   help="sobrescreve TUDO sem merge")
    p.add_argument("--no-merge", action="store_true",
                   help="pula arquivos existentes em vez de mesclar")
    p.add_argument("--no-hooks", action="store_true",
                   help="pula instalação de git hooks")
    p.add_argument("--dry-run", action="store_true",
                   help="mostra o que mudaria sem escrever nada")
    p.add_argument("--profile", choices=["core", "full"], default=None,
                   help="perfil da metodologia (ADR-0050): core = constituição "
                        "+ decisions + UNRELEASED + features finas (default em "
                        "instalação nova); full = adiciona changelog completo e "
                        "orçamento de prosa maior. Sem a flag, re-deploy "
                        "preserva o perfil já gravado no .meta.yaml")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"ERRO: target não existe: {target}", file=sys.stderr)
        return 1
    if not target.is_dir():
        print(f"ERRO: target não é um diretório: {target}", file=sys.stderr)
        return 1

    dry_run = getattr(args, "dry_run", False)

    print("=" * 38)
    print("Deploy da metodologia de memória" + (" [DRY-RUN]" if dry_run else ""))
    print("=" * 38)

    from feat_memory import __version__
    print(f"Versão: {__version__}")
    print(f"Target: {target}")
    if dry_run:
        print("Modo dry-run: nada será escrito; só o que mudaria é reportado.")
    print()

    if check_v03_layout(target):
        return 1

    if migrate_legacy_layout(target, dry_run):
        print()

    deploy_dir = target / ".feat-memory-deploy"
    # Remove o diretório transiente legado (de versões anteriores que tinham
    # merge queue para AGENTS.md). v0.4+ resolve a constituição direto via
    # bloco com sentinelas, sem handoff intermediário.
    if deploy_dir.exists() and not dry_run:
        shutil.rmtree(deploy_dir, ignore_errors=True)

    changes = 0       # arquivos criados/atualizados
    env_actions = 0   # git config + hooks
    warnings = 0      # avisos de frontmatter (deploy não corrige)

    fc, warnings = deploy_constitution(target, args.force, not args.no_merge, dry_run)
    changes += fc
    print()

    changes += deploy_meta(target, dry_run, getattr(args, "profile", None))
    print()

    changes += deploy_changelog(target, dry_run)
    print()

    changes += deploy_ideas(target, dry_run)
    print()

    fc, ec = deploy_gitattributes(target, dry_run)
    changes += fc
    env_actions += ec
    print()

    changes += ensure_gitignore(target, dry_run)
    print()

    changes += deploy_skills(target, args.force, dry_run)
    print()

    changes += deploy_agents(target, dry_run)
    print()

    changes += create_directories(target, dry_run)
    print()

    if not args.no_hooks:
        env_actions += install_git_hooks(target, dry_run)
    else:
        print("Git hooks: pulado (--no-hooks)")
    print()

    if dry_run:
        print("Auditoria inicial: pulada em --dry-run (roda após aplicar)")
    else:
        run_audit(target)
    print()

    print("=" * 38)
    if dry_run:
        parts = []
        if changes:
            parts.append(f"{changes} arquivo(s)")
        if env_actions:
            parts.append(f"{env_actions} ação(ões) de ambiente")
        if parts:
            print(f"Dry-run: {' + '.join(parts)} a aplicar.")
        else:
            print("Dry-run: nada a fazer — tudo em dia.")
        if warnings:
            print(f"⚠ {warnings} aviso(s) de frontmatter para corrigir à mão "
                  "(o deploy não os resolve).")
        print("Nada foi escrito. Rode sem --dry-run para aplicar.")
        print("=" * 38)
        return 0

    print("Deploy concluído.")
    print("=" * 38)
    print()

    print_next_steps(target)

    return 0
