Você está implementando o backend MJ-D-D-2024.

Use todos os arquivos deste pacote como especificação.

OBJETIVO:
Construir o backend do D&D Byonder Solo pessoal em FastAPI.

REGRAS:
1. Não duplicar o Rule Engine existente.
2. Não duplicar o MiMo Proxy existente.
3. Base44 conversa somente com este serviço.
4. Rule Engine é a autoridade mecânica.
5. MiMo é somente narrador.
6. Nunca deixar o LLM rolar dados.
7. Nunca transformar needs_rule_validation em sucesso ou fracasso.
8. Persistir campanha e histórico.
9. Nunca colocar secrets no frontend.
10. Manter Docker/Render funcionando.

PRIMEIRO:
- criar todos os arquivos;
- instalar dependências;
- executar testes;
- testar /health;
- testar criação de campanha;
- testar um turno;
- testar que uma resolução não validada produz FATOS_RESOLVIDOS={}.

SEGUNDO:
- integrar URLs do Rule Engine e MiMo por variáveis de ambiente.

TERCEIRO:
- preparar integração com Base44.

NÃO:
- inventar classes, subclasses, magias ou números;
- copiar texto integral de livros;
- mover lógica mecânica para o prompt;
- permitir que o narrador determine resultados.
