"""
services/isapi_poller.py — Grupo Ronda · Conferência de Câmeras
Coleta status de NVRs e câmeras via Hikvision ISAPI.
 
Endpoints utilizados (autenticação HTTP Digest — RFC 2617):
  GET /ISAPI/System/workingstatus?format=json          → status geral (CPU, HD, canais)
  GET /ISAPI/System/workingstatus/chanStatus?format=json → status individual de cada canal
  GET /ISAPI/ContentMgmt/InputProxy/channels/status   → câmeras IP conectadas ao NVR
  GET /ISAPI/System/deviceInfo?format=json             → modelo, firmware, nº série
 
Logging:
  Cada polling gera entradas em duas saídas simultâneas:
    1. Logger Python padrão  → arquivo de log do Flask (via app.py)
    2. PollLog (in-memory)   → ring buffer por nvr_id, acessível via /conferencia/api/logs
"""
 
from __future__ import annotations
 
import concurrent.futures
import logging
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Optional
 
import requests
from requests.auth import HTTPDigestAuth
 
# ──────────────────────────────────────────────────────────────────────────────
# Logger do módulo — integra automaticamente com o logging do Flask
# ──────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
 
ISAPI_NS = "http://www.isapi.org/ver20/XMLSchema"
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Ring buffer de logs in-memory
# ──────────────────────────────────────────────────────────────────────────────
 
class PollLog:
    """
    Buffer circular de eventos de polling por nvr_id.
    Thread-safe. Mantém os últimos `maxlen` eventos globais
    e os últimos `per_nvr` eventos por NVR.
 
    Acessado pela rota GET /conferencia/api/logs para exibição em tempo real.
    """
 
    _global: deque = deque(maxlen=500)
    _per_nvr: dict[str, deque] = {}
    _lock: Lock = Lock()
 
    @classmethod
    def record(
        cls,
        nvr_id: str,
        level: str,       # "INFO" | "WARNING" | "ERROR" | "DEBUG"
        message: str,
        detail: str = "",
    ) -> None:
        entry = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nvr_id": nvr_id,
            "level": level,
            "message": message,
            "detail": detail,
        }
        with cls._lock:
            cls._global.append(entry)
            if nvr_id not in cls._per_nvr:
                cls._per_nvr[nvr_id] = deque(maxlen=100)
            cls._per_nvr[nvr_id].append(entry)
 
        # Espelha no logger Python para que o arquivo de log do Flask capture também
        log_fn = {
            "INFO":    logger.info,
            "WARNING": logger.warning,
            "ERROR":   logger.error,
            "DEBUG":   logger.debug,
        }.get(level, logger.info)
        msg = f"[{nvr_id}] {message}"
        if detail:
            msg += f" | {detail}"
        log_fn(msg)
 
    @classmethod
    def get_global(cls, limit: int = 200) -> list[dict]:
        with cls._lock:
            entries = list(cls._global)
        return entries[-limit:]
 
    @classmethod
    def get_nvr(cls, nvr_id: str, limit: int = 100) -> list[dict]:
        with cls._lock:
            buf = cls._per_nvr.get(nvr_id, deque())
            return list(buf)[-limit:]
 
    @classmethod
    def clear(cls, nvr_id: str | None = None) -> None:
        with cls._lock:
            if nvr_id:
                cls._per_nvr.pop(nvr_id, None)
            else:
                cls._global.clear()
                cls._per_nvr.clear()
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Modelos de dados
# ──────────────────────────────────────────────────────────────────────────────
 
@dataclass
class CameraStatus:
    channel_id: int
    channel_name: str = ""
    online: bool = False
    signal_ok: bool = False       # True = sinal normal (0 no ISAPI = normal)
    recording: bool = False
    record_status: int = 0        # 0=ok 1=exc HD 2=câmera offline 3=outro
    bit_rate_kbps: int = 0
    ip_address: str = ""
    model: str = ""
    raw_status: str = ""          # "online" | "offline" | "idle"
 
 
