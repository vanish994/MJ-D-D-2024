# BUILD SPEC — MJ-D-D-2024

## Objetivo

Construir um RPG solo pessoal baseado em D&D 2024, mantendo separação rígida entre estado, mecânica determinística e narrativa.

## Repositórios existentes

### Rule Engine
`https://github.com/vanish994/dnd-byonder-backend`

Já possui SQLite/FTS5, `/health`, `/v1/rules/search`, `/v1/rules/context`, `/v1/resolve`, contrato `FATOS_RESOLVIDOS` e configuração Render.

IMPORTANTE: `/v1/resolve` atualmente retorna `needs_rule_validation`. Nunca inventar resultados.

### MiMo Proxy
`https://github.com/pedrofariasx/mimo-ai-proxy`

Já possui `/v1/chat/completions`, `/v1/models`, `/health`, API key, histórico SQLite, streaming e gateway OpenAI-compatible.

Não reimplementar o proxy.

## Stack

- Python 3.11+
- FastAPI
- Pydantic
- HTTPX
- SQLite no MVP
- PostgreSQL preparado para produção
- Docker
- Render

## Estrutura

```text
app/
  main.py
  config.py
  models.py
  api/
    campaigns.py
    turns.py
  services/
    campaign_service.py
    rule_engine_client.py
    mimo_client.py
    turn_service.py
    dice.py
  prompts/
    narrator.md
  storage/
    db.py
```

## Estado

Campanha:
- id
- nome
- personagem
- cena
- NPCs
- estado mecânico
- inventário
- recursos
- histórico resumido
- timestamps

Não armazenar texto integral de livros na campanha.

## Mecânica

O Rule Engine é a autoridade para d20, modificadores, proficiência, ataques, dano, testes, salvaguardas, vantagem/desvantagem, iniciativa, AC, HP, condições, ações/bônus/reação, movimento, descanso, concentração, magia e recursos.

Só habilitar uma mecânica depois de regra validada + teste determinístico.

## Dados aleatórios

Nunca deixar o LLM gerar uma rolagem. Use `secrets.randbelow()` ou equivalente. Registrar fórmula, dados, modificador e total.

## FATOS_RESOLVIDOS

```json
{
  "resolution_id": "res_x",
  "status": "resolved",
  "action": "attack_roll",
  "outcome": "hit",
  "rolls": [],
  "damage": null,
  "conditions_applied": [],
  "state_changes": [],
  "rules_used": []
}
```

Sem regra validada:

```json
{"status":"needs_rule_validation"}
```

O narrador deve receber `{}` quando não houver resolução.

## Narrador

O narrador descreve cenas e interpreta NPCs. Não rola, calcula bônus/dano/HP/CA, decide acerto/erro ou cria mudanças mecânicas.

## API

`POST /v1/campaigns`

`GET /v1/campaigns/{id}`

`POST /v1/campaigns/{id}/turn`

Turno:

```json
{"player_input":"Eu abro a porta.","stream":false}
```

## Variáveis

```env
RULE_ENGINE_URL=https://...
RULE_ENGINE_API_KEY=...
MIMO_URL=https://...
MIMO_API_KEY=...
DATABASE_URL=sqlite:///./data/campaigns.db
CORS_ORIGIN=*
PORT=8000
```

## Critério de conclusão

1. Criar campanha.
2. Receber intenção.
3. Consultar mecânica quando necessário.
4. Produzir FATOS_RESOLVIDOS.
5. Persistir estado.
6. Enviar fatos ao narrador.
7. Retornar narrativa.
8. Nunca inventar resolução mecânica ausente.
