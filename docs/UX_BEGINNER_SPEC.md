NOVA TAREFA — CAMADA DE UX PARA INICIANTES DE D&D 2024

Continue o projeto atual MJ-D-D-2024 exatamente de onde ele está.
NÃO recrie o projeto e NÃO altere os repositórios:
- dnd-byonder-backend
- mimo-ai-proxy

Objetivo:
Transformar o MJ-D-D-2024 em um jogo solo de D&D 2024 que também ensine o jogador a jogar, mesmo que ele nunca tenha jogado D&D.

A implementação deve ser uma camada de UX/assistência sobre o Rule Engine existente.

==================================================
1. PRINCÍPIO FUNDAMENTAL
==================================================

Separação obrigatória:

RULE ENGINE
→ única autoridade sobre regras e mecânicas.

ORQUESTRADOR
→ coordena estado, intenção, resolução e narrativa.

UX ASSISTANT
→ explica ao jogador o que ele pode fazer e por quê.

MIMO
→ somente narrativa, NPCs, descrição de cenas e consequências narrativas.

O UX Assistant NÃO pode inventar regras.

O MIMO NÃO pode decidir:
- resultado de ataque
- dano
- sucesso/falha mecânica
- custo de ação
- recuperação de recursos
- duração de efeitos
- condições
- qualquer outro resultado mecânico.

==================================================
2. "O QUE POSSO FAZER?"
==================================================

Adicionar ao combate uma função/botão:

"O que posso fazer?"

Ela deve consultar o estado atual do personagem e apresentar as opções válidas.

Exemplo:

SEU TURNO

Movimento
• Até X pés

Ação
• Atacar
• Correr
• Desengajar
• Esquivar
• Ajudar
• Preparar
• Procurar
• Usar objeto
• Outras ações disponíveis

Ação Bônus
• [somente opções realmente disponíveis]

Reação
• [somente opções realmente disponíveis]

Não mostrar opções que o personagem não possa realizar naquele estado,
quando o Rule Engine conseguir determinar isso.

==================================================
3. CUSTO DE CADA AÇÃO
==================================================

Mostrar claramente o custo:

⚔️ Atacar — Ação

🏃 Correr — Ação

🛡️ Esquivar — Ação

✨ [habilidade] — Ação Bônus

↩️ [reação disponível] — Reação

Movimento — Movimento

Isso deve ser derivado de dados estruturados do Rule Engine/personagem,
não inventado pelo modelo.

==================================================
4. EXPLICAÇÃO PARA INICIANTES
==================================================

Criar três níveis de explicação:

MODO INICIANTE
→ linguagem simples
→ pequenas explicações sobre cada opção
→ explicar termos de D&D quando necessário

MODO NORMAL
→ mostrar opções + custo
→ explicações apenas quando relevantes

MODO AVANÇADO
→ interface mais compacta
→ detalhes mecânicos disponíveis sob demanda

O jogador deve poder alterar o modo nas configurações.

==================================================
5. AVISOS INTELIGENTES
==================================================

O sistema deve avisar quando uma ação possui uma consequência
ou quando um recurso importante está disponível.

Exemplos:

"Você ainda possui uma Ação Bônus neste turno."

"Você já usou sua Ação Bônus neste turno."

"Você ainda possui uma Reação."

"Você já utilizou sua Reação."

"Seu Movimento ainda não foi totalmente utilizado."

NÃO bombardear o jogador com mensagens.

Mostrar somente avisos relevantes.

==================================================
6. AÇÃO INVÁLIDA
==================================================

Quando o jogador tentar algo que não pode fazer:

NÃO simplesmente retornar erro.

Explicar de forma amigável.

Exemplo:

"Você não pode usar essa habilidade agora porque ela exige uma
Ação Bônus e sua Ação Bônus já foi utilizada neste turno."

Ou:

"Você não pode realizar essa ação porque não possui o recurso necessário."

A explicação deve ser baseada no motivo retornado pelo Rule Engine.

==================================================
7. DESCANSO LONGO
==================================================

Depois de um descanso longo, criar um resumo visual:

🌙 DESCANSO LONGO CONCLUÍDO

❤️ Pontos de Vida:
[resultado]

✨ Recursos recuperados:
[lista]

🧹 Efeitos encerrados:
[lista]

⏳ Efeitos que continuam:
[lista]

O resumo deve ser produzido a partir do resultado mecânico do Rule Engine.

Não inferir que uma condição, magia ou efeito terminou apenas porque
o modelo narrativo acha que deveria terminar.

==================================================
8. ESTADO NECESSÁRIO
==================================================

Verificar se o estado persistente da campanha atualmente contém
informações suficientes para a UX.