@dataclass
class HddStatus:
    hdd_id: int
    status: int = 0               # 0=ativo 1=sleep 2=exceção 4=não-formatado 5=desconectado
    capacity_mb: int = 0
    free_space_mb: int = 0
    enabled: bool = True
 
    @property
    def status_label(self) -> str:
        return {
            0: "Ativo", 1: "Dormindo", 2: "Exceção",
            3: "Erro (sleep)", 4: "Não formatado",
            5: "Desconectado", 6: "Formatando",
        }.get(self.status, "Desconhecido")
 
    @property
    def usage_pct(self) -> float:
        if self.capacity_mb <= 0:
            return 0.0
        return round((self.capacity_mb - self.free_space_mb) / self.capacity_mb * 100, 1)
 
 
@dataclass
class DeviceInfo:
    """Informações estáticas do dispositivo — capturadas uma vez e cacheadas."""
    model: str = ""
    firmware: str = ""
    serial: str = ""
    device_name: str = ""
 
 
@dataclass
class NvrStatus:
    nvr_id: str
    name: str
    host: str
    port: int
    reachable: bool = False
    error: str = ""
    dev_status: int = 0           # 0=normal 1=CPU alta 2=erro hardware
    cameras: list[CameraStatus] = field(default_factory=list)
    hdds: list[HddStatus] = field(default_factory=list)
    device_info: DeviceInfo = field(default_factory=DeviceInfo)
    polled_at: Optional[datetime] = None
    # Métricas de duração do polling (ms) para diagnóstico
    poll_duration_ms: int = 0
 
    @property
    def cameras_online(self) -> int:
        return sum(1 for c in self.cameras if c.online)
 
    @property
    def cameras_total(self) -> int:
        return len(self.cameras)
 
    @property
    def cameras_offline(self) -> int:
        return self.cameras_total - self.cameras_online
 
    @property
    def health_label(self) -> str:
        if not self.reachable:
            return "INACESSÍVEL"
        if self.cameras_offline > 0 or self.dev_status != 0:
            return "ATENÇÃO"
        return "OK"
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Cliente ISAPI
# ──────────────────────────────────────────────────────────────────────────────
 
class ISAPIClient:
    """
    Wrapper HTTP com HTTP Digest Auth (RFC 2617) para ISAPI Hikvision.
    Cada instância mantém uma Session para reaproveitar o handshake de autenticação.
    """
 
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
        self.session.verify = False   # câmeras Hikvision usam cert auto-assinado
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
 
    def get_xml(self, path: str) -> ET.Element:
        resp = self._get(path, accept_json=False)
        return ET.fromstring(resp.content)
 
    # ── Endpoints ISAPI ───────────────────────────────────────────────────
 
    def get_working_status(self) -> dict:
        """GET /ISAPI/System/workingstatus — status geral (CPU, HD, canais)."""
        return self.get_json("/ISAPI/System/workingstatus?format=json")
 
    def get_chan_status(self) -> dict:
        """GET /ISAPI/System/workingstatus/chanStatus — status por canal."""
        return self.get_json("/ISAPI/System/workingstatus/chanStatus?format=json")
 
    def get_inputproxy_status(self) -> ET.Element:
        """GET /ISAPI/ContentMgmt/InputProxy/channels/status — câmeras IP conectadas."""
        return self.get_xml("/ISAPI/ContentMgmt/InputProxy/channels/status")
 
    def get_device_info(self) -> dict:
        """GET /ISAPI/System/deviceInfo — modelo, firmware, nº série."""
        return self.get_json("/ISAPI/System/deviceInfo?format=json")
 
    def ping(self) -> bool:
        """Verifica alcançabilidade do dispositivo sem autenticação completa."""
        try:
            r = self.session.get(
                f"{self.base_url}/ISAPI/System/deviceInfo",
                timeout=self.timeout,
            )
            return r.status_code in (200, 401)  # 401 = NVR responde mas pede auth
        except Exception:
            return False
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Parsers de respostas ISAPI
# ──────────────────────────────────────────────────────────────────────────────
 
