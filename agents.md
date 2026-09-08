# Agentes — Limpeza de legado sem regressão

## Rabibi-Maestro

- Orquestra a branch `codex/dominus-legacy-cleanup-goal`, mantém o escopo preso ao `goal.md`, integra os resultados e executa as buscas de consumidores antes e depois de cada remoção.
- Pode ajustar artefatos de contexto e fazer correções pequenas de integração, mas não promove para `main` nem executa deploy.

## Worker Backend

- Remove apenas camadas, imports, aliases e rotas comprovadamente redundantes no backend FastAPI.
- Preserva integralmente `IdentityClient`, `WhatsAppClient`, ownership por tenant, autenticação humana, CRM, webhooks, SSE, pedidos, mídia e upload.
- Não altera criptografia, scopes, contratos HTTP válidos, modelos persistidos ou migrations.

## Worker Frontend e Documentação

- Remove somente a UI e os helpers de autenticação Instagram ligados às rotas mortas do domínio WhatsApp.
- Mantém Instagram como dado/canal do CRM e integração n8n, bem como tokens humanos e todos os fluxos funcionais existentes.
- Atualiza a documentação operacional para descrever apenas o contrato atual congelado no `goal.md`.

## Code Review e QA Jules

- Revisam exclusivamente o commit enviado e tratam regressão funcional, segurança, contrato e falha de testes como bloqueadores P0/P1.
- Validam a suíte completa em uma branch não produtiva. Deploy e merge em `main` permanecem proibidos sem autorização explícita do usuário.

## Regras comuns

- Toda exclusão exige busca estática prévia e prova automatizada posterior.
- Nenhum segredo pode aparecer em prompt, commit, log ou relatório.
- Achados fora do caminho de limpeza são preservados e, se necessário, registrados para trabalho futuro; não são corrigidos nesta entrega.
