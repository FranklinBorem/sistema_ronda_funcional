# CI/CD e Qualidade — Estratégia Futura

## Git e branches

- **Branch principal** (`main`) sempre deployável — reflete o que está em produção.
- **Branches de trabalho** por etapa/funcionalidade (ex.: `fix/ronda-subprocess`, `feature/multi-tenant-empresa`), seguindo exatamente o padrão já adotado no plano de correção (uma branch por etapa, nunca commit direto em `main`).
- Nomenclatura sugerida: `fix/`, `feature/`, `chore/`, `docs/` como prefixo — ajuda a entender a natureza da mudança só pelo nome da branch.

## Pull Requests e Code Review

- Mesmo trabalhando sozinho hoje, abrir Pull Request (mesmo que só você aprove) tem valor: obriga a revisar o próprio diff antes de aplicar, documenta a intenção da mudança (descrição do PR), e cria o hábito que será necessário no dia em que houver mais alguém no time.
- Template de PR sugerido: objetivo da mudança, arquivos alterados, como foi testado, riscos conhecidos — essencialmente o mesmo formato usado nas etapas do plano de correção já produzido.

## Lint e formatter

- **Python**: `ruff` (rápido, cobre lint + parte de formatação) ou a combinação clássica `flake8` + `black`. Recomendo `ruff` por simplicidade de configuração (uma ferramenta só) para um projeto mantido por um desenvolvedor único.
- **JavaScript** (`server.js`): `eslint` + `prettier`, se o bot crescer em complexidade — hoje é pequeno o suficiente para não ser urgente.

## Testes automáticos

- Rodar a suíte de testes (`operations/testes.md`) a cada push/PR — não faz sentido ter testes se eles não rodam automaticamente antes de qualquer merge.

## GitHub Actions (proposta mínima, não implementar ainda)

Pipeline conceitual:
```
on: pull_request, push para main
jobs:
  lint:       roda ruff
  test:       sobe um PostgreSQL de teste (service container), roda pytest
  build:      (futuro) build da imagem Docker, se a opção B de deployment for adotada
```

## Deploy

- **MVP**: deploy manual guiado (ex.: um script `deploy.sh` documentado, não um clique mágico) — automatizar deploy completo é Fase 4/5, quando o volume de mudanças justificar.
- **Futuro**: deploy automático para ambiente de homologação a cada merge em `main`; deploy para produção com aprovação manual (mesmo que seja você mesmo aprovando, é uma trava consciente antes de afetar clientes reais).

## Como isso entra no projeto, na prática

Não precisa ser tudo de uma vez. Ordem sugerida: (1) lint local, roda manualmente por enquanto; (2) testes automatizados básicos (Fase 0/1, conforme `operations/testes.md`); (3) GitHub Actions rodando lint+testes em PR (assim que existir suíte de teste mínima); (4) deploy automatizado só depois que houver confiança na suíte de testes — automatizar deploy sem testes automatizados é mais risco do que benefício.
