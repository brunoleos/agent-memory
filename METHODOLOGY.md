# Metodologia: memória persistente para agentes

## Princípios

O problema que esta metodologia resolve é específico e mensurável: agentes LLM operando em código carregam três tipos qualitativamente distintos de conhecimento — invariantes do projeto, capacidades implementadas, foco operacional — e cada um tem ciclo de vida próprio. Misturar esses tipos em um único arquivo gera dois problemas simétricos: o conteúdo estável fica poluído por contexto efêmero, e o conteúdo efêmero compete por atenção com regras permanentes. A solução é separar por ciclo de mutação, não por tópico.

A escolha de quatro artefatos não é arbitrária. Cada um responde uma pergunta que os outros não respondem bem, e cada um tem uma regra de mutação que torna a manutenção previsível. Esta assimetria é o que mantém o sistema barato no longo prazo, mesmo após anos de desenvolvimento contínuo.

| Artefato | Pergunta | Verdade | Mutação |
|---|---|---|---|
| `AGENTS.md` | Sob quais regras? | Normativa | Rara |
| `.feat-memory/manifest/` | O que existe hoje? | Descritiva | Append-only |
| `.feat-memory/changelog/` | O que está em voo / o que shippou? | Volátil + imutável | UNRELEASED editável; releases imutáveis |
| `.feat-memory/decisions/` | Por que escolhemos assim? | Histórica | Imutável + supersede |

A metodologia adota convenções consolidadas em vez de inventar vocabulário. O arquivo `AGENTS.md` segue a convenção multi-agente reconhecida por ferramentas como Claude Code, Cursor, Aider e Continue; ADRs em pasta `decisions/` seguem o padrão de Michael Nygard de 2011; os critérios de aceitação seguem a notação EARS (Easy Approach to Requirements Syntax) com seus cinco padrões canônicos. Toda a inteligência mora na disciplina das mutações, não em ferramentas exclusivas.

Há uma assimetria deliberada no outro sentido: o que **não** é artefato. O planejamento de uma sessão é efêmero — vive na conversa ou no plan mode da ferramenta — e **não** vira um quinto artefato persistente (um *spec* ou design doc longo). Um spec duplicaria o Manifest (o quê) e os ADRs (o porquê) e apodreceria como qualquer artefato que ninguém relê. O registro durável de uma sessão é ADR + Feature; a disciplina que torna isso seguro é escrevê-los cedo — ADRs como `proposed`, features como `planned` — para que a retomada dependa deles, e não de um plano que some no próximo reset de contexto (ADR-0041).

## Doutrinas

Quatro normas transversais governam todos os artefatos e skills. Elas nasceram de
evidência de campo — dois stales encontrados por um agente frio num consumidor real,
cada um provando uma doutrina distinta — e a procedência exata de cada uma está
registrada no [ADR-0050](.feat-memory/decisions/0050-v3-reform-observability-and-profiles.md).

### Memória errada é pior que memória nenhuma

Um agente frio confia no que a memória afirma; um axioma falso absorvido da memória
contamina toda a sessão sem deixar sintoma. O objetivo do sistema não é ter memória —
é ter memória que não mente. Corolário operacional: afirmação sobre um artefato
(inclusive a de um auditor) se verifica contra o artefato, nunca se repete de segunda
mão.

### Memória paralela drifta; memória ortogonal não consegue driftar

Todo conteúdo que *reafirma* o que código, testes ou README já mostram é memória
paralela: uma segunda fonte que inevitavelmente diverge da primeira. Todo conteúdo
que registra o que o código não pode expressar — IDs estáveis, status, porquês,
alternativas rejeitadas, trabalho em voo — é ortogonal: não há original com que
divergir. A metodologia corta o paralelo e cultiva o ortogonal: prosa vive numa
fonte só; artefatos de memória carregam ponteiros, não cópias.

### Doutrina do observável

