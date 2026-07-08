# Melhorias futuras

Este documento cataloga extensões viáveis para a metodologia, organizadas por horizonte de implementação. Cada item descreve o problema que resolve, a forma proposta e os trade-offs envolvidos. A lista não é uma promessa de roadmap; é um inventário de ideias que a operação real do sistema vai eventualmente justificar ou descartar.

## Implementadas

Esta seção registra o que já saiu do plano e está disponível na metodologia. Os itens permanecem documentados para que a história de evolução da metodologia fique explícita, em vez de ser silenciosa.

### Notação EARS completa

Os critérios de aceitação no Manifest agora seguem os cinco padrões canônicos da Easy Approach to Requirements Syntax: ubiquitous, event, state, optional, unwanted, com um sexto padrão complex como escape para combinações. O `feat-memory audit` valida que cada critério declara `pattern` e contém os campos obrigatórios para aquele padrão. Critérios mal-formados são erro de schema e bloqueiam o build.

### Pre-commit hook

O hook em `src/feat_memory/governance/data/hooks/pre-commit` é instalado pelo `feat-memory deploy` e roda `feat-memory audit --strict` antes de cada commit. A flag `--strict` promove warnings (drift) a errors. O hook respeita `--no-verify` como válvula de escape para casos excepcionais. A combinação recomendada continua sendo hook local mais checagem em CI.

### Geração automática de propostas de ADR

A ferramenta `feat-memory propose-adr` examina o diff atual e detecta sinais de mudança arquitetural não-trivial: volume, dependências alteradas, mudanças em múltiplos diretórios, padrões linguísticos em mensagens de commit. Quando detecta sinais, gera um draft em `.feat-memory/decisions/proposals/`, subpasta que o `feat-memory audit` ignora explicitamente para preservar a invariante de imutabilidade dos ADRs reais. O modo `--prompt` emite um prompt estruturado para um agente LLM em vez do template direto, separando detecção determinística de redação que exige julgamento.

### Portabilidade total via Python

Todas as ferramentas e scripts do pacote estão escritos em Python 3.10 ou superior, sem dependência de shell scripts. O pre-commit hook é Python executável. A única dependência externa é PyYAML, declarada em `pyproject.toml` e instalada automaticamente pelo pipx. O pacote roda em Linux, macOS e Windows nativamente.

### Versionamento semântico e changelog

O pacote tem versionamento semântico em arquivo `VERSION` na raiz (lido dinamicamente pelo `pyproject.toml`) e histórico em `CHANGELOG.md` seguindo o formato Keep a Changelog. Cada release publicada no GitHub corresponde a uma tag `vX.Y.Z` e a uma seção do `CHANGELOG.md`.

### Distribuição como CLI Python (v0.3.0)

O feat-memory é distribuído como pacote Python com entry point `feat-memory = feat_memory.cli:main` definido em `pyproject.toml`. O usuário clona o repositório uma vez na máquina e instala em modo editable com `pipx install -e <clone>`; o binário `feat-memory` no PATH lê código direto do clone, então `git pull` no clone atualiza a CLI imediatamente em todos os projetos consumidores. Templates, skills e o pre-commit hook ficam em `src/feat_memory/data/` e são acessados via `importlib.resources` (funciona em editable e wheel install). Esta arquitetura substitui o modelo v0.2.0 ("clonar para `.feat-memory/` dentro do projeto") e elimina a duplicação de scripts em cada projeto consumidor.

### Robustez de tratamento de erros

O `feat-memory propose-adr` ganhou validação prévia de base ref, com mensagens de erro acionáveis quando o repositório tem poucos commits para `HEAD~1` funcionar. O `feat-memory audit` ganhou mensagem acionável quando PyYAML está ausente, incluindo opções de instalação para diferentes ambientes (pip, pip3, virtualenv, --break-system-packages). Estas mudanças tornam o feedback de erro útil em vez de obscuro.

### Cross-check de status vs. release no audit (v0.10.0)

