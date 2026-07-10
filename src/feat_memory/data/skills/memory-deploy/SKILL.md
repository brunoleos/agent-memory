---
name: memory-deploy
summary: "instalar/adotar a metodologia num projeto: deploy mecânico e, em legacy, gênese retroativa multi-fonte (testes, telas, código, deps; git secundário)."
description: >-
  Use quando o usuário pede para instalar a metodologia em um projeto (frases como "instale a metodologia", "configure o feat-memory", "rode o setup", "este projeto não tem AGENTS.md", "ajude a adotar esta estrutura"). Conduz a adoção: detecta greenfield versus legacy, executa `feat-memory deploy` (que cuida sozinho do bloco com sentinelas no AGENTS.md), e em projetos legacy faz gênese retroativa por engenharia reversa multi-fonte (code-first): triangula testes, telas, documentação, código e dependências para extrair capacidades e decisões, com o git log como fonte secundária para datar/justificar. Propõe o frontmatter da AGENTS.md (project, stack, constraints) a partir de evidência observável e apresenta ao mantenedor para aprovação — nunca grava esses valores sem aval humano.
---

# Memory deploy

Esta skill é o ponto de entrada único para instalar a metodologia em qualquer projeto. Conduz três etapas: detecção do estado do projeto, deploy mecânico via CLI, e (apenas em projetos legacy) gênese retroativa de ADRs e do Manifest.

A skill **propõe** o frontmatter da `AGENTS.md` (project, stack, constraints) a partir de evidência observável do projeto e **apresenta ao mantenedor para aprovação** antes de gravar — nunca cristaliza esses valores sem aval humano. Esse é o gate: propor é encorajado, gravar sem aprovação é proibido. O bloco de metodologia entre sentinelas markdown é gerenciado pelo `feat-memory deploy` (refrescado a cada execução) e não se confunde com o frontmatter. Seções em prosa específicas do projeto (Identidade, Convenções) seguem sendo autoria do mantenedor, registradas quando ele achar útil.

## Quando usar

A skill aplica-se em duas situações. A primeira é quando o usuário pede para instalar a metodologia pela primeira vez, com frases como "instale a metodologia neste projeto", "configure o feat-memory aqui", "rode o setup". A segunda é quando o usuário pede para adotar a metodologia em um projeto legado, com frases como "este projeto não tem AGENTS.md" ou "preciso popular o Manifest a partir do código existente".

A skill não se aplica quando os artefatos da metodologia já estão totalmente populados. Nesse caso use `memory-bootstrap` para retomar trabalho. Também não se aplica quando o usuário quer apenas rodar o deploy mecânico em CI ou automação; nesse caso, `feat-memory deploy <projeto> --no-merge` deve ser invocado diretamente sem mediação de skill.

## Procedimento

A skill executa três etapas sequenciais. As duas primeiras são sempre executadas. A terceira só roda em projetos legacy.

### Etapa 1: detectar o estado do projeto

Examine o projeto para classificá-lo. Os sinais que distinguem greenfield de legacy são objetivos e podem ser checados rapidamente.

Considere o projeto greenfield quando o repositório tem poucos commits (menos de cinco, ou apenas commit inicial), há pouco ou nenhum código (apenas README e arquivos de configuração), e não há entrypoints públicos identificáveis (rotas HTTP, comandos CLI, módulos exportados).

Considere o projeto legacy quando há histórico Git substancial (dez ou mais commits), código de produção em pastas como `src/`, `app/`, `lib/`, stack identificável via arquivos de manifesto, e ausência de `AGENTS.md` ou apenas template não-personalizado.

Casos de borda incluem projetos com algum código mas em desenvolvimento ativo recente, que devem ser tratados como legacy se há entrypoints públicos identificáveis. Repositório completamente vazio é greenfield sem ressalvas. Quando ambíguo, pergunte ao usuário em vez de assumir.

