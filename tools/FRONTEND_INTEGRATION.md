# Integração de frontend

Este guia é independente de framework e hospedagem. O frontend pode ser adicionado em uma pasta deste repositório ou mantido em outro projeto; em ambos os casos, o cliente conversa somente com o MJ-D-D-2024.

## Fluxo

1. Criar/recuperar campanha pela API do MJ.
2. Enviar toda fala do jogador a `POST /v1/campaigns/{id}/turn`.
3. Renderizar a resposta do MJ e o `resolution_status` sem inferir resultados.
4. Ler a projeção de ajuda em `GET /v1/campaigns/{id}/assistant`; manter `null` como desconhecido e não fabricar ações.
5. Alterar somente o modo de explicação via `PATCH /v1/campaigns/{id}/ux-settings`.

## Contrato com o Rule Engine

O adapter do MJ nomeia internamente a entrada `player_input`, mas o contrato existente de `/v1/resolve` espera a chave JSON `action`. Por compatibilidade, o MJ envia a fala original do jogador nesse campo. Não transforme isso em payload estruturado unilateralmente: qualquer schema de ator, alvo, deslocamento, arma e contexto precisa ser versionado e aceito pelo serviço externo.

## Segurança e disponibilidade

A API não implementa autenticação/autorização e o SQLite não é persistente no Render atual. Não exponha dados reais até essas limitações serem corrigidas. Configure CORS somente com a origem da interface. Segredos permanecem no servidor MJ/gerenciador de ambiente; nunca no navegador.

Os testes locais usam mocks. Confirme os endpoints e credenciais reais de Rule Engine/MiMo antes de declarar a integração concluída.
