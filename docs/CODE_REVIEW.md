# Code Review — MJ-D-D-2024 MVP e `rule-resolution-v1`

## Resumo

A mudança valida e projeta respostas do Rule Engine por um contrato versionado, aplica alterações de estado somente em respostas `resolved` válidas e envia `{}` ao MiMo em status pendentes ou inválidos. O fluxo preserva o contrato HTTP externo; nenhuma mecânica D&D ou integração real foi adicionada.

**Veredito:** aprovado como alteração de contrato local e fail-closed; não significa que os serviços externos implementem o schema.

## Achados críticos

Nenhum bloqueador identificado nesta revisão local. Antes de uso público com campanhas reais, permanecem os riscos preexistentes de autenticação/autorização ausente e persistência SQLite não durável no Render.

## Questões importantes ainda abertas

1. **Integração real não testada.** Os testes usam mocks. URL, credenciais e chamadas reais a `/health`, `/v1/resolve` e `/v1/chat/completions` continuam pendentes; o Rule Engine pode responder apenas com o formato legacy `needs_rule_validation`.
2. **Schema V1 não negociado com o backend externo.** `rule-resolution-v1` é validação local no MJ. Uma resposta `resolved` real só poderá ser aceita depois que o serviço externo produzir esse formato e for testado ponta a ponta.
3. **Sem resolução mecânica.** Esta mudança não implementa ataques, testes, RNG, dano, CDs, iniciativa, condições, descanso ou personagens. A Knowledge Base continua sendo evidência/candidata, não uma regra executável automática.
4. **Intenção continua provisória.** `mj-rule-state-v1` preserva a fala e metadados lexicais; não é parsing estruturado nem contrato negociado com o Rule Engine.
5. **Segurança e operação preexistentes.** A API não associa campanhas a uma identidade autenticada e o armazenamento SQLite não é durável no Render. Não fazer deploy nesta etapa.

## Pontos menores

- `stream=true` retorna `501`; streaming continua fora do escopo.
- O classificador lexical é consultivo e não decide roteamento nem resultados.

## Pontos positivos

- Contrato explícito com enum de seis status, tipos estritos, rejeição de campos desconhecidos e limites de payload/coleções; JSON profundamente aninhado falha de forma controlada.
- Status diferente de `resolved` descarta fatos, snapshots, referências e mudanças de estado; formato legacy é limitado ao objeto mínimo `needs_rule_validation`.
- Respostas `resolved` são projetadas por allowlist; `request`, `reason` e `message` não são encaminhados como fatos.
- Mudanças de estado aceitam apenas mapa limitado com valores escalares, e conflitos com o formato nested legacy falham fechados.
- Rule Engine continua antes do MiMo; mocks verificam a ordem e a ausência de fatos quando não há resolução.
- Documentação separa `mj-rule-state-v1` do novo contrato de resposta e não alega compatibilidade real.

## Cobertura de testes

**68 testes passaram** com dependências fixadas, incluindo contrato, dados inválidos, seis status, fail-closed, pipeline, APIs e adapters com mocks. `compileall` e `git diff --check` também passaram. Nenhum desses testes é uma integração real.

## Perguntas para a próxima etapa

1. Quando o Rule Engine externo poderá produzir e documentar `rule-resolution-v1`?
2. Qual autenticação e banco persistente serão escolhidos antes de qualquer publicação pública?
3. O contrato de intenção estruturada será versionado em etapa separada, com autorização explícita sobre o serviço externo?