Apresente sua classificação e peça confirmação antes de prosseguir. Algo como: "Este parece ser um projeto legado, com 47 commits e código em `src/api/`. Vou rodar o deploy e depois fazer gênese retroativa de ADRs e Manifest. Confirma?"

### Etapa 2: executar o deploy mecânico

Em ambos os cenários (greenfield e legacy), rode `feat-memory deploy <projeto>` para estabelecer a estrutura física, onde `<projeto>` é o caminho absoluto da raiz do projeto consumidor. O comando:

- Cria `AGENTS.md` com frontmatter scaffold + bloco com sentinelas, ou — se já existe — anexa o bloco preservando todo o resto do conteúdo do usuário. Em re-deploys, o bloco é refrescado de forma idempotente.
- Cria `CLAUDE.md` (redirect mínimo `@AGENTS.md`) se ausente; deixa quieto se existe.
- Cria `.feat-memory/changelog/UNRELEASED.md` se ausente.
- Copia as skills para `skills/` (sempre sobrescritas; conteúdo de metodologia).
- Cria pastas `.feat-memory/manifest/features/` e `.feat-memory/decisions/proposals/`.
- Instala o pre-commit hook se for repositório Git.
- Refresca os blocos de `.gitattributes` e `.gitignore`.

Não use `--force` aqui. O `--force` reescreve `AGENTS.md` inteira a partir do template, perdendo conteúdo do usuário fora do bloco. O comportamento padrão (sentinel-block refresh) é o que você quer para adoção.

Se o deploy reportar erros, pare e investigue. Geralmente são problemas de permissão ou Python ausente.

Após o deploy estabelecer a estrutura, prossiga para a Etapa 2.1 (propor o frontmatter). Em greenfield, esse é o trabalho final da skill — sugira commitar após a aprovação. Em legacy, faça também a Etapa 3 (gênese de Manifest e ADRs).

### Etapa 2.1: propor o frontmatter para aprovação

O deploy deixou o frontmatter como esqueleto (legacy sem frontmatter) ou template (greenfield), com `project`/`stack`/`constraints` por preencher. Proponha valores a partir de evidência e **apresente ao mantenedor para aprovação — não grave sem aval**. Use `feat-memory schema` para a forma exata de cada campo.

- **project**: o nome do projeto. Fato observável (nome do diretório/repositório) — proponha direto.
- **stack**: detectável dos manifestos (`package.json`, `pyproject.toml`, `go.mod`, …) e da estrutura. Proponha `language`, `architecture` e as deps de runtime relevantes que você observa.
- **constraints**: rascunhe a partir de evidência mecânica — regras impostas por tooling (configs de lint/formatter), gates de CI (suíte obrigatória, build), dependências fixadas/evitadas, e lições/avisos já escritos em prosa na AGENTS.md. Para cada uma, proponha `id`, `severity` (`hard`|`soft`) e `rule`; marque-as explicitamente como **rascunho**. Inclua candidatas de **identidade**: quando o *como* do produto é o próprio valor (ex.: "o movimento é orgânico, por tendências de força"), esse "como" pertence à constituição como constraint — nunca a critérios de aceite (doutrina do observável, ADR-0050).

Apresente o frontmatter proposto inteiro para o mantenedor revisar, editar e aprovar. Gravar valores não-aprovados como se fossem decisão oficial é tão grave quanto cristalizar um ADR sem revisão. Após a aprovação, grave no frontmatter e rode `feat-memory audit` para confirmar conformidade.

### Etapa 3 (apenas legacy): gênese retroativa de ADRs e Manifest

Esta etapa só executa em projetos legacy. Ela popula `.feat-memory/decisions/` e `.feat-memory/manifest/features/` a partir do que já existe no repositório. (O frontmatter da AGENTS.md já foi proposto na Etapa 2.1; aqui o foco é Manifest e ADRs.)