No mínimo considerar:

- HP atual/máximo
- condições
- efeitos ativos
- duração dos efeitos
- concentração quando aplicável
- ações disponíveis
- ação bônus disponível
- reação disponível
- movimento restante
- recursos de classe
- recursos de personagem
- inventário relevante
- posição quando necessária
- turno/rodada
- estado de combate

Se algum desses dados ainda não existir no modelo atual,
implementar a estrutura necessária no MJ-D-D-2024.

Não inventar valores padrão que possam alterar a mecânica.

==================================================
9. CONTRATO ESTRUTURADO
==================================================

Sempre que possível, criar uma estrutura semelhante a:

{
  "turn_resources": {
    "action": true,
    "bonus_action": true,
    "reaction": true,
    "movement_remaining": 30
  },
  "available_actions": [],
  "available_bonus_actions": [],
  "available_reactions": [],
  "unavailable_actions": [
    {
      "name": "...",
      "reason": "..."
    }
  ],
  "active_effects": [],
  "conditions": []
}

IMPORTANTE:

Esse exemplo é apenas um contrato de referência.

Antes de implementá-lo, analisar os modelos atuais do projeto e integrar
com a arquitetura existente em vez de criar uma segunda fonte de verdade.

==================================================
10. COMBATE — INTERFACE
==================================================

A interface deve deixar visualmente claro:

┌──────────────────────────────┐
│ SEU TURNO                    │
│                              │
│ Movimento: 30 ft             │
│ Ação: disponível             │
│ Ação Bônus: disponível       │
│ Reação: disponível           │
│                              │
│ [⚔️ Atacar]                  │
│ [✨ Habilidades]             │
│ [🛡️ Outras ações]            │
│ [💡 O que posso fazer?]      │
└──────────────────────────────┘

Adaptar o design ao frontend existente.

Não criar uma interface completamente separada se já existir uma UI
de combate/campanha.

==================================================
11. ENSINO PROGRESSIVO
==================================================

Não mostrar todas as regras para um iniciante de uma vez.

Exemplo:

Primeiro combate:
"Você tem uma Ação. Uma das coisas que pode fazer é atacar."

Ao passar o mouse/tocar:

"Atacar usa sua Ação."

Quando aparecer Ação Bônus pela primeira vez:

"Ação Bônus é um tipo especial de ação que algumas habilidades usam.
Você pode ter no máximo uma por turno."

O sistema deve ensinar conforme o jogador encontra as mecânicas.

Não transformar o jogo em um tutorial obrigatório.

==================================================
12. TESTES
==================================================

Criar testes para pelo menos:

1. Personagem com Ação disponível.
2. Personagem sem Ação.
3. Personagem com Ação Bônus disponível.
4. Personagem sem Ação Bônus.
5. Personagem com Reação disponível.
6. Personagem sem Reação.
7. Movimento restante.
8. Tentativa de ação inválida.
9. Descanso longo recuperando recursos.
10. Descanso longo encerrando efeitos.
11. Descanso longo mantendo efeitos que não terminam.
12. "O que posso fazer?" refletindo corretamente o estado atual.

Os testes devem verificar que a UX não inventa mecânicas.

==================================================
13. NÃO FAZER
==================================================

NÃO:

- colocar regras dentro do prompt do Mimo;
- deixar o LLM decidir quais ações são válidas;
- gerar dados pelo LLM;
- duplicar o Rule Engine;
- alterar dnd-byonder-backend;
- alterar mimo-ai-proxy;
- transformar automaticamente os 15.716 rule candidates em regras;
- considerar mocks como integração real;
- copiar textos completos dos livros de D&D.

==================================================
14. ORDEM DE IMPLEMENTAÇÃO
==================================================

1. Inspecionar o estado atual do MJ-D-D-2024.
2. Identificar onde o estado de combate é armazenado.
3. Identificar o contrato atual entre MJ-D-D-2024 e Rule Engine.
4. Criar/adaptar o modelo estruturado de recursos do turno.
5. Implementar "O que posso fazer?".
6. Implementar avisos contextuais.
7. Implementar explicação de ações inválidas.
8. Implementar resumo de descanso longo.
9. Implementar modos iniciante/normal/avançado.
10. Criar testes.
11. Executar os testes com mocks.
12. Não declarar integração real concluída até existirem URLs/chaves reais.

Antes de modificar estruturas existentes, explique no relatório quais arquivos
serão alterados e por quê.

Ao finalizar, retornar:

- arquivos modificados;
- novas estruturas criadas;
- testes adicionados;
- resultado dos testes;
- limitações atuais;
- quais partes ainda dependem do Rule Engine real;
- quais partes ainda dependem da integração real com MiMo.