O `feat-memory audit` passou a confrontar o `status` declarado das features contra as versões realmente released. Antes, a auditoria validava validade estrutural (schema, integridade referencial de IDs) mas não verdade semântica — uma feature `in_progress` cujo trabalho já saiu em release passava clean. Foi assim que o próprio repo acumulou 11 features fantasma `in_progress` após v0.6.0–v0.9.0. Agora `validate_release_status` (F-0020, ADR-0024) emite warning quando o `version` de uma feature `in_progress` consta no CHANGELOG ou em tag Git — promovido a error sob `--strict`, bloqueando o commit. Em paralelo, o frescor do STATE acima de 14 dias ganhou destaque visual no relatório (apresentação, não Issue: staleness no commit continua sendo o nudge soft de F-0013). A assimetria — bloquear mentira factual, nudgar higiene — está documentada em ADR-0024.

### Distribuição via PyPI com trusted publishing (v0.11.0)

O pacote passou a ser publicável na PyPI: `.github/workflows/release.yml` builda sdist+wheel e publica a cada tag `vX.Y.Z` via trusted publishing (OIDC, sem token persistente). No caminho, corrigiu-se um bug latente de `package-data` (o pre-commit hook, movido para `governance/data/hooks/` no split F-0017, era omitido do wheel) e adicionou-se `tests/test_packaging.py` para impedir a regressão. Metadados ajustados a PEP 639 (license SPDX, sem classifier de licença). Quando o mantenedor reservar o nome e configurar o publisher, `pipx install feat-memory` passa a ser o caminho de instalação do usuário final. F-0021, ADR-0025.

### CI cross-OS como segunda linha de defesa (v0.11.0)

`.github/workflows/ci.yml` roda `pytest` + `feat-memory audit --strict` em cada push/PR, numa matriz {ubuntu, macos, windows} × {3.11, 3.12}. A matriz cross-OS torna a constraint C1 ("roda nativamente nos três sistemas") verificável por execução em vez de só declarada; o `audit --strict` no CI fecha o furo deixado pelo `--no-verify` do pre-commit. F-0022, ADR-0026.

### Campo `version` em ADRs formalizado (v0.11.0)

O campo `version` no frontmatter de ADRs — presente em ADRs antigos, ausente nos recentes, sem regra — virou opcional formalizado: `validate_decision` valida o formato `X.Y.Z` quando presente mas nunca o exige; `propose-adr` pré-preenche o campo em novos drafts; a METHODOLOGY documenta a semântica (release de aceite). Sem backfill (ADRs antigos sem o campo seguem válidos). Fecha um drift conhecido. F-0023, ADR-0027.

### Constraints `hard` enforced via checkers declarativos (v0.12.0)

Antes adiado ("vago e caro de generalizar; cada regra exige um validador próprio"), o linting de constraints foi promovido a flagship sob o posicionamento de ser **a melhor camada de "constitution"** do spec-driven development: uma constituição *verificada* a cada commit supera uma só lida. A razão que adiava o item é resolvida sem um validador por regra — por um **conjunto fechado** de cinco checkers genéricos (`forbid_paths`, `require_paths`, `forbid_pattern`, `require_pattern`, `dependencies`) que o projeto compõe via YAML, sem escrever Python. Cada constraint pode declarar um bloco `check` opcional no frontmatter do `AGENTS.md`; o `feat-memory audit` o executa contra o repositório e emite Issue herdando a severity da constraint (hard→error/bloqueia, soft→warning); `check` malformado é erro de schema. Vive em `governance/constraints.py` (não em `memory/schemas.py`): executar checker varre a árvore — governança, não schema (ADR-0021). Tudo stdlib + pyyaml (C2 preservada), agnóstico de linguagem — `dependencies` cobre pyproject.toml/requirements.txt/package.json. Dogfood: C1 e C2 deste repo são checadas a cada audit. C3 ("segue a metodologia") e C4 ("docs em pt-br") ficam declarativas — sem checker barato e confiável, limitação honesta. F-0024, ADR-0028.

### Reforma v3: doutrinas, perfis e a condicional do manifest (v3.0.0)

Uma auditoria de agente frio num consumidor real encontrou dois stales de memória na mesma sessão — mecanismo apodrecido num critério de aceite e prosa paralela driftada num README — e o debate de arbitragem que se seguiu produziu a maior reforma da metodologia até aqui (ADR-0050, com procedência de evidência por item e condição de falsificação pré-registrada; postmortem de migração em ADR-0051). Entregas: quatro doutrinas na METHODOLOGY (memória-errada-pior-que-nenhuma; paralela-drifta/ortogonal-não; observável delimitada; procedência de evidência); perfis de deploy `core|full` com `core` default para adoções novas (F-0042); manifest rebaixado a registro com orçamento de prosa por perfil (F-0043); propagação de supersede com acknowledgment por arquivo via `reconciled:` (F-0044); amostragem adversarial `feat-memory sample` com prompts de refutação ponderados por risco (F-0045); nudge de léxico de mecanismo com a nova severidade `info`, nunca promovida (F-0046); audit reenquadrado (integridade referencial, não verdade semântica); consumer notice só em MAJOR ("upgrade quando doer"); teste do agente frio fechando todo debrief; gênese retroativa gerando features finas sem transcrever prosa.

