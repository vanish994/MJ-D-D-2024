# Publicação

1. Abra/crie `vanish994/MJ-D-D-2024`.
2. Copie todo este conteúdo para a raiz.
3. Não copie livros nem a base textual para este repositório.
4. Não copie o código do MiMo Proxy.
5. Configure `RULE_ENGINE_URL`, `RULE_ENGINE_API_KEY`, `MIMO_URL` e `MIMO_API_KEY`.
6. Rode `uvicorn app.main:app --reload --port 8000`.
7. Teste `GET /health`.
8. Crie uma campanha em `POST /v1/campaigns`.
9. Envie turnos em `POST /v1/campaigns/{id}/turn`.
10. Conecte o Base44 somente ao MJ-D-D-2024.

## Prompt para a ferramenta

Implemente este repositório respeitando README.md, ARCHITECTURE.md e docs/BUILD_SPEC.md. Preserve a separação Rule Engine/Narrador. Não copie conteúdo protegido dos livros. Não invente regras. Antes de adicionar qualquer resolver mecânico, valide a regra no Rule Engine e crie testes determinísticos. Não altere os repositórios externos sem confirmação explícita.
