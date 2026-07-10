# Manual do usuário

Este manual cobre o uso prático da metodologia de memória persistente para agentes em projetos reais. A documentação técnica completa da doutrina está em `METHODOLOGY.md`; o roadmap de extensões está em `FUTURE_IMPROVEMENTS.md`. Este manual é o ponto de entrada para usuários novos.

## O que este projeto resolve

Agentes LLM perdem todo o contexto entre sessões. Sem memória persistente, você precisa explicar o projeto inteiro toda vez que abre uma nova sessão, ou aceitar que o agente vai inventar premissas, ignorar decisões já tomadas, e refazer trabalho que já foi feito. Em projetos pequenos isso é apenas tedioso; em projetos médios a grandes, vira um gargalo real que limita o quanto você consegue delegar ao agente.

A solução é uma camada de memória estruturada em quatro artefatos versionados, um para cada tipo qualitativamente diferente de conhecimento sobre o projeto. A constituição (`AGENTS.md`) registra as regras invariantes que o agente deve respeitar sempre. O manifesto (`manifest/`) descreve o que o sistema faz hoje, com critérios verificáveis. O changelog vivo (`changelog/UNRELEASED.md`) registra o trabalho em voo — e é dele que a próxima sessão deriva o que carregar. As decisões (`decisions/`) registram escolhas arquiteturais imutáveis com supersedência explícita. Quatro skills automatizam os fluxos mais comuns (instalação, início de sessão, debrief antes de commit, briefing pós-pull), e ferramentas em Python validam consistência e detectam problemas.

## Quando usar este projeto

A metodologia faz sentido quando pelo menos duas destas condições são verdadeiras: o projeto vai durar mais de algumas semanas, várias pessoas (humanas ou agentes) vão tocar o código, há decisões arquiteturais não-triviais que merecem registro, e há valor em poder retomar trabalho rapidamente sem reler tudo. Para um script de uso único ou um experimento descartável, a metodologia é overhead injustificado.

A metodologia também faz sentido em projetos legados que estão sendo retomados após pausa longa, onde o conhecimento sobre por que certas escolhas foram feitas se perdeu. Nesse caso, a skill de gênese retroativa reconstrói parte desse conhecimento a partir do histórico Git e do código existente.

## Instalação em três passos

A instalação tem três passos. **Primeiro**, na sua máquina (uma vez só), clone o feat-memory e instale como editable install via pipx:

```bash
git clone https://github.com/brunoleos/feat-memory.git ~/dev/feat-memory
pipx install -e ~/dev/feat-memory
```

A flag `-e` é editable install: o binário `feat-memory` no seu PATH lê código direto do clone, então `git pull` no clone atualiza a CLI imediatamente em todos os projetos consumidores sem precisar reinstalar. Implicações detalhadas estão em "Implicações do editable install" abaixo.

**Segundo**, no projeto consumidor, rode:

```bash
feat-memory deploy /caminho/do/projeto
```

Isso monta `AGENTS.md`, `CLAUDE.md`, `.feat-memory/changelog/UNRELEASED.md`, `.feat-memory/manifest/`, `.feat-memory/decisions/`, `.feat-memory/ideas.md`, `skills/`, `.gitattributes`, instala o pre-commit hook se for repositório Git, e adiciona `.feat-memory-deploy/` (estado transiente do deploy) ao `.gitignore`.

O deploy tem dois perfis (ADR-0050): **core**, default em instalação nova, monta a espinha — constituição, decisions, UNRELEASED e features finas; **full** (`--profile full`) adiciona a operação completa de changelog e um orçamento de prosa maior (valores e semântica na [METHODOLOGY.md](METHODOLOGY.md), §Perfis de instalação). A escolha fica gravada em `.feat-memory/.meta.yaml`; re-deploy sem a flag preserva o perfil, e instalações antigas (pré-v3) resolvem para `full` — você nunca ganha warnings novos só porque a CLI avançou.

**Terceiro**, abra uma sessão com seu agente preferido (Claude Code, Cursor, ou outro que reconheça `AGENTS.md`) e diga "instale a metodologia neste projeto". A skill `memory-deploy` assume o controle, detecta se o projeto é greenfield ou legacy, e conduz a personalização apropriada. Faça o primeiro commit dos artefatos gerados com mensagem clara como "adopt feat-memory methodology".

Em CI ou automação sem intervenção humana, rode `feat-memory deploy <projeto> --no-merge`. A flag `--no-merge` pula a refresh do bloco em `AGENTS.md`/`CLAUDE.md` existentes — útil quando nenhuma modificação é desejada.

