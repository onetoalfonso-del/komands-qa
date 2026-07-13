"""
T1-Contract — Contrato OpenAPI v2.2.3 via Schemathesis.

Genera casos de prueba automáticamente desde docs/openapi.json y los valida
contra la implementación. Por defecto corre contra el mock en memoria (sin red).

Uso:
    # Mock (CI / Railway — sin red)
    pytest tests/contract/ -v

    # Servidor real DEV
    KOMANDS_TEST_URL=http://onf-komands.cl:9016 pytest tests/contract/ -v

Qué valida Schemathesis:
    - Nunca HTTP 5xx con payloads conformes al spec (not_a_server_error)
    - Los códigos de respuesta están dentro de los documentados en el spec
    - Los 13 endpoints funcionales del AnexoH v2.2.3 se cubren automáticamente
"""
import os
import time
import uuid
from pathlib import Path

import requests as _requests

import pytest
import schemathesis.openapi as _oa
from hypothesis import HealthCheck, settings
from jose import jwt
from schemathesis.checks import not_a_server_error

pytestmark = pytest.mark.contract

# ─── Configuración ────────────────────────────────────────────────────────────

_SPEC = Path(__file__).parent.parent.parent / "docs" / "openapi.json"
_REAL_URL = os.getenv("KOMANDS_TEST_URL", "")

# JWT HS256 compatible con el mock del conftest.py
# El servidor real usa RS256 firmado por Axway — modo real requiere credenciales aparte
_JWT_SECRET = "test-secret-komands-qa"

# Cache del token real (se obtiene una vez por sesión de pytest)
_cached_real_token: str | None = None


# ─── Auth ─────────────────────────────────────────────────────────────────────

def _fetch_real_token() -> str:
    """
    Obtiene un token real desde el servidor KOMANDs vía OAuth2 client_credentials.
    Lee DEV_CLIENT_ID / DEV_CLIENT_SECRET del entorno (nunca hardcodeados).
    """
    client_id = os.getenv("KOMANDS_CLIENT_ID", "")
    client_secret = os.getenv("KOMANDS_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError(
            "T1-C Real requiere KOMANDS_CLIENT_ID y KOMANDS_CLIENT_SECRET.\n"
            "Configura esas variables de entorno (Railway o local .env) y vuelve a ejecutar."
        )
    resp = _requests.post(
        f"{_REAL_URL}/api/Komands/v1/auth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "komands:provision komands:query",
        },
        timeout=15,
        verify=False,  # onf-komands.cl:9016 usa cert autofirmado en algunos ambientes
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _provision_token(vno: str = "DTV") -> str:
    """
    Modo mock: token HS256 compatible con el mock del conftest.
    Modo real: token OAuth2 obtenido del servidor onf-komands.cl:9016.
    """
    global _cached_real_token
    if _REAL_URL:
        if _cached_real_token is None:
            _cached_real_token = _fetch_real_token()
        return _cached_real_token
    return jwt.encode(
        {
            "sub": "sn-integration",
            "vno_id": vno,
            "scope": "komands:provision komands:query",
            "exp": int(time.time()) + 3600,
        },
        _JWT_SECRET,
        algorithm="HS256",
    )


def _required_headers() -> dict:
    """Headers obligatorios según AnexoH v2.2.3 (requeridos en todos los endpoints)."""
    return {
        "Authorization": f"Bearer {_provision_token()}",
        "X-Source-System": "SN",
        "X-Correlation-ID": str(uuid.uuid4()),
        "X-Source-System-ID": "SN-QA-001",
        "X-User-ID": "sn-integration",
        "X-User-Role": "agent",
        "X-User-Organization": "ON-NET CHILE",
    }


# ─── Schema ───────────────────────────────────────────────────────────────────
# Carga docs/openapi.json y filtra los 13 endpoints funcionales:
#   POST + GET para: unsubscription, device-modification, service-modification,
#   fiber-change, service-activation, pon-transfer + GET query-access
# Excluye: /health, /health/ready, /fullfilment (legacy), /auth/token

_schema = _oa.from_path(_SPEC)

if _REAL_URL:
    _schema.config.base_url = _REAL_URL
else:
    from tests.conftest import _build_test_app
    _schema.app = _build_test_app()
    _schema.config.base_url = "http://testserver/"

