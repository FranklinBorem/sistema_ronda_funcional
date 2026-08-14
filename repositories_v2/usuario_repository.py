"""
repositories_v2/usuario_repository.py — Acesso a dados de usuários (schema novo).

Substitui repositories/monitor_repository.py no schema reconstruído.
Segue o mesmo padrão de injeção de sessão de repositories/base.py.

DECISÃO DE DESIGN A REVISITAR NA FASE 2 (multi-tenant real):
`usuario_login` é único POR EMPRESA no schema novo (não globalmente,
ver docs/database/modelo-banco.md), o que permite duas empresas
diferentes terem cada uma um usuário "admin". Por ora, como existe
uma única empresa operando, `buscar_por_login()` retorna o primeiro
usuário encontrado com aquele login, sem seletor de empresa na tela
de login. Quando houver uma segunda empresa real usando o sistema,
esse método (e o formulário de login) precisam ganhar um campo de
empresa/slug — está sinalizado aqui de propósito para não ser
esquecido.
"""

from __future__ import annotations

from typing import Optional

from models_v2.usuario import Usuario
from .base import BaseRepositoryV2


class UsuarioRepository(BaseRepositoryV2):

    def buscar_por_login(self, usuario_login: str) -> Optional[Usuario]:
        """Retorna o usuário pelo login ou None. Usado no login.

        Ver docstring do módulo — retorna o primeiro encontrado entre
        empresas até existir seletor de empresa na tela de login.
        """
        return (
            self.session
            .query(Usuario)
            .filter_by(usuario_login=usuario_login)
            .first()
        )

    def buscar_por_id(self, usuario_id: int) -> Optional[Usuario]:
        return self.session.get(Usuario, usuario_id)

    def listar_por_empresa(self, empresa_id: int) -> list[Usuario]:
        return (
            self.session
            .query(Usuario)
            .filter_by(empresa_id=empresa_id)
            .order_by(Usuario.nome)
            .all()
        )

    def criar(
        self,
        empresa_id: int | None,
        nome: str,
        usuario_login: str,
        senha_plain: str,
        papel: str,
    ) -> Usuario:
        """
        Cria e persiste um novo usuário.
        Lança sqlalchemy.exc.IntegrityError se (empresa_id, usuario_login)
        já existir.
        """
        usuario = Usuario(
            empresa_id=empresa_id,
            nome=nome,
            usuario_login=usuario_login,
            papel=papel,
        )
        usuario.set_senha(senha_plain)
        self.session.add(usuario)
        self.session.flush()   # gera o ID sem fechar a transação
        return usuario

    def existe_login_na_empresa(self, empresa_id: int | None, usuario_login: str) -> bool:
        return (
            self.session
            .query(Usuario.id)
            .filter_by(empresa_id=empresa_id, usuario_login=usuario_login)
            .first()
        ) is not None
