# Modelo Conceitual de Segurança

## Autenticação

- **MVP**: login usuário/senha, hash Werkzeug (já correto em `models/monitor.py` — manter). Sessão via cookie Flask assinado por `SECRET_KEY`.
- **Futuro**: considerar 2FA para papéis administrativos (Admin da Empresa/Super Admin), se clientes de segurança patrimonial exigirem como requisito de compliance — não é bloqueio do MVP.

## Autorização

- **MVP**: papel fixo por usuário (`security` já discutido em `architecture/casos-de-uso.md`), verificado via decorator sobre o `login_required` já existente (`core/auth.py`).
- **Futuro**: permissões granulares por ação (RBAC completo), se a operação de algum cliente exigir controle mais fino do que os 6 papéis padrão oferecem.

## Sessões

- **MVP**: sessão Flask padrão (`session["usuario_id"]`, `session["empresa_id"]`, `session["papel"]`), com `SECRET_KEY` obrigatório em produção (correção já mapeada no plano de correção, categoria A).
- **Futuro**: expiração configurável de sessão, invalidação remota (logout forçado por admin).

## Credenciais de NVR (segredo de equipamento)

- **Problema confirmado**: senha de NVR/câmera armazenada em texto plano hoje (`models/nvr.py`, `models/nvr_monitorado.py`), e reenviada em texto plano no HTML de edição (`templates/conferencia/nvr_form.html`).
- **MVP**: parar de reenviar a senha no HTML (correção isolada, já no plano de correção) + estender a convenção já existente no código (`core/nvr_config.py:_resolver_segredo`, que resolve `env:NOME_VAR` a partir de variável de ambiente) para cobrir também o fluxo de Conferência de Câmeras. Isso reduz exposição sem exigir infraestrutura nova.
- **Futuro**: criptografia simétrica reversível (a senha precisa ser usada de verdade para autenticar no NVR, então não pode ser hash — precisa ser decifrável), com chave fora do banco; ou integração com um cofre de segredos dedicado (Vault, AWS Secrets Manager) quando o volume/exigência de clientes justificar o custo operacional.

## Secrets (aplicação)

- **MVP**: nenhum segredo (webhook Discord, SMTP, `SECRET_KEY`) em texto no código — tudo via variável de ambiente, correção já mapeada.
- **Futuro**: secrets por empresa (não globais ao processo) via tabela `integracoes` (`database/modelo-banco.md`), com valores sensíveis dentro dela também não em texto plano.

## CSRF

- **MVP**: `Flask-WTF`/`CSRFProtect` em todos os formulários autenticados — mas, conforme já decidido no plano de correção revisado, essa etapa é feita **após** a Fase 1 (fundação de tenant/unidade), para não retrabalhar os mesmos templates duas vezes.

## Rate limiting

- **MVP**: limite simples de tentativas de login por usuário/IP.
- **Futuro**: rate limiting por API/endpoint conforme a superfície pública crescer (ex.: se um dia existir API pública para clientes).

## Auditoria

- **MVP**: tabela `auditoria` simples (quem, quando, o quê, em qual empresa) para ações de escrita/configuração sensíveis — não é necessário auditar leitura/visualização.
- **Futuro**: relatórios de auditoria exportáveis, retenção configurável por plano.

## Isolamento de empresas

- **MVP**: filtro de `empresa_id` centralizado nos repositories (camada de aplicação) — ver `database/multi-tenancy.md` para a decisão completa.
- **Futuro**: Row-Level Security no PostgreSQL como segunda camada, ao menos nas tabelas mais sensíveis (credenciais de equipamento, ocorrências) desde o início do multi-tenant — não é "futuro distante", é recomendado já na Fase 2, mas tratado aqui como incremento sobre o filtro de aplicação, não substituto dele.

## Comunicação com equipamentos

- **MVP**: mantém o modelo atual — HTTP Digest Auth, TLS sem verificação de certificado (`services/isapi_poller.py:verify=False`), aceito conscientemente porque câmeras Hikvision usam certificado autoassinado em rede local/privada — **não é um problema a corrigir sem entender a topologia de rede de cada cliente**, é uma decisão de risco aceito documentada.
- **Futuro**: se algum cliente expuser NVRs em rede menos confiável, avaliar VPN/túnel dedicado por cliente em vez de relaxar verificação de certificado.

## APIs

- **MVP**: não há API pública — as rotas HTTP existentes servem a própria interface web e o bot WhatsApp (autenticado por token, correção já mapeada).
- **Futuro**: API pública documentada, com autenticação por API key/OAuth, quando um cliente pedir integração própria (Fase 5).

## Logs

- **MVP**: `@app.errorhandler` global + logging estruturado de exceções (já mapeado no plano de correção) — mínimo necessário para depurar incidentes.
- **Futuro**: correlação de logs por empresa/request-id, para investigar incidentes específicos de um cliente sem vasculhar log de todos.

## Backup

- **MVP**: `pg_dump` regular do banco, testado (restauração validada) antes de qualquer mudança de schema — já é parte da Etapa 0 do plano de correção.
- **Futuro**: backup automatizado com retenção definida, e plano de recuperação de desastre documentado (RTO/RPO) quando houver SLA contratual com clientes.

---

## Resumo MVP vs. Futuro

| Item | MVP | Futuro |
|---|---|---|
| Autenticação | Usuário/senha + hash | + 2FA opcional |
| Autorização | Papel fixo (6 níveis) | RBAC granular |
| Credencial de NVR | `env:` convention estendida + não reenviar em HTML | Criptografia/cofre dedicado |
| Secrets da app | Variável de ambiente | Por empresa, em `integracoes` |
| CSRF | Sim, após Fase 1 | — |
| Rate limiting | Login | Por endpoint/API |
| Auditoria | Ações de escrita sensíveis | Exportável, retenção configurável |
| Isolamento de empresa | Filtro de aplicação | + Row-Level Security |
| Comunicação com equipamento | TLS sem verificação (aceito) | VPN/túnel se necessário |
| API | Nenhuma pública | Pública documentada |
| Logs | Erro global + logging estruturado | Correlação por empresa |
| Backup | `pg_dump` manual testado | Automatizado + plano de recuperação |
