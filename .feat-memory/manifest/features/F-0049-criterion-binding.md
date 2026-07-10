---
id: F-0049
name: criterion-binding
status: shipped
introduced: 2026-07-10
version: 3.1.0
user_value: >
  Rastreabilidade desce ao nível do critério: um teste que cita o token
  F-NNNN-AN declara cobrir aquele aceite, o audit mede a cobertura por
  critério e o prompt de refutação aponta o teste declarado — sem executar
  nada e sem acoplar a framework algum.
contracts:
  api:
    - src/feat_memory/memory/binding.py::criterion_bindings
    - src/feat_memory/memory/binding.py::coverage_summary
  tests:
    - tests/test_criterion_binding.py
acceptance:
  - {id: A1, pattern: event, trigger: "um arquivo listado em contracts.tests contém o token F-NNNN-AN de um critério da própria feature", response: "aquele critério conta como coberto na métrica de cobertura por critério"}
  - {id: A2, pattern: ubiquitous, requirement: "o match do token é case-insensitive e com word-boundary — F-0001-A22 nunca cobre o critério A2"}
  - {id: A3, pattern: unwanted, trigger: "um arquivo de contracts.tests não existe", response: "os critérios ficam não-cobertos sem erro (existência é assunto do drift check)"}
  - {id: A4, pattern: state, state: "nenhum binding existe no repositório", response: "o relatório exibe a cobertura por critério como não-adotada (—), nunca como dívida de 0%"}
  - {id: A5, pattern: event, trigger: "feat-memory sample amostra uma feature com critério coberto", response: "o prompt de refutação anota o teste declarado ao lado do critério"}
depends_on: [F-0045]
decisions: [ADR-0052]
---