## Curto prazo

### Comando de busca no Manifest — **[Adiado]**

> _Triagem 2026-06-03: ganho marginal com ~20 features e mantenedor solo. Revisitar quando o Manifest passar de ~50 features._

Um subcomando `feat-memory query` que responde perguntas comuns sem o agente precisar carregar arquivos. Exemplos: `feat-memory query depends-on F-0007` lista features que dependem de `F-0007`, `feat-memory query affected-by ADR-0002` lista features afetadas por uma decisão, `feat-memory query stale --days 90` lista features sem update há mais de noventa dias. Reduz o custo de retomada para perguntas frequentes.

## Médio prazo

> _Triagem 2026-06-03: nenhum destes entrou no ciclo v0.11.0. Os marcadores abaixo registram a decisão e a razão para não reabrir a discussão sem fato novo._

### Coordenação multi-agente — **[Adiado]**

> _YAGNI: o uso real é sessão única, projeto solo. Revisitar quando houver trabalho concorrente de fato no mesmo repo._

A versão atual assume sessão única em série. Quando duas sessões de Claude Code rodam em paralelo no mesmo repositório, há risco de conflito no `.feat-memory/STATE.md` e de duplicação de IDs em features novas. A proposta é um protocolo simples de lock: o agente cria um arquivo `.state.lock` com sua identidade ao iniciar uma sessão; outros agentes detectam o lock e operam em modo read-only no Manifest até o lock ser liberado. Para IDs novos, uma reserva atômica via Git push força resolução de conflito explícita.

### Coverage real ligado a pytest-cov — **[Rejeitado]**

> _Acopla a tool a Python/pytest. A metodologia é genérica (serve qualquer projeto/linguagem); `manifest_coverage` mede presença de teste por design. Coverage real é trabalho do CI do projeto consumidor, não da tool._

O campo `manifest_coverage` hoje mede apenas presença de arquivos de teste, não cobertura real de execução. A extensão é cruzar com a saída de `pytest --cov` (ou equivalente) e reportar cobertura real por feature. Uma feature pode ter arquivo de teste linkado mas com cobertura efetiva de quinze por cento, e o sistema atual não detecta isso. O trabalho é em parsear o relatório de coverage e mapear de volta para feature IDs via convenção de nomes ou marcadores no teste.

### Geração de OpenAPI a partir do Manifest — **[Rejeitado]**

> _Acopla a tool a um domínio (APIs HTTP) e a Pydantic/OpenAPI. Fere a identidade genérica. Cabe a um plugin externo, não ao core._

Para features de API, o campo `contracts.api` aponta para a função handler e `contracts.schemas` aponta para os schemas Pydantic. Com essa informação, é possível gerar a especificação OpenAPI automaticamente, garantindo que a documentação externa fique sempre alinhada com o Manifest interno. Útil principalmente em sistemas com SDK de cliente gerado a partir de OpenAPI, onde drift entre spec e implementação tem impacto direto em consumidores.

### Snapshot histórico do State — **[Adiado]**

> _`git log .feat-memory/STATE.md` já entrega isso ad-hoc; baixo valor incremental para uma ferramenta dedicada._

O `.feat-memory/STATE.md` é reescrito a cada sessão e a história fica no Git. Para análises retrospectivas — "qual era o foco do time em janeiro?", "quanto tempo passamos em F-0007?" — fazer `git log .feat-memory/STATE.md` é viável mas inconveniente. A proposta é um script que extrai snapshots semanais do `.feat-memory/STATE.md` e produz uma timeline navegável. Nada que não dê para fazer ad-hoc, mas a presença da ferramenta induz a hábito.

## Longo prazo

### Busca semântica sobre o Manifest — **[Rejeitado]**

> _Exigiria dependência de embeddings/índice vetorial, ferindo C2 (dependência externa única: pyyaml). Em escala, o subcomando `query` (determinístico) cobre a maior parte da necessidade sem deps._

