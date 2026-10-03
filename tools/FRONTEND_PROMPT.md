# Prompt para implementar um frontend do MJ-D-D-2024

Implemente uma interface de jogo para o backend `MJ-D-D-2024`, no mesmo repositório ou em um projeto separado, sem exigir fornecedor específico.

## Arquitetura obrigatória

```text
Jogador → Frontend → MJ-D-D-2024 → Rule Engine → FATOS_RESOLVIDOS → MiMo Proxy → Narração
```

O frontend chama somente a API do MJ. Nunca chama o Rule Engine ou o MiMo diretamente. Toda fala do jogador é encaminhada a `POST /v1/campaigns/{id}/turn`; o MJ executa Rule Engine antes do MiMo. O MiMo é somente narrador.

## Regras da interface

- Não rolar dados, calcular dano/CD, decidir sucesso/fracasso, aplicar regras ou editar estado mecânico no frontend.
- Mostrar estado e opções somente quando vierem em resposta/snapshot validado pelo Rule Engine. `null` significa desconhecido/indisponível, não zero ou “nenhuma opção”.
- Exibir feedback de validação/ação inválida usando a mensagem estruturada recebida do MJ; não criar justificativas mecânicas.
- Para `needs_rule_validation` ou `narrative_only`, representar o resultado sem afirmar sucesso mecânico.
- Custos, recursos, condições, efeitos e resumo de descanso são dados de origem do Rule Engine; não inferir valores.
- Preferência de explicação `beginner`, `normal` ou `advanced` é somente visual.

## API atual

- `POST /v1/campaigns`, `GET /v1/campaigns/{id}`.
- `POST /v1/campaigns/{id}/turn` para cada fala do jogador.
- `GET /v1/campaigns/{id}/assistant` para projeção UX atual.
- `PATCH /v1/campaigns/{id}/ux-settings` para modo de explicação.

## Limites conhecidos

A integração real ainda não foi validada. A revisão recebida informa que o Rule Engine atual responde `needs_rule_validation` com fatos vazios para `/v1/resolve`; até que essa capacidade mude, o jogo não resolve mecânicas de D&D. A API do MJ também não tem autenticação, então use somente ambiente privado de desenvolvimento até existir autenticação/autorização.

Nunca coloque API keys do Rule Engine ou MiMo no frontend. Não declare integração real com base em mocks.
