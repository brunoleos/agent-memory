---
id: F-0040
name: deploy-dry-run
status: shipped
introduced: 2026-06-30
version: 2.4.0
user_value: O flag `--dry-run` no `feat-memory deploy` mostra o que seria criado/atualizado (arquivos, hooks, git config) sem escrever um byte — para revisar o efeito de um upgrade antes de commitar.
contracts:
  api: src/feat_memory/deploy.py::run
  tests: tests/test_deploy.py
acceptance:
  - {id: A1, pattern: event, trigger: "feat-memory deploy --dry-run é invocado", response: "reporta cada mudança no condicional (criaria/atualizaria/já em dia) e não escreve nenhum arquivo"}
  - {id: A2, pattern: ubiquitous, requirement: "a árvore do projeto fica byte-idêntica após um dry-run (garantia coberta por teste de regressão)"}
  - {id: A3, pattern: state, state: "nada divergente", response: "reporta 'nada a fazer — tudo em dia'"}
depends_on: []
decisions: []
---

A garantia de zero-mutação é dada por **teste de regressão** (`test_dry_run_after_deploy_is_byte_identical`), não pela arquitetura — preferiu-se um flag `dry_run` propagado + guarda em cada escrita a um sandbox copy-and-diff (custo de copiar a árvore + `.git`, e divergência de comportamento de Git no clone). O teste cobre a classe "guard de escrita esquecido".
