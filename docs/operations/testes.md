# Estratégia de Testes

## Estado atual (confirmado)

Não há suíte de testes automatizados no repositório — `teste.py` e `testar_deteccao.py` são scripts de depuração manual, não testes no sentido de pytest/CI. Todo o produto hoje é validado manualmente.

## Tipos de teste e onde cada um se aplica neste projeto

| Tipo | O que valida | Exemplo neste projeto |
|---|---|---|
| **Unitário** | Uma função/classe isolada, sem banco/rede | `Monitor.verificar_senha()` retorna corretamente para senha certa/errada |
| **Integração** | Componentes reais trabalhando juntos (ex.: service + repository + banco de teste) | `RondaService.iniciar_ronda_multi()` cria o registro correto no banco |
| **API** | Requisição HTTP real contra as rotas Flask | `POST /login` com credenciais válidas retorna redirecionamento e seta sessão |
| **Banco** | Migrations aplicam/revertem sem erro, constraints funcionam | `flask db upgrade`/`downgrade` não quebram; UNIQUE de `usuarios(empresa_id, usuario_login)` rejeita duplicata |
| **Equipamento** | Comunicação com NVR real (ou simulado) | Driver ISAPI interpreta corretamente uma resposta simulada de status de canal |
| **IA** | Corretude do pipeline de detecção | Dado um snapshot de teste com pessoa conhecida, o modelo detecta com confiança acima do threshold esperado |
| **Ponta a ponta (E2E)** | Fluxo completo do usuário | Login → disparar ronda → ver resultado no histórico |

## O que implementar primeiro (ordem recomendada)

1. **Testes de integração dos fluxos já corrigidos na Fase 0** — especialmente `RondaService.iniciar_ronda_multi()` (o bug mais crítico já mapeado) e autenticação — porque são justamente os pontos onde já sabemos que existiu regressão silenciosa (a ronda "parecia funcionar" mas não executava).
2. **Testes de API dos endpoints de autenticação e autorização** — são a base de segurança de todo o resto; qualquer regressão aqui é grave.
3. **Testes de banco (migrations)** — antes de rodar qualquer migration em produção, ela deve ser testada em banco de teste (`upgrade`/`downgrade`).
4. **Testes de isolamento multi-tenant** (quando a Fase 2 chegar) — o requisito mais crítico do produto comercial (RNF04) deveria ter teste automatizado dedicado, não só validação manual.
5. Testes de equipamento/IA vêm depois, e tendem a ser os mais difíceis de automatizar totalmente (dependem de hardware real ou fixtures simulados) — usar mocks/dados de exemplo gravados, não NVR real, para não tornar a suíte de testes dependente de rede física.

## Exemplos conceituais (sem código de produção, só ilustrativo)

**Unit Test** (conceitual):
```
teste: "verificar_senha retorna False para senha incorreta"
dado um Monitor com senha_hash de "abc123"
quando verificar_senha("errada") é chamado
entao o resultado deve ser False
```

**Integration Test** (conceitual):
```
teste: "iniciar_ronda_multi cria registro em status em_andamento"
dado um banco de teste com um NVR cadastrado e ativo
quando RondaService.iniciar_ronda_multi(unidade_id) é chamado
entao deve existir uma Ronda no banco com status "em_andamento"
e apos a execucao (thread) concluir, o status deve mudar para "finalizada" ou "com_alertas"
```

**End-to-End Test** (conceitual):
```
teste: "fluxo completo de login e disparo de ronda"
dado um usuario valido cadastrado
quando o teste faz login via POST /login
e em seguida faz POST /iniciar_ronda_multi
entao a resposta deve confirmar que a ronda foi criada
e, consultando /historico, a ronda deve aparecer listada
```

## Nota sobre testes de IA/equipamento

Testar contra um NVR real na suíte de CI é frágil (depende de rede, disponibilidade do equipamento, e pode até interferir na operação real). A prática recomendada é gravar respostas reais do ISAPI uma vez (fixtures) e testar o driver contra essas respostas gravadas — valida a lógica de parsing sem depender do equipamento estar acessível durante o teste.
