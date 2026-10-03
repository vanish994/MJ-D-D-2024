# Code Review — MJ-D-D-2024 MVP + camada UX

## Summary

**Intenção:** construir o backend FastAPI do `MJ-D-D-2024` a partir do ZIP e acrescentar uma camada UX que apresente somente dados fornecidos pelo Rule Engine, preservando o MiMo como narrador. A separação e o fail-closed estão cobertos por testes simulados, mas o projeto **não está pronto para deploy público com dados reais**.

**Veredito:** **Request Changes para deploy público**; o código pode ser revisado em PR como MVP/backend scaffold, com as limitações abaixo claramente aceitas.

## Critical issues — corrigir antes de publicar para jogadores

1. **A API não tem autenticação/autorização.** `app/main.py` monta as rotas sem middleware de identidade, e `app/api/campaigns.py` permite criar e ler campanhas pelo ID. Em uma instância pública, qualquer pessoa com um UUID de campanha pode ler/escrever dados. CORS não é uma barreira para clientes que não sejam navegador. Implementar autenticação/ownership apropriados para o frontend antes de armazenar campanhas pessoais.
2. **Persistência não é durável no manifesto Render atual.** `app/storage/db.py` aceita somente SQLite; `render.yaml` não provisiona disco/DB. O filesystem efêmero pode perder campanhas em reinícios/redeploys. Não usar para dados que o jogador espera preservar até escolher e implementar armazenamento durável.

## Major issues — integração/escopo ainda incompletos

1. **Integração real não foi testada.** Não há URLs nem credenciais reais nesta cópia. Os testes usam `MockTransport` e mocks locais; a health check local não verifica os serviços. Testar `/health`, `/v1/resolve` e `/v1/chat/completions` nos serviços reais antes de afirmar integração concluída.
2. **O contrato de opções atuais ainda depende do Rule Engine.** `app/api/ux.py` projeta o último snapshot salvo; não há consulta em tempo real de ações disponíveis. A projeção exige `current: true` e esconde opções se uma tentativa posterior não foi resolvida. Isso é seguro, mas o endpoint não terá opções até o serviço externo emitir o snapshot estruturado acordado.
3. **O frontend Base44 não está neste repositório.** O backend oferece `GET /assistant` e `PATCH /ux-settings`, mas não criou nem conectou o botão, o painel visual, o onboarding ou o ensino progressivo.
4. **A classificação de intenção é heurística.** `app/services/turn_service.py` registra um rótulo lexical e todas as entradas chamam `/v1/resolve`; o rótulo pode estar errado, mas não pula o Rule Engine nem calcula resultado. Ainda precisa de validação ampliada no jogo real.
5. **Os modos de explicação têm diferenças limitadas.** O modo avançado oculta `explanation`; iniciante e normal passam descrições retornadas pelo Rule Engine. Glossário e ensino progressivo não foram implementados, pois não há conteúdo estruturado/autorizado nem frontend disponível.
6. **Autenticação e origem CORS continuam pendentes no Render.** O fallback do código é `localhost`; `.env.example` mantém `*` para uso local. Definir a origem exata do Base44 antes da conexão. CORS restrito, isoladamente, não substitui autenticação.

## Minor issues

- `stream=true` permanece explicitamente sem suporte e retorna `501`.
- O MVP implementa SQLite, não o adaptador PostgreSQL sugerido como próximo passo na especificação.

## Positive feedback

- Alterações mecânicas só são aplicadas após validar `status: resolved` e `FATOS_RESOLVIDOS`; `needs_rule_validation` envia `{}` ao MiMo.
- SQL usa parâmetros; entrada, payloads, tamanho do histórico e mudanças de estado têm limites.
- O feedback de ação inválida é proveniente do Rule Engine; o orquestrador não cria custos/resultados mecânicos.
- A UX retorna `null`/indisponível para dados ausentes e só apresenta ações de um snapshot explicitamente atual.
- Testes determinísticos e simulados cobrem fluxos, erros, modos, recursos, movimento, descanso e proteção contra valores inventados.

## Test coverage

**47 testes passaram** com dependências fixadas. Também passou um smoke test HTTP local de `GET /health`. Nenhum desses resultados comprova integração com Render, Rule Engine ou MiMo reais.

## Questions for author

1. Qual workspace/projeto Base44 existente deve receber a UI? O pedido de localizar esse frontend permanece sem resposta; a mensagem “usarei o Render” confirmou apenas o destino de hospedagem do backend.
2. O Rule Engine emitirá `FATOS_RESOLVIDOS.ux_snapshot` com `current`, opções, custos, recursos e estados? Qual será o schema/endpoint final?
3. Qual estratégia de autenticação e persistência durável será usada antes de armazenar campanhas em uma URL pública?
