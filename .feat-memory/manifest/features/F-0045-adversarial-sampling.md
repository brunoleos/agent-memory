---
id: F-0045
name: adversarial-sampling
status: shipped
introduced: 2026-07-08
version: 3.0.0
user_value: >
  A verdade semântica dos critérios de aceite — que nenhum checker
  determinístico cobre — ganha verificação por amostragem: o comando sorteia
  features ponderadas por risco e emite prompts de refutação prontos para um
  agente LLM executar, cobrindo o modo de falha "revisado-e-escapou".
contracts:
  api:
    - src/feat_memory/memory/sample.py::run
    - src/feat_memory/memory/sample.py::score_feature
    - src/feat_memory/memory/sample.py::emit_prompts
  tests:
    - tests/test_sample.py
acceptance:
  - {id: A1, pattern: event, trigger: "feat-memory sample é executado num projeto com features ativas", response: "prompts de refutação em stdout, um por feature amostrada, contendo os critérios EARS e a instrução de falhar ruidosamente; exit 0"}
  - {id: A2, pattern: ubiquitous, requirement: "features que citam ADRs superseded (ou alterados após o último commit da feature) aparecem antes das demais na amostra"}
  - {id: A3, pattern: optional, feature: "--seed é fornecido", response: "duas execuções com a mesma semente e a mesma memória produzem saída idêntica"}
  - {id: A4, pattern: unwanted, trigger: "não há features ativas", response: "mensagem de nada-a-refutar e exit 0"}
  - {id: A5, pattern: optional, feature: "--event supersede|release é fornecido", response: "o evento disparador aparece registrado na saída"}
depends_on: []
decisions: [ADR-0050]
---
