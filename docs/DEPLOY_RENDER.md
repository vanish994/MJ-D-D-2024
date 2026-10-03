# Preparação para Render

O projeto inclui `render.yaml` para criar um serviço Docker, mas **nenhum serviço foi criado ou implantado**. O manifesto é apenas preparação; deploy e integração real são etapas separadas.

## Antes de publicar

1. Configure `RULE_ENGINE_URL`, `RULE_ENGINE_API_KEY`, `MIMO_URL` e `MIMO_API_KEY` como variáveis privadas do serviço. Não coloque chaves no repositório, frontend ou mensagens.
2. Configure `CORS_ORIGIN` para a origem exata do frontend escolhido, não `*`.
3. Implemente autenticação/autorização de jogador. A API atual não tem autenticação e não deve armazenar campanhas pessoais em endpoint público.
4. Escolha persistência durável. O MVP implementa SQLite; o manifesto não provisiona disco persistente e PostgreSQL não é suportado pelo código. Não use filesystem efêmero para campanhas que devam sobreviver a reinícios.
5. Confira no painel do Render disponibilidade e custo de plano/armazenamento antes de provisionar recursos.

## Variáveis

| Variável | Uso |
|---|---|
| `RULE_ENGINE_URL` | URL base do Rule Engine externo. |
| `RULE_ENGINE_API_KEY` | Enviada como `X-API-Key`. |
| `MIMO_URL` | URL base do MiMo Proxy externo. |
| `MIMO_API_KEY` | Enviada como `Authorization: Bearer`. |
| `DATABASE_URL` | Atualmente aceita somente `sqlite:///...`; planejar durabilidade separadamente. |
| `CORS_ORIGIN` | Uma ou mais origens do frontend, separadas por vírgula. |
| `PORT` | Injetada pelo Render; `8000` é o fallback local. |

## Testes reais obrigatórios

Após inserir URLs e credenciais diretamente nas configurações privadas do Render, teste os serviços reais sem copiar segredos para o repositório:

```bash
curl -fsS "$RULE_ENGINE_URL/health" \
  -H "X-API-Key: $RULE_ENGINE_API_KEY"

curl -fsS "$MIMO_URL/health" \
  -H "Authorization: Bearer $MIMO_API_KEY"
```

Depois, valide `POST $RULE_ENGINE_URL/v1/resolve` com diálogo e ações aprovadas pelo contrato real. Teste `POST $MIMO_URL/v1/chat/completions` com `stream: false` e confirme o schema/retorno. Faça um turno pelo MJ e verifique fail-closed para fatos não resolvidos. Registre status e data sem registrar API keys.

`GET /health` do MJ verifica somente a aplicação local; não comprova a saúde dos serviços externos.