A gênese é **engenharia reversa multi-fonte, code-first** (ADR-0030, ADR-0031). Seu objetivo é reconstruir o *propósito* do sistema — o que ele faz para o usuário e por que foi construído assim — com **alta precisão e baixa alucinação**. Nenhuma fonte sozinha basta: o código é a verdade do *comportamento* mas exige inferência de *intenção*; os testes descrevem a intenção de forma executável; as telas mostram as capacidades como o usuário as vê; o git conta o *porquê/quando* mas é pobre em repos squashados. A precisão vem de **triangular** essas fontes, não de confiar em uma.

Rode `feat-memory migrate` uma vez para colher pistas — ele aponta testes, telas, entrypoints, stack e commits com cara de decisão, agnóstico de linguagem. Trate a saída como "por onde começar a ler", nunca como a resposta.

#### As fontes de evidência, da mais precisa à menos (para inferir propósito)

1. **Testes — a fonte mais precisa de comportamento *pretendido*.** São spec executável, mantida e verificada por asserção. Os de aceitação/E2E (Playwright, Cypress, `*.spec`, `*_test`) descrevem **jornadas de usuário** — cada `describe`/`it`/nome de cenário é quase uma feature + critério `acceptance` prontos. Os unitários revelam os **contratos** de cada módulo. Fixtures e factories expõem o modelo de domínio. Leia os testes *antes* de inferir intenção do código cru.
2. **UI / telas — o mapa de capacidades como o usuário as vê.** Em apps com frontend, o conjunto de telas/rotas/páginas/forms ≈ o conjunto de capacidades. Labels, textos de botão e strings de i18n **nomeiam** as features na língua do usuário (excelente matéria-prima para `user_value`). A tabela de rotas é um índice de features.
3. **Documentação viva.** README (a seção "Features"/"Usage" lista capacidades literalmente), `docs/`, CHANGELOG (narra a evolução e decisões), specs de contrato (OpenAPI/Swagger, schema GraphQL, `.proto`). Declara intenção — mas pode estar **desatualizada**; trate como hipótese a verificar contra o código.
4. **Entrypoints + código (fonte da verdade do comportamento).** A superfície pública — rotas, comandos, exports, handlers, consumers — e o caminho dela até os dados. Leia os entrypoints reais da linguagem (`package.json::bin`/`exports`, `main`, `index.*`, rotas declaradas), não só os diretórios de convenção. O código **prova** o que acontece; o *propósito* ainda exige inferência sua.
5. **Manifestos de dependência + estrutura = decisões.** Cada lib escolhida (e cada uma conspicuamente *evitada*) é uma decisão. O shape de `src/`, as camadas (hexagonal, adapters/ports), os limites de módulo codificam arquitetura. Config de build/lint/CI/Docker e hooks revelam convenções impostas (candidatas a `constraints`, embora quem as autora seja o humano).
6. **Git — o porquê/quando, fonte secundária e variável.** Mensagens de commit, PRs, padrões de revert, tags/releases datam e justificam decisões já identificadas nas fontes acima. Rico se granular, ~nulo se squashado — e isso é esperado, não bloqueio.

#### Técnicas de precisão (como ler sem alucinar)

- **Triangulação.** Uma afirmação sobre comportamento é forte só quando ≥2 fontes independentes concordam (ex.: uma rota + um teste E2E + um bullet do README). Afirmação de fonte única é **hipótese**, não fato.
- **Confiança em camadas.** Separe o **observado** (um teste asserta; o código faz) do **inferido** (você adivinha a intenção). Só cristalize o observado; marque o inferido como tal e leve para confirmação humana. Na dúvida, não escreva.
- **Top-down e bottom-up.** Forme hipóteses de cima (README, telas, entrypoints) e verifique-as de baixo (testes, código). Onde divergem, o código vence para *comportamento* — e a própria divergência é sinal (doc apodrecida, feature meio-removida).
- **Cobertura é mapa de importância.** Código muito testado é capacidade load-bearing; área sem teste é trivial ou arriscada. Use a densidade de testes para priorizar o que vira feature primeiro.
- **Nomes são evidência, não prova.** Nome de função/arquivo/teste codifica intenção mas pode estar stale e mentir. Confirme contra asserções e comportamento.
- **Ausência é sinal.** Uma camada que não existe, uma dependência evitada, uma área sem testes — também são decisões. Investigue o vazio.
- **Datar decisões por múltiplos sinais.** `git blame`, data de entrada da dep no lockfile, CHANGELOG; mtime do arquivo só como último recurso.

