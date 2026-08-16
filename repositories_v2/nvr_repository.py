"""
repositories_v2/nvr_repository.py — Acesso a dados de Nvr/Camera/Preset
(schema novo, câmera sempre vinculada a um Nvr/grupo, via 'via_nvr' ou
'ip_direto' — ver docs/database/modelo-banco.md).

Substitui repositories/nvr_repository.py no schema reconstruído.
"""

from __future__ import annotations

from typing import Optional

from models_v2.nvr import Nvr, Camera, Preset, CAPACIDADES_PADRAO_POR_TIPO
from services_v2.isapi_client import descobrir_canais
from .base import BaseRepositoryV2


class NvrRepository(BaseRepositoryV2):

    # ── NVR (grupo/site) ─────────────────────────────────────────────────

    def listar_por_unidade(self, unidade_id: int) -> list[Nvr]:
        return (
            self.session.query(Nvr)
            .filter_by(unidade_id=unidade_id)
            .order_by(Nvr.nome)
            .all()
        )

    def buscar_por_id(self, nvr_id: int) -> Optional[Nvr]:
        return self.session.get(Nvr, nvr_id)

    def criar_nvr(
        self,
        unidade_id: int,
        nome: str,
        fabricante: str = "hikvision",
        modelo: str | None = None,
        endereco_ip: str | None = None,
        porta: int | None = 80,
        usuario_acesso: str | None = None,
        credencial_ref: str | None = None,
    ) -> Nvr:
        """
        Cria o registro de NVR/grupo. `endereco_ip` fica None quando o
        registro existe só como agrupador organizacional de câmeras
        avulsas (nenhum dispositivo físico próprio a consultar).
        """
        nvr = Nvr(
            unidade_id=unidade_id,
            nome=nome,
            fabricante=fabricante,
            modelo=modelo,
            endereco_ip=endereco_ip,
            porta=porta,
            usuario_acesso=usuario_acesso,
            credencial_ref=credencial_ref,
        )
        self.session.add(nvr)
        self.session.flush()
        return nvr

    def atualizar_nvr(self, nvr: Nvr, **campos) -> Nvr:
        for chave, valor in campos.items():
            if hasattr(nvr, chave):
                setattr(nvr, chave, valor)
        self.session.flush()
        return nvr

    def excluir_nvr(self, nvr: Nvr) -> None:
        self.session.delete(nvr)  # cascade remove cameras/presets (ver models_v2/nvr.py)
        self.session.flush()

    # ── Auto-descoberta de canais ao cadastrar um NVR físico ────────────

    def cadastrar_nvr_com_descoberta(
        self,
        unidade_id: int,
        nome: str,
        endereco_ip: str,
        usuario_acesso: str,
        senha_plain: str,
        porta: int = 80,
        fabricante: str = "hikvision",
        timeout: int = 8,
    ) -> tuple[Nvr, list[Camera], Exception | None]:
        """
        Cria o NVR e tenta descobrir os canais via ISAPI, criando uma
        Camera (modo_conexao='via_nvr') por canal encontrado.

        Retorna (nvr, cameras_criadas, erro_descoberta). Se a consulta
        ISAPI falhar (equipamento inacessível/credencial errada), o NVR
        AINDA é criado (o operador pode ter digitado o IP certo mas o
        equipamento estar temporariamente fora do ar) — mas nenhuma
        câmera é criada automaticamente, e o erro é retornado para a
        rota decidir como avisar o operador. Nunca lança a exceção
        ISAPI direto — quem chama decide o tratamento de UI.
        """
        # credencial_ref hoje guarda a senha em texto — mitigação futura
        # via convenção env: já existente em core/nvr_config.py, ver
        # docs/security/seguranca.md (Fase 0/1, fora do escopo desta etapa).
        nvr = self.criar_nvr(
            unidade_id=unidade_id, nome=nome, fabricante=fabricante,
            endereco_ip=endereco_ip, porta=porta,
            usuario_acesso=usuario_acesso, credencial_ref=senha_plain,
        )

        cameras_criadas: list[Camera] = []
        erro: Exception | None = None
        try:
            canais = descobrir_canais(
                host=endereco_ip, port=porta,
                username=usuario_acesso, password=senha_plain,
                timeout=timeout,
            )
            for item in canais:
                cam = self.criar_camera(
                    nvr_id=nvr.id, modo_conexao="via_nvr",
                    canal=item["canal"], tipo="generica", nome=item["nome"],
                )
                cameras_criadas.append(cam)
        except Exception as e:  # falha de rede/auth ISAPI — não impede o cadastro do NVR
            erro = e

        return nvr, cameras_criadas, erro

    # ── Câmeras ──────────────────────────────────────────────────────────

    def listar_cameras(self, nvr_id: int) -> list[Camera]:
        return (
            self.session.query(Camera)
            .filter_by(nvr_id=nvr_id)
            .order_by(Camera.canal, Camera.nome)
            .all()
        )

    def listar_cameras_ptz_por_unidade(self, unidade_id: int) -> list[Camera]:
        """
        Câmeras com capacidade PTZ e ao menos um preset, de todos os
        NVRs/grupos de uma Unidade — a lista de trabalho da ronda
        automatizada (Fase C da religação, ver core/ronda_multi_nvr.py:
        executar_ronda_multi_v2).
        """
        return (
            self.session.query(Camera)
            .join(Nvr, Camera.nvr_id == Nvr.id)
            .filter(Nvr.unidade_id == unidade_id)
            .filter(Camera.capacidades["ptz"].as_boolean() == True)  # noqa: E712
            .filter(Camera.presets.any())
            .all()
        )

    def buscar_camera(self, camera_id: int) -> Optional[Camera]:
        return self.session.get(Camera, camera_id)

    def criar_camera(
        self,
        nvr_id: int,
        modo_conexao: str,
        tipo: str,
        canal: int | None = None,
        endereco_ip: str | None = None,
        porta: int | None = None,
        usuario_acesso: str | None = None,
        credencial_ref: str | None = None,
        nome: str | None = None,
        capacidades: dict | None = None,
    ) -> Camera:
        camera = Camera(
            nvr_id=nvr_id, modo_conexao=modo_conexao, tipo=tipo,
            canal=canal, endereco_ip=endereco_ip, porta=porta,
            usuario_acesso=usuario_acesso, credencial_ref=credencial_ref,
            nome=nome,
        )
        camera.capacidades = (
            capacidades if capacidades is not None
            else dict(CAPACIDADES_PADRAO_POR_TIPO.get(tipo, {}))
        )
        self.session.add(camera)
        self.session.flush()
        return camera

    def atualizar_camera(self, camera: Camera, **campos) -> Camera:
        for chave, valor in campos.items():
            if hasattr(camera, chave):
                setattr(camera, chave, valor)
        self.session.flush()
        return camera

    def excluir_camera(self, camera: Camera) -> None:
        self.session.delete(camera)
        self.session.flush()

    # ── Presets ──────────────────────────────────────────────────────────

    def listar_presets(self, camera_id: int) -> list[Preset]:
        return (
            self.session.query(Preset)
            .filter_by(camera_id=camera_id)
            .order_by(Preset.numero)
            .all()
        )

    def criar_preset(self, camera_id: int, numero: int, descricao: str | None = None) -> Preset:
        preset = Preset(camera_id=camera_id, numero=numero, descricao=descricao)
        self.session.add(preset)
        self.session.flush()
        return preset

    def excluir_preset(self, preset: Preset) -> None:
        self.session.delete(preset)
        self.session.flush()