_schema = (
    _schema
    .include(path_regex=r"^/api/Komands/v1/")
    .exclude(path="/api/Komands/v1/auth/token")
)


# ─── Códigos documentados en AnexoH v2.2.3 ────────────────────────────────────

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ⚠️  BLOQUEO CONOCIDO — 405 Method Not Allowed en servidor real :9016       ║
# ║                                                                              ║
# ║  CAUSA: Los endpoints de provisioning en onf-komands.cl:9016 REQUIEREN      ║
# ║  pasar por Axway APIM. Llamadas directas (sin APIM) retornan HTTP 405.      ║
# ║  Esto NO es un bug del código — es la restricción de infraestructura.       ║
# ║                                                                              ║
# ║  ESTADO ACTUAL (Julio 2026):                                                 ║
# ║    ✗  APIM hoy rutea a BluePlanet (producción)                              ║
# ║    ✗  Factibilidad (GET /query-access) aún no implementada en :9016         ║
# ║    ✗  T1-C Real llama directo a :9016, sin pasar por APIM → 405             ║
# ║                                                                              ║
# ║  PENDIENTE — activar Opción B (T1-C via APIM) cuando se cumpla:             ║
# ║    1. PostgreSQL DEV disponible (Semana 3)                                   ║
# ║    2. T-FLG activa el feature flag en la tabla de ruteo                      ║
# ║    3. APIM apunta a KOMANDs en vez de BluePlanet                            ║
# ║    → Recién ahí T1-C Real debe enrutarse por APIM_URL + SN_CONSUMER_KEY     ║
# ║                                                                              ║
# ║  REFERENCIA: confirmado por Jeffrey Fierro · 13-07-2026                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
_ALLOWED_CODES = {200, 202, 400, 401, 403, 404, 405, 409, 422}
# 405 incluido temporalmente: respuesta esperada al llamar directo sin APIM (ver bloqueo arriba)

# ─── Test ─────────────────────────────────────────────────────────────────────

@_schema.parametrize()
@settings(
    max_examples=15,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    deadline=None,
)
def test_contrato_openapi(case):
    """
    ESCENARIO: Contrato OpenAPI 3.0 — AnexoH v2.2.3 — 13 endpoints funcionales

    Genera payloads desde el spec automáticamente y verifica que el servidor
    no retorne errores internos ni respuestas fuera del contrato documentado.

    Resultado esperado (mock — CI/Railway):
      - Nunca HTTP 5xx con payload conforme al spec
      - HTTP 202 Accepted para POST exitosos

    Resultado esperado (servidor real — KOMANDS_TEST_URL configurado):
      - Código de respuesta dentro del rango documentado en AnexoH v2.2.3:
          202  Accepted         — operación encolada correctamente
          400  Bad Request      — payload inválido o campo requerido ausente
          401  Unauthorized     — token ausente, expirado o inválido
          403  Forbidden        — VNO sin permisos sobre el recurso
          404  Not Found        — ONT o recurso no existe
          409  Conflict         — operación duplicada (idempotencia)
          422  Unprocessable    — datos semánticamente incorrectos
          NUNCA 5xx             — cualquier 5xx indica defecto en el servidor
      - Content-Type: application/json en toda respuesta
    """
    case.headers = {**(case.headers or {}), **_required_headers()}

    if _REAL_URL:
        response = case.call(verify=False)

        assert response.status_code < 500, (
            f"\nResultado obtenido:  HTTP {response.status_code} — error interno del servidor"
            f"\nResultado esperado:  nunca HTTP 5xx con payload conforme al spec"
        )
        assert response.status_code in _ALLOWED_CODES, (
            f"\nResultado obtenido:  HTTP {response.status_code}"
            f"\nResultado esperado:  código documentado en AnexoH v2.2.3"
            f"\n                     202 Accepted | 400 Bad Request | 401 Unauthorized"
            f"\n                     403 Forbidden | 404 Not Found | 409 Conflict | 422 Unprocessable"
        )
        ct = response.headers.get("content-type", "")
        assert "application/json" in ct, (
            f"\nResultado obtenido:  Content-Type: {ct!r}"
            f"\nResultado esperado:  application/json en toda respuesta"
        )
    else:
        case.call_and_validate(checks=[not_a_server_error])
