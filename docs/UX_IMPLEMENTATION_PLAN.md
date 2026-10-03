# Plano de implementação — UX para iniciantes

## Intenção

Adicionar ao backend `MJ-D-D-2024` uma camada de apresentação/assistência configurável que possa explicar o estado do jogo sem se tornar uma fonte de regras. A interface Base44 permanece externa; este repositório não contém o frontend.

## Arquivos previstos e motivo

- `docs/UX_BEGINNER_SPEC.md`: preservar integralmente a nova especificação recebida.
- `app/models.py`: definir estruturas opcionais e validadas para o snapshot de combate e os três modos de explicação. Campos mecânicos ausentes permanecem `null`/indisponíveis; nenhum valor padrão de regra será criado.
- `app/services/ux_assistant.py` (novo): projetar somente dados estruturados fornecidos pelo Rule Engine; formatar avisos, opções e resumo de descanso apenas quando houver fonte explícita. Não calcular disponibilidade, custos, movimento, recuperação nem duração.
- `app/api/ux.py` (novo) e `app/main.py`: expor uma leitura da projeção para Base44 e uma atualização da preferência de modo, sem permitir que a UI altere o estado mecânico.
- `app/api/campaigns.py`: inicializar apenas a preferência de apresentação do modo iniciante; isso não define estado de jogo.
- `app/services/turn_service.py` e `app/api/turns.py`: manter o fail-closed, registrar motivo de recusa somente quando retornado pelo Rule Engine e expor resumo de descanso somente se o serviço entregar os dados estruturados.
- `tests/test_ux_assistant.py` e `tests/test_api.py`: cobrir recursos disponíveis/indisponíveis, movimento, ação inválida, descanso longo, modos e estados ausentes com dados simulados.
- `README.md` e `docs/INTEGRATION_STATUS.md`: documentar limitações, setup e a diferença entre mocks e validação real.

## Limites conhecidos

O contrato atual documentado no ZIP não define uma operação do Rule Engine para consultar, em tempo real, a lista de ações válidas, recursos do turno ou estado de descanso longo. Assim, a projeção não inventará nem apresentará opções como atuais sem um snapshot explícito e marcado como atual pelo Rule Engine. O repositório também não contém o frontend Base44, então nenhum botão/UI será criado aqui.

Os mocks validam somente o contrato local. A integração só poderá ser considerada real depois da configuração de URLs e credenciais e de testes contra `/health`, `/v1/resolve` e `/v1/chat/completions` nos serviços reais. Nenhum arquivo de `dnd-byonder-backend` ou `mimo-ai-proxy` será modificado.
