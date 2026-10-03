# Arquitetura

```text
Jogador → Base44 (interface externa) → MJ-D-D-2024
                                          ↓ interpreta intenção
                                     Rule Engine
                                          ↓ FATOS_RESOLVIDOS
                                      MiMo Proxy
                                          ↓ narração
                                        Jogador
```

O `MJ-D-D-2024` mantém campanhas e coordena os serviços externos. Não replica o Rule Engine nem o MiMo Proxy. Este repositório não contém a interface Base44 e não altera os outros dois serviços.

## Pipeline de turno

1. Receber a intenção e carregar a campanha.
2. Classificar a intenção como indicação auxiliar; essa classificação não escolhe o resultado nem permite pular o próximo passo.
3. Enviar **toda entrada do jogador** ao Rule Engine, inclusive diálogo e ações narrativas.
4. Validar estritamente `FATOS_RESOLVIDOS`; `narrative_only`, resolução ausente, não validada ou malformada produz fatos `{}`. Só fatos validados podem alterar o estado mecânico.
5. Persistir o turno pendente e mudanças que vieram de fatos validados.
6. Enviar ao MiMo o contexto e os fatos validados (ou `{}`); nunca pedir ao narrador que calcule regras.
7. Persistir o texto narrativo ou marcar o turno como falho se o proxy estiver indisponível.

## Camada UX

A camada UX é uma projeção, não uma segunda fonte de verdade. O endpoint de assistência lê o snapshot registrado nos fatos mais recentes do Rule Engine e só apresenta opções quando o snapshot contém `current: true`. Campos ausentes permanecem indisponíveis; listas/custos/avisos não são inventados. O modo iniciante/normal/avançado é metadado de apresentação salvo em `ux_settings`.

A camada aceita dados estruturados para recursos, opções e descanso longo, mas o contrato atual do Rule Engine ainda não confirma esses campos nem define uma consulta em tempo real de disponibilidade. Sem esse suporte, a API responde com status `unavailable` ou `incomplete`. A UI e o ensino progressivo visual ficam no frontend Base44 externo.

## Persistência e implantação

O MVP usa SQLite. PostgreSQL e armazenamento durável no Render não estão implementados/configurados. A implantação pública também exige decidir autenticação e restringir CORS; não foi feito deploy nesta etapa.
