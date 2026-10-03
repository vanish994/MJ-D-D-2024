# Contrato de estado para o Rule Engine — V1

## Escopo e compatibilidade

`mj-rule-state-v1` versiona o objeto enviado **dentro do campo `state`** pelo adapter do MJ. Ele não é uma nova versão da rota externa nem altera o payload HTTP de `/v1/resolve`. O adapter continua enviando a fala original em `action`, o estado versionado em `state` e a lista existente `rule_ids` (vazia por padrão):

```json
{
  "action": "Eu tento abrir a porta.",
  "state": {
    "schema_version": "mj-rule-state-v1",
    "campaign_id": "campaign_123",
    "character": {},
    "mechanical_state": {},
    "inventory": [],
    "resources": {},
    "scene": {},
    "intent": {
      "classification": "mechanical_likely",
      "player_input": "Eu tento abrir a porta."
    }
  },
  "rule_ids": []
}
```

O formato acima é montado pelo MJ em `app/services/turn_contract.py`. O `dnd-byonder-backend` atual aceita `state` como um dicionário genérico, mas seu resolver `/v1/resolve` não consome esses campos: enquanto não houver mecânica validada, ele pode retornar `needs_rule_validation` e `facts_resolvidos: {}`. Portanto, o estado estruturado prepara o contrato do lado MJ; **não significa que a integração externa já interpreta ficha, inventário ou cena**. A busca `/v1/rules/search` continua sendo apenas evidência e nunca é tratada como resolução.

## Pipeline

```text
player_input
    ↓
classify_intent(player_input)                 # rótulo auxiliar
    ↓
build_rule_state(...)                         # transporte tipado/versionado
    ↓
POST /v1/resolve { action, state, rule_ids }   # rota externa preservada
    ↓
validação da resposta pelo MJ
    ├── resposta e fatos resolvidos válidos → aplicar somente state_changes
    └── status diferente, fatos vazios/inválidos ou resposta inconsistente
             → facts_resolvidos = {}; nenhuma mudança mecânica
    ↓
MiMo recebe FATOS_RESOLVIDOS válidos ou {}
    ↓
narração
```

A chamada ao Rule Engine acontece antes do MiMo para toda entrada, inclusive diálogo. A classificação lexical é somente o campo `intent.classification`; ela não rola dados, não determina sucesso/fracasso e não decide se o Rule Engine será chamado.

## Campos de `mj-rule-state-v1`

| Campo | Origem | Regra |
|---|---|---|
| `schema_version` | Constante do contrato local. | Sempre `mj-rule-state-v1`. |
| `campaign_id` | Argumento da campanha processada. | Identifica a campanha; não é dado mecânico. |
| `character` | `campaign.character`. | Valor presente é preservado; ausente (`None`) vira `{}`. Nenhum atributo, nível, classe ou bônus é sintetizado. |
| `mechanical_state` | `campaign.mechanical_state`. | Deve ser objeto/dict. O builder rejeita tipo não-objeto; o estado não é interpretado nem calculado aqui. |
| `inventory` | `campaign.inventory`. | Valor presente é preservado; ausente (`None`) vira `[]`. Itens não são inferidos nem avaliados. |
| `resources` | `campaign.resources`. | Valor presente é preservado; ausente (`None`) vira `{}`. Quantidades/custos não são calculados. |
| `scene` | `campaign.scene`. | Valor presente é preservado; ausente (`None`) vira `{}`. A cena não é convertida em regra. |
| `intent.classification` | `classify_intent(player_input)`. | Só `mechanical_likely` ou `narrative_or_unknown` no classificador atual; anotação auxiliar. |
| `intent.player_input` | Entrada do jogador. | Texto original associado à classificação; não constitui resolução. |

O builder usa defaults apenas para os campos ausentes especificados. Não acrescenta PV, CA, posição, iniciativa, ações disponíveis, modificadores, resultados, condições ou outros fatos. Não transforma campos de intenção em `status`, `outcome` ou `state_changes`.

## Resposta e `FATOS_RESOLVIDOS`

A semântica vigente permanece: o MJ só aceita fatos se a resposta externa tiver `status: "resolved"` e o objeto `facts_resolvidos` (ou a chave legada `FATOS_RESOLVIDOS`) também validar com `status: "resolved"`. Só então as mudanças declaradas podem ser aplicadas. Status diferente de `resolved` produz fatos `{}` mesmo que uma resposta inconsistente inclua mudanças dentro de `facts_resolvidos`.

Exemplo fail-closed que o MJ deve rejeitar integralmente:

```json
{
  "status": "needs_rule_validation",
  "facts_resolvidos": {
    "status": "resolved",
    "state_changes": [{"key": "hp", "value": 0}]
  }
}
```

O retorno ao MiMo será `FATOS_RESOLVIDOS: {}` e o estado da campanha não muda. O modelo local continua permitindo os campos futuros (`resolution_id`, `action`, `outcome`, `rolls`, `damage`, `conditions_applied`, `state_changes`, `rules_used`, `ux_snapshot`, `long_rest_summary`), mas campo disponível no schema não significa mecânica implementada nem autoriza valor inventado.

## Responsabilidades

### MJ-D-D-2024

- transportar campanha, fala e estado existente no envelope versionado;
- gerar somente a classificação auxiliar de intenção;
- manter o formato externo atual de `/v1/resolve`;
- validar formato/status dos fatos recebidos;
- aplicar apenas mudanças autorizadas por fatos resolvidos válidos;
- enviar fatos válidos ou `{}` ao narrador.

### Rule Engine

Quando mecânicas futuras forem autorizadas e validadas, será o único responsável por validar as regras aplicáveis, produzir rolagens e resultados mecânicos, declarar `state_changes` e emitir `ux_snapshot`/resumos estruturados. No serviço externo atual, `/v1/resolve` segue fail-closed e essas capacidades ainda não estão disponíveis.

### MiMo

É exclusivamente narrador: interpreta NPCs e descreve a cena e as consequências narrativas dos fatos recebidos. Não rola dados, calcula dano ou CD, decide acerto/sucesso, aplica condições nem modifica estado. Com `FATOS_RESOLVIDOS={}`, não declara resultado mecânico.

## UX

`ux_assistant.py` permanece uma projeção dos dados explicitamente devolvidos pelo Rule Engine. Se o serviço futuramente fornecer `turn_resources`, `available_actions`, condições, efeitos ou resumos validados, o MJ poderá formatá-los para a interface; não calcula disponibilidade, ação utilizada, movimento restante, gasto/recuperação de recursos ou duração. Campos ausentes permanecem desconhecidos/indisponíveis.

## Limites e próximas versões

Este envelope não fecha o schema mecânico de ficha, ator/alvo, condições, combate ou rolagens; esses formatos dependem da decisão de arquitetura e do primeiro escopo de mecânicas aprovado. Também não altera os limites próprios de `action` no serviço externo, que atualmente são menores que o máximo de `player_input` aceito pelo MJ. Compatibilidade real só poderá ser confirmada com teste contra o serviço externo; os testes locais usam mocks. Nenhuma mecânica de D&D foi implementada por este contrato.
