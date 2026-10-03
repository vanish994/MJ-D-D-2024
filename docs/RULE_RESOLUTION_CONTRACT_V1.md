# Contrato de resposta do Rule Engine — `rule-resolution-v1`

## Escopo

Este contrato valida **a resposta** de `POST /v1/resolve`. Ele é separado do envelope de entrada local `mj-rule-state-v1`, enviado no campo externo `state`. O adapter continua enviando `{ "action": <fala>, "state": <envelope>, "rule_ids": [] }`; esta implementação não altera o endpoint nem afirma que o serviço externo já produz respostas V1.

O contrato valida e projeta dados; **não implementa regras, testes, RNG, dano, CDs, combate ou personagem**.

## Resposta versionada

```json
{
  "schema_version": "rule-resolution-v1",
  "resolution_id": "res_123",
  "status": "resolved",
  "action": { "type": "ability_check", "actor_id": "character_001" },
  "request": { "player_input": "Eu tento abrir a porta." },
  "check": { "ability": "strength", "skill": null, "dc": 15, "modifier": 3 },
  "rolls": [{ "type": "d20", "result": 14 }],
  "outcome": { "success": true, "total": 17 },
  "facts_resolvidos": {},
  "state_changes": {},
  "rules_used": [],
  "ux_snapshot": {},
  "long_rest_summary": null
}
```

Os campos além de `schema_version` e `status` são opcionais. O consumidor não os preenche com defaults que representem fatos mecânicos. Um objeto `facts_resolvidos` não vazio precisa satisfazer o schema conhecido do MJ e declarar `status: "resolved"`; `{}` significa que não há fatos aninhados adicionais.

Um status pendente versionado também pode ser mínimo e não exige `outcome`:

```json
{
  "schema_version": "rule-resolution-v1",
  "status": "needs_rule_validation"
}
```

### Status aceitos

- `needs_rule_validation`
- `awaiting_input`
- `awaiting_roll`
- `resolved`
- `invalid_action`
- `rule_not_found`

Um status diferente, versão diferente, propriedade não reconhecida, estrutura/tipo inválido ou payload acima do limite é tratado como resposta inválida.

## Compatibilidade com o Rule Engine atual

O único formato sem `schema_version` aceito é o legado mínimo:

```json
{ "status": "needs_rule_validation" }
```

Somente esse objeto mínimo é aceito sem versão; qualquer campo adicional em resposta legacy falha fechado. Nenhum status legacy `resolved` é aceito sem versão. O backend atual pode responder nesse formato mínimo; a exceção não representa suporte ao contrato V1 nem integração real concluída.

## Autorização e fail-closed

1. **Somente `status: "resolved"`** pode autorizar fatos, `state_changes`, `rules_used`, `ux_snapshot` ou `long_rest_summary`.
2. Em qualquer outro status, esses campos são descartados. O MJ envia `FATOS_RESOLVIDOS: {}` ao MiMo e não altera o estado, mesmo que a resposta inclua campos contraditórios.
3. Uma resposta `resolved` que falhe em qualquer validação inteira também falha fechada: status efetivo `needs_rule_validation`, fatos `{}` e nenhuma mudança de estado.
4. Para uma resposta válida `resolved`, o MJ projeta para o narrador apenas campos validados do resultado. `request`, `reason` e `message` não são copiados para `FATOS_RESOLVIDOS`; a fala do jogador já é enviada separadamente.
5. `state_changes` é aplicado separadamente da projeção narrativa e somente depois da validação. Aceita um objeto com no máximo 32 chaves seguras e valores escalares JSON (`string`, `number`, `boolean` ou `null`); objetos/listas aninhados e chaves fora do padrão são rejeitados. O formato legado de lista `{key, value}` dentro de `facts_resolvidos` é validado e normalizado; se conflitar com o objeto top-level, o resultado inteiro falha fechado.
6. `ux_snapshot` e `long_rest_summary` passam pelos schemas UX existentes antes de serem projetados. Não são inferidos pelo MJ.

O contrato rejeita campos extras (`extra="forbid"`) e tipos coercivos. Os limites atuais são 50 KB para a resposta e 100 referências em `rules_used`.

## Projeção para o MiMo

- Status não resolvido ou resposta inválida: `{}` exatamente.
- Status `resolved`: projeção normalizada dos campos validados (`schema_version`, `status`, ação, teste, rolagens, resultado, fatos aninhados, alterações autorizadas, referências e snapshots presentes).
- A entrada original e texto de erro do upstream não são incorporados à projeção.

O MiMo continua sendo somente narrador. O prompt local proíbe rolar dados, calcular dano/CD, decidir sucesso, aplicar regras ou alterar estado; uma resposta validada do Rule Engine é a única origem de fatos mecânicos.

Resultados de busca na Knowledge Base são evidências ou candidatos para interpretação humana/etapas futuras; **não se tornam automaticamente regras executáveis** nem autorizam mudanças de estado por si só.

## Validação local e integração real

Os testes desta mudança são unitários/de integração simulada. Eles cobrem payloads versionados, status, compatibilidade legacy mínima, rejeição de tipos/campos/estruturas inválidos, ausência de mutação para status não resolvidos e projeção ao MiMo. **Não provam que os serviços reais implementam o contrato.** A validação ponta a ponta ainda depende de URL/credenciais reais e de testes HTTP autorizados com `/health`, `/v1/resolve` e `/v1/chat/completions`.