#### Fase 3.1: levantar evidências por fonte e formar hipóteses

Varra as seis fontes na ordem acima, registrando para cada achado a **fonte** e o **nível de confiança**. Comece pelos testes e telas (mais precisos para *uso*), cruze com README/docs, e só então mergulhe no código dos entrypoints para confirmar comportamento e expor decisões estruturais. O produto desta fase é uma lista de candidatos a **capacidade** (→ features) e a **decisão** (→ ADRs), cada um com as fontes que o sustentam.

#### Fase 3.2: Manifest a partir das capacidades

Para cada capacidade, proponha uma feature com ID monotônico, `status: shipped`, `user_value` baseado no que faz para o usuário (não na implementação técnica — prefira a linguagem das telas/README à dos identificadores), `contracts` apontando para arquivos reais (inclua o **arquivo de teste** que cobre a capacidade — é o contrato executável), e `acceptance` em notação EARS **derivada diretamente das asserções dos testes** quando existirem, ou inferida do comportamento observável (docstrings, rotas, telas) quando não. Quando uma capacidade não tem teste nem doc que a sustente — só o seu palpite — marque-a como hipótese de baixa confiança ou deixe-a fora (cobertura honesta).

**Critérios só enunciam observáveis externos — nunca mecanismo** (doutrina do observável, ADR-0050). "Retorna os nós sem sobreposição após estabilizar" é observável; "usa atrator central com collision layers" é mecanismo — vocabulário de ADR que apodrece junto com o mecanismo quando ele muda. Quando a *maneira* é identidade do produto, ela sobe à constituição como constraint (Etapa 2.1) e desce aos critérios como **observáveis de trajetória** ("movimento contínuo durante o assentamento", "sem teleporte"), nunca como nomes de algoritmo. Critérios só de estado final tendem ao tautológico; prefira observáveis que discriminem o comportamento ao longo do caminho.

Não inclua `metrics` na gênese inicial — métricas só aparecem quando há medições reais. Apresente as features em lotes pequenos (cinco por vez no máximo). Lotes grandes desencorajam revisão crítica.

**A feature é um registro, não um documento** (doutrina da ortogonalidade, ADR-0050): gere features **frontmatter-only** — id, status, `user_value` em uma frase, aceites, ponteiros. **Nunca transcreva prosa de README/docs para o corpo** — prosa que reafirma outra fonte é memória paralela e drifta (foi o vetor de um incidente real de contaminação de agente). O audit avisa quando o corpo excede o orçamento do perfil (core: 10 linhas não-vazias; full: 40); corpo, quando existir, guarda só racional que nenhum outro artefato abriga. Um arquivo inchado sinaliza feature mal-escopada (provavelmente duas). Rode `feat-memory schema` para o vocabulário exato de campos (obrigatórios, opcionais, patterns EARS).

Aplique a cada feature o **"Teste de uma capacidade"** (detalhado na skill `memory-debrief`): user_value numa frase sem emendar assuntos; `acceptance` coesos; nome = substantivo de capacidade (o audit bloqueia nomes-balde, ADR-0035); bugfix/cleanup não vira feature. Nunca agrupe várias capacidades num arquivo "guarda-chuva".

#### Fase 3.3: ADRs a partir das decisões

