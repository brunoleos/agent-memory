---
id: F-0043
name: manifest-prose-budget
status: shipped
introduced: 2026-07-08
version: 3.0.0
user_value: >
  Prosa acumulada no corpo de features — o vetor de memória paralela — passa a
  ser visível e limitada por perfil: o audit avisa quando o corpo excede o
  orçamento, empurrando racional para ADRs e mantendo a feature como registro.
contracts:
  api:
    - src/feat_memory/memory/schemas.py::validate_feature
    - src/feat_memory/memory/schemas.py::PROSE_BUDGET_BY_PROFILE
  tests:
    - tests/test_prose_budget.py
acceptance:
  - {id: A1, pattern: event, trigger: "o audit roda num projeto de perfil core com feature ativa cujo corpo tem mais de 10 linhas não-vazias", response: "um warning nomeando o arquivo, a contagem e o limite aparece no relatório"}
  - {id: A2, pattern: state, state: "o perfil em vigor é full", response: "o mesmo corpo só gera warning acima de 40 linhas não-vazias"}
  - {id: A3, pattern: ubiquitous, requirement: "features do archive nunca recebem warning de orçamento de prosa"}
  - {id: A4, pattern: unwanted, trigger: "o audit roda com --strict num projeto core com corpo acima do orçamento", response: "o warning é promovido a error e o exit code é 1"}
depends_on: [F-0042]
decisions: [ADR-0050]
---
