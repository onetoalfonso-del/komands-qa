"""
Fixtures para tests de integración contra APIM real (ambiente PRE).

Lee credenciales del environment de Postman existente — no hardcodea nada.
El token OAuth2 (client_credentials) se obtiene una vez por sesión y dura ~1 hora.

Opción --run-id (1-9): cambia el último dígito de los datos de prueba para evitar
conflictos entre ejecuciones paralelas o sucesivas.

Archivo de environment esperado:
    collection Blueplanet/VnoB1_vnoid03 PRE.postman_environment.json

Ejemplos:
    pytest tests/integration/ -m integration --no-cov              # usa run-id 1 por defecto
    pytest tests/integration/ -m integration --no-cov --run-id 3   # usa instancia 3
"""
import json
import base64
from pathlib import Path

import httpx
import pytest

_ENV_FILE = Path("collection Blueplanet/VnoB1_vnoid03 PRE.postman_environment.json")

# ─── Base de datos de prueba ──────────────────────────────────────────────────
# El último dígito se reemplaza con el --run-id elegido.

_VNO            = "03"
_ACCESS_ID_BASE = "03-TESTPREPROD-DIR02803674-"   # + run_id  → ej: -1, -2, -3
_SERIAL_BASE    = "SCOM1303200"                   # + run_id  → ej: SCOM13032001
_SPEED_PLAN     = "940/940"


# ─── CLI option ──────────────────────────────────────────────────────────────

def pytest_addoption(parser):
    parser.addoption(
        "--run-id",
        action="store",
        default="1",
        help="Número de instancia de prueba (1-9). Cambia el último dígito del "
             "access_id y serial para evitar conflictos. Por defecto: 1",
    )


# ─── Fixtures de datos de prueba ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def run_id(request) -> str:
    rid = request.config.getoption("--run-id")
    assert rid.isdigit() and 1 <= int(rid) <= 9, "--run-id debe ser un número del 1 al 9"
    return rid


@pytest.fixture(scope="session")
def apim_vno() -> str:
    return _VNO


@pytest.fixture(scope="session")
def apim_access_id(run_id: str) -> str:
    """ACCESS ID de prueba — el sufijo numérico cambia con --run-id."""
    return f"{_ACCESS_ID_BASE}{run_id}"


@pytest.fixture(scope="session")
def apim_serial(run_id: str) -> str:
    """Serial de prueba — el último dígito cambia con --run-id."""
    return f"{_SERIAL_BASE}{run_id}"


@pytest.fixture(scope="session")
def apim_speed_plan() -> str:
    return _SPEED_PLAN


# ─── Fixtures de conexión ─────────────────────────────────────────────────────

def _load_postman_env() -> dict:
    data = json.loads(_ENV_FILE.read_text(encoding="utf-8"))
    return {v["key"]: v["value"] for v in data["values"]}


def _fetch_token(apim_url: str, consumer_key: str, consumer_secret: str) -> str:
    credentials = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
    resp = httpx.post(
        f"{apim_url}/token",
        headers={"Authorization": f"Basic {credentials}"},
        data={"grant_type": "client_credentials"},
        timeout=30.0,
        verify=False,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def apim_env() -> dict:
    return _load_postman_env()


@pytest.fixture(scope="session")
def apim_token(apim_env: dict) -> str:
    return _fetch_token(
        apim_env["apimURL"],
        apim_env["consumerKey"],
        apim_env["consumerSecret"],
    )


@pytest.fixture(scope="session")
def apim_headers(apim_token: str) -> dict:
    return {
        "Authorization": f"Bearer {apim_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="session")
def apim_client(apim_env: dict):
    with httpx.Client(base_url=apim_env["apimURL"], timeout=30.0, verify=False) as client:
        yield client
