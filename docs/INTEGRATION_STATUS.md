# Status da integração

## Validado nesta implementação

A suíte local cobre o orquestrador, persistência SQLite temporária, contrato HTTP dos adaptadores com `httpx.MockTransport`, endpoints FastAPI com serviços substituídos por mocks, ordem Rule Engine → MiMo inclusive em diálogo, resolução não validada fail-closed, feedback de ação inválida, snapshot UX, modos de explicação e resumo de descanso longo. **Esses testes são simulados e não comprovam disponibilidade nem compatibilidade dos serviços externos.**

## Pendente — Rule Engine real

Ainda não há URL nem credencial real configuradas nesta cópia. Antes de declarar a integração concluída, configurar `RULE_ENGINE_URL` e `RULE_ENGINE_API_KEY` no ambiente Render e testar contra o serviço real:

1. `GET {RULE_ENGINE_URL}/health`.
2. `POST {RULE_ENGINE_URL}/v1/resolve` com um diálogo e com um caso de ação aprovados para o contrato real; conferir autenticação, schema, resposta, status `narrative_only` para fala sem resolução mecânica e que `needs_rule_validation` nunca vire sucesso/fracasso no orquestrador.
3. Confirmar com o proprietário do serviço se ele emitirá `FATOS_RESOLVIDOS.ux_snapshot` com `current: true`, custos/opções e campos de estado. Esse contrato não está definido na especificação atual; sem ele o botão não pode exibir opções atuais.

## Pendente — MiMo Proxy real

Ainda não há URL nem credencial real configuradas nesta cópia. Configurar `MIMO_URL` e `MIMO_API_KEY` no Render e testar contra o serviço real:

1. `GET {MIMO_URL}/health`.
2. `POST {MIMO_URL}/v1/chat/completions` com autenticação Bearer e `stream: false`; confirmar o schema OpenAI-compatible, seleção de modelo e retorno de conteúdo narrativo.
3. Fazer um turno de ponta a ponta e confirmar que, com fatos `{}`, o narrador não declara resultado mecânico.

## Pendente — Base44 e publicação

O repositório contém apenas o backend. Nenhum botão/tela foi criado nem conectado ao Base44. O usuário indicou Render como destino, mas não foi feito deploy. Antes de expor a API, configurar autenticação de jogador, definir CORS para a origem Base44 e escolher persistência durável; este MVP tem SQLite apenas e o manifesto não provisiona disco/DB.

**Conclusão:** testes de mock passam; integração real, UX visual e prontidão para dados persistentes/uso público permanecem pendentes.
