# Arquitetura

```text
Jogador → Frontend → MJ-D-D-2024
                         ↓ interpreta intenção
                    Rule Engine externo
                         ↓ FATOS_RESOLVIDOS
                     MiMo Proxy externo
                         ↓ narração
                       Jogador
```

O `MJ-D-D-2024` mantém campanhas, estado, orquestração, adapters e orientação do jogador. O frontend pode ser criado dentro deste repositório ou definido separadamente; nenhum provedor específico de frontend é requisito. `dnd-byonder-backend` (Rule Engine) e `mimo-ai-proxy` continuam dependências externas e não são modificados pelo projeto MJ.

## Pipeline de turno

1. Receber a fala e carregar a campanha.
2. Classificar a intenção como indicação auxiliar; a classificação não escolhe o resultado nem permite pular o Rule Engine.
3. Enviar toda entrada do jogador ao Rule Engine, inclusive diálogo.
4. Validar estritamente `FATOS_RESOLVIDOS`; `narrative_only`, resolução ausente, não validada ou malformada produz fatos `{}`. Só fatos validados podem alterar o estado mecânico.
5. Persistir o turno pendente e mudanças que vieram de fatos validados.
6. Enviar ao MiMo o contexto e os fatos validados (ou `{}`); nunca pedir ao narrador que calcule regras.
7. Persistir a narração ou marcar o turno como falho se o proxy estiver indisponível.

## Contrato do Rule Engine

O adapter MJ nomeia a entrada como `player_input`; o endpoint externo existente ainda recebe `action`, e o MJ envia a fala original nesse campo para manter compatibilidade. Isso não constitui uma interpretação estruturada. Os campos ator, alvo, movimento, arma, contexto e mecânicas solicitadas precisam de um contrato versionado e acordado com o serviço externo antes de serem enviados.

A revisão recebida indica que o `/v1/resolve` externo atualmente responde `needs_rule_validation` e fatos vazios de forma deliberada. O MJ conserva esse fail-closed; mecânicas jogáveis dependem de uma etapa separada no serviço de regras. Nenhum cálculo mecânico é implementado no narrador.

## Camada UX

A camada UX é uma projeção, não uma segunda fonte de verdade. O endpoint de assistência lê o snapshot nos fatos mais recentes e só apresenta opções quando contém `current: true`. Dados ausentes permanecem indisponíveis. O contrato externo ainda não confirma o schema de disponibilidade, custos, recursos, efeitos ou descanso longo; enquanto isso não existir, a projeção permanece limitada.

## Persistência e implantação

O MVP usa SQLite. PostgreSQL e armazenamento durável no Render não estão implementados/configurados. A API ainda não oferece autenticação de jogador; nenhuma implantação pública foi feita.