A única dependência externa do pacote é PyYAML, declarada em `pyproject.toml` e instalada automaticamente pelo `pipx`. Todo o resto usa apenas a biblioteca padrão do Python 3.10 ou superior, garantindo portabilidade entre Linux, macOS e Windows sem necessidade de WSL ou outras camadas de compatibilidade.

### Implicações do editable install

Em editable install (`pipx install -e <clone>`), o binário `feat-memory` no seu PATH lê código direto do clone. Isso muda algumas coisas em relação a um install convencional:

- **Edições refletem imediatamente.** Modifique `audit.py` no clone e a próxima execução de `feat-memory audit` em qualquer projeto já usa a nova lógica. Não precisa reinstalar.
- **`git pull` no clone atualiza a CLI.** Ótimo para receber correções, mas atenção a versões: o `VERSION` no clone determina qual semver os projetos consumidores estão "rodando".
- **Mover ou deletar o clone quebra a CLI.** Antes de mover o diretório do clone, faça `pipx uninstall feat-memory` e reinstale no novo path.
- **Templates e skills também são live.** Como `data/templates/` e `data/skills/` ficam dentro do pacote (`src/feat_memory/data/`), suas edições afetam o próximo `feat-memory deploy` imediatamente.
- **Não use `pipx upgrade` em editable.** O comando não funciona em modo editable; use `git pull` no clone.
- **Conta um por dev.** Cada desenvolvedor mantém seu próprio clone e seu próprio editable install. Não compartilhe via diretório de rede.

Quando o pacote estiver publicado na PyPI (planejado), o caminho de instalação para usuários finais será `pipx install feat-memory` (sem `-e`), e atualização será `pipx upgrade feat-memory`. As implicações acima deixam de valer porque a CLI passa a ser uma cópia imutável até o próximo upgrade.

## Os quatro artefatos no dia-a-dia

O esquema completo de cada artefato — schema, regras de mutação, porquês — vive na [METHODOLOGY.md](METHODOLOGY.md) (§§1–5). Para operar, basta saber quem responde o quê:

- **`AGENTS.md`** — as regras. Personalizado uma vez, raramente tocado; mudanças em constraints `hard` exigem ADR.
- **`.feat-memory/manifest/features/`** — o que o sistema faz: uma microspec por capacidade (`F-NNNN-slug.md`), com critérios EARS; o INDEX é gerado pelo audit, nunca editado à mão.
- **`.feat-memory/changelog/UNRELEASED.md`** — o trabalho em voo. Cada bullet cita as F/ADR que toca, e é disso que a próxima sessão deriva o que carregar; `feat-memory release` congela o conteúdo em `changelog/<X.Y.Z>.md` imutável.
- **`.feat-memory/decisions/`** — os porquês, imutáveis; mudança de decisão é supersede, nunca edição.

## Fluxo de trabalho típico

O dia-a-dia são quatro momentos, cada um coberto por uma skill — o procedimento autoritativo de cada uma vive no respectivo `skills/*/SKILL.md`:

- **Início de sessão** — "onde paramos?" → `memory-bootstrap` carrega o UNRELEASED, expande só o que ele referencia e apresenta um briefing tático. Vazio = nada em voo; candidatos vêm do funil `ideas.md`.
- **Durante o trabalho** — o agente segue a constituição (o hook bloqueia violação de constraint `hard`); capacidade nova nasce cedo como feature `proposed`, decisão como ADR `proposed`.
- **Antes de cada commit relevante** — "vou commitar" → `memory-debrief` move Manifest e UNRELEASED junto com o código, propõe ADR se houve decisão, roda o audit e fecha com o teste do agente frio. Em branch destinada a merge, checa colisões de ID.
- **Depois de um `git pull`** — "o que veio do pull?" → `memory-pull-brief` reconcilia o UNRELEASED local (read-only sobre `manifest/` e `decisions/`, que já vieram corretos).

## Atualizações da metodologia

A metodologia evolui ao longo do tempo, e cada projeto que a adota precisa de um caminho claro para receber essas evoluções sem perder customizações locais. O versionamento semântico em `VERSION` e o histórico em [.feat-memory/changelog/INDEX.md](.feat-memory/changelog/INDEX.md) tornam a evolução transparente; cada release corresponde a uma tag `vX.Y.Z` em <https://github.com/brunoleos/feat-memory/releases>. A versão da CLI instalada é mostrada por `feat-memory --version` ou `pipx list`.

