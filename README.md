# MJ-D-D-2024 — D&D Byonder Solo

Orquestrador backend para uma campanha solo de D&D 2024, com separação entre regras, estado e narrativa.

**Estado:** o MVP está commitado e enviado à branch `feat/mj-dnd-2024-mvp`; o PR #1 está aberto como draft. Os 47 testes são locais/simulados. Não houve deploy nem teste contra os serviços reais. O frontend não faz parte desta implementação e pode ser desenvolvido neste repositório ou decidido separadamente.

## Arquitetura

```text
Jogador → Frontend → MJ-D-D-2024
                         ↓ interpreta intenção
                    Rule Engine externo
                         ↓ FATOS_RESOLVIDOS
                     MiMo Proxy externo
                         ↓ narração
                       Jogador
```

**Toda entrada do jogador passa pelo Rule Engine antes do MiMo.** O rótulo lexical do MJ é apenas metadado; não decide resultado nem pula o Rule Engine. O MJ aplica somente `state_changes` presentes em `FATOS_RESOLVIDOS` validados. O MiMo recebe fatos validados ou `{}` e não rola dados, calcula dano/CD, aplica regras ou altera o estado.

A revisão recebida junto ao projeto informa que o `/v1/resolve` atual do serviço externo é deliberadamente fail-closed e retorna `needs_rule_validation` com fatos vazios. Portanto, as mecânicas reais ainda não estão jogáveis; o MJ não deve mascarar essa limitação narrando resultados como sucesso ou fracasso. Esta informação não foi revalidada por uma chamada HTTP real nesta etapa; veja `docs/INTEGRATION_STATUS.md`.

## Executar e testar localmente

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # preencha somente valores de desenvolvimento; não versione segredos
uvicorn app.main:app --reload --port 8000
```

Em outro terminal:

```bash
python -m unittest discover -s tests -v
```

Os testes substituem os serviços externos por mocks. Eles validam o comportamento local e não comprovam a integração real.

## Endpoints do MJ-D-D-2024

| Método | Rota | Uso |
|---|---|---|
| `GET` | `/health` | Saúde do MJ; não verifica dependências externas. |
| `POST` | `/v1/campaigns` | Criar campanha. |
| `GET` | `/v1/campaigns/{id}` | Ler campanha. |
| `POST` | `/v1/campaigns/{id}/turn` | Enviar a fala; o MJ chama Rule Engine antes do MiMo. `stream=true` retorna `501` neste MVP. |
| `POST` | `/v1/rules/search` | Encaminhar busca ao serviço externo. |
| `GET` | `/v1/campaigns/{id}/assistant` | Projetar dados UX somente de snapshot atual explicitamente fornecido pelo Rule Engine. Campos ausentes permanecem `null`/indisponíveis. |
| `PATCH` | `/v1/campaigns/{id}/ux-settings` | Alterar apenas o modo de apresentação (`beginner`, `normal`, `advanced`). |

## Contrato em transição

O adapter interno recebe `player_input`, mas o endpoint externo atual `/v1/resolve` usa a chave JSON `action`; por compatibilidade, o MJ envia a fala original nessa chave. Não há ainda um parser de intenção estruturada (ator, alvo, movimento, arma, contexto) acordado com o Rule Engine. Criar esse formato exigirá uma versão compatível do contrato externo; não é seguro alterar apenas um lado. Qualquer interpretação deve acontecer no MJ/Rule Engine, nunca no MiMo.

O snapshot UX (`ux_snapshot`) e o resumo de descanso longo (`long_rest_summary`) só são exibidos quando estruturados nos fatos confiáveis. O Rule Engine ainda não confirmou esse schema nem forneceu esses dados na integração real.

## Configuração, persistência e segurança

As URLs e credenciais são variáveis de ambiente. `RULE_ENGINE_API_KEY` é enviada como `X-API-Key`; `MIMO_API_KEY`, como `Authorization: Bearer`. Não inclua credenciais no frontend, Git ou mensagens. Consulte `docs/DEPLOY_RENDER.md`.

O armazenamento implementado é SQLite. PostgreSQL e persistência durável no Render não estão implementados. A API também não possui autenticação/autorização de jogador; não exponha campanhas reais em uma instância pública até resolver esses pontos e restringir CORS à origem escolhida para o frontend.

## Documentação

- `docs/BUILD_SPEC.md`: especificação funcional recebida no ZIP.
- `docs/PIPELINE.md`: fluxo operacional, incluindo fail-closed.
- `docs/INTEGRATION_STATUS.md`: diferença entre testes simulados e integração real.
- `docs/CODE_REVIEW.md`: achados e limitações.
- `docs/UX_BEGINNER_SPEC.md`: especificação UX recebida.
- `tools/FRONTEND_PROMPT.md` e `tools/FRONTEND_INTEGRATION.md`: orientação provider-agnostic para uma futura interface.
