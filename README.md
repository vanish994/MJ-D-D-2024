# MJ-D-D-2024 — D&D Byonder Solo

Orquestrador backend para uma campanha solo de D&D 2024, com separação entre regras, estado e narrativa.

**Estado atual:** implementação local preparada para revisão e publicação em PR. Os testes são unitários e simulam os serviços externos; nenhuma integração real ou implantação no Render foi executada. O frontend Base44 não está neste repositório.

## Arquitetura

```text
Jogador → Base44 → MJ-D-D-2024
                       ↓ interpreta intenção
                  Rule Engine
                       ↓ FATOS_RESOLVIDOS (ou {} sem resolução mecânica)
                   MiMo Proxy
                       ↓ narração
                    Jogador
```

**Toda entrada do jogador passa primeiro pelo Rule Engine e só então pelo MiMo.** O rótulo lexical do MJ é apenas metadado; nunca pula essa chamada nem determina resultado. O Rule Engine é a única autoridade mecânica. O MiMo recebe `FATOS_RESOLVIDOS` validados e nunca deve decidir rolagens, custos, sucesso, dano, recursos ou mudanças de estado. Para `narrative_only` ou qualquer resolução não validada, o orquestrador envia `{}` ao narrador e não aplica mudanças mecânicas.

## Executar e testar localmente

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # preencha apenas o que for usar; não versione segredos
uvicorn app.main:app --reload --port 8000
```

Em outro terminal, execute os testes (todos os clientes externos são simulados):

```bash
python -m unittest discover -s tests -v
```

## Endpoints do orquestrador

| Método | Rota | Uso |
|---|---|---|
| `GET` | `/health` | Saúde do próprio MJ-D-D-2024; não verifica dependências externas. |
| `POST` | `/v1/campaigns` | Criar campanha. |
| `GET` | `/v1/campaigns/{id}` | Ler campanha. |
| `POST` | `/v1/campaigns/{id}/turn` | Processar turno; `stream=true` retorna `501` neste MVP. |
| `POST` | `/v1/rules/search` | Encaminhar busca ao Rule Engine. |
| `GET` | `/v1/campaigns/{id}/assistant` | Projetar o snapshot UX mais recente, somente se o Rule Engine o tiver marcado como atual. Sem snapshot, opções e recursos retornam `null`, não listas vazias que possam ser confundidas com “nenhuma”. |
| `PATCH` | `/v1/campaigns/{id}/ux-settings` | Alterar `explanation_mode`: `beginner`, `normal` ou `advanced`. É uma preferência de apresentação, não um estado mecânico. |

O snapshot UX é um contrato opcional aceito em `FATOS_RESOLVIDOS.ux_snapshot`. Custos, listas de ações, recursos, efeitos e explicações só são apresentados se vierem estruturados do Rule Engine. O resumo de descanso longo também só é apresentado a partir de `long_rest_summary` retornado pelo serviço. O motivo de ação inválida é repassado somente quando o Rule Engine o fornece.

## Configuração de serviços

As URLs e credenciais são variáveis de ambiente. `RULE_ENGINE_API_KEY` é enviada como `X-API-Key`; `MIMO_API_KEY`, como `Authorization: Bearer`. Não inclua credenciais no frontend, no Git ou em mensagens. No Render, configure-as como variáveis secretas do serviço.

O armazenamento implementado é SQLite. PostgreSQL ainda não foi implementado. O manifesto Render não cria disco persistente; portanto, o SQLite no filesystem efêmero não deve ser usado para campanhas que precisem sobreviver a reinícios. Verifique [o guia de implantação](docs/DEPLOY_RENDER.md) antes de publicar.

## Limitações e segurança antes de uso público

A API ainda não implementa autenticação de jogador e o arquivo `.env.example` usa CORS permissivo para desenvolvimento local. Não publique dados de campanha em uma instância pública antes de implementar autenticação e restringir CORS ao domínio do frontend. O classificador de intenção é lexical e heurístico, mas apenas registra uma indicação; todas as entradas chamam o Rule Engine independentemente desse rótulo.

O contrato atual documentado para o Rule Engine não define uma consulta estruturada de ações disponíveis e recursos do turno. A camada UX, portanto, falha de forma segura até receber um snapshot explicitamente atual; ela não inventa ações, alcance, movimento, recuperação ou duração. A interface Base44 e o ensino progressivo visual dependem de acesso ao frontend, que não está presente aqui.

Consulte `docs/INTEGRATION_STATUS.md` para distinguir o que foi testado com mocks do que ainda depende dos serviços reais. A especificação UX recebida está preservada em `docs/UX_BEGINNER_SPEC.md`.
