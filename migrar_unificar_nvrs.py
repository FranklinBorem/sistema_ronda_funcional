"""
migrar_unificar_nvrs.py — Migração única: unifica nvr_monitorado em nvrs.

O que este script faz, nesta ordem:
  1. Adiciona as colunas `porta`, `use_https` e `criado_em` na tabela `nvrs`
     (se ainda não existirem).
  2. Copia para `nvrs` todo registro de `nvr_monitorado` cujo `nvr_id` ainda
     não exista em `nvrs` (evita duplicar/sobrescrever registros já
     cadastrados via módulo PTZ).
  3. Imprime um resumo do que foi migrado. NÃO apaga `nvr_monitorado` —
     isso é feito manualmente depois, só quando você confirmar que está
     tudo certo (veja instruções no final da saída).

Uso:
    python migrar_unificar_nvrs.py

Pré-requisito: rode isto DEPOIS de trocar models/nvr.py pela versão
atualizada (com porta/use_https/criado_em) e ANTES de remover
models/nvr_monitorado.py — o script ainda precisa da tabela antiga existir
para ler os dados dela.
"""

from __future__ import annotations

from app import app  # ajuste se o factory/app não se chamar "app" em app.py
from extensions import db
from sqlalchemy import inspect, text


def _coluna_existe(nome_tabela: str, nome_coluna: str) -> bool:
    insp = inspect(db.engine)
    colunas = [c["name"] for c in insp.get_columns(nome_tabela)]
    return nome_coluna in colunas


def _adicionar_colunas_faltantes() -> None:
    print("→ Verificando colunas da tabela 'nvrs'...")
    alteracoes = []

    if not _coluna_existe("nvrs", "porta"):
        alteracoes.append("ALTER TABLE nvrs ADD COLUMN porta INTEGER NOT NULL DEFAULT 80")
    if not _coluna_existe("nvrs", "use_https"):
        alteracoes.append("ALTER TABLE nvrs ADD COLUMN use_https BOOLEAN NOT NULL DEFAULT false")
    if not _coluna_existe("nvrs", "criado_em"):
        alteracoes.append("ALTER TABLE nvrs ADD COLUMN criado_em TIMESTAMP")

    if not alteracoes:
        print("  Nenhuma coluna faltando — já está tudo criado.")
        return

    with db.engine.begin() as conn:
        for sql in alteracoes:
            print(f"  Executando: {sql}")
            conn.execute(text(sql))

    print(f"  {len(alteracoes)} coluna(s) adicionada(s).")


def _migrar_dados() -> None:
    print("\n→ Copiando registros de 'nvr_monitorado' para 'nvrs'...")

    from models.nvr import Nvr
    from models.nvr_monitorado import NvrMonitorado

    existentes_em_nvrs = {n.nvr_id for n in Nvr.query.all()}
    origem = NvrMonitorado.query.all()

    migrados, ignorados = [], []

    for m in origem:
        if m.nvr_id in existentes_em_nvrs:
            ignorados.append(m.nvr_id)
            continue

        novo = Nvr(
            nvr_id=m.nvr_id,
            site=m.site,
            nome=m.nome,
            ip=m.ip,
            usuario=m.usuario,
            senha=m.senha,
            porta=m.porta,
            use_https=m.use_https,
            ativo=m.ativo,
            criado_em=m.criado_em,
            # campos PTZ não existiam em nvr_monitorado — ficam no default
            # do model (ptz_channel=1, snapshot_channel="501", etc.)
        )
        db.session.add(novo)
        migrados.append(m.nvr_id)

    db.session.commit()

    print(f"  Migrados: {len(migrados)} → {migrados}")
    if ignorados:
        print(f"  Ignorados (já existiam em 'nvrs'): {len(ignorados)} → {ignorados}")
        print("  ATENÇÃO: revise manualmente esses IDs — pode haver dados")
        print("  divergentes entre o cadastro antigo do PTZ e o do Conferência.")


def main() -> None:
    with app.app_context():
        _adicionar_colunas_faltantes()
        _migrar_dados()

    print("\n✅ Migração concluída.")
    print("\nPróximos passos:")
    print("  1. Acesse /nvrs no navegador e confirme que os NVRs aparecem")
    print("     com os dados corretos (IP, porta, HTTPS, etc.)")
    print("  2. Rode o polling (Conferência) e confirme que continua OK")
    print("  3. Só depois disso, remova a tabela antiga:")
    print('     psql -U postgres -h localhost -d vigilante_ia -c "DROP TABLE nvr_monitorado;"')
    print("  4. Apague o arquivo models/nvr_monitorado.py do projeto")


if __name__ == "__main__":
    main()
