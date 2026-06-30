# Integração — Conferência de Câmeras no Grupo Ronda

## 1. Instalar dependência

```
pip install requests --break-system-packages
```
(`requests` provavelmente já está no projeto; se não, adicionar ao requirements.txt)

---

## 2. Copiar arquivos para o projeto

```
isapi_poller.py                  → raiz do projeto (junto de ronda.py, app.py)
blueprints/conferencia_bp.py     → blueprints/conferencia_bp.py
templates/conferencia/painel.html → templates/conferencia/painel.html
```

---

## 3. Registrar blueprint em app.py

```python
from blueprints.conferencia_bp import conferencia_bp
app.register_blueprint(conferencia_bp)
```

---

## 4. Configurar os NVRs em config.py (ou diretamente em app.py)

```python
NVRS = [
    {
        "id":        "nvr_ufv01",          # ID único interno
        "name":      "UFV 01 – Sede",      # Nome exibido no painel
        "host":      "192.168.1.100",      # IP do NVR
        "port":      80,                   # Porta HTTP (ou 443 para HTTPS)
        "username":  "admin",
        "password":  "SuaSenha",
        "use_https": False,
    },
    {
        "id":        "nvr_ufv02",
        "name":      "UFV 02 – Norte",
        "host":      "192.168.2.100",
        "port":      80,
        "username":  "admin",
        "password":  "SuaSenha",
        "use_https": False,
    },
    # Adicione quantos NVRs precisar
]

# Timeout por NVR (segundos). Ajuste se a rede for lenta.
ISAPI_TIMEOUT = 8

# Workers paralelos (um thread por NVR simultâneo)
ISAPI_WORKERS = 4
```

---

## 5. Acessar o painel

```
http://localhost:5000/conferencia/
```

---

## Endpoints disponíveis

| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/conferencia/` | Dashboard visual |
| GET | `/conferencia/api/status` | JSON com todos os NVRs |
| GET | `/conferencia/api/status/<nvr_id>` | JSON de um NVR específico |

---

## Dados retornados por NVR

```json
{
  "nvr_id": "nvr_ufv01",
  "name": "UFV 01 – Sede",
  "reachable": true,
  "health": "OK",            // "OK" | "ATENÇÃO" | "INACESSÍVEL"
  "cameras_total": 16,
  "cameras_online": 15,
  "cameras_offline": 1,
  "cameras": [
    {
      "id": 1,
      "name": "Portão Principal",
      "online": true,
      "signal_ok": true,
      "recording": true,
      "record_status": 0,     // 0=ok, 1=exc HD, 2=câmera offline, 3=outro
      "bit_rate_kbps": 2048,
      "ip": "192.168.1.11",
      "model": "DS-2DE4A425IWG-E"
    }
  ],
  "hdds": [
    {
      "id": 1,
      "status": 0,
      "status_label": "Ativo",
      "capacity_mb": 3000000,
      "free_space_mb": 800000,
      "usage_pct": 73.3
    }
  ]
}
```

---

## Endpoints ISAPI utilizados

| Endpoint | Propósito |
|----------|-----------|
| `GET /ISAPI/System/workingstatus?format=json` | Status geral do NVR (CPU, HDs, canais) |
| `GET /ISAPI/System/workingstatus/chanStatus?format=json` | Status de cada canal (online/sinal/gravação/bitrate) |
| `GET /ISAPI/ContentMgmt/InputProxy/channels/status` | Status das câmeras IP (nome, IP, modelo) |

Autenticação: **HTTP Digest** (MD5), conforme seção 3.1 do manual ISAPI.

---

## Adicionando ao menu do sistema

No seu template `base.html`, adicione o link:

```html
<a href="{{ url_for('conferencia.painel') }}">⚙ Conferência de Câmeras</a>
```