Em projetos com mais de cinquenta features, encontrar a feature relevante por nome ou tags vira difícil. Indexar os campos `name`, `user_value` e o corpo das features em embeddings permite busca por similaridade: "qual feature trata de autenticação?" retorna as três mais relevantes mesmo que nenhuma tenha "autenticação" no nome. O custo é manter o índice atualizado; em projetos pequenos não vale, em projetos grandes economiza muito tempo.

### Federação entre projetos — **[Adiado]**

> _Especulativo; sem caso real de monorepo/multi-projeto consumindo a tool hoje._

Em monorepos ou em organizações com múltiplos projetos relacionados, faz sentido linkar Manifests. Uma feature em `projeto-a` pode declarar `depends_on_external: projeto-b/F-0042`, e o `feat-memory audit` consulta o Manifest do projeto vizinho via Git submodule ou registry. Habilita raciocínio cross-cutting sobre dependências sem precisar duplicar informação.

### Versionamento de schema — **[Adiado]**

> _Torna-se necessário só no primeiro bump de `schema_version`. Até lá é YAGNI; quando vier, é pré-requisito de qualquer evolução de schema._

A versão atual usa `schema_version: 2` em todos os artefatos. Quando o schema mudar (campos novos, formatos diferentes), precisamos de migration scripts que atualizem artefatos antigos preservando informação. A proposta é um diretório `src/feat_memory/migrations/` com scripts numerados, um para cada incremento de schema, expostos como `feat-memory migrate-schema --to N` (dry-run por padrão).

### Integração com feature flags — **[Rejeitado]**

> _Acopla a tool a SaaS externos (LaunchDarkly/Unleash/Flagsmith), ferindo a portabilidade e a dependência única. Cabe a adapter externo, não ao core._

Quando `status: shipped` em produção é mediado por feature flags (LaunchDarkly, Unleash, Flagsmith), seria útil que o Manifest refletisse o estado real de exposição. Uma feature pode estar marcada como shipped mas com flag desligada para 95% dos usuários, e essa nuance importa para decisões operacionais. A integração é via adapter por provedor, lendo o estado da flag e anexando ao registro da feature.

### Análise de drift histórico — **[Adiado]**

> _Agora viável (a CI existe — F-0022), mas é nice-to-have de time grande. Sem demanda real, fica no horizonte._

Manter `manifest_drift` é uma série temporal valiosa: pode-se medir quanto drift acumulou entre releases, quais features são mais propensas a drift, e correlacionar com regressões. A proposta é um job de CI que registra a métrica diariamente em uma tabela ou arquivo append-only, e um dashboard mínimo (HTML estático gerado por script) para visualização. Útil principalmente em times grandes onde refactors frequentes desafiam a manutenção do Manifest.

## Ideias avaliadas e rejeitadas

Algumas extensões parecem atraentes mas não passam o teste de custo-benefício, e vale documentar a rejeição para evitar reabrir a discussão.

A geração automática completa de ADRs a partir de diffs foi rejeitada porque ADRs são exatamente o tipo de conteúdo onde julgamento humano é insubstituível. A versão implementada de `feat-memory propose-adr` é deliberadamente parcial: ela detecta sinais e gera template, mas exige preenchimento humano (ou assistido por LLM em modo `--prompt`) para se tornar ADR de fato. Geração end-to-end totalmente automática produziria ADRs vazios e poluiria a memória arquitetural.

Migração automática silenciosa do Manifest a partir do código foi rejeitada pelo mesmo motivo da migração de ADRs: cristaliza interpretações erradas como verdades. O agente pode propor, o humano decide.

Webhooks que disparam em cada commit do State foram rejeitados por baixo retorno: a frequência seria alta, o sinal seria ruidoso, e o problema que resolveriam (notificar pessoas sobre mudanças) é melhor resolvido por hábito de leitura semanal do `git log .feat-memory/STATE.md` ou pelo dashboard de drift histórico.

Substituir os arquivos markdown por banco de dados foi avaliado e rejeitado. A simplicidade de markdown mais Git é o que torna a metodologia portável e auditável; mover para um banco perde a propriedade de "tudo está no repositório, versionado, sem dependência externa". Para projetos onde isso muda — federação entre dezenas de equipes, por exemplo — o item de federação acima é o caminho preferível, não substituição completa.