def _ns(tag: str) -> str:
    return f"{{{ISAPI_NS}}}{tag}"
 
 
def parse_chan_status(data: dict) -> list[CameraStatus]:
    """
    Parseia JSON_ChanStatus.
    DS-7732NI-I4(B) retorna: {"ChanStatusList": {"ChanStatus": [...]}}
    Alguns modelos retornam:  {"ChanStatus": [...]}
    bitRate vem em bits/s — convertido para Kbps dividindo por 1024.
    O nome da câmera já vem no campo "name" desta resposta.
    """
    cameras: list[CameraStatus] = []
 
    # Normaliza wrapper ChanStatusList (DS-7732 e similares)
    if "ChanStatusList" in data:
        chan_list = data["ChanStatusList"].get("ChanStatus", [])
    else:
        chan_list = data.get("ChanStatus", [])
 
    if isinstance(chan_list, dict):
        chan_list = [chan_list]
 
    for ch in chan_list:
        bit_rate_raw = int(ch.get("bitRate", 0))
        # bitRate pode vir em bits/s (>100000) ou já em Kbps (<100000)
        bit_rate_kbps = bit_rate_raw // 1024 if bit_rate_raw > 100_000 else bit_rate_raw
 
        cameras.append(CameraStatus(
            channel_id=int(ch.get("chanNo", 0)),
            channel_name=ch.get("name", ""),   # DS-7732 inclui nome aqui
            online=int(ch.get("online", 0)) == 1,
            signal_ok=int(ch.get("signal", 1)) == 0,   # 0=normal 1=perda de sinal
            recording=int(ch.get("record", 0)) == 1,
            record_status=int(ch.get("recordStatus", 0)),
            bit_rate_kbps=bit_rate_kbps,
        ))
    return cameras
 
 
def parse_hd_status(data: dict) -> list[HddStatus]:
    """Parseia HDStatus dentro de JSON_WorkingStatus."""
    ws = data.get("WorkingStatus", data)
    hd_list = ws.get("HDStatus", [])
    if isinstance(hd_list, dict):
        hd_list = [hd_list]
    return [
        HddStatus(
            hdd_id=int(hd.get("hdNo", 0)),
            status=int(hd.get("status", 0)),
            capacity_mb=int(hd.get("volume", 0)),
            free_space_mb=int(hd.get("freeSpace", 0)),
            enabled=hd.get("enable", 1) != 0,
        )
        for hd in hd_list
    ]
 
 