Em editable install (caminho atual durante o desenvolvimento da própria CLI), atualizar é simplesmente `git pull` no clone. A CLI passa a refletir a versão nova imediatamente. Se quiser fixar em uma tag específica:

```bash
cd ~/dev/feat-memory
git fetch --tags
git checkout v0.3.0
```

Para reaplicar templates e skills no projeto consumidor após um upgrade da CLI, rode `feat-memory deploy <projeto>` novamente — é idempotente, preserva tudo que é seu (conteúdo fora do bloco de sentinelas, UNRELEASED existente, perfil gravado). A especificação completa do que é refrescado, preservado ou pulado está na [METHODOLOGY.md](METHODOLOGY.md), seção **Deploy**.

E quanto à cadência: **upgrade quando doer**. A CLI só avisa sobre desatualização quando o MAJOR difere (ADR-0050/0051); diferenças de minor/patch são silenciosas. Atualize quando um release note resolver uma dor sua — não por existir versão nova.

Para times que usam a metodologia em múltiplos projetos, a recomendação é fixar todos os clones na mesma tag, avançando todos juntos quando uma release nova justifica adoção. Cada projeto consumidor decide quando rodar `feat-memory deploy` para receber as mudanças.

Migrando de v0.1.0 ou v0.2.0 (modelo "clone da tool para `.feat-memory/` no projeto"): instale a v0.3.0 via pipx (passos acima), depois em cada projeto consumidor rode `feat-memory deploy <projeto>`. À época, o comando detectava `.feat-memory/` rastreada pelo Git no projeto consumidor e imprimia instruções para tirar a tool clonada do índice e do disco; os artefatos da metodologia (`AGENTS.md`, `STATE.md`, `manifest/`, etc.) ficavam preservados na raiz. A partir da v0.6.0, a pasta `.feat-memory/` passa a ser o lar dos artefatos da metodologia (`STATE.md`, `manifest/`, `decisions/`) — colisão de nomenclatura que requer cuidado: se você ainda tem clone da tool em `.feat-memory/`, remova-o antes de rodar o deploy v0.6.0+, que vai criar `.feat-memory/manifest/` e `.feat-memory/decisions/` no mesmo lugar.

## Comandos importantes

A auditoria valida schemas, gera os índices e calcula os indicadores de saúde — o que ela garante (e o que deliberadamente não garante) está na [METHODOLOGY.md](METHODOLOGY.md), §Auditoria. Invocações: `feat-memory audit` para o relatório; `--json --strict` para CI; `--strict --no-index` é o modo do pre-commit hook. Para colisões de ID antes de um merge: `feat-memory audit --check-collisions origin/main` — renumere o lado ainda não mesclado.

A verdade semântica dos critérios é da amostragem adversarial: `feat-memory sample --event release` (ou `--event supersede`) emite prompts de refutação para o seu agente executar (METHODOLOGY, §Amostragem adversarial). Para propor ADR a partir do diff: `feat-memory propose-adr --staged` gera draft em `decisions/proposals/` para revisão humana. Para gênese em legacy: `feat-memory migrate --limit 200` imprime pistas (a skill `memory-deploy` já o invoca). Para adapters: `feat-memory features --json` exporta o Manifest estruturado.

## Resolução de problemas comuns

Quando o pre-commit hook bloqueia um commit que parece legítimo, examine a saída da auditoria. Drift de contratos significa que `.feat-memory/manifest/features/F-NNNN.md` aponta para arquivos de código que não existem mais, geralmente porque você refatorou sem atualizar a feature correspondente. A solução é atualizar a feature no mesmo commit do código. Se você precisa contornar deliberadamente em situação excepcional, `git commit --no-verify` ignora todos os hooks, mas use com critério: hooks que não podem ser ignorados acabam sendo desinstalados, e o hook é aliado, não inimigo.

Quando o `.feat-memory/changelog/UNRELEASED.md` parece inconsistente com o código real, o problema é geralmente uma sessão anterior que não fez debrief direito. A solução é invocar a skill `memory-debrief` agora, examinando o diff acumulado desde o último registro e atualizando as entradas para refletir a realidade atual — cada uma citando as F/ADR que toca, porque é delas que a retomada deriva.

Quando duas branches têm features ou ADRs com IDs colidentes, rode `--check-collisions` antes do merge. A solução é renumerar o artefato mais novo na branch que ainda não foi mesclada, atualizando o nome do arquivo, o campo `id` no frontmatter, e qualquer referência cruzada em outras features ou ADRs. ADRs já mesclados na branch destino nunca são renumerados.

