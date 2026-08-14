"""
services_v2/isapi_client.py — Cliente ISAPI Hikvision (cópia isolada
de services/isapi_poller.py:ISAPIClient — ver __init__.py deste
pacote para o porquê da duplicação temporária).

Usado por repositories_v2/nvr_repository.py para a auto-descoberta de
canais ao cadastrar um NVR físico (docs/database/modelo-banco.md:
"Fluxo de cadastro 'subir o NVR'").
"""

from __future__ import annotations

import logging
from typing import TypedDict

import requests
from requests.auth import HTTPDigestAuth

logger = logging.getLogger(__name__)


class CanalDescoberto(TypedDict):
    canal: int
    nome: str


class ISAPIClient:
    """Wrapper HTTP com HTTP Digest Auth (RFC 2617) para ISAPI Hikvision."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int = 8,
        use_https: bool = False,
    ):
        scheme = "https" if use_https else "http"
        self.base_url = f"{scheme}://{host}:{port}"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = HTTPDigestAuth(username, password)
        self.session.verify = False  # câmeras Hikvision usam cert auto-assinado
        if use_https:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get(self, path: str, accept_json: bool = False) -> requests.Response:
        url = self.base_url + path
        headers = {"Accept": "application/json"} if accept_json else {}
        resp = self.session.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def get_json(self, path: str) -> dict:
        return self._get(path, accept_json=True).json()

    def get_chan_status(self) -> dict:
        """GET /ISAPI/System/workingstatus/chanStatus — status por canal, inclui nome."""
        return self.get_json("/ISAPI/System/workingstatus/chanStatus?format=json")

    def ping(self) -> bool:
        try:
            r = self.session.get(
                f"{self.base_url}/ISAPI/System/deviceInfo", timeout=self.timeout
            )
            return r.status_code in (200, 401)  # 401 = NVR responde mas pede auth
        except Exception:
            return False


def descobrir_canais(
    host: str, port: int, username: str, password: str, timeout: int = 8
) -> list[CanalDescoberto]:
    """
    Consulta um NVR físico via ISAPI e retorna a lista de canais
    encontrados, para popular automaticamente Camera (modo_conexao=
    'via_nvr') no cadastro. Levanta a exceção original em caso de
    falha de rede/autenticação — quem chama decide como tratar
    (ex.: exibir erro ao operador, sem criar NVR "quebrado").
    """
    client = ISAPIClient(host, port, username, password, timeout=timeout)
    data = client.get_chan_status()

    if "ChanStatusList" in data:
        chan_list = data["ChanStatusList"].get("ChanStatus", [])
    else:
        chan_list = data.get("ChanStatus", [])
    if isinstance(chan_list, dict):
        chan_list = [chan_list]

    canais: list[CanalDescoberto] = []
    for ch in chan_list:
        numero = int(ch.get("id", ch.get("channel", 0)))
        nome = str(ch.get("name") or f"Canal {numero}").strip()
        if numero:
            canais.append({"canal": numero, "nome": nome})
    return canais
