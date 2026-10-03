# Pipeline

```text
Jogador
   ↓
MJ-D-D-2024 — classifica intenção apenas como metadado e monta `mj-rule-state-v1`
   ↓
Rule Engine /v1/resolve — chamado para toda entrada, inclusive diálogo
   ↓
Validar envelope recebido com `rule-resolution-v1`
   ├── status resolved válido → autorizar fatos/snapshot e aplicar somente state_changes validados
   └── status pendente, inválido ou schema incorreto → fatos={}, nenhuma mudança mecânica
   ↓
Persistir turno pendente, status e projeção validada
   ↓
MiMo Proxy /v1/chat/completions — somente narrativa; recebe fatos validados ou {}
   ↓
Persistir narrativa concluída ou marcar turno como failed
   ↓
Jogador
```

**Não há atalho do MJ diretamente ao MiMo.** `build_rule_state()` coloca `campaign_id`, `character`, `mechanical_state`, `inventory`, `resources`, `scene` e `intent` dentro do campo externo `state`. Campos opcionais ausentes usam somente os defaults vazios documentados; o builder não calcula regras. O adapter mantém o formato `/v1/resolve` (`action`, `state`, `rule_ids`) sem alteração. A classificação lexical é apenas registrada como metadado; ela não determina sucesso, fracasso ou cálculo e não decide se o Rule Engine será chamado.

A resposta é validada por `app/services/resolution_contract.py`. Só `status: resolved` autoriza projeção de fatos, `state_changes`, `rules_used`, `ux_snapshot` e `long_rest_summary`. Os status `needs_rule_validation`, `awaiting_input`, `awaiting_roll`, `invalid_action` e `rule_not_found` resultam em fatos `{}` enviados ao MiMo e nenhuma mudança mecânica. Um status não reconhecido, versão errada, campo extra, tipo incorreto ou payload malformado falha para `needs_rule_validation`, sem aplicar parte alguma do resultado. A única resposta sem versão aceita é o formato legacy mínimo `{"status":"needs_rule_validation"}`; campos adicionais nesse formato são rejeitados.

Em resposta resolvida válida, o MJ envia ao MiMo uma projeção normalizada apenas dos campos reconhecidos e validados; omite `request`, `reason` e `message`. O MJ aplica `state_changes` separadamente, somente quando o status efetivo é `resolved`, com chaves seguras e valores escalares. A lista legacy `{key, value}` dentro de fatos é normalizada; conflito com o mapa novo invalida o envelope inteiro. Se o Rule Engine falhar, o turno não é enviado ao narrador e o endpoint retorna erro upstream. Um erro do MiMo deixa um registro de turno `failed`; se a mecânica já foi validada, os fatos e mudanças válidas continuam registrados.

Os schemas `mj-rule-state-v1` e `rule-resolution-v1` são contratos locais do MJ. O backend externo atual pode continuar aceitando `state` como dict genérico e responder somente `needs_rule_validation`; nem o estado enviado nem os testes simulados comprovam que ele implemente o contrato de resolução V1. Consulte [`RULE_ENGINE_CONTRACT_V1.md`](RULE_ENGINE_CONTRACT_V1.md) e [`RULE_RESOLUTION_CONTRACT_V1.md`](RULE_RESOLUTION_CONTRACT_V1.md).

## Ajuda de combate

`GET /v1/campaigns/{id}/assistant` projeta somente `ux_snapshot` validado da resolução mais recente. Para liberar opções, o snapshot precisa vir do Rule Engine com `current: true`. Uma tentativa posterior sem resolução confirmada invalida o menu anterior; campos ausentes retornam `null` e o status indica `unavailable`/`incomplete`.

Avisos de ação, ação bônus, reação e movimento são traduções de valores explícitos do snapshot. Custos, explicações, ações disponíveis/indisponíveis, condições, efeitos e recursos são pass-through estruturado. O modo `beginner`, `normal` ou `advanced` muda somente a apresentação; no modo avançado, a descrição fornecida pelo Rule Engine é ocultada.

Feedback de ação inválida é passado do motivo/mensagem validado do Rule Engine quando presente; caso contrário, o orquestrador comunica apenas que a resolução não ocorreu e que nenhuma mecânica foi alterada. O MiMo não recebe autorização para decidir a validade.

O resumo de descanso longo só é retornado quando os fatos validados identificam `action.type: "long_rest"` (ou a forma legacy equivalente) e incluem `long_rest_summary`. HP, recursos recuperados e efeitos encerrados/continuados não são calculados pelo orquestrador.