Critérios de aceite só enunciam **observáveis externos** — o que se pode verificar
de fora, sem citar o mecanismo interno. Mecanismo ("qual algoritmo", "qual estrutura
de força") é território exclusivo de ADR: quando o mecanismo muda, o ADR é superseded
e o critério observável sobrevive intacto. Duas delimitações: (1) quando o *como* é
identidade do produto (a maneira é o valor), ele sobe à constituição como constraint
e desce aos critérios apenas como **observáveis de trajetória** (propriedades do
percurso, nunca nomes de algoritmo); (2) critérios só de estado final tendem ao
tautológico — um mecanismo que viole a identidade também "chega ao fim" — então
prefira observáveis que discriminem o comportamento ao longo do caminho.

### Disciplina de procedência de evidência

Toda mudança de metodologia ou reforma nomeia a evidência exata que a prova. Um
incidente não pode ser alistado como prova de itens que ele não prova: inflar a
procedência das próprias reformas é o mesmo pecado da memória que mente. Quando a
evidência sustenta menos do que o texto reivindica, o texto encolhe.

## 1. Constitution: `AGENTS.md`

O `AGENTS.md` é o ponto de entrada do projeto. Ele segue a convenção multi-agente que funciona com Claude Code, Cursor, Aider, Continue e outras ferramentas, eliminando a necessidade de uma "skill de bootstrap" customizada e de duplicar instruções por ferramenta. Um arquivo `CLAUDE.md` mínimo coexiste na raiz contendo apenas `@AGENTS.md`, que faz o Claude Code carregar a constituição via sintaxe de importação. Times que usam apenas uma ferramenta podem manter só o arquivo correspondente; times multi-agente compartilham a mesma constituição sem duplicação.

O `AGENTS.md` contém apenas o que não muda entre sessões: identidade do projeto, restrições técnicas, e ponteiros para os outros artefatos.

O frontmatter YAML torna o conteúdo parseável por scripts sem sacrificar legibilidade humana. As restrições têm `severity` explícita: `hard` bloqueia o build quando violada, `soft` apenas gera warning. Esta distinção é o que separa convenções de estilo (que podem ser ignoradas em casos extremos) de regras de segurança (que nunca podem).

Cada restrição pode declarar um bloco `check` opcional que a torna **enforced** em vez de só declarativa: o `feat-memory audit` o executa contra o repositório e emite uma violação herdando a `severity` da restrição. O conjunto de checkers é fechado e genérico — `forbid_paths`, `require_paths`, `forbid_pattern`, `require_pattern` e `dependencies` — composto via YAML, sem código por regra ([ADR-0028](.feat-memory/decisions/0028-constraints-declarative-checkers.md)). Restrição sem `check` permanece puramente declarativa. Nem toda regra é mecanizável de forma barata e confiável (o idioma da documentação, por exemplo); o schema não finge que é — enforça onde dá, declara onde não dá. Tudo opera com a dependência única do projeto, sem ferramentas externas.

O campo `budgets` define os orçamentos de tamanho que o sistema impõe sobre si mesmo. O orçamento de retomada (CLAUDE + UNRELEASED + dois índices) deve ficar abaixo de doze kilobytes para que um agente possa carregar todo o contexto inicial em poucos tokens. O `UNRELEASED.md` deve ficar enxuto pela mesma razão: crescimento descontrolado significa que o agente não está promovendo o trabalho para release nem para os artefatos apropriados.

Mudanças em `AGENTS.md` exigem ADR sempre que alteram restrições `hard` ou referenciam novas convenções arquiteturais. A regra prática é: se a mudança requer explicação para um futuro contribuidor, ela merece ADR.

## 2. Manifest: `.feat-memory/manifest/`

O Manifest é descritivo, não aspiracional. Cada arquivo descreve uma capacidade que existe ou está sendo construída agora, com contratos verificáveis no código. A estrutura é uma pasta com um arquivo por feature mais um índice gerado automaticamente, simétrica à pasta `.feat-memory/decisions/`.

A escolha de um arquivo por feature, em vez de um arquivo monolítico, resolve três problemas simultaneamente. Diffs no Git ficam limpos quando uma feature evolui isoladamente. O agente carrega apenas as features relevantes para a tarefa atual, mantendo o orçamento de contexto sob controle. E a história de cada feature fica preservada no `git log` do seu próprio arquivo, sem precisar de timestamps redundantes no documento.

### Schema da feature

Cada arquivo de feature tem o nome `F-NNNN-slug.md`, onde NNNN é um número monotônico de quatro dígitos e slug é um identificador curto em kebab-case. O ID nunca é reutilizado; uma feature deprecada vira `status: deprecated` mas mantém o arquivo, permitindo que ADRs e outras features continuem referenciando-a com integridade.

Os campos obrigatórios do frontmatter são `id`, `name`, `status`, `user_value`, `contracts` e `acceptance`. Os opcionais incluem `version` (semver da última release que tocou a feature), `owner` (time ou pessoa), `depends_on` (lista de IDs de outras features), `decisions` (lista de IDs de ADRs relacionados) e `metrics` (medidas operacionais, com timestamp).

A feature é um **registro, não um documento** (doutrina da ortogonalidade, ADR-0050): o valor vive no frontmatter — aceites observáveis e ponteiros — e o corpo em prosa é onde memória paralela se acumula. O `feat-memory audit` emite warning quando o corpo excede o orçamento do perfil de instalação (`core`: 10 linhas não-vazias; `full`: 40). Corpo, quando existir, guarda apenas racional que nenhum outro artefato abriga — nunca transcrição de README/docs. Critérios de aceite enunciam **observáveis externos, nunca mecanismo** (doutrina do observável): vocabulário de mecanismo pertence a ADRs e, quando aparece em critério, o audit emite um nudge informativo derivado do léxico dos próprios ADRs (F-0046).

O campo `status` aceita quatro valores: `proposed` (intencionada, ainda não construída), `in_progress` (em construção ativa), `shipped` (entregue e em uso) e `deprecated` (mantida apenas para compatibilidade reversa). A transição de status é registrada no commit que faz a mudança. `proposed` é o **mesmo estado de entrada de um ADR** — o vocabulário do futuro é unificado entre Feature e ADR (ADR-0047).

O campo `contracts` é o mais importante porque torna o arquivo automaticamente verificável. Cada caminho referenciado deve apontar para um arquivo que existe no código (`src/api/search.py::search_endpoint` significa "função `search_endpoint` no módulo `src/api/search.py`"). O `feat-memory audit` checa estes caminhos e marca como drift qualquer referência quebrada.

### Critérios de aceitação em notação EARS

O campo `acceptance` é uma lista de critérios estruturados na notação EARS. Cada critério tem um `id` estável e um `pattern` que determina os campos obrigatórios. A notação distingue cinco situações qualitativamente diferentes em que um requisito pode se aplicar, e a explicitação do padrão elimina ambiguidade sobre quando o requisito está em vigor.

O padrão **ubiquitous** descreve um comportamento sempre ativo, uma invariante do sistema. Tem apenas o campo `requirement`. A formulação canônica é "o sistema deve sempre X". Use para propriedades que devem valer em qualquer estado, como "embeddings devem permanecer L2-normalizados".

O padrão **event** descreve uma resposta a um gatilho externo, do tipo estímulo-resposta. Tem campos `trigger` e `response`. A formulação canônica é "quando X, o sistema deve Y". Use para ações iniciadas externamente, como "quando o endpoint recebe uma query, retornar top-k".

O padrão **state** descreve um comportamento que se aplica enquanto o sistema está em determinada condição. Tem campos `state` e `response`. A formulação canônica é "enquanto X, o sistema deve Y". Use para comportamentos condicionais ao estado interno, como "enquanto reindex está rodando, retornar 503".

O padrão **optional** descreve um comportamento que se ativa quando uma feature opcional está presente. Tem campos `feature` e `response`. A formulação canônica é "onde X for fornecido, o sistema deve Y". Use para flags ou parâmetros opcionais, como "onde metric=dot_product for fornecido, usar dot product".

O padrão **unwanted** descreve uma resposta a uma situação indesejada. Tem campos `trigger` e `response`. A formulação canônica é "se X, então o sistema deve Y". Use para condições de erro e proteções defensivas, como "se um vetor zero for fornecido, retornar 400".

O padrão **complex** existe como escape para combinações que não cabem nos cinco padrões básicos. Tem apenas o campo `requirement` em prosa estruturada. Use com parcimônia: a maioria dos critérios cabe em um dos cinco padrões canônicos, e quebrar em múltiplos critérios é geralmente preferível a usar `complex`.

A validação no `feat-memory audit` exige que cada critério tenha `pattern` declarado e que os campos obrigatórios para aquele padrão estejam presentes e não-vazios. Critérios mal-formados bloqueiam o build, garantindo que a notação seja seguida consistentemente.

### Quando criar uma feature

A unidade de uma feature é uma capacidade coerente que entrega valor identificável ao usuário ou ao operador do sistema. "Pool de conexões com Oracle" é uma feature; "função que parseia JSON" não é, é detalhe de implementação. A regra prática: se você consegue escrever um `user_value` em uma frase sem usar termos puramente técnicos, é feature; senão, é parte de uma feature maior.

Features podem (e frequentemente devem) depender umas das outras. `F-0007 vector-similarity-search` depende de `F-0003 docling-ingest` e `F-0005 embedding-pipeline`, e essa cadeia fica explícita em `depends_on`. Quando uma feature é deprecada, o `feat-memory audit` detecta automaticamente outras features que ainda dependem dela e gera warning.

## 3. Changelog vivo: `.feat-memory/changelog/`

O changelog é o artefato volátil — e também o histórico imutável, na mesma pasta, distinguidos só por estarem ou não tagueados. `changelog/UNRELEASED.md` guarda o **trabalho em voo** (concluído mas não lançado): entradas-bullet no estilo Keep-a-Changelog, cada uma referenciando as `F-NNNN`/`ADR-NNNN` que toca. `changelog/<X.Y.Z>.md` é um arquivo **imutável por tag** — o histórico de releases; `changelog/INDEX.md` é gerado (ADR-0042).

O **orçamento de retomada é derivado**: o conjunto de features e ADRs ativos é a união das referências citadas nas entradas-bullet do UNRELEASED — não há lista `active_*` mantida à mão (que envelhecia silenciosamente). Isso transforma o UNRELEASED num cursor sobre o Manifest: o agente carrega só os arquivos referenciados, mantendo o contexto enxuto. UNRELEASED vazio = nada em voo — a `memory-bootstrap` então olha o último release no `INDEX` e o backlog de sugestões (ADR-0043, ADR-0046).

`feat-memory release X.Y.Z` fecha um ciclo: congela o UNRELEASED em `changelog/<X.Y.Z>.md`, reinicia o UNRELEASED, regenera o INDEX e cria a tag `vX.Y.Z`. O bump de `VERSION` é **per-commit** (a versão evolui visível); a **tag, só no release** (ADR-0045). A imutabilidade dos arquivos por-tag dá a rastreabilidade reversa que o `Recent` dava, sem buffer circular a manter — e a pasta por-tag não colide em merge multiagente como o `STATE.md`/`CHANGELOG.md` monolíticos colidiam (ADR-0042/0043, que superseded o event-sourcing de STATE da ADR-0018/0019).

## 4. Decisions: `.feat-memory/decisions/`

Cada decisão arquitetural não-trivial vira um arquivo numerado em `.feat-memory/decisions/NNNN-slug.md`. Decisões nunca são editadas após `accepted`; são substituídas por novas que apontam para as antigas via `supersedes`. Esta imutabilidade é fundamental — uma decisão editável é só uma anotação, não tem o peso histórico que justifica o esforço de escrevê-la.

O frontmatter referencia features explicitamente via `affects_features`. Uma decisão pode afetar várias features, e uma feature pode encarnar várias decisões. Esta relação muitos-para-muitos é o que torna ADRs e Manifest ortogonais em vez de redundantes.

Os campos obrigatórios do frontmatter de um ADR são `id`, `date` e `status`. O campo `version` é **opcional**: quando presente, registra a release (semver `X.Y.Z`, prefixo `v` aceito) em que a decisão foi aceita — simétrico ao `version` das features. O `feat-memory audit` valida o formato quando o campo existe, mas nunca o exige (ADRs sem `version` permanecem válidos). O `feat-memory propose-adr` pré-preenche o campo com a versão atual do pacote no draft gerado. Não há backfill obrigatório: ADRs antigos sem o campo continuam corretos.

O corpo segue quatro seções padronizadas: Contexto (o problema), Decisão (a escolha feita), Consequências (positivas e negativas), Alternativas rejeitadas (com a razão da rejeição). A seção de alternativas é a mais importante e a mais frequentemente esquecida. Sem ela, um futuro leitor não tem como saber se a alternativa óbvia já foi considerada e descartada por uma boa razão, ou se ninguém pensou nela.

Quando uma decisão é substituída, o ADR original tem apenas seu campo `superseded_by` atualizado — nada mais é alterado. O ADR substituto explica o motivo da mudança em sua seção de Contexto. Esta convenção preserva o raciocínio original mesmo quando as conclusões mudam.

Quando a substituição é apenas **parcial** — a decisão nova invalida só parte do ADR — não se deixa o original meio-válido. Marca-se o ADR-base inteiro como `superseded` e divide-se seu conteúdo em ADRs novos: um com a decisão nova, outro(s) re-afirmando a parte que continua válida, com o `superseded_by` do base listando todos os sucessores. Assim nenhum ADR vigente é parcialmente falso (ADR-0040).

Superseder **propaga** (ADR-0050, F-0044): o `feat-memory audit` lista todo artefato vivo (features ativas, ADRs ativos, `AGENTS.md`, `UNRELEASED`) que ainda cita o ID do ADR antigo, e emite um warning por arquivo até que ele seja revisado e reconhecido. O acknowledgment é o campo `reconciled:` do ADR que supersede — uma lista de paths que o autor declara ter revisado quanto a citações do modelo antigo (citações históricas legítimas permanecem; citações apodrecidas são atualizadas). O checklist é referencial: prova que a revisão aconteceu e ficou registrada, não que foi bem feita — essa camada é da amostragem adversarial.

### Propostas de ADR (`.feat-memory/decisions/proposals/`)

Drafts gerados pela ferramenta `feat-memory propose-adr` ficam em uma subpasta separada que o `feat-memory audit` ignora explicitamente. Drafts não são ADRs e não têm validade arquitetural — são pontos de partida para conversa. Quando um draft é revisado e aprovado, o arquivo é renomeado com slug definitivo e movido para `.feat-memory/decisions/`, momento em que passa a ser auditado normalmente.

A separação é deliberada: ADRs são imutáveis e proposals são mutáveis, e misturar os dois quebraria a invariante de imutabilidade. Drafts podem (e devem) ser editados livremente até o momento da promoção; uma vez em `.feat-memory/decisions/`, ficam congelados.

## 5. O futuro: `.feat-memory/ideas.md`

Se o passado mora em `decisions/`/`changelog/` e o presente no `UNRELEASED`, o futuro tem dois estágios. O **comprometido** já vive nos artefatos: uma capacidade intencionada é uma Feature `proposed`; uma decisão em gestação é um ADR `proposed` (em `proposals/`). O **cru** — ideias ainda não triadas — mora no `.feat-memory/ideas.md`: um funil commitado e compartilhado entre agentes (merge normal, **não** `merge=ours`) para capacidades de produto, decisões a tomar e melhorias do próprio sistema de agentes. Existe porque não se pode contar com um issue tracker no projeto cliente, e porque uma ideia crua ainda não merece o peso de um Feature/ADR.

O pipeline é único: **ideia (`ideas.md`) → `proposed` (Feature/ADR) → realizando (`in_progress` / decidindo) → realizado (`shipped` / `accepted`)**. A triagem, no debrief, roteia cada ideia pelo tipo — capacidade→Feature `proposed`; decisão→ADR `proposed`; evolução do sistema→aplica direto; senão descarta. A disciplina é anti-tracker: itens curtos e transitórios — uma ideia promovida ou descartada **sai** do funil. Quando o `UNRELEASED` está vazio, a `memory-bootstrap` oferece candidatos do `ideas.md` como próximo foco (ADR-0047).

## Skills

A metodologia inclui quatro skills em `skills/` na raiz do workspace (deployadas pelo `feat-memory deploy` a partir do package data em `src/feat_memory/data/skills/`) que orientam o agente nos fluxos críticos. Elas são opcionais — todo o protocolo está documentado neste arquivo — mas sua presença torna a aplicação consistente e libera o agente de precisar relembrar a doutrina inteira a cada interação.

A skill `memory-deploy` cobre a adoção inicial. Ela é o ponto de entrada único para instalar a metodologia em qualquer projeto, ativando quando o usuário pede para configurar ou adotar a estrutura. A skill detecta automaticamente se o projeto é greenfield (poucos commits, pouco código, sem entrypoints públicos) ou legacy (histórico substancial, código de produção, stack identificável), e ramifica para o fluxo apropriado. Em ambos os casos, ela executa o `feat-memory deploy` para a estrutura mecânica antes de personalizar — o comando é a infraestrutura subjacente que a skill orquestra. Para greenfield, segue personalização interativa em diálogo curto sobre identidade, stack, restrições e foco inicial. Para legacy, segue gênese retroativa em quatro fases revisadas (constituição a partir do código, ADRs a partir do git log, Manifest a partir dos entrypoints, `changelog/UNRELEASED.md` inicial vazio), com o princípio fundamental de que cristalização silenciosa de interpretações erradas é o pior erro possível.

A skill `memory-bootstrap` cobre o início de sessão. Ela ativa quando o usuário pergunta sobre o estado atual do projeto e instrui o agente a carregar `.feat-memory/changelog/UNRELEASED.md` e os índices, expandir apenas as features e ADRs referenciados nas entradas em voo, e apresentar um briefing tático curto antes de prosseguir. Quando detecta que o último commit é um merge que tocou artefatos da metodologia, ela delega para `memory-pull-brief` antes do briefing tático.

A skill `memory-debrief` cobre o fim de unidade de trabalho. Ela ativa quando o usuário sinaliza intenção de commitar e instrui o agente a examinar o diff, atualizar entradas do Manifest para features tocadas, registrar o trabalho como entrada-bullet no `.feat-memory/changelog/UNRELEASED.md` (citando as F/ADR tocadas), e gerar proposta de ADR via `feat-memory propose-adr` se a sessão produziu uma decisão arquitetural não-trivial. Fecha com retrospectiva inline e captura de sugestões no backlog (ADR-0046). Esta é a skill mais usada no dia-a-dia, porque cobre o momento em que o trabalho realizado precisa ser refletido na memória persistente antes de virar commit.

A skill `memory-pull-brief` cobre o momento pós-`git pull` em projeto cliente que recebeu commits de colegas. Ela ativa por trigger manual ("o que veio do pull", "brifa as mudanças do main") ou por delegação a partir da `memory-bootstrap`. Examina o diff trazido pelo pull, identifica mudanças semânticas em features e ADRs (transições de status, novos IDs, supersedes), cruza com as referências `F`/`ADR` nas entradas do `.feat-memory/changelog/UNRELEASED.md` local, e propõe ajustes nele para refletir a nova realidade. Por design é read-only sobre `.feat-memory/manifest/` e `.feat-memory/decisions/` — esses já vieram corretos do pull, e escrever neles seria reverter trabalho de colegas.

A separação em quatro skills em vez de uma reflete a estrutura real do trabalho com a metodologia: quatro momentos qualitativamente diferentes (adoção, início de sessão, fim de unidade, sincronização pós-pull), cada um com sua própria checklist e cada um com seus próprios riscos de ser executado errado. Skills monolíticas tendem a ser ignoradas; skills específicas e curtas tendem a ser invocadas no momento certo.

A escolha de fazer da `memory-deploy` o ponto de entrada — em vez de exigir que o usuário invoque o `feat-memory deploy` diretamente — reflete uma decisão de design importante. O comando sozinho instala a estrutura mecânica mas não personaliza nada, o que deixa um projeto greenfield com `AGENTS.md` genérico inútil ou um projeto legacy com Manifest vazio que ignora todo o código existente. A skill envolve o comando com a inteligência necessária para que a instalação produza valor real desde o primeiro commit. O comando direto permanece disponível para automação e CI, onde personalização não se aplica.

## Perfis de instalação

O `feat-memory deploy --profile core|full` instala a metodologia em dois tamanhos (ADR-0050, F-0042). O perfil **core** — default para adoções novas — é a espinha de valor comprovado: constituição, decisions, `changelog/UNRELEASED.md` e features finas (registro frontmatter-only, orçamento de prosa de 10 linhas). O perfil **full** adiciona a operação completa de changelog (releases congelados por tag) e um orçamento de prosa maior (40 linhas) para racional curto em corpos de feature.

O perfil vive em `.feat-memory/.meta.yaml` (`profile`, schema 2) e calibra as políticas do audit. Re-deploy sem a flag **preserva** o perfil gravado; instalações pré-v3 (meta sem o campo) resolvem para `full` em todos os caminhos de degradação — uma instalação existente nunca ganha warnings novos só porque a CLI avançou ("upgrade quando doer", ADR-0050/0051). Os perfis também tornam a tese do manifest falsificável por módulo: a condicional pré-registrada no ADR-0050 define o que condenaria (contaminação originada de feature fina) e o que absolveria (10 sessões frias ou 3 ciclos adversariais limpos) o conceito.

## Workflow de merge e rebase

Os quatro artefatos têm comportamentos qualitativamente diferentes sob merge, e tratá-los uniformemente produz resultados ruins. A metodologia adota estratégias diferenciadas suportadas por configuração Git e por convenções de workflow que as skills já promovem implicitamente.

O `.feat-memory/changelog/UNRELEASED.md` é o caso patológico clássico. Duas branches paralelas registram trabalho em voo diferente, e o merge produziria conflito. A configuração `merge=ours` no `.gitattributes` resolve automaticamente, mantendo a versão da branch destino. O UNRELEASED não é fonte de verdade compartilhada — é o cursor da última sessão de trabalho ativa, e tentar mesclar duas visões paralelas produz texto incoerente sem ganho operacional. Os arquivos por-tag `changelog/<X.Y.Z>.md`, ao contrário, são imutáveis e merge-safe.

Os índices gerados (`.feat-memory/manifest/INDEX.md` e `.feat-memory/decisions/INDEX.md`) seguem a mesma estratégia. Eles são recriados a cada execução do `feat-memory audit`, então a regra prática é resolver o conflito escolhendo qualquer versão e regenerar. A configuração `merge=ours` para esses dois arquivos elimina o conflito explicitamente, e a skill `memory-bootstrap` detecta sessões pós-merge para regenerar automaticamente.

Os ADRs em `.feat-memory/decisions/` enfrentam um problema diferente: colisão de IDs quando branches paralelas criam ADRs simultaneamente. O Git em si não detecta isso como conflito (são arquivos diferentes), mas o resultado é semanticamente quebrado. A solução é renumerar o ADR mais recente após o merge, ajustando todas as referências cruzadas. O `feat-memory audit --check-collisions origin/main` detecta a situação preventivamente quando rodado na branch antes do merge, e a skill `memory-debrief` invoca essa checagem na rotina pré-commit em branches que serão mescladas.

As features em `.feat-memory/manifest/features/` têm dois sub-casos. Quando duas branches criam features novas com IDs diferentes, não há conflito real e o merge é trivial. Quando duas branches modificam a mesma feature existente (por exemplo, ambas adicionando critérios de aceitação ou atualizando métricas), há conflito real que precisa de resolução manual. A estratégia recomendada é mesclar à mão, preservando todas as adições de ambos os lados (critérios de aceitação são aditivos por natureza), e tomando a versão mais recente para campos como `metrics` ou `version` que têm semântica de substituição. Colisão de IDs em features é detectada pelo mesmo `--check-collisions` que cobre ADRs.

Para rebase, a dinâmica é a mesma com uma sutileza. O rebase replica os commits da feature branch sobre a branch destino atualizada, então conflitos de ADR ou State aparecem em cada commit replicado. A configuração `merge=ours` cobre State e índices. Para ADRs com colisão de ID, o ideal é resolver a colisão antes do rebase (renumerando na feature branch enquanto ela ainda é local), em vez de durante o rebase quando o contexto está mais opaco. Isso reforça a importância da checagem `--check-collisions` na rotina de debrief.

A configuração do driver `merge.ours.driver` no Git é feita automaticamente pelo `feat-memory deploy`, que executa `git config merge.ours.driver true` no projeto. Em outros clones do mesmo repositório, cada desenvolvedor precisa rodar essa configuração manualmente uma vez (o `feat-memory deploy` faz isso, mas o `.gitattributes` já versionado pode não disparar nova execução do deploy). A documentação do `.gitattributes` deployado registra a instrução para esses casos.

## Protocolo do agente

O protocolo cabe em três frases e opera sobre os quatro artefatos sem precisar de skill customizada — agentes que reconhecem `AGENTS.md` (Claude Code via redirect, Cursor, Aider, Continue) já carregam a constituição automaticamente.

Na inicialização, o agente carrega `AGENTS.md`, `.feat-memory/changelog/UNRELEASED.md`, `.feat-memory/manifest/INDEX.md` e `.feat-memory/decisions/INDEX.md`. O total fica dentro do orçamento de doze kilobytes definido em `AGENTS.md::budgets::resumption_max_bytes`. O agente então expande apenas as features e ADRs **referenciados** nas entradas-bullet do UNRELEASED — o conjunto ativo é derivado, não uma lista mantida à mão.

Durante o trabalho, qualquer mudança de comportamento exige atualizar a feature correspondente no Manifest no mesmo commit do código. O Manifest é a única fonte de verdade sobre o que o sistema faz; se uma capacidade não está no Manifest, ela não existe, mesmo que o código já tenha sido escrito. Esta rigidez parece custosa mas paga dividendos imediatos: o problema clássico de agentes inventando features que não combinam com o sistema existente desaparece.

A definição não espera o commit final. Uma capacidade nova nasce **cedo** como feature `proposed`, e a decisão que a molda como ADR `proposed` — ainda durante o trabalho, antes de o código estar pronto. Assim a retomada se ancora sempre em ADR+Feature, que o agente já sabe carregar, e nunca num plano efêmero que some no próximo reset de contexto. O planejamento vive na conversa ou no plan mode da ferramenta; não vira um spec persistente (ADR-0041).

No debrief, o agente registra o trabalho como uma entrada-bullet no `.feat-memory/changelog/UNRELEASED.md` (citando as F/ADR que tocou), atualiza ou cria entradas no Manifest para features tocadas, e cria um ADR se a sessão produziu uma decisão arquitetural não-trivial. Fecha com uma retrospectiva inline e tria as ideias do futuro para o funil `ideas.md` (ADR-0047/0048). O debrief é parte do trabalho, não opcional — uma sessão sem debrief é trabalho perdido.

## Auditoria

O `feat-memory audit` produz um relatório de uma página com os indicadores de saúde do projeto. Cada um responde uma pergunta operacional concreta sobre se o sistema está entregando valor ou virando burocracia.

O que a auditoria garante — e declara no próprio relatório — é **integridade referencial e movimento conjunto** doc↔código: IDs que resolvem, paths que existem, artefatos que se movem juntos no commit. Ela **não** garante verdade semântica: um critério pode estar referencialmente íntegro e factualmente apodrecido (ADR-0050). Essa camada é responsabilidade da amostragem adversarial (seção adiante). Os issues têm três severidades: `error` (bloqueia sempre), `warning` (bloqueia sob `--strict`) e `info` — nudges heurísticos que **nunca** são promovidos e nunca mudam o exit code; o relatório humano os resume numa linha e o detalhe sai no `--json`.

A **conformidade de schema** mede se todos os artefatos passam validação estrutural, incluindo a validação dos critérios de aceitação contra os padrões EARS. Qualquer erro aqui bloqueia o build — schemas inválidos significam que o agente vai consumir dados quebrados na próxima sessão.

A **conformidade de constraints** mede as restrições `hard`/`soft` que declaram um bloco `check`: o audit executa cada checker contra o repositório e reporta quantas foram checadas e quantas violaram. Violação de restrição `hard` é error e bloqueia o build; `soft` é warning. Restrições sem `check` não entram na conta. É o indicador que torna a constituição enforced em vez de só lida (ADR-0028).

O **custo de retomada** soma os bytes de `AGENTS.md`, `CLAUDE.md` (quando presente como redirect), `.feat-memory/changelog/UNRELEASED.md` e os dois índices. Acima de doze kilobytes, o sistema está consumindo tokens demais antes mesmo do trabalho começar; é hora de compactar índices ou enxugar o UNRELEASED.

O **frescor** mede o tempo desde o último update do `.feat-memory/changelog/UNRELEASED.md`. Acima de uma semana com trabalho em voo, a última sessão não fez debriefing — bug de processo, não de software.

A **cobertura do manifest** mede a porcentagem de features cujo campo `contracts.tests` aponta para arquivos de teste que existem. Cobertura caindo significa que estamos enviando capacidades sem rede de segurança.

O **drift do manifest** lista features cujos contratos apontam para caminhos inexistentes. Drift não-vazio significa que código foi refatorado sem atualizar o Manifest — viola a regra fundamental de "Manifest e código commitados juntos".

A **velocity** detecta a patologia mais comum: features que entram em `in_progress` e nunca saem. Acima de catorze dias em progresso é warning; acima de trinta é problema operacional.

A **saúde de decisões** mede a razão de substituição (superseded sobre total) e o número de decisões em `accepted` há mais de cento e oitenta dias sem revisão. Razão muito baixa significa decisões fossilizadas; muito alta, decisões tomadas sem maturidade. A faixa saudável fica entre vinte e cinquenta por cento.

### Modo strict

A flag `--strict` promove warnings (drift) a errors. Em modo padrão o `feat-memory audit` retorna exit 0 mesmo com drift presente, porque drift pode ser temporário (você refatorou e ainda vai atualizar o Manifest no próximo commit). Em modo strict, qualquer drift bloqueia. Issues de severidade `info` nunca são promovidos — nudge não vira coerção. O modo strict é usado pelo pre-commit hook e deve ser usado pela CI.

## Amostragem adversarial

O `feat-memory sample` cobre a camada que nenhum checker determinístico alcança: a **verdade semântica** dos critérios de aceite — o modo de falha em que um artefato foi revisado, atualizado no vocabulário, e mesmo assim manteve semântica apodrecida (ADR-0050, F-0045). A ferramenta sorteia features ativas ponderadas por risco — ADRs citados com status `superseded` pesam mais, assim como ADRs alterados depois do último commit da feature — e emite, em stdout, prompts de **refutação** para um agente LLM executar: "prove que este critério ainda é verdade no código; falhe ruidosamente se não conseguir". O prompt pede refutação, nunca confirmação — verificador que quer confirmar, confirma.

A separação é a mesma do `propose-adr`: detecção e priorização são determinísticas e baratas (ficam na CLI); o julgamento exige ler código e fica no agente. O gatilho recomendado é **por evento** — após um supersede (`--event supersede`) e a cada release (`--event release`) — nunca por commit: o custo de LLM se concentra onde o risco se concentra. O comando sempre retorna exit 0: amostrar é convite, não gate. Um veredito REFUTADO alimenta a condição de falsificação pré-registrada do ADR-0050.

## Pre-commit hook

O hook em `src/feat_memory/governance/data/hooks/pre-commit` é instalado em `.git/hooks/pre-commit` automaticamente pelo `feat-memory deploy`. Como o diretório `.git/` não é versionado, cada clone do projeto consumidor precisa rodar `feat-memory deploy` uma vez para instalar o hook.

O hook roda `feat-memory audit --strict --no-index` antes de cada commit. Se a auditoria falha — schema inválido, EARS mal-formado, drift detectado — o commit é bloqueado e o desenvolvedor vê a lista exata de problemas. Para contornar deliberadamente em situações excepcionais, `git commit --no-verify` ignora todos os hooks. Esta válvula de escape é importante: hooks que não podem ser ignorados acabam sendo desinstalados, e o objetivo é nudge, não coerção.

A combinação hook local mais checagem em CI é o padrão recomendado. O hook pega a maioria dos problemas no início do ciclo de feedback, quando o custo de correção é mínimo; a CI pega os casos onde o hook foi pulado ou não estava instalado, e impede merges incorretos. Sem hook local, todo erro espera o tempo de CI para ser detectado.

## Geração de propostas de ADR

A ferramenta `feat-memory propose-adr` examina o diff atual contra um commit base (HEAD~1 por padrão, ou mudanças staged com `--staged`) e aplica heurísticas para detectar mudanças que podem merecer um ADR. Os sinais que ela observa incluem volume da mudança (cinco arquivos ou cem linhas), alterações em arquivos de manifesto de dependências, mudanças em três ou mais diretórios distintos, e mensagens de commit contendo padrões linguísticos de decisão como "switched from", "instead of", "deprecated".

Quando os sinais são detectados, a ferramenta gera um draft pré-preenchido em `.feat-memory/decisions/proposals/NNNN-draft.md`, com as seções TODO marcadas e os sinais detectados anotados como contexto. O draft não é um ADR — é matéria-prima para um, e o `feat-memory audit` ignora a subpasta `proposals/` para preservar a invariante de que ADRs verdadeiros são imutáveis.

A ferramenta também oferece um modo `--prompt` que emite um prompt estruturado para um agente LLM em vez de gerar o template diretamente. Este modo é útil quando você quer aproveitar a presença de um agente Claude para redigir o draft completo, e o prompt já inclui as instruções para o agente decidir se a mudança realmente merece um ADR (recusando explicitamente se for trivial) e para preencher cada seção com substância em vez de placeholders.

A separação entre detecção e redação é deliberada. A detecção é determinística e barata; a redação exige julgamento. Manter as duas etapas separadas evita que o sistema gere automaticamente ADRs vazios apenas porque algumas heurísticas dispararam, o que poluiria a memória arquitetural com ruído.

## Migração

Para um projeto novo, criar `AGENTS.md`, `.feat-memory/changelog/`, `.feat-memory/manifest/` e `.feat-memory/decisions/` leva minutos, e a primeira feature a ser entregue já segue o protocolo. Para projetos legados, a migração tem dois passos sequenciais.

Primeiro, `feat-memory migrate` examina os últimos cem ou duzentos commits e propõe ADRs candidatos a partir de mensagens contendo padrões como "switched", "instead of", "revert", "decided to". Os candidatos são impressos para revisão humana, não escritos automaticamente. Esta restrição é deliberada — gênese retroativa não pode ser silenciosa, sob pena de cristalizar interpretações erradas como decisões oficiais.

Segundo, o agente examina os módulos públicos do código (entrypoints da API, casos de uso, comandos CLI) e propõe entradas iniciais do Manifest, marcando-as como `status: shipped` mas sem métricas. O humano revisa e aprova antes da gravação. Em sistemas grandes (cento e oitenta mil linhas, mais de um ano de desenvolvimento), o agente trabalha como assistente da migração, não como executor autônomo: ele propõe, o humano dispõe.

## Casos de borda

**E quando duas sessões paralelas tocam o changelog vivo?** Os arquivos por-tag (`changelog/<X.Y.Z>.md`) são imutáveis e não colidem em merge — vantagem direta sobre o `STATE.md`/`CHANGELOG.md` monolíticos. O `UNRELEASED.md` é marcado `merge=ours` no `.gitattributes` (volátil; cada working tree mantém o seu), e o conjunto ativo é derivado das suas entradas. Para coordenação simultânea mais forte, ver `FUTURE_IMPROVEMENTS.md`.

**E features muito pequenas?** Se uma capacidade não merece um arquivo próprio, provavelmente é parte de uma feature maior. Resista à tentação de criar features triviais — o Manifest perde valor quando vira lista de funções. A regra é a mesma do início: `user_value` em uma frase sem termos puramente técnicos.

**E ADRs para mudanças menores?** Se a mudança não exigiria explicação para um futuro contribuidor, ela não merece ADR. A pergunta operacional: "se eu olhar este commit em seis meses, vou entender por que essa escolha?" Se a resposta for sim, comentário no commit basta; se for não, vire ADR. A ferramenta `feat-memory propose-adr` ajuda a calibrar essa intuição, mas a decisão final é humana.

**E quando o `feat-memory audit` reporta drift mas o caminho está certo?** Verifique convenções de path: o `feat-memory audit` checa caminhos relativos à raiz do projeto. `src/api/search.py::search_endpoint` é interpretado como "arquivo `src/api/search.py` existe", o `::search_endpoint` é metadata para o agente. Drift vem de arquivos movidos ou renomeados sem atualizar o Manifest.

**E para projetos sem testes?** Cobertura zero é cobertura honesta. Melhor que cobertura inflada por testes inexistentes. Se a equipe não tem prática de testes, o Manifest expõe esse débito explicitamente, o que é o primeiro passo para resolvê-lo.

**E se o pre-commit hook está bloqueando trabalho legítimo?** A flag `--no-verify` no `git commit` ignora todos os hooks. Use com critério: se você está usando regularmente, o sinal é que ou o hook está calibrado errado (drift transitório sendo bloqueado) ou o time precisa de treinamento na metodologia. Investigue a causa em vez de tornar `--no-verify` rotina.