Quando o `feat-memory audit` reporta erros de notação EARS em critérios de aceitação, rode `feat-memory schema` (ou veja [docs/SCHEMA-REFERENCE.md](docs/SCHEMA-REFERENCE.md)) — a referência gerada, sincronizada com o validador por teste, lista os campos obrigatórios de cada pattern.

Quando o pre-commit hook não dispara a auditoria e libera commits silenciosamente, é porque o binário `feat-memory` não está no `PATH` do shell que faz o commit. O hook é deliberadamente fail-open nesse cenário: emite um aviso em `stderr` ("AVISO: 'feat-memory' não encontrado no PATH; pulando auditoria") e libera o commit, em vez de bloquear. A justificativa é que hooks que viram inimigo (bloqueando trabalho legítimo de quem ainda não instalou a CLI) acabam sendo desinstalados ou bypassados com `--no-verify` virando hábito, o que destrói a utilidade da checagem para todos. Se você está confiando na auditoria e quer detectar esse cenário, configure CI para rodar `feat-memory audit --strict` no PR — assim o hook local é nudge, e a CI é a rede de segurança real.

## Trabalhando em time

Quando o time tem múltiplas pessoas tocando o projeto, a metodologia funciona sem coordenação adicional na maioria dos casos. Cada pessoa abre uma branch, trabalha, faz debrief, commita, e merge. Os conflitos previsíveis (UNRELEASED, índices) são resolvidos automaticamente pelo `.gitattributes`; a semântica completa de merge e rebase por artefato está na [METHODOLOGY.md](METHODOLOGY.md), §Workflow de merge e rebase.

Os dois pontos onde coordenação importa são a escolha de IDs novos (que pode produzir colisão) e a modificação simultânea da mesma feature (que pode produzir conflito real). Para o primeiro, a skill `memory-debrief` checa colisões automaticamente e propõe renumeração. Para o segundo, a resolução é manual seguindo a regra de "preservar adições, substituir campos de overwrite": critérios de aceitação são aditivos, métricas são substitutivas.

Em projetos onde múltiplos agentes podem rodar em paralelo (por exemplo, um agente de coding mais um agente de testes mais um humano), a metodologia ainda funciona em série. A coordenação multi-agente em paralelo está documentada como melhoria futura em `FUTURE_IMPROVEMENTS.md`.

## Casos de uso de referência

A metodologia foi projetada com três casos de uso principais em mente, e a documentação inclui exemplos pedagógicos de cada um. O caso de uso de uma feature de busca semântica em banco vetorial, exemplificado por `examples/manifest/features/F-0001-vector-similarity-search.md`, mostra como uma capacidade técnica não-trivial é decomposta em metadados estruturados, contratos verificáveis, e seis critérios de aceitação cobrindo os cinco padrões EARS. O caso de uso de uma decisão sobre métrica de similaridade, exemplificado por `examples/decisions/0002-cosine-similarity-default.md`, mostra como uma escolha técnica que parece pequena vira ADR quando há trade-offs reais e alternativas rejeitadas. O caso de uso da própria adoção da metodologia, exemplificado por `examples/decisions/0001-record-architecture-decisions.md`, mostra como o ADR fundacional registra a meta-decisão de adotar ADRs.

Estes exemplos não são copiados pelo `feat-memory deploy` para o seu projeto, ficando apenas no clone do feat-memory (`~/dev/feat-memory/examples/`) para consulta. Você pode usar o ADR-0001 como ponto de partida para o seu próprio ADR fundacional adaptando o contexto, mas os outros dois exemplos são puramente pedagógicos.

## Próximos passos

Depois de instalar a metodologia, três ações curtas estabelecem a fundação. Primeiro, personalize o `AGENTS.md` substituindo o template genérico por descrição real do seu projeto, sua stack, e suas restrições não-negociáveis específicas. Segundo, crie sua primeira feature em `.feat-memory/manifest/features/F-0001-<slug>.md` para a próxima capacidade que você vai construir, mesmo que seja simples. Terceiro, registre seu primeiro ADR em `.feat-memory/decisions/0001-<slug>.md` para a primeira decisão arquitetural não-trivial que você fizer; o ADR fundacional sobre adotar a própria metodologia é uma escolha natural.

A partir daí, o uso é orgânico. Cada sessão começa com `memory-bootstrap`, cada commit relevante termina com `memory-debrief`, decisões importantes viram ADRs, e capacidades viram features. A metodologia desaparece no fundo, e o que sobressai é a sensação de que o agente realmente conhece o projeto.
