# Plano de implementação — UX para iniciantes

## Intenção

Adicionar ao backend `MJ-D-D-2024` uma camada de apresentação/assistência configurável que explique apenas dados confiáveis do estado do jogo, sem se tornar uma fonte de regras. O frontend ainda não foi implementado; ele pode ser criado neste repositório ou definido separadamente, sem dependência de um fornecedor específico.

## Entregue no backend

- `docs/UX_BEGINNER_SPEC.md`: preserva a especificação UX recebida.
- `app/models.py`: estruturas validadas para snapshots e modos; campos ausentes permanecem indisponíveis.
- `app/services/ux_assistant.py`: projeção somente de dados do Rule Engine; não calcula disponibilidade, custos, movimento, recuperação ou duração.
- `app/api/ux.py` e `app/main.py`: endpoints de projeção e preferência, sem permitir que a interface altere o estado mecânico.
- `app/services/turn_service.py` e `app/api/turns.py`: fail-closed, passagem de feedback somente do Rule Engine e resumo de descanso somente quando estruturado.
- Testes de recursos, movimento, ação inválida, descanso, modos e dados ausentes usando mocks.

## Limites

O contrato atual do Rule Engine não define uma operação real para consultar opções válidas, recursos do turno ou duração de efeitos. A camada não inventa esses valores e exige snapshot explícito marcado como atual. Como o `/v1/resolve` está atualmente fail-closed segundo a revisão recebida, a UX de combate não estará funcional até existir suporte real no motor de regras.

Os mocks validam somente o contrato local. Integração real depende de URLs/credenciais e chamadas a `/health`, `/v1/resolve` e `/v1/chat/completions`. Nenhum repositório de serviço externo foi modificado; nenhuma implantação foi feita.
