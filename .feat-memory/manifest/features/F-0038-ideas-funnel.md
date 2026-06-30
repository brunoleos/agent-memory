---
id: F-0038
name: ideas-funnel
status: shipped
introduced: 2026-06-26
version: 2.2.0
user_value: Ideias cruas do futuro (capacidades, decisões, evolução do sistema de agentes) vivem num funil commitado em .feat-memory/ideas.md, triadas para Feature/ADR proposed — e fallback de retomada quando nada está em voo.
contracts:
  api: src/feat_memory/deploy.py::deploy_ideas
  tests: tests/test_deploy.py
acceptance:
  - {id: A1, pattern: event, trigger: "feat-memory deploy é invocado", response: "cria .feat-memory/ideas.md se ausente; refresca o cabeçalho preservando as entradas do usuário"}
  - {id: A2, pattern: ubiquitous, requirement: "o funil é commitado/versionado (merge normal, não merge=ours)"}
  - {id: A3, pattern: state, state: "changelog/UNRELEASED.md vazio", response: "a bootstrap oferece candidatos do ideas.md como próximo foco"}
depends_on: [F-0036]
decisions: [ADR-0047]
---
