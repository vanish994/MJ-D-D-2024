# Code Review — MJ-D-D-2024 MVP

## Resumo

O PR implementa um backend FastAPI para o MJ, com campanhas, orquestração Rule Engine → MiMo, persistência SQLite, adapters, testes e uma projeção UX conservadora. A arquitetura local é coerente e a suíte simulada passa; o projeto ainda não é um D&D 2024 mecanicamente jogável nem está pronto para produção pública.

**Veredito:** apto como scaffold/MVP de orquestração em PR; não declarar integração real nem gameplay mecânico concluído.

## Achados críticos antes de uso público com campanhas reais

1. **Sem autenticação/autorização.** `app/main.py` monta as rotas sem identidade/ownership; `app/api/campaigns.py` permite ler campanha por UUID. CORS não protege chamadas diretas. Implementar autenticação e associação jogador/campanha antes de armazenar dados reais.
2. **Persistência Render não durável.** `app/storage/db.py` aceita somente SQLite e o manifesto não provisiona armazenamento persistente. O filesystem efêmero pode perder campanhas após reinício/redeploy.

## Pendências funcionais e de integração

1. **Rule Engine real ainda fail-closed.** A revisão fornecida pelo usuário informa que o `/v1/resolve` atual retorna `needs_rule_validation` e fatos vazios. Não foi feita chamada real nesta tarefa; de acordo com essa checagem, ataques, testes, dano, CDs e descanso ainda não são resolvidos. A implementação correta no MJ é não inventar resultado; a resolução determinística pertence a uma etapa separada do motor de regras.
2. **Integração real não testada.** Os 47 testes usam mocks. Faltam URLs/credenciais reais e chamadas aos endpoints reais `/health`, `/v1/resolve` e `/v1/chat/completions`.
3. **Contrato de intenção é provisório.** `RuleEngineClient.resolve` recebe agora `player_input`, mas o endpoint externo espera a chave JSON `action`; o adapter envia a fala original nesse campo para preservar compatibilidade. A decomposição ator/alvo/movimento/arma/contexto exige contrato versionado e compatível com o serviço externo; não alterar um lado unilateralmente.
4. **UX depende de dados inexistentes no contrato real.** Opções, recursos, snapshots atuais e resumo de descanso só aparecem se fornecidos e validados pelo Rule Engine. A projeção falha de forma segura, mas provavelmente retornará indisponível com o serviço atual.
5. **Frontend não incluído.** A API disponibiliza rotas para uma futura UI, mas nenhum frontend foi implementado. O projeto é provider-agnostic; a interface pode ser incluída aqui ou decidida separadamente.
6. **Explicação progressiva ainda parcial.** O modo avançado oculta `explanation`; iniciantes/normal recebem o texto explícito do Rule Engine. Glossário e orientação visual progressiva exigem conteúdo confiável e UI.

## Pontos menores

- `stream=true` ainda retorna `501`; streaming não faz parte deste MVP.
- O classificador de intenção continua lexical e apenas anota o turno; não é um parser estruturado e não deve ser tratado como tal.

## Pontos positivos

- Toda fala, inclusive diálogo, percorre Rule Engine antes do MiMo; o teste verifica a ordem.
- Só fatos `resolved` validados podem aplicar mudanças de estado; fatos vazios são enviados em casos não resolvidos.
- O MiMo permanece narrador e recebe prompt separado; não recebe autoridade mecânica.
- SQL parametrizado, limites de payload/estado e validação estrita reduzem risco de dados malformados.
- Campos UX ausentes não são preenchidos com defaults inventados.

## Cobertura

**47 testes passaram** com dependências fixadas e mocks; o smoke test local de `GET /health` passou. Isso não comprova os serviços reais.

## Perguntas para a próxima etapa

1. Qual será o contrato/versionamento para intenção estruturada entre MJ e Rule Engine?
2. A mecânica determinística será implementada no Rule Engine em uma etapa futura, mediante autorização explícita para esse repositório externo?
3. Qual autenticação e armazenamento durável serão usados antes da publicação pública?
