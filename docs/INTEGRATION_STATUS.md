# Status da integração

## O que foi validado localmente

A suíte cobre o orquestrador, persistência SQLite temporária, contratos HTTP dos adapters com `httpx.MockTransport`, endpoints FastAPI com mocks, ordem Rule Engine → MiMo inclusive em diálogo, fail-closed, feedback de ação inválida, snapshot UX, modos de explicação e resumo de descanso longo. **Mocks são somente testes: não comprovam disponibilidade nem compatibilidade dos serviços reais.**

## Rule Engine externo

A checagem anexada pelo usuário informa que o `/v1/resolve` atual de `dnd-byonder-backend` responde `needs_rule_validation` com `facts_resolvidos: {}` por design. Essa informação veio de uma revisão do conteúdo do serviço; **não foi revalidada com uma chamada real nesta implementação**. Assim, o MJ está arquiteturalmente conectado, mas o jogo ainda não resolve mecanicamente ataques, testes, dano, CDs, condições, recursos ou descanso. O MJ não deve simular esses resultados.

Quando houver um contrato mecânico disponível, testar no serviço real:

1. `GET {RULE_ENGINE_URL}/health`.
2. `POST {RULE_ENGINE_URL}/v1/resolve` com diálogo e casos aprovados de ação; conferir autenticação, schema, status e `FATOS_RESOLVIDOS`.
3. Confirmar um contrato versionado para intenção estruturada e para `ux_snapshot`; hoje o adapter mantém compatibilidade enviando a fala original na chave externa `action`.

Não alterar `dnd-byonder-backend` sem autorização explícita.

## MiMo Proxy externo

URLs e credenciais reais não estão configuradas/testadas. Antes de considerar concluída a integração, testar no proxy real:

1. `GET {MIMO_URL}/health`.
2. `POST {MIMO_URL}/v1/chat/completions` com Bearer e `stream: false`; confirmar o schema OpenAI-compatible e retorno narrativo.
3. Fazer um turno ponta a ponta e conferir que fatos `{}` não levam o narrador a declarar sucesso ou fracasso mecânico.

Não alterar `mimo-ai-proxy` sem autorização explícita.

## Frontend, Render e segurança

Nenhuma interface foi implementada neste repositório. O projeto não depende de fornecedor específico; o frontend poderá ser desenvolvido aqui ou definido posteriormente. O destino Render está documentado, mas **não houve deploy**. Antes de uso público com campanhas reais, implementar autenticação/autorização, restringir CORS e escolher armazenamento durável: o MVP usa SQLite e o manifesto não provisiona disco nem banco.

**Conclusão:** o pipeline local e seus testes simulados estão validados; mecânicas reais, integração real, UI e prontidão para dados persistentes permanecem pendentes.