def parse_inputproxy_status(root: ET.Element) -> dict[int, dict]:
    """
    Parseia XML_InputProxyChannelStatusList ou XML_InputProxyChannelList.
    Suporta ambos os endpoints:
      /InputProxy/channels/status  → online/ip (sem nome/modelo)
      /InputProxy/channels         → nome/ip/modelo (sem status online)
    Retorna {channelID: {ip, name, model, raw_status}}.
    """
    result: dict[int, dict] = {}
 
    # Tenta InputProxyChannelStatus (endpoint /status)
    for ch in root.iter(_ns("InputProxyChannelStatus")):
        ch_id_el = ch.find(_ns("id"))
        if ch_id_el is None:
            continue
        ch_id = int(ch_id_el.text or 0)
 
        ip = ""
        src = ch.find(_ns("sourceInputPortDescriptor"))
        if src is not None:
            ip_el = src.find(_ns("ipAddress"))
            if ip_el is not None:
                ip = ip_el.text or ""
 
        online_el = ch.find(_ns("online"))
        raw_status = "unknown"
        if online_el is not None:
            raw_status = "online" if online_el.text == "true" else "offline"
 
        result[ch_id] = {"ip": ip, "name": "", "model": "", "raw_status": raw_status}
 
    # Tenta InputProxyChannel (endpoint /channels) — tem nome e modelo
    for ch in root.iter(_ns("InputProxyChannel")):
        ch_id_el = ch.find(_ns("id"))
        if ch_id_el is None:
            continue
        ch_id = int(ch_id_el.text or 0)
 
        name = ""
        name_el = ch.find(_ns("name"))
        if name_el is not None:
            name = name_el.text or ""
 
        ip = ""
        model = ""
        src = ch.find(_ns("sourceInputPortDescriptor"))
        if src is not None:
            ip_el = src.find(_ns("ipAddress"))
            if ip_el is not None:
                ip = ip_el.text or ""
            model_el = src.find(_ns("model"))
            if model_el is not None:
                model = model_el.text or ""
 
        existing = result.get(ch_id, {})
        result[ch_id] = {
            "ip":         ip or existing.get("ip", ""),
            "name":       name or existing.get("name", ""),
            "model":      model or existing.get("model", ""),
            "raw_status": existing.get("raw_status", "unknown"),
        }
 
    return result
 
 
def parse_device_info(data: dict) -> DeviceInfo:
    """
    Parseia DeviceInfo.
    Alguns NVRs (ex: DS-7732NI-I4(B)) retornam XML mesmo com ?format=json.
    Neste caso o dict virá vazio e o XML já foi parseado pelo cliente.
    """
    di = data.get("DeviceInfo", data)
    return DeviceInfo(
        model=di.get("model", ""),
        firmware=di.get("firmwareVersion", ""),
        serial=di.get("serialNumber", ""),
        device_name=di.get("deviceName", ""),
    )
 
 
def parse_device_info_xml(root: ET.Element) -> DeviceInfo:
    """Parseia DeviceInfo quando o NVR retorna XML em vez de JSON."""
    def txt(tag: str) -> str:
        el = root.find(_ns(tag))
        return el.text.strip() if el is not None and el.text else ""
    return DeviceInfo(
        model=txt("model"),
        firmware=txt("firmwareVersion"),
        serial=txt("serialNumber"),
        device_name=txt("deviceName"),
    )
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Poller de um único NVR
# ──────────────────────────────────────────────────────────────────────────────
 
