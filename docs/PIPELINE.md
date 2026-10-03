# Pipeline

```text
Jogador
   ↓
MJ-D-D-2024 — recebe a fala e classifica a intenção como indicação auxiliar
   ↓
Rule Engine /v1/resolve — chamado para TODA entrada, inclusive diálogo
   ↓
FATOS_RESOLVIDOS validados
   ├── resolved → aplicar somente state_changes autorizados
   ├── narrative_only → fatos={}
   └── precisa validar/erro/contrato inválido → fatos={} e nenhuma mudança mecânica
   ↓
Persistir turno pendente, status e fatos
   ↓
MiMo Proxy /v1/chat/completions — somente narrativa; recebe os fatos válidos ou {}
   ↓
Persistir narrativa concluída ou marcar turno como failed
   ↓
Jogador
```

**Não há atalho do MJ diretamente ao MiMo.** A classificação lexical é apenas registrada como `intent_classification`; ela não determina sucesso, fracasso ou cálculo e não decide se o Rule Engine será chamado. Se o Rule Engine falhar, o turno não é enviado ao narrador e o endpoint retorna erro upstream. Se ele responder `narrative_only`, o MiMo recebe fatos `{}`. Se retornar `needs_rule_validation`, resolução inválida ou fatos malformados, o MiMo também recebe `{}` e o estado mecânico permanece inalterado. Um erro do MiMo deixa um registro de turno `failed`; se a mecânica já foi validada, os fatos e mudanças válidas continuam registrados.

## Ajuda de combate

`GET /v1/campaigns/{id}/assistant` projeta somente `FATOS_RESOLVIDOS.ux_snapshot` do resultado mais recente do Rule Engine. Para liberar opções, o snapshot precisa vir do Rule Engine com `current: true`. Uma tentativa posterior sem resolução confirmada invalida o menu anterior; campos ausentes retornam `null` e o status indica `unavailable`/`incomplete`.

Avisos de ação, ação bônus, reação e movimento são traduções de valores explícitos do snapshot. Custos, explicações, ações disponíveis/indisponíveis, condições, efeitos e recursos são pass-through estruturado. O modo `beginner`, `normal` ou `advanced` muda somente a apresentação; no modo avançado, a descrição fornecida pelo Rule Engine é ocultada.

Feedback de ação inválida é passado do motivo/mensagem do Rule Engine quando presente; caso contrário, o orquestrador comunica apenas que a resolução não ocorreu e que nenhuma mecânica foi alterada. O MiMo não recebe autorização para decidir a validade.

O resumo de descanso longo só é retornado quando os fatos resolvidos identificam `action: "long_rest"` e incluem `long_rest_summary`. HP, recursos recuperados e efeitos encerrados/continuados não são calculados pelo orquestrador.
