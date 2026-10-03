# Preparação para Render

O projeto inclui um `render.yaml` para criar um serviço Docker, mas **nenhum serviço foi criado ou implantado nesta tarefa**. O deploy deve esperar a configuração dos serviços externos e as decisões de segurança/persistência descritas aqui.

## Antes de publicar

1. Configure `RULE_ENGINE_URL`, `RULE_ENGINE_API_KEY`, `MIMO_URL` e `MIMO_API_KEY` como variáveis privadas do serviço Render. Não coloque chaves no repositório, frontend ou mensagens.
2. Configure `CORS_ORIGIN` para a origem exata do frontend Base44, não `*`.
3. Planeje autenticação de jogador. A API atual não tem autenticação e não é adequada para armazenar campanhas pessoais em um endpoint público.
4. Escolha armazenamento durável. O MVP implementa SQLite; o manifesto não provisiona disco persistente e PostgreSQL ainda não é suportado pelo código. Não use o filesystem efêmero para campanhas que precisem sobreviver a reinício/redeploy.
5. Confirme no painel do Render a disponibilidade e o custo do plano/armazenamento antes de provisionar recursos. Este projeto não provisiona nem compra recursos.

## Variáveis

| Variável | Uso |
|---|---|
| `RULE_ENGINE_URL` | URL base do serviço externo. |
| `RULE_ENGINE_API_KEY` | Enviada como header `X-API-Key`. |
| `MIMO_URL` | URL base do MiMo Proxy externo. |
| `MIMO_API_KEY` | Enviada como `Authorization: Bearer`. |
| `DATABASE_URL` | Atualmente aceita somente `sqlite:///...`; persistência durável precisa ser planejada separadamente. |
| `CORS_ORIGIN` | Uma ou mais origens separadas por vírgula; use a origem do Base44. |
| `PORT` | Injetada pelo Render; o Dockerfile usa `8000` como fallback local. |

## Testes de integração reais obrigatórios

Depois de inserir as URLs e credenciais no Render, teste os dois serviços reais, sem copiar segredos para o repositório:

```bash
curl -fsS "$RULE_ENGINE_URL/health" \
  -H "X-API-Key: $RULE_ENGINE_API_KEY"

curl -fsS "$MIMO_URL/health" \
  -H "Authorization: Bearer $MIMO_API_KEY"
```

Em seguida, valide `POST $RULE_ENGINE_URL/v1/resolve` com um payload e uma regra de teste confirmados pelo contrato real do Rule Engine. Não use um resultado inventado como prova. Teste `POST $MIMO_URL/v1/chat/completions` com `stream: false` e confirme o schema/retorno. Por fim, faça um turno real pelo MJ-D-D-2024 e confira o fail-closed com uma ação ainda não validada. Registre os códigos HTTP, os status e a data do teste, sem registrar valores de API keys.

O `/health` do MJ-D-D-2024 verifica somente a aplicação local; ele não comprova a saúde dos dois serviços externos.