class CameraConferencePoller:
    """
    Faz polling completo de um NVR via ISAPI e retorna NvrStatus.
    Cada endpoint é tentado de forma independente — falha em um não
    interrompe os demais (tolerância a falha parcial).
 
    Todos os eventos são registrados em PollLog para exibição em tempo real.
    """
 
    def __init__(
        self,
        client: ISAPIClient,
        nvr_id: str,
        nvr_name: str,
        nvr_host: str,
        nvr_port: int,
    ):
        self.client = client
        self.nvr_id = nvr_id
        self.nvr_name = nvr_name
        self.nvr_host = nvr_host
        self.nvr_port = nvr_port
 
    def _log(self, level: str, message: str, detail: str = "") -> None:
        PollLog.record(self.nvr_id, level, message, detail)
 
    def poll(self) -> NvrStatus:
        t_start = datetime.now()
        self._log("INFO", f"Iniciando polling — {self.nvr_host}:{self.nvr_port}")
 
        result = NvrStatus(
            nvr_id=self.nvr_id,
            name=self.nvr_name,
            host=self.nvr_host,
            port=self.nvr_port,
            polled_at=t_start,
        )
 
        # ── 1. Verificação de alcançabilidade ─────────────────────────────
        if not self.client.ping():
            result.error = "Dispositivo inacessível (ping ISAPI falhou)"
            result.reachable = False
            self._log("ERROR", "Dispositivo inacessível", result.error)
            result.poll_duration_ms = int((datetime.now() - t_start).total_seconds() * 1000)
            return result
 
        self._log("DEBUG", "Ping OK — dispositivo responde")
 
        # ── 2. Informações do dispositivo ──────────────────────────────────
        try:
            # DS-7732NI-I4(B) retorna XML mesmo com ?format=json — tenta JSON, cai em XML
            try:
                dev_data = self.client.get_json("/ISAPI/System/deviceInfo?format=json")
                if "model" in str(dev_data):
                    result.device_info = parse_device_info(dev_data)
                else:
                    raise ValueError("Resposta não parece JSON de DeviceInfo")
            except Exception:
                dev_root = self.client.get_xml("/ISAPI/System/deviceInfo")
                result.device_info = parse_device_info_xml(dev_root)
            self._log(
                "INFO",
                "DeviceInfo obtido",
                f"modelo={result.device_info.model} firmware={result.device_info.firmware}",
            )
        except Exception as e:
            self._log("WARNING", "DeviceInfo falhou (não crítico)", str(e))
 
        # ── 3. Status de canais (câmeras) ──────────────────────────────────
        try:
            chan_data = self.client.get_chan_status()
            result.cameras = parse_chan_status(chan_data)
            result.reachable = True
            online = sum(1 for c in result.cameras if c.online)
            total = len(result.cameras)
            self._log(
                "INFO" if online == total else "WARNING",
                f"Canais: {online}/{total} online",
                f"{total - online} offline" if online < total else "",
            )
            # Log individual de câmeras offline
            for cam in result.cameras:
                if not cam.online:
                    self._log(
                        "WARNING",
                        f"Canal {cam.channel_id} OFFLINE",
                        f"record_status={cam.record_status}",
                    )
        except Exception as e:
            result.error = str(e)
            self._log("ERROR", "chanStatus falhou", str(e))
 
        # ── 4. Status geral do dispositivo (CPU + HD) ─────────────────────
        try:
            ws_data = self.client.get_working_status()
            ws = ws_data.get("WorkingStatus", ws_data)
            result.dev_status = int(ws.get("devStatus", 0))
            result.hdds = parse_hd_status(ws_data)
            result.reachable = True
 
            # Log de status do dispositivo
            dev_label = {0: "Normal", 1: "CPU alta", 2: "Erro hardware"}.get(
                result.dev_status, f"status={result.dev_status}"
            )
            self._log(
                "INFO" if result.dev_status == 0 else "WARNING",
                f"Dispositivo: {dev_label}",
            )
 
            # Log de HDs
            for hd in result.hdds:
                level = "INFO" if hd.status == 0 else "WARNING"
                self._log(
                    level,
                    f"HD {hd.hdd_id}: {hd.status_label} — uso {hd.usage_pct}%",
                    f"livre={hd.free_space_mb}MB de {hd.capacity_mb}MB",
                )
        except Exception as e:
            self._log("WARNING", "workingstatus falhou", str(e))
 
        # ── 5. Enriquecimento via InputProxy (IP, nome e modelo) ──────────
        try:
            # /status → online/ip
            proxy_info: dict[int, dict] = {}
            try:
                status_root = self.client.get_inputproxy_status()
                proxy_info = parse_inputproxy_status(status_root)
            except Exception as e:
                self._log("DEBUG", "InputProxy/status falhou", str(e))
 
            # /channels → nome + modelo (endpoint separado no DS-7732)
            try:
                chan_root = self.client.get_xml("/ISAPI/ContentMgmt/InputProxy/channels")
                channels_info = parse_inputproxy_status(chan_root)
                # Mescla: channels tem nome/modelo, status tem online/ip
                for ch_id, ch_data in channels_info.items():
                    existing = proxy_info.get(ch_id, {})
                    proxy_info[ch_id] = {
                        "ip":         ch_data.get("ip") or existing.get("ip", ""),
                        "name":       ch_data.get("name") or existing.get("name", ""),
                        "model":      ch_data.get("model") or existing.get("model", ""),
                        "raw_status": existing.get("raw_status", "unknown"),
                    }
            except Exception as e:
                self._log("DEBUG", "InputProxy/channels falhou", str(e))
 
            enriched = 0
            for cam in result.cameras:
                info = proxy_info.get(cam.channel_id, {})
                if info.get("name") and not cam.channel_name:
                    cam.channel_name = info["name"]
                if info.get("ip"):
                    cam.ip_address = info["ip"]
                if info.get("model"):
                    cam.model = info["model"]
                if info.get("raw_status") and info["raw_status"] != "unknown":
                    cam.raw_status = info["raw_status"]
                if info:
                    enriched += 1
            self._log("DEBUG", f"InputProxy: {enriched} câmeras enriquecidas com IP/nome/modelo")
        except Exception as e:
            self._log("DEBUG", "InputProxy enrich falhou (não crítico)", str(e))
 
        # ── Finalização ───────────────────────────────────────────────────
        duration_ms = int((datetime.now() - t_start).total_seconds() * 1000)
        result.poll_duration_ms = duration_ms
 
        health = result.health_label
        level = "INFO" if health == "OK" else ("WARNING" if health == "ATENÇÃO" else "ERROR")
        self._log(
            level,
            f"Polling concluído — health={health} ({duration_ms}ms)",
            f"câmeras={result.cameras_online}/{result.cameras_total} online",
        )
 
        return result
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Gerenciador multi-NVR
# ──────────────────────────────────────────────────────────────────────────────
 
