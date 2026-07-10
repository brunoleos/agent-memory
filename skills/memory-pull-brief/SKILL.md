---
name: memory-pull-brief
summary: "após `git pull`, brifar o que veio do remote e reconciliar o UNRELEASED.md."
description: Use após git pull em projeto cliente quando o usuário pergunta o que mudou no remote (frases como "o que veio do pull?", "brifa as mudanças do main", "atualizei meu branch, o que mudou?", "reconcilia o em-voo com o que veio"). Examina o diff do pull, identifica mudanças em features e decisions e no bloco metodológico de AGENTS.md, cruza com .feat-memory/changelog/UNRELEASED.md local, e propõe ajustes para refletir a nova realidade. Read-only sobre .feat-memory/manifest/ e .feat-memory/decisions/ — só escreve em .feat-memory/changelog/UNRELEASED.md após aprovação do usuário.
---

# Memory pull-brief

Quando o usuário acaba de fazer `git pull` (ou um merge equivalente) e quer saber o que veio do remote, execute esta rotina antes de seguir trabalhando.

## Quando usar

Esta skill se aplica quando o usuário diz coisas como:
- "o que veio do pull?"
- "brifa as mudanças do main"
- "atualizei meu branch, o que mudou?"
- "reconcilia o em-voo com o que veio"
- "fiz pull, o que mudou nos artefatos?"

Também se aplica por delegação a partir de `memory-bootstrap` quando o último commit é merge **e** o merge tocou `.feat-memory/manifest/features/`, `.feat-memory/decisions/`, ou o bloco entre sentinelas de `AGENTS.md`. Nesse caso, a pull-brief roda antes do briefing tático normal da bootstrap.

Não se aplica para:
- Pulls que só trouxeram código (nenhum artefato da metodologia tocado) — termine cedo, em uma frase
- Sessões sem pull recente (não invente um range)

## Procedimento

Execute em ordem. Cada passo é condicional ao que veio.

### 1. Determine o range do pull

Por padrão, use `@{1}..HEAD` — `@{1}` é a posição anterior do reflog, então este range cobre o que o último pull (ou merge/reset) trouxe.

Antes de aceitar o default, verifique a ação anterior:

```
git reflog -1 --format='%gs'
```

Se a mensagem **não** menciona `pull` ou `merge`, o range default é ambíguo (o usuário pode ter feito commits locais depois do pull). Nesse caso, peça ao usuário a base explícita. Não chute. Registre a base usada no briefing.

### 2. Liste arquivos tocados

```
git diff --name-only <base>..HEAD
```

Filtre para os caminhos relevantes:
- `.feat-memory/manifest/features/F-*.md` — novos, modificados, removidos
- `.feat-memory/decisions/*.md` (incluindo `proposals/` e `superseded/`)
- `.feat-memory/changelog/*.md` — releases novos congelados upstream
- `AGENTS.md` — apenas se o diff atingiu o conteúdo entre as sentinelas

**Ignore `changelog/UNRELEASED.md`.** O `.gitattributes` da metodologia o marca com `merge=ours`, então mudanças do colega são silenciosamente descartadas pelo merge driver. Reportar seria enganoso.

Se nenhum arquivo relevante apareceu, encerre em uma frase: "Pull não tocou artefatos da metodologia." Não invente briefing.

### 3. Extraia mudança semântica de cada arquivo

Para arquivos novos: leia o frontmatter atual. Para modificados: compare o frontmatter antes (`git show <base>:<path>`) e depois. Reporte:

- **Features**: ID, transição de `status`, mudança de `version`, mudanças em `acceptance` (resumido)
- **ADRs**: ID, transição de `status`, `supersedes` / `superseded_by`, `affects_features`
- **Releases (`changelog/<tag>.md`)**: versões novas congeladas upstream
- **AGENTS.md (bloco sentinela)**: indique apenas que a metodologia foi atualizada upstream

Para removidos: registre o ID e o slug.

### 4. Reconcilie com o `changelog/UNRELEASED.md` local

Não há lista `active_*` — o conjunto ativo é **derivado** das referências `F-NNNN`/`ADR-NNNN` nas entradas-bullet do `UNRELEASED.md` local. Para cada referência citada nas suas entradas em voo, verifique se mudou upstream:

- Feature referenciada que virou `shipped`/`deprecated` upstream → a entrada do UNRELEASED pode estar obsoleta (o trabalho já saiu pelo colega) → propor ajustar/remover a entrada
- ADR referenciado que virou `superseded` upstream → idem
- Feature/ADR referenciado **removido** upstream → propor ajuste (e alertar que pode indicar incompatibilidade de branches — pedir confirmação)

Não proponha **adições** ao UNRELEASED automaticamente. Novidades do colega são contexto que o usuário deve conhecer, mas só entram em foco por decisão dele.

### 5. Apresente o briefing e proponha ajustes

```
**Pull range:** <base>..HEAD (N commits)
**Novidades upstream:**
- F-XXXX (slug) — nova, status: shipped
- F-YYYY (slug) — status: in_progress → shipped
- ADR-NNNN (slug) — nova, affects: F-YYYY

**Ajustes propostos no changelog/UNRELEASED.md:**
- Remover/ajustar a entrada que cita F-YYYY (agora shipped upstream)

Aprova os ajustes? (s/n)
```

Aguarde aprovação explícita antes de escrever.

### 6. Aplique e valide

Após aprovação:
- Edite `.feat-memory/changelog/UNRELEASED.md`, ajustando/removendo as entradas obsoletas
- Rode `feat-memory audit --strict` para detectar drift (ex.: uma entrada cita ADR removido upstream). Se reclamar, surfaceie sem tentar consertar — pode indicar conflito real que o usuário precisa decidir.

## O que evitar

- Não modifique `.feat-memory/manifest/features/*.md` nem `.feat-memory/decisions/*.md`. Vieram corretos do pull — escrever neles reverteria trabalho de colegas.
- Não adicione entradas ao UNRELEASED automaticamente. Novidades do colega entram em foco só por decisão explícita dele.
- Não execute se o branch local tem commits feitos depois do pull (passo 1 detecta) — o range fica ambíguo. Peça base explícita.
- Não duplique briefing quando chamada por delegação da bootstrap. Termine a pull-brief, deixe a bootstrap seguir para a expansão das refs com o UNRELEASED já reconciliado.
- Não tente diff de `UNRELEASED.md` — `merge=ours` dropa mudanças upstream silenciosamente.
