"""
debug_isapi.py — Testa autenticação Basic e Digest no NVR Piacatu
"""
import requests
from requests.auth import HTTPDigestAuth, HTTPBasicAuth
import urllib3
urllib3.disable_warnings()

HOST  = "10.38.16.67"
PORT  = 80
USER  = "admin"
SENHA = "Orl809423"   # <-- trocar

BASE    = f"http://{HOST}:{PORT}"
PATH    = "/ISAPI/System/deviceInfo"
HEADERS = {"Accept-Encoding": "identity"}

print("=" * 50)
print(f"Testando {BASE}{PATH}")
print("=" * 50)

# Teste 1: Digest (padrão Hikvision)
print("\n► Digest Auth:")
try:
    r = requests.get(BASE + PATH, auth=HTTPDigestAuth(USER, SENHA),
                     headers=HEADERS, timeout=8, verify=False)
    print(f"  HTTP {r.status_code}")
    print(r.text[:300])
except Exception as e:
    print(f"  ERRO: {e}")

# Teste 2: Basic Auth
print("\n► Basic Auth:")
try:
    r = requests.get(BASE + PATH, auth=HTTPBasicAuth(USER, SENHA),
                     headers=HEADERS, timeout=8, verify=False)
    print(f"  HTTP {r.status_code}")
    print(r.text[:300])
except Exception as e:
    print(f"  ERRO: {e}")

# Teste 3: Sem auth (ver se retorna 401 ou outro código)
print("\n► Sem autenticação:")
try:
    r = requests.get(BASE + PATH, headers=HEADERS, timeout=8, verify=False)
    print(f"  HTTP {r.status_code}")
    print(r.text[:300])
except Exception as e:
    print(f"  ERRO: {e}")

# Teste 4: Porta alternativa 8080
print(f"\n► Digest Auth na porta 8080:")
try:
    r = requests.get(f"http://{HOST}:8080{PATH}",
                     auth=HTTPDigestAuth(USER, SENHA),
                     headers=HEADERS, timeout=5, verify=False)
    print(f"  HTTP {r.status_code}")
    print(r.text[:300])
except Exception as e:
    print(f"  ERRO: {e}")
