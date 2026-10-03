# Análise técnica — Rule Engine determinístico de D&D 2024

- **Data da análise:** 2026-10-03
- **Escopo:** levantamento e proposta de arquitetura/contratos; **nenhuma mecânica foi implementada**.
- **Repositório/branch em análise:** `vanish994/MJ-D-D-2024`, `feat/mj-dnd-2024-mvp`, commit `10fc5d0795c01b141383ff496349be577c9e12d9` (PR #1 aberto como draft).
- **Snapshot externo inspecionado:** `vanish994/dnd-byonder-backend`, `origin/main`, commit `ed3c18517fd6d1194f40a48b92026e26a377be09`.

## Síntese executiva

O MJ já implementa o fluxo HTTP/orquestrador e uma validação local conservadora de fatos, mas não estrutura a intenção além de um rótulo lexical. O `main` atual do backend externo é uma **API de busca de evidências**, não um motor mecânico executável: `/v1/resolve` sempre retorna `needs_rule_validation` e fatos vazios. A base contém 15.716 candidatos e nenhum está marcado como validado; os templates de teste não têm entradas ou resultados esperados.

Portanto, ainda não é possível resolver deterministicamente nem a primeira ação de combate. Também há divergências concretas no contrato — por exemplo, o MJ aceita falas de até 10.000 caracteres enquanto o resolver externo limita `action` a 200 — e a estrutura de estado passada ao Rule Engine não inclui os dados tipados do personagem, inventário ou combate.

A proposta preserva o fluxo **Jogador → MJ → intenção estruturada → Rule Engine → `FATOS_RESOLVIDOS` → MiMo → narração**. A aleatoriedade deve ficar dentro da fronteira do único Rule Engine escolhido, com fonte criptograficamente segura em produção e rolagens injetáveis nos testes. Esta análise **não escolhe** entre evoluir `dnd-byonder-backend` ou criar um resolver separado no MJ: essa decisão e algumas escolhas de escopo precisam de aprovação antes de qualquer implementação.

## Escopo, método e fontes

A análise do MJ foi feita sobre os arquivos da branch indicada. O backend foi examinado em `origin/main` no commit acima — API, documentação e metadados SQLite — sem editar seus arquivos. O clone local do backend estava em outra branch; por isso ela não foi usada para atribuir capacidades ao `main`. A base SQLite do snapshot foi aberta em modo somente leitura e consultada apenas para nomes de tabelas, contagens, edições e status; nenhum texto de livro foi reproduzido neste relatório.

Fontes primárias do backend, fixadas ao commit auditado: [`rule_engine/app.py`](https://github.com/vanish994/dnd-byonder-backend/blob/ed3c18517fd6d1194f40a48b92026e26a377be09/rule_engine/app.py), [`RULE_ENGINE.md`](https://github.com/vanish994/dnd-byonder-backend/blob/ed3c18517fd6d1194f40a48b92026e26a377be09/RULE_ENGINE.md), [`GAME_CONTRACT.md`](https://github.com/vanish994/dnd-byonder-backend/blob/ed3c18517fd6d1194f40a48b92026e26a377be09/GAME_CONTRACT.md), [`INVENTORY.json`](https://github.com/vanish994/dnd-byonder-backend/blob/ed3c18517fd6d1194f40a48b92026e26a377be09/dnd2024_knowledge_base/knowledge_base/INVENTORY.json), [`DATA_SCHEMA.json`](https://github.com/vanish994/dnd-byonder-backend/blob/ed3c18517fd6d1194f40a48b92026e26a377be09/dnd2024_knowledge_base/knowledge_base/DATA_SCHEMA.json), [`AUDIT.json`](https://github.com/vanish994/dnd-byonder-backend/blob/ed3c18517fd6d1194f40a48b92026e26a377be09/dnd2024_knowledge_base/knowledge_base/AUDIT.json) e [`TEST_CASES.json`](https://github.com/vanish994/dnd-byonder-backend/blob/ed3c18517fd6d1194f40a48b92026e26a377be09/dnd2024_knowledge_base/knowledge_base/TEST_CASES.json).

No MJ, as referências principais são `app/models.py`, `app/services/turn_service.py`, `app/services/rule_engine_client.py`, `app/services/campaign_service.py`, `app/services/mimo_client.py`, `app/services/ux_assistant.py` e as rotas em `app/api/`. Não foram feitas chamadas HTTP aos serviços reais; a disponibilidade e compatibilidade de produção permanecem não verificadas. O repositório `mimo-ai-proxy` não foi inspecionado nem modificado nesta etapa; as observações abaixo sobre MiMo limitam-se ao payload que o adapter do MJ envia.

## 1. Estado atual dos dois componentes

| Área | MJ-D-D-2024 na branch analisada | `dnd-byonder-backend` em `origin/main` |
|---|---|---|
| Papel | API/orquestrador, persistência SQLite, adapters, histórico e projeção UX. | API de consulta de evidências do corpus; `/v1/resolve` ainda não executa regras. |
| Interpretação | `classify_intent()` aplica heurística lexical e grava `mechanical_likely` ou `narrative_or_unknown`. A fala original continua sendo enviada; o rótulo não roteia nem resolve. | Recebe apenas texto no campo `action`; não há schema de intenção, ator ou alvo. |
| Estado | Campanha com `character` JSON opaco (máx. 20 KB), `scene`, `npcs`, `mechanical_state`, `inventory`, `resources`, `ux_settings`, `history` e timestamps. | `ResolveRequest.state` aceita qualquer `dict`, sem esquema mecânico e sem persistir estado de campanha. |
| Resolução | Só aceita fatos quando resposta e objeto de fatos têm status `resolved` e passam pelo modelo/limites locais. | Responde sempre `needs_rule_validation`, `facts_resolvidos: {}` e uma explicação; `state` e `rule_ids` não participam de cálculo. |
| Aleatoriedade | Existe `app/services/dice.py` com `secrets.randbelow()` e limites, mas `process_turn()` não o chama. Não é parte do gameplay. | Não há endpoint, classe ou fluxo de rolagem no `main` auditado. |
| UX | Modelos e projeções locais opcionais para snapshot de combate e resumo de descanso longo. | Não retorna `ux_snapshot` nem `long_rest_summary`. |
| MiMo | Recebe a fala, a cena, o prompt e fatos resolvidos ou `{}`; é chamado após o Rule Engine. | Não é responsabilidade deste repositório. |

### Capacidades reais do backend externo

| Endpoint | Contrato implementado | Capacidade observada e limite |
|---|---|---|
| `GET /health` | Sem payload. | Abre o SQLite e informa `status`, escopo declarado, quantidade de documentos e chunks. Não testa resolução mecânica nem dependências adicionais. |
| `POST /v1/rules/search` | `query` (2–500 caracteres), `limit` (1–30), `edition` e `document` opcionais. `X-API-Key` é exigido somente se `RULE_ENGINE_API_KEY` estiver configurada. | Busca no FTS5 e devolve chunks de texto com título, seção, página/linhas e `chunk_id`; declara que são evidências e exigem validação. Não devolve uma regra executável vinculada ao resolver. |
| `GET /v1/rules/context` | `q` e `limit`, com a mesma autenticação indireta. | Atalho para a busca. Não resolve ação. |
| `POST /v1/resolve` | `action` (1–200 caracteres), `state: dict` e `rule_ids: list[str]`, ambos opcionais/default vazios. | O código retorna sempre `needs_rule_validation`, ecoa `action`, emite `facts_resolvidos: {}` e informa `reason`/`next_step`. Não usa estado nem IDs para calcular. |

A instalação atual registra 7 documentos, 2.265 chunks, 15.716 `rule_candidates`, 25 entidades e 5.038 referências. **Todos os 15.716 candidatos estão com `status=needs_validation`**. Os 13 templates em `TEST_CASES.json` têm `input={}`, `expected=null` e nenhum `source_rule_id`; não são testes mecânicos executáveis.

O `INVENTORY.json` classifica 3 documentos como 2024, 1 como 2025 e 3 como `not explicit`, além de registrar dois arquivos candidatos a duplicata do DMG 2024. O `/health` declara incluir `supplements_without_explicit_edition`; a busca aplica `edition` apenas se o chamador a enviar e não filtra automaticamente a fonte canônica. Isso **não corresponde ao modo estrito** anteriormente definido para a busca (somente fontes 2024/2025, excluindo suplementos sem edição explícita e preferindo o DMG canônico). O adapter atual do MJ sequer expõe os filtros opcionais `edition`/`document`. Nenhuma alteração foi feita no backend para corrigir essa divergência.

### Lacunas externas confirmadas

No `main` auditado não há resolução de testes, salvaguardas, ataques, dano, crítico, vantagem/desvantagem, CA, PV, condições, movimento, ação/ação bônus/reação, iniciativa, descansos, recursos, concentração ou morte a 0 PV. Não há schema tipado de personagem, criatura, equipamento, combate ou duração de efeito; não há contrato de estado versionado, idempotência ou `state_delta`; não há endpoint de rolagem. A existência de candidatos de regras e busca FTS **não equivale** a possuir um resolver.

Há ainda uma quebra de encadeamento: a busca retorna `chunk_id`/trechos, enquanto `/v1/resolve` aceita `rule_ids` mas os ignora. Nenhum identificador de regra validada é produzido pela busca e consumido por um resolver. A documentação da base confirma que regras seguem pendentes de validação contra as fontes e que os testes aguardam binding a regras verificadas.

## 2. Mapa do contrato atual, ponta a ponta

| Etapa | Contrato/código atual | Efeito e lacuna |
|---|---|---|
| Entrada HTTP | `TurnRequest.player_input` não vazio, até 10.000 caracteres; `stream=false` por padrão. `stream=true` retorna 501. | É texto livre; não carrega IDs do ator/alvo, opção escolhida ou estado tipado. |
| Classificação | `classify_intent(player_input)` grava um rótulo lexical. | É metadado auxiliar, não um parser; não pode ser fonte mecânica nem decidir que uma fala pule o motor. |
| Adapter `/v1/resolve` | MJ envia `{"action": player_input, "state": mechanical_state, "rule_ids": []}` com `X-API-Key` se configurada. | O texto do jogador vai para o campo legado `action`; `character`, `inventory`, `resources`, `scene`, NPCs e histórico não são enviados como estado mecânico. |
| Resposta externa atual | `{status: "needs_rule_validation", action, facts_resolvidos: {}, reason, next_step}`. | O MJ transforma em fatos `{}` e não aplica alteração mecânica; como a chamada em si funcionou, ainda chama o narrador com fatos vazios. Se o upstream falhar em HTTP/rede, o MJ retorna 502 e não chama o MiMo. |
| Validação de fatos | Exige status externo `resolved`, objeto em `facts_resolvidos` ou `FATOS_RESOLVIDOS`, status interno `resolved`, campos conhecidos por `FactsResolved`, limite de 50 KB e até 32 mudanças de estado com chaves planas válidas. | `extra=forbid` reduz campos inesperados, mas `rolls`, `damage`, condições e valores de estado são estruturas genéricas; isso não valida semântica, faixas, identidade de entidade nem regras. |
| Aplicação de estado | Cada `{key,value}` de `state_changes` vira `mechanical_state[key] = value`; campanha é salva como JSON em uma linha SQLite. | É um mapa plano sem allowlist semântica, versão de estado, controle de concorrência ou operações de entidade. O MJ persiste fatos antes de chamar MiMo. |
| `FactsResolved` | Modelo admite `resolution_id`, `status`, `action`, `outcome`, `rolls`, `damage`, `conditions_applied`, `state_changes`, `rules_used`, `ux_snapshot` e `long_rest_summary`. | O backend externo atual não devolve esses dados resolvidos; a presença dos campos no MJ é capacidade de validação/projeção, não prova de mecânica implementada. |
| Snapshot UX | A projeção usa o `ux_snapshot` do turno mais recente resolvido; exige `current: true`. Tenta invalidar menus antigos se um turno posterior não for resolvido. | Nenhum snapshot é produzido pelo resolver atual. `current` não está ligado a uma versão de estado externa. |
| Resumo de descanso longo | O endpoint do MJ o exibe se o fato `action` for `long_rest`/`long rest` e houver `long_rest_summary`. | O modelo só descreve descanso longo; não existe resumo de descanso curto. Os valores são pass-through e não são calculados localmente. |
| Adapter MiMo | `POST /v1/chat/completions`, `stream:false`, `model=mimo-v2.5-no-thinking`, Bearer; system prompt + uma mensagem atual com `campaign_id`, `scene`, `FATOS_RESOLVIDOS`, `player_input`. | MiMo recebe fatos ou `{}` e não é chamado antes do Rule Engine. O adapter não passa `character`, `mechanical_state`, inventário nem histórico explicitamente; usa `user=campaign_id`, mas o comportamento de histórico interno do proxy não foi verificado. |

### Incompatibilidades específicas a resolver no contrato

1. O MJ aceita `player_input` de até 10.000 caracteres; o backend limita `action` a 200. Uma fala maior pode receber 422 no upstream, que o adapter converte em erro e o endpoint MJ expõe como 502.
2. O modelo MJ de busca aceita query de 1–500 caracteres e envia apenas `query`/`limit`; o backend exige query de pelo menos 2 caracteres e oferece filtros opcionais que o MJ não modela. Uma query de 1 caractere pode virar 502; a busca não implementa o modo estrito por padrão.
3. O backend retorna `next_step`, mas o MJ só usa `reason` ou `message` no feedback; `next_step` não é propagado.
4. O backend recebe `rule_ids`, mas não os usa; a busca devolve `chunk_id`, não `rule_id` executável/validado. Não há binding entre evidência de busca e resolução.
5. O schema `FactsResolved` do MJ exige status interno `resolved` para aplicar fatos, além do status externo. Isso é seguro para o contrato atual, mas precisa ser documentado e versionado para evitar payloads “resolvidos” aceitos por um serviço e rejeitados pelo outro.

## 3. Dados necessários por mecânica: existente, exigido e ainda a projetar

“Exigido” abaixo significa necessário **se** a mecânica correspondente for automatizada; não significa que o contrato atual já aceite ou valide o dado. Nenhum campo da coluna de proposta foi implementado nesta etapa.

| Informação | Já existe hoje | Necessidade mecânica | O que falta projetar/decidir |
|---|---|---|---|
| Personagem/ator | `CampaignCreate.character` é JSON opaco; o Rule Engine recebe somente `mechanical_state`. | Identificar quem age e qual ficha/estado usar em cada resolução. | Identificador estável do ator e schema versionado da ficha; definir se há um personagem pré-criado ou criação completa. |
| Nível/classe/subclasse | Podem estar escondidos em JSON opaco, mas não são validados nem enviados. | Nível e classe/subclasse quando alterarem proficiência, opções, recursos ou regras de uma ação. | Fonte e versão desses valores; só adicionar campos para mecânicas do escopo aprovado. |
| Atributos, perícias e salvaguardas | Sem campos tipados. | Testes e salvaguardas precisam do modificador pertinente, proficiência/expertise quando aplicável, condições/modificadores e DC ou fonte determinística da DC. | Decidir se o motor recebe atributos brutos ou modificadores derivados. Para os brutos, definir cálculo e fonte; para os derivados, validar proveniência. |
| Proficiências | Sem schema tipado. | Ataques/testes/salvaguardas que dependem de proficiência exigem a proficiência e o bônus aplicável ao personagem. | Schema para perícias, salvaguardas, armas e ferramentas; não inferir pela classe não estruturada. |
| Equipamento/arma | `inventory` é uma lista genérica na campanha, não enviada ao resolver. | Ataque/dano exigem item escolhido e perfil validado: tipo de ataque, dado/tipo de dano, propriedades/requisitos e alcance pertinentes à regra. | IDs estáveis, perfil mecânico com fonte e seleção explícita do jogador; não inferir arma da prosa se ambígua. |
| Alvo/criatura | `npcs` é lista genérica; nenhum alvo tipado. | Para ataque/dano/efeitos: identidade, CA, PV, defesas e condições relevantes do alvo. | Modelo de entidades/criaturas e identificação inequívoca do alvo; origem/versionamento do bloco de estatísticas. |
| Distância, posição e movimento | A UX admite `position` como dict e movimento restante como número/unidade; não há entrada tipada para resolver. | Alcance, deslocamento, obstáculos e movimento restante dependem da posição, velocidade e abstração espacial. | Escolher grade, zonas/faixas ou teatro da mente; definir unidades, linha de visão e quais situações serão fora do MVP. |
| Ação, ação bônus e reação | Não há ledger mecânico persistido. UX tem três booleanos opcionais de disponibilidade; entrada chega como texto. | Validar custo/uso por turno e gatilhos de reação; exige turno/rodada, ator ativo e histórico dos gastos. | Estado tipado por turno e ciclo de vida; não deixar o frontend ou MiMo marcar uso. |
| Recursos | `resources` e snapshots UX são dicts genéricos; não enviados ao resolver. | Gastar/recuperar recurso exige quantidade atual/máxima, custo, gatilho e regra de recuperação. | IDs, tipos, limites, momento de recuperação e vínculo a classe/item, conforme o escopo de personagem aprovado. |
| Condições | Snapshot UX prevê `conditions: list[dict]`, mas não existe estado mecânico tipado. | Aplicação/remoção precisa de definição, fonte, alvos, efeitos, regras de interação e duração/gatilho. | Registro validado de condição, origem e expiração; não inventar interpretação a partir de texto livre. |
| Modificadores | Não há estrutura semântica. | Vantagem/desvantagem, bônus, penalidades, cobertura, resistência e efeitos dependem de origem, contexto e regras de combinação. | Representar cada modificador com origem/regra e momento de aplicação; decidir como conflitos/empilhamento são auditados. |
| Ambiente | `scene` é dict opaco enviado somente ao MiMo, não ao Rule Engine. | Cobertura, terreno, visibilidade e outras regras ambientais só entram se fizerem parte da mecânica habilitada. | Delimitar quais propriedades ambientais são mecânicas e quais são apenas narrativas; schema mínimo por regra. |
| Combate/iniciativa | UX prevê `combat_active`, `round_number` e `turn_number`; não são entradas nem estado persistido tipado. | Iniciativa exige participantes, valores de iniciativa, ordem, rodada/turno ativo; ações exigem estado do turno. | Máquina de estados de combate, transições e critérios para iniciar/encerrar. |
| PV, CA e defesas | O snapshot UX prevê PV; campanha não define CA/defesas. O resolver recebe dict arbitrário. | Ataques necessitam CA; dano necessita PV e resistência/vulnerabilidade/imunidade pertinentes. | Campos tipados por entidade e regras de atualização; resolver valida limites e alvo. |
| Efeitos/concentração/duração | UX tem listas/dict genéricos e um resumo de descanso longo; não há contrato de entrada. | Aplicar/terminar efeitos depende de fonte, duração, início/fim, gatilhos, concentração e interação com descanso/turnos. | Modelo explícito de duração (rodadas/turnos/evento/descanso/concentração) e regras de expiração. |
| Rolagens | MJ tem utilitário local isolado; backend não oferece rolagem. | Testes/ataques/dano requerem dados aleatórios gerados no lado autoritativo e persistidos com a resolução. | Escolher o único serviço que rola; definir idempotência, trilha de auditoria e formato das faces/modificadores. |
| Regras/fontes | Busca retorna chunk e evidência; todos candidatos do banco estão `needs_validation`. | Cada mecânica executável precisa de regra validada e casos determinísticos com resultado esperado. | Registro de regras validadas, proveniência/versão, política estrita de edição e binding regra→resolver→teste. |

## 4. Dependências e ordem das mecânicas

| Ordem | Mecânica/camada | Dependências mínimas | Observação de escopo |
|---:|---|---|---|
| 0 | Regra-fonte e testes | Regra conferida em fonte permitida, ID estável, versão/proveniência e casos esperados aprovados. | Bloqueia todas as mecânicas; candidatos FTS não bastam. |
| 1 | Estado/ficha tipados | Ator, entidades, valores necessários, versão de estado e validação de domínio. | Escolher ficha pré-gerada vs. criação; sem defaults mecânicos inventados. |
| 2 | Rolagem e modificadores base | CSPRNG, injeção determinística em teste, registro de faces, modificador e total; modelo de vantagem/desvantagem. | Componente comum, mas somente usado após regra/fórmula validada. |
| 3 | Testes de atributo e salvaguardas | Atributo/perícia/proficiência, DC definida, condições/modificadores pertinentes, fórmula e resultado da rolagem. | Fatia simples para validar resolução e fatos sem ainda gerir combate completo. |
| 4 | Estado de combate e iniciativa | Entidades/participantes, iniciativa, ordem, rodada, turno ativo, controle de ações e estado versionado. | Necessário antes de afirmar disponibilidade/uso de ação em combate. |
| 5 | Ataque, CA, acerto/crítico, dano e PV | Ator, arma, alvo, bônus, CA, vantagem/desvantagem, regra de crítico, rolagens de dano, tipo e defesas do alvo. | Primeiro ciclo de combate; cada subregra precisa de evidência e testes. |
| 6 | 0 PV/morte/estabilização | PV, dano recebido e regras/estado de morte aplicáveis. | Vem após dano e PV; sem regras validadas, não narrar morte/estabilização como resolvida. |
| 7 | Condições, efeitos e concentração | Aplicação/remoção, fonte, duração, gatilhos, turnos e interações. | Requer relógio de combate/efeitos e snapshots UX com versão. |
| 8 | Movimento/reação | Velocidade, posição/alcance, terreno/obstáculos conforme abstração espacial, deslocamento gasto e gatilhos. | Não pode ser especificado antes da decisão grade/faixas/teatro da mente. |
| 9 | Descansos e recuperação | Tipo de descanso, elegibilidade, tempo/estado, dados de vida/recursos, efeitos que acabam/continuam e testes. | Implementar descanso curto e longo separadamente; UI apenas exibe resultado do resolver. |
| 10 | Recursos de classe, magia e subclasses | Ficha completa, recursos, componentes/efeitos, condições, fontes validadas e muitas interações. | Escopo maior; recomenda-se deixar após o primeiro slice jogável. |

**Possível primeiro slice jogável (proposta, não decisão):** personagem pré-gerado + criatura de teste com bloco validado; iniciativa simples; uma ação de ataque com arma; rolagem, CA, acerto/crítico, dano e PV; fatos/estado versionados; UX indicando recurso de turno. Isso requer aprovar o escopo de ficha, criatura, distância e regras de fonte. Não inclui editor completo de personagem, todas as classes/magias nem um sistema tático geral.

## 5. Proposta de contrato de resolução

Os exemplos a seguir são **propostas não implementadas**. Nomes e valores ilustrativos não definem regra de D&D. A mudança precisa ser coordenada no único Rule Engine escolhido e versionada; não trocar unilateralmente o contrato atual.

### Requisição proposta

Manter a fala original para contexto/auditoria, mas enviar também intenção estruturada não mecânica produzida/confirmada pelo MJ. O Rule Engine continua validando legalidade e calculando o resultado; o parser do MJ nunca envia um sucesso/dano calculado.

```json
{
  "contract_version": "2",
  "request_id": "req_uuid",
  "campaign_id": "campaign_uuid",
  "expected_state_version": 12,
  "actor_id": "pc_1",
  "player_input": "Eu ataco o goblin com a espada.",
  "intent": {
    "type": "weapon_attack",
    "target_id": "creature_1",
    "weapon_id": "weapon_1"
  },
  "state_snapshot": { "...": "estado tipado, versão 12" }
}
```

Justificativa dos campos novos: `request_id` evita nova rolagem/dupla aplicação em retry; `expected_state_version` detecta estado antigo; IDs de ator/alvo/arma eliminam ambiguidade; `intent` separa estrutura de fala livre. Se a intenção não for identificável sem adivinhar, o MJ deve pedir esclarecimento; não deve fabricar alvo, arma, movimento ou opção. O conjunto mínimo de `intent.type` e campos obrigatórios depende da primeira fatia mecânica aprovada.

O contrato atual usa `action` com texto livre até 200 caracteres. A migração deve resolver explicitamente a incompatibilidade com o `player_input` de até 10.000 do MJ: limitar a entrada de turno, alterar o limite do serviço de regras, ou criar endpoint/versão nova. Também deve definir se o serviço seleciona internamente a regra validada; o cliente não deve conseguir forçar um `rule_id` candidato não validado.

### Resposta proposta

```json
{
  "contract_version": "2",
  "request_id": "req_uuid",
  "resolution_id": "res_uuid",
  "state_version_before": 12,
  "state_version_after": 13,
  "status": "resolved",
  "reason": null,
  "facts_resolvidos": {
    "status": "resolved",
    "action": "weapon_attack",
    "outcome": "<resultado calculado pelo Rule Engine>",
    "rolls": [
      {
        "formula": "1d20+5",
        "results": [13],
        "modifier": 5,
        "total": 18,
        "critical": false
      }
    ],
    "damage": null,
    "conditions_applied": [],
    "state_delta": [],
    "rules_used": [],
    "ux_snapshot": { "...": "snapshot após a resolução, state_version 13" }
  }
}
```

`damage`, `state_delta`, `rules_used` e demais dados ficam vazios/ausentes até que a regra aplicável seja validada. `critical` só tem significado para rolagens em que a regra de crítico se aplica; não é uma classificação universal do dado. Para erro de regra pendente, intenção ambígua ou estado conflitante, retornar um status não resolvido, explicação legível e **nenhuma mudança de estado**; o MJ mantém `FATOS_RESOLVIDOS={}`. A lista final de status e a convenção canônica entre `facts_resolvidos` e `FATOS_RESOLVIDOS` precisam de versão/compatibilidade explícita.

## 6. Proposta de contrato de estado

A diretriz do produto atribui ao MJ a persistência/estado da campanha e ao Rule Engine a autoridade exclusiva sobre as transições mecânicas. Uma arquitetura compatível é: MJ armazena snapshot versionado; envia snapshot e `expected_state_version`; Rule Engine calcula sem o MJ reproduzir regras; devolve `state_delta` validado; MJ aplica atomicamente apenas se a versão ainda for a esperada. O MJ não recalcula o delta. Uma repetição de `request_id` devolve a resolução original e não rola novamente.

Separar conceitualmente ficha estável, estado de entidades e estado de combate, em vez de continuar usando um dicionário plano sem schema. Campos concretos só entram quando necessários à mecânica aprovada:

- **Ficha/ator:** ID; nível/classe/subclasse somente se suportados; atributos ou modificadores com proveniência; proficiências; equipamento/IDs de armas e recursos. É preciso escolher entre valores base (com derivação validada no motor) ou bônus pré-computados (com procedência verificável).
- **Entidade/alvo:** ID e tipo; PV atual/máximo e CA para o slice de ataque; resistências/imunidades somente se cobertas; posição/velocidade somente após escolher abstração espacial.
- **Estado de combate:** combate ativo; rodada/ordem/ator ativo; estado disponível/usado/desconhecido para ação, ação bônus, reação e movimento. Não manter contadores paralelos no frontend.
- **Condições/efeitos/recursos:** IDs e fontes; valores necessários; duração ou gatilho; custo/recuperação apenas quando regra validada e recurso fizer parte do escopo.
- **Envelope de estado:** `schema_version` e `state_version` para migração e concorrência. Cada transição identifica entidade/campo/operação e novo valor validado, em vez de atribuir uma chave plana arbitrária.

O schema acima é uma direção; não é proposta de preencher todos os atributos, subclasses, magias ou blocos de criatura de uma só vez. O Rule Engine deve receber apenas os dados tipados necessários para aquela ação, e rejeitar/solicitar dados ausentes em vez de presumir valores. Retenção do histórico mecânico também precisa ser definida: hoje a campanha mantém no máximo 50 turnos, o que não basta como trilha de auditoria durável de todas as rolagens/alterações.

## 7. Proposta de contrato UX

O Rule Engine precisa devolver uma projeção vinculada à mesma resolução/versão do estado, por exemplo `resolution_id`, `state_version`, `current=true` e horário. A UX nunca consulta o MiMo para descobrir regra ou disponibilidade. O schema atual do MJ é uma primeira estrutura local, não um contrato acordado com o Rule Engine.

| Exibição | Dado autoritativo necessário | Estado atual do contrato MJ |
|---|---|---|
| Ações disponíveis | IDs estáveis das opções, tipo/custo e aplicabilidade ao estado atual. | `available_actions` existe no modelo como opções com nome, custo e explicação; sem ID estável; o backend externo não envia. |
| Ação usada/disponível | Estado explícito `available/used/unavailable/unknown` ligado a ator/turno. | `turn_resources.action: bool | null`; `false` é interpretado como já usada. Não há distinção completa entre usada e indisponível. |
| Ação bônus/reação | Mesmo estado explícito, com ator/turno e gatilho quando aplicável. | Booleanos opcionais e listas de opções no modelo; sem emissão real pelo backend. |
| Movimento restante | Valor, unidade, posição/turno/versão e regra de movimento aplicada. | Número e unidade opcionais para UX; sem modelo de entrada/saída mecânico. |
| Recursos | IDs, nome, atual/máximo, custo e recuperação conforme estado/ação. | Dicionários genéricos; sem semântica/validação. |
| Condições | Identificador, alvo, fonte, descrição curta validada e duração/expiração. | Lista genérica de dicts; sem esquema de duração. |
| Efeitos ativos | Identidade/fonte, concentração se houver, duração restante e gatilho de expiração. | Lista genérica e dict de concentração; sem semântica estruturada. |
| Efeitos que terminam no descanso | Resultado efetivo após resolver o descanso, com lista de encerrados e continuados. | `LongRestSummary` prevê `effects_ended`/`effects_continuing`; não há resumo de descanso curto. |
| Opção inválida | ID da opção, resultado de validação, código/motivo e referência da regra. | `unavailable_actions` tem nome e motivo textual, mas sem ID/código/ref obrigatório. |
| Contexto de frescor | `state_version`/`resolution_id` correspondentes ao estado salvo; `current=true`. | O modelo exige `current=true` para mostrar opções, mas não tem `state_version`; o serviço externo não emite snapshot. |

A recomendação é preferir um enum explícito a booleanos para estados de economia de ação, e tornar IDs/motivos estáveis para interação acessível e testes. Valores ausentes significam **desconhecido**, não zero nem “nenhuma opção”. Um snapshot antigo ou de outra `state_version` não pode ser mostrado como atual. `long_rest_summary` e eventual resumo de descanso curto são resultados da resolução, não previsões criadas pela UI.

## 8. Aleatoriedade e contrato de rolagem

Hoje, o utilitário local do MJ usa `secrets.randbelow()`, injeta fonte aleatória para testes e retorna `formula`, `dice` (faces e resultados), `modifier` e `total`. Ele está explicitamente fora de `process_turn()`, não retorna `critical`, não implementa regras de vantagem/ataque e **não deve ser conectado ao gameplay sozinho** enquanto o Rule Engine for externo.

Recomendação arquitetural, sem escolher A/B: a aleatoriedade deve ser executada dentro da fronteira do **único** Rule Engine aprovado. A mecânica recebe resultados de um provedor de rolagem e é testável com resultados injetados; em produção, o provedor usa CSPRNG (`secrets.randbelow()` ou equivalente). O MiMo, frontend, navegador e cliente não escolhem faces. O resolver calcula se a face natural constitui crítico segundo a regra pertinente; um helper genérico de dados não decide isso.

O formato proposto pelo pedido é adequado como registro mínimo, com ajuste para múltiplos dados:

```json
{
  "formula": "1d20+5",
  "results": [13],
  "modifier": 5,
  "total": 18,
  "critical": false
}
```

Para auditoria, associar o resultado ao `request_id`, `resolution_id`, propósito/tipo da rolagem e regra usada; vantagem/desvantagem deve registrar todas as faces e qual foi escolhida. Não reexecutar uma rolagem em retry do mesmo `request_id`; guardar a resposta imutável ou devolver a resolução anterior. Não expor seed interna de CSPRNG como substituto de auditoria. Os nomes finais (`results` vs. atual `dice`) devem ser fechados em contrato versionado.

## 9. Alternativas arquiteturais — decisão não tomada

| Alternativa | Vantagens | Desvantagens/riscos | Consequência contratual |
|---|---|---|---|
| **A. Evoluir `dnd-byonder-backend` como Rule Engine** | Mantém busca/corpus e execução no serviço que já ocupa esse papel; permite um único catálogo de regras, validação, resolver e fonte aleatória; evita duplicar mecânicas no MJ. | Exige autorização explícita para alterar o repositório externo; necessita transformar candidatos em regras validadas, schemas/estado, testes, idempotência e compatibilidade; deploy externo é ciclo separado (não será feito agora). | Evoluir `/v1/resolve` de texto livre/fail-closed para contrato versionado; ligar regra validada à evidência, testes, `FATOS_RESOLVIDOS`, delta, UX e rolagens. |
| **B. Criar Rule Resolver separado dentro do MJ** | Mudanças ficam no repositório sob implementação do orquestrador; pode facilitar testar/deployar o primeiro slice junto ao estado da campanha. | Cria segundo sistema de regras/resolução ao lado do serviço chamado atualmente Rule Engine; alto risco de duplicar fonte, validação, regras, testes e autoridade. A busca atual fornece evidência/chunks, não regras executáveis nem IDs validados. Se escolhido, é necessário definir o backend externo como fonte de evidência e garantir que **somente um** resolver esteja ativo — sem fallback duplo. | Mudaria a fronteira atual: o MJ passaria a executar regras localmente ou hospedar serviço interno, enquanto o backend externo deixaria de ser o resolver. Requer contrato de sincronização/versionamento das regras e um plano explícito para não resolver duas vezes. |

A arquitetura atualmente documentada aponta para A (Rule Engine externo), mas esta análise **não seleciona A nem B**. B não deve ser tratado como fallback provisório dentro do MJ; exigiria decisão explícita de migração e justificativa de não duplicação.

## 10. Ordem recomendada de implementação após aprovação

1. **Decidir A/B e autoridade de estado**; definir qual único componente é o resolver e onde o snapshot canônico de campanha reside.
2. **Confirmar política estrita de fontes** já definida pelo jogador e a discrepância atual do `main`; acordar uma forma autorizada de aplicar filtro 2024/2025, excluir edição não explícita e resolver duplicata canônica antes de executar regras.
3. **Selecionar a primeira fatia de jogo** (por exemplo, personagem pré-gerado e uma criatura), limites de criação de ficha, unidade espacial e estado que persistirá.
4. **Validar fontes e especificar regras** para cada mecânica do slice; registrar IDs/proveniência e preencher casos com entrada e resultado esperado. Não ativar candidate rules automaticamente.
5. **Versionar request/response e schemas**: intenção estruturada, dados mínimos do ator/alvo, estados `needs_input`/`invalid`/`needs_rule_validation`, resposta de fatos, erros e contrato de compatibilidade. Corrigir os limites 10.000/200 e 1/2 caracteres.
6. **Modelar estado e idempotência**: versão do estado, deltas por entidade, aplicação atômica no MJ e retry sem re-rolagem. Definir retenção/auditoria de turnos.
7. **Implementar provedor de rolagem** dentro do resolver escolhido, com CSPRNG em produção e faces injetadas em testes; validar fórmula/limites e registrar roll junto à resolução.
8. **Resolver testes e salvaguardas**, depois iniciativa/ordem/economia de turno, para testar primeiro o fluxo determinístico básico.
9. **Implementar slice de ataque**: ação, alvo, arma, alcance dentro da abstração escolhida, bônus, CA, vantagem/desvantagem, crítico, dano e PV, cada qual com testes de fronteira.
10. **Adicionar 0 PV/morte/estabilização, condições, efeitos e reações**, seguido de movimento conforme o modelo espacial aprovado.
11. **Adicionar descansos e recuperação**; curto e longo separadamente, aplicando somente transições do resolver.
12. **Emitir UX snapshot versionado** após cada resolução e integrar UI; só depois ampliar classes, subclasses, recursos e magia.
13. **Testar contrato simulado e integração real separadamente**: testes unitários determinísticos, testes HTTP contractuais e, quando URLs/credenciais estiverem configuradas, chamadas reais a `/health`, `/v1/resolve` e `/v1/chat/completions`. Mocks nunca contam como integração real.

## 11. Decisões que precisam de aprovação antes de implementar

1. **A ou B:** evoluir o resolver no `dnd-byonder-backend` ou mudar a fronteira e criar um resolver isolado dentro do MJ. Nenhuma opção foi escolhida nesta análise.
2. **Autorização para qualquer alteração externa:** se A for escolhido, será necessária autorização explícita para modificar `dnd-byonder-backend`; esta tarefa não altera nem faz deploy dos serviços externos.
3. **Primeiro slice jogável:** personagem pré-gerado/monstro fixo versus editor/fichas mais abrangentes; define classes, campos e volume de regra inicial.
4. **Fonte estrita no serviço ativo:** manter a regra já aprovada (2024/2025, excluir três fontes sem edição explícita, priorizar DMG canônico) e autorizar o local/contrato que deve aplicar esse filtro. O `origin/main` atual ainda inclui fontes `not explicit` em seu escopo declarado.
5. **Estado canônico:** confirmar MJ como persistidor do snapshot/versionamento com Rule Engine retornando delta, ou propor outra propriedade; não manter cópias mecânicas divergentes.
6. **Ficha e entidades:** atributos brutos ou bônus derivados; formato de criatura/alvo; proveniência e modo de criação. O contrato atual não decide isso.
7. **Distância e movimento:** grade, zonas/faixas ou teatro da mente; unidades, alcance e obstáculos que entram no primeiro slice.
8. **Intenção estruturada e compatibilidade:** vocabulário inicial, como pedir esclarecimento, tamanho máximo da fala e escolha entre endpoint/versão nova ou migração coordenada do `/v1/resolve`.
9. **Aleatoriedade/retries:** confirmar idempotência por `request_id`, retenção de rolagens e campos de auditoria; a proposta é CSPRNG no único resolver, sem dados no MiMo/cliente.
10. **Retenção e uso público:** duração do histórico/registro de rolagens, autenticação e persistência durável antes de campanhas reais/publicação. São limites atuais do MJ e não foram alterados aqui.

## 12. Validação e limites desta etapa

Este commit deve conter **somente este documento técnico**. Nenhum código funcional ou mecânica foi alterado; não houve mudança em `dnd-byonder-backend` ou `mimo-ai-proxy`; nenhum deploy Render ou merge foi feito. Os 47 testes existentes e `git diff --check` serão executados antes do commit. Como as URLs/credenciais reais não foram configuradas/testadas nesta análise, as conclusões sobre capacidades externas vêm do código e documentação do `origin/main` fixado no commit indicado, não de chamadas de produção.