Para cada decisão identificada (dependências, estrutura, camadas, cortes de escopo, convenções impostas por tooling), redija um ADR no formato padrão com as quatro seções (Contexto, Decisão, Consequências, Alternativas rejeitadas). Use o **git como fonte secundária** aqui: `git show <sha>` dos candidatos do `migrate`, PRs e o CHANGELOG ajudam a datar a decisão e recuperar a justificativa original; quando o histórico não cobre (squash), data com a melhor evidência (lockfile, CHANGELOG) e descreve o contexto a partir do código. Marque `status: accepted` porque a decisão já está em produção. Filtre decisão arquitetural de verdade versus refactor mecânico ou correção de bug.

Apresente cada ADR proposto individualmente para revisão humana. Não gere uma fila sem aprovação intermediária — o cansaço do revisor é o inimigo. Ao aprovar, escreva diretamente em `.feat-memory/decisions/NNNN-slug.md` (não em `proposals/`, porque são reconstruções de decisões já tomadas, não propostas novas).

#### Fase 3.4: `changelog/UNRELEASED.md` inicial e auditoria

Deixe `.feat-memory/changelog/UNRELEASED.md` **vazio** (só o template) após a gênese: a gênese estabelece o histórico (Manifest + decisions), não trabalho em voo. Não invente um foco; o usuário registra a primeira entrada quando começar a trabalhar, referenciando as F/ADR que tocar. O orçamento de retomada será derivado dessas entradas (ADR-0043).

Rode `feat-memory audit` para validar a estrutura completa e sugira o commit inicial.

## Princípios fundamentais

Cristalização silenciosa é o pior erro possível. Em qualquer fase de gênese (Etapa 3), gerar ADRs ou features sem revisão humana cristaliza interpretações erradas como decisões oficiais. Sempre apresente para aprovação antes de gravar em qualquer artefato. Nenhuma economia de tempo justifica esse risco.

Lote pequeno, revisão crítica. Lotes grandes saturam a atenção do revisor e produzem aprovação por cansaço, que é tão ruim quanto cristalização silenciosa. Limite a cinco itens por rodada de aprovação.

Quando em dúvida, não escreva. Em gênese, isso significa deixar uma feature ou ADR fora da gênese inicial em vez de escrevê-la imprecisa.

Autoria do frontmatter: propor a partir de evidência, aprovar com o humano. A skill propõe `project`/`stack`/`constraints` a partir do que observa (nome do projeto, manifestos, tooling, deps, lições já escritas) e apresenta para aprovação; nunca grava esses valores sem o aval do mantenedor. Constraints inferidas são explicitamente rascunho. O gate é aprovação humana, não proibição de propor — cristalizar valores não-aprovados é tão ruim quanto cristalizar um ADR sem revisão (ADR-0032). A prosa de identidade/convenções fora do frontmatter segue sendo autoria do mantenedor.

## O que evitar

Não rode `feat-memory deploy --force` automaticamente. O `--force` reescreve `AGENTS.md` do template, perdendo conteúdo do usuário fora do bloco com sentinelas. É escolha consciente do operador, e a skill deve respeitar essa escolha apenas quando o usuário pede explicitamente.

Não tente cobrir cem por cento das decisões históricas ou dos entrypoints na primeira gênese. Capture o que é claro e importante; o resto entra incrementalmente conforme o trabalho normal toca essas áreas. Cobertura parcial honesta é melhor que cobertura total inventada.

Não invente `metrics` ou medições estimadas. Se não há valor real medido, omita o campo. Métricas inventadas comprometem a credibilidade do Manifest todo.

Não inclua features para detalhes de implementação puramente internos. A unidade do Manifest é capacidade nomeável com `user_value` em uma frase.

Não transcreva prosa de README/docs para corpos de features, e não enuncie mecanismo em critérios de aceite. As duas coisas são os dois modos de falha comprovados de memória que mente: prosa paralela drifta sem reconciliação, e mecanismo em critério apodrece junto com o mecanismo (ADR-0050).

Não confunda os dois fluxos de criação de ADR. Na gênese retroativa, ADRs vão diretamente para `.feat-memory/decisions/` porque são reconstruções históricas. Em uso normal (skill `memory-debrief`), ADRs novos vão para `.feat-memory/decisions/proposals/` primeiro.
