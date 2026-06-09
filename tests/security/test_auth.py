"""
Tests de autenticación — SEC-01 a SEC-06
=========================================
Fuente: docs/05_gaps_seguridad.md → sección "Autenticación APIs"

Qué estamos probando:
    El API Gateway de Komands debe rechazar cualquier request que no traiga
    un JWT válido con los claims correctos. Esto protege todos los endpoints
    de red (/activation, /deactivation, etc.).

Cómo funciona cada test:
    1. ARRANGE  — preparamos el estado inicial (headers, token, payload)
    2. ACT      — hacemos el request HTTP
    3. ASSERT   — verificamos que el código de respuesta es el esperado

El payload JSON siempre es válido en estos tests. Lo que cambiamos
es el HEADER de autenticación, para aislar exactamente lo que probamos.
"""

import pytest
from fastapi.testclient import TestClient

from tests.mocks.payloads import ACTIVATION_NOKIA_FTTH_VALID

# Usamos este payload en todos los tests.
# No es lo que estamos probando — solo necesitamos un body válido
# para que el endpoint no rechace por campos faltantes.
PAYLOAD = ACTIVATION_NOKIA_FTTH_VALID


class TestAutenticacionAPI:
    """
    Los 6 casos SEC del documento de seguridad.

    Por qué usamos una clase:
        Agrupa todos los casos relacionados. pytest la descubre automáticamente
        porque el nombre empieza con "Test".
    """

    # ──────────────────────────────────────────────────────────────────────────
    # SEC-01: Sin token
    # ──────────────────────────────────────────────────────────────────────────

    def test_sec01_sin_token_devuelve_401(self, test_client: TestClient):
        """
        ESCENARIO: El request llega sin header Authorization.

        Por qué debe fallar:
            Sin token no hay forma de saber quién hace el request ni
            a qué VNO pertenece. Es la primera línea de defensa.

        Resultado esperado: HTTP 401 Unauthorized
        """
        # ARRANGE: no ponemos ningún header de autenticación
        # ACT: hacemos el request como si viniese desde ServiceNow sin auth
        response = test_client.post("/api/v1/activation", json=PAYLOAD)

        # ASSERT: el servidor debe rechazarlo con 401
        assert response.status_code == 401, (
            f"Sin token se esperaba 401 pero llegó {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # SEC-02: Token malformado
    # ──────────────────────────────────────────────────────────────────────────

    def test_sec02_token_malformado_devuelve_401(self, test_client: TestClient):
        """
        ESCENARIO: El header Authorization viene con un string que no es JWT.

        Por qué puede pasar:
            Un cliente mal configurado, un ataque de fuerza bruta,
            o un token de otro sistema.

        Resultado esperado: HTTP 401 Unauthorized
        """
        # ARRANGE: el token es una cadena aleatoria, no un JWT firmado
        headers = {"Authorization": "Bearer esto_no_es_un_jwt_valido_abc123"}

        # ACT
        response = test_client.post("/api/v1/activation", json=PAYLOAD, headers=headers)

        # ASSERT
        assert response.status_code == 401, (
            f"Token malformado se esperaba 401 pero llegó {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # SEC-03: Token expirado
    # ──────────────────────────────────────────────────────────────────────────

    def test_sec03_token_expirado_devuelve_401(
        self, test_client: TestClient, expired_token: str
    ):
        """
        ESCENARIO: El token es un JWT bien formado pero ya expiró (exp en el pasado).

        Por qué puede pasar:
            Los tokens duran 1 hora. Si ServiceNow reutiliza uno viejo
            o el reloj está desincronizado, el token puede llegar vencido.

        El fixture 'expired_token' viene del conftest.py — tiene exp = ahora - 60s.

        Resultado esperado: HTTP 401 Unauthorized
        """
        # ARRANGE: usamos el fixture que nos da un token ya vencido
        headers = {"Authorization": f"Bearer {expired_token}"}

        # ACT
        response = test_client.post("/api/v1/activation", json=PAYLOAD, headers=headers)

        # ASSERT
        assert response.status_code == 401, (
            f"Token expirado se esperaba 401 pero llegó {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # SEC-04: Token válido — el caso feliz
    # ──────────────────────────────────────────────────────────────────────────

    def test_sec04_token_valido_devuelve_202(
        self, test_client: TestClient, valid_token: str
    ):
        """
        ESCENARIO: JWT válido, no expirado, VNO=DTV, scope correcto.

        Este es el "caso feliz" — el camino normal que siguen todas las
        operaciones de ServiceNow en producción.

        Resultado esperado: HTTP 202 Accepted + txn_id en el body
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {valid_token}"}

        # ACT
        response = test_client.post("/api/v1/activation", json=PAYLOAD, headers=headers)

        # ASSERT: el código es 202
        assert response.status_code == 202, (
            f"Token válido se esperaba 202 pero llegó {response.status_code}"
        )

        # También verificamos la estructura del body de respuesta
        body = response.json()
        assert "txn_id" in body, "La respuesta debe incluir txn_id"
        assert body["status"] == "ACCEPTED", "El estado inicial debe ser ACCEPTED"

    # ──────────────────────────────────────────────────────────────────────────
    # SEC-05: VNO no autorizada
    # ──────────────────────────────────────────────────────────────────────────

    def test_sec05_vno_no_autorizada_devuelve_403(
        self, test_client: TestClient, invalid_vno_token: str
    ):
        """
        ESCENARIO: JWT válido y firmado, pero el claim vno_id = 'FAKE_VNO'
                   que no está en la lista de VNOs de ON·NET.

        Por qué importa:
            Aunque el token esté bien firmado, solo las 4 VNOs reales
            (DTV, CVTR, ENTEL, TCH) pueden operar en Komands.

        El fixture 'invalid_vno_token' viene del conftest.py.

        Resultado esperado: HTTP 403 Forbidden (no 401, porque el token
        en sí es válido — el problema es la autorización, no la autenticación)
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {invalid_vno_token}"}

        # ACT
        response = test_client.post("/api/v1/activation", json=PAYLOAD, headers=headers)

        # ASSERT: 403, no 401 — la diferencia es importante
        assert response.status_code == 403, (
            f"VNO inválida se esperaba 403 pero llegó {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # SEC-06: Scope insuficiente
    # ──────────────────────────────────────────────────────────────────────────

    def test_sec06_scope_insuficiente_devuelve_403(
        self, test_client: TestClient, readonly_token: str
    ):
        """
        ESCENARIO: JWT válido con VNO=DTV, pero scope = 'komands:read'.
                   El cliente solo tiene permiso de lectura e intenta un POST.

        Por qué importa:
            El scope 'komands:write' es obligatorio para todas las operaciones
            que modifican la red (activation, deactivation, etc.).
            Un cliente de solo lectura (ej: monitoreo) no puede activar servicios.

        El fixture 'readonly_token' viene del conftest.py.

        Resultado esperado: HTTP 403 Forbidden
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {readonly_token}"}

        # ACT
        response = test_client.post("/api/v1/activation", json=PAYLOAD, headers=headers)

        # ASSERT
        assert response.status_code == 403, (
            f"Scope insuficiente se esperaba 403 pero llegó {response.status_code}"
        )
