---
id: F-0042
name: deploy-profiles
status: shipped
introduced: 2026-07-08
version: 3.0.0
user_value: >
  Adoções novas pagam só pela espinha comprovada da metodologia: o deploy
  grava um perfil (core|full) no .meta.yaml e a governança calibra suas
  políticas por ele, tornando a tese do manifest falsificável por módulo.
contracts:
  api:
    - src/feat_memory/deploy.py::deploy_meta
    - src/feat_memory/deploy.py::_resolve_deploy_profile
    - src/feat_memory/shared/parsing.py::resolve_profile
  tests:
    - tests/test_meta.py
acceptance:
  - {id: A1, pattern: event, trigger: "deploy é executado sem --profile num target virgem", response: "o .meta.yaml resultante registra profile core e schema_version 2"}
  - {id: A2, pattern: event, trigger: "re-deploy sem --profile num target cujo .meta.yaml registra profile full", response: "o profile full é preservado no arquivo resultante"}
  - {id: A3, pattern: event, trigger: "re-deploy sem --profile num target com .meta.yaml pré-v3 (sem campo profile)", response: "o .meta.yaml resultante registra profile full"}
  - {id: A4, pattern: unwanted, trigger: "o .meta.yaml está ausente, corrompido ou com profile inválido quando a governança o consulta", response: "resolve_profile retorna full e nenhum warning novo aparece no relatório por causa disso"}
  - {id: A5, pattern: ubiquitous, requirement: "o relatório do audit exibe o perfil de governança em vigor"}
depends_on: []
decisions: [ADR-0050]
---
