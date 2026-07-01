"""
Fixtures E2E.

Por defecto: corre contra el mock local (sin infraestructura).
Contra servidor real: define la variable de entorno KOMANDS_E2E_URL.

Ejemplos:
    # modo mock (default — para demo y CI)
    pytest tests/e2e/ -v

    # modo real (requiere servidor desplegado y credenciales)
    $env:KOMANDS_E2E_URL      = "https://onf-komands.cl:9016"
    $env:KOMANDS_E2E_CLIENT_ID     = "<client_id>"
    $env:KOMANDS_E2E_CLIENT_SECRET = "<client_secret>"
    pytest tests/e2e/ -v -m e2e
"""
import os
import pytest
import httpx
from fastapi.testclient import TestClient

from tests.conftest import _build_test_app, _make_portal_token

_E2E_URL    = os.getenv("KOMANDS_E2E_URL", "").rstrip("/")
_CLIENT_ID  = os.getenv("KOMANDS_E2E_CLIENT_ID", "")
_SECRET     = os.getenv("KOMANDS_E2E_CLIENT_SECRET", "")

_BASE = "/api/Komands/v1"


@pytest.fixture(scope="module")
def e2e_client():
    """Cliente HTTP apuntando al mock (default) o al servidor real (si KOMANDS_E2E_URL está definido)."""
    if _E2E_URL:
        with httpx.Client(base_url=_E2E_URL, verify=False, timeout=30.0) as client:
            yield client
    else:
        yield TestClient(_build_test_app(), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def e2e_token(e2e_client):
    """
    Token JWT para el flujo E2E.
    - Mock: token de portal ADMIN (cubre escritura + lectura).
    - Real: obtiene token OAuth2 via POST /auth/token con client_credentials.
    """
    if _E2E_URL and _CLIENT_ID:
        resp = e2e_client.post(
            f"{_BASE}/auth/token",
            data={
                "grant_type":    "client_credentials",
                "client_id":     _CLIENT_ID,
                "client_secret": _SECRET,
            },
        )
        assert resp.status_code == 200, f"Auth falló: {resp.text}"
        return resp.json()["access_token"]
    return _make_portal_token("ADMIN")


@pytest.fixture(scope="module")
def e2e_headers(e2e_token):
    """Headers HTTP estándar para todo el flujo E2E."""
    return {
        "Authorization":    f"Bearer {e2e_token}",
        "X-Correlation-ID": "e2e-ciclo-vida-nokia-001",
        "X-Source-System":  "ServiceNow",
        "Content-Type":     "application/json",
    }


def e2e_modo() -> str:
    return f"REAL ({_E2E_URL})" if _E2E_URL else "MOCK (local)"
