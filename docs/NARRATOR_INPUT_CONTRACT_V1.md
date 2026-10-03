# Fronteira de entrada narrativa — `narrator-input-v1`

## Contratos em sequência

```text
mj-rule-state-v1
    ↓ solicitação e estado interno de orquestração
rule-resolution-v1
    ↓ resposta mecânica validada
narrator-input-v1
    ↓ contexto autorizado entregue ao narrador
```

`narrator-input-v1` é um contrato independente; não substitui nem altera as versões dos outros dois. Ele contém `schema_version`, `campaign` (somente `campaign_id`), `player_input`, `scene`, `character_context`, `narrative_context`, `resolved_facts` e `ux_context`. O modelo rejeita versões desconhecidas e campos extras no nível do contrato e na referência de campanha.

## Projeção e contenção

O builder conserva a fala recebida sem reescrevê-la. Da campanha, envia somente o identificador, a cena atual e os campos separados `character_context` e `narrative_context` quando explicitamente presentes. Não busca nem copia automaticamente `character`, `mechanical_state`, `inventory`, `resources`, `npcs`, `history` ou outros dados do banco. A cena é limitada a tipo, descrição, local e participantes; local e participantes aceitam somente campos explicitamente públicos. A descrição da cena e os dois contextos separados devem ser curados como informação que o personagem pode saber ou perceber; segredos não devem ser colocados nesses campos.

`resolved_facts` só é preenchido quando o resultado recebido pelo builder tem status `resolved` e provém do objeto validado pelo contrato `rule-resolution-v1`. Em qualquer outro status, inclusive resolução inválida transformada em fail-closed, `resolved_facts` e `ux_context` são `{}`. O `ux_context` é apenas a cópia do `ux_snapshot` explicitamente validado dentro dos fatos, sem valores padrão nem inferências.

## Compatibilidade do adapter

O adapter envia o objeto `narrator-input-v1` ao endpoint OpenAI-compatible já existente. O prompt local ainda referencia `FATOS_RESOLVIDOS`; por isso, o adapter acrescenta temporariamente um alias com o valor **idêntico** a `resolved_facts`. O prompt e o comportamento do proxy não foram alterados. A migração/remoção desse alias pertence a uma tarefa futura de atualização do prompt.

> `narrator-input-v1` não concede autoridade mecânica ao Mimo-ai.

O Mimo continua sem autoridade para decidir regras, CD, modificadores, rolagens, resultados, dano, cura, condições, duração, custos, disponibilidade mecânica ou mudanças de estado. Os testes locais cobrem o modelo, o builder e a serialização do adapter com mocks; não comprovam integração com o MiMo real.