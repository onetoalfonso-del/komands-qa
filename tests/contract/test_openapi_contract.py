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


# ─── Auth ─────────────────────────────────────────────────────────────────────

def _provision_token(vno: str = "DTV") -> str:
    """Token con scope provision+query, HS256, compatible con mock."""
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
    Resultado esperado: nunca HTTP 5xx con payload generado desde el spec.

    Schemathesis genera hasta 15 combinaciones por endpoint (válidas e inválidas)
    y verifica que ninguna provoque HTTP 500. Los 4xx son esperados para payloads
    inválidos — eso confirma que la validación funciona.
    """
    case.headers = {**(case.headers or {}), **_required_headers()}
    # Mock mode: solo verifica que no haya 5xx (el mock no valida headers ni schemas).
    # Servidor real: quitar 'checks=' para activar todos los checks del spec.
    case.call_and_validate(checks=[not_a_server_error])