@dataclass
class NvrConfig:
    nvr_id: str
    name: str
    host: str
    port: int
    username: str
    password: str
    use_https: bool = False
 
 
class ConferenceManager:
    """
    Coordena polling paralelo de múltiplos NVRs via ThreadPoolExecutor.
    Falha em um NVR não afeta os demais.
    """
 
    def __init__(
        self,
        nvr_configs: list[NvrConfig],
        workers: int = 4,
        timeout: int = 8,
    ):
        self.nvr_configs = nvr_configs
        self.workers = workers
        self.timeout = timeout
 
    def _poll_one(self, cfg: NvrConfig) -> NvrStatus:
        client = ISAPIClient(
            cfg.host, cfg.port, cfg.username, cfg.password,
            timeout=self.timeout, use_https=cfg.use_https,
        )
        poller = CameraConferencePoller(
            client, cfg.nvr_id, cfg.name, cfg.host, cfg.port,
        )
        try:
            return poller.poll()
        except Exception as e:
            PollLog.record(cfg.nvr_id, "ERROR", "Polling falhou completamente", str(e))
            logger.exception(f"[{cfg.nvr_id}] Polling falhou completamente")
            return NvrStatus(
                nvr_id=cfg.nvr_id,
                name=cfg.name,
                host=cfg.host,
                port=cfg.port,
                reachable=False,
                error=str(e),
                polled_at=datetime.now(),
            )
 
    def poll_all(self) -> list[NvrStatus]:
        """
        Executa polling de todos os NVRs em paralelo.
        Retorna lista ordenada conforme a ordem original de nvr_configs.
        """
        if not self.nvr_configs:
            logger.warning("ConferenceManager.poll_all: nenhum NVR configurado")
            return []
 
        logger.info(f"ConferenceManager: iniciando polling de {len(self.nvr_configs)} NVR(s)")
 
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._poll_one, cfg): cfg for cfg in self.nvr_configs}
            results: list[NvrStatus] = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
 
        order = {cfg.nvr_id: i for i, cfg in enumerate(self.nvr_configs)}
        results.sort(key=lambda r: order.get(r.nvr_id, 999))
 
        ok = sum(1 for r in results if r.health_label == "OK")
        logger.info(
            f"ConferenceManager: polling concluído — "
            f"{ok}/{len(results)} NVRs OK"
        )
        return results