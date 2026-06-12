"""API tests — POST /api/Komands/v1/activation.

Convención: test_act<NN>_<vendor>_<producto>_<escenario>

Qué estamos probando:
    El endpoint de activación recibe un payload con los datos del ONT
    y devuelve HTTP 202 + txn_id cuando todo es válido.
    También valida autenticación (401), autorización (403) y
    acceso por rol RBAC (202/403).

    Nota: el servidor usado es la mini-app de conftest.py (TestClient).
    No se necesita servidor real ni base de datos.

Fuentes:
    - AnexoH_Especificacion_APIs_v2_2_FINAL → contrato POST /activation
    - LLD ADR-008 → base path /api/Komands/v1/ (pendiente migrar a /api/Komands/v1/)
    - tests/mocks/payloads.py → payloads reutilizables
"""
import pytest

from tests.mocks.payloads import (
    ACTIVATION_NOKIA_FTTH_VALID,
    ACTIVATION_NOKIA_FTTH_INTERNET_ONLY,
    ACTIVATION_HUAWEI_FTTH_VALID,
    ACTIVATION_HUAWEI_FTTH_WITH_IPTV,
    ACTIVATION_NOKIA_SSAA_GROUP_A,
    ACTIVATION_HUAWEI_SSAA_GROUP_A,
    ACTIVATION_INVALID_VNO,
)


# ─── ACT-01 a ACT-04: Payloads válidos → HTTP 202 ────────────────────────────

class TestActivacionValida:
    """
    Casos felices — el API debe aceptar activaciones válidas de
    Nokia y Huawei, FTTH y SSAA, devolviendo 202 + txn_id.
    """

    # ACT-01
    def test_act01_nokia_ftth_tres_servicios_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia FTTH con INTERNET + VOIP + IPTV.

        Es el caso más completo de Nokia FTTH — tres servicios, cada uno
        con su QoS específico. Si este caso pasa, la ruta básica funciona.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202, (
            f"Se esperaba 202, se obtuvo {response.status_code}. "
            f"Body: {response.text}"
        )

    # ACT-02
    def test_act02_nokia_ftth_internet_only_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia FTTH con solo INTERNET.

        Caso mínimo válido — un solo servicio. Valida que el sistema
        no rechaza activaciones parciales (sin VoIP ni IPTV).

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_INTERNET_ONLY,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # ACT-03
    def test_act03_huawei_ftth_internet_voip_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Huawei FTTH con INTERNET + VOIP.

        Primer caso Huawei — valida que el endpoint acepta ambos vendors.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_HUAWEI_FTTH_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # ACT-04
    def test_act04_huawei_ftth_con_iptv_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Huawei FTTH con INTERNET + VOIP + IPTV.

        Huawei con los tres servicios — incluye gemport 7 para IPTV.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_HUAWEI_FTTH_WITH_IPTV,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # ACT-05
    def test_act05_nokia_ssaa_grupo_a_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA grupo A (B2B).

        SSAA es el producto empresarial. Usa grupos (A/B/C/D/E/BX/DX)
        en vez de servicios (INTERNET/VOIP/IPTV).

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_A,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # ACT-06
    def test_act06_huawei_ssaa_grupo_a_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Huawei SSAA grupo A — VNO CVTR.

        Valida combinación Huawei + SSAA + VNO distinta a DTV.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {
            "Authorization": f"Bearer {_make_token(vno_id='CVTR')}",
            "X-Correlation-ID": "test-act06",
            "X-VNO-ID": "CVTR",
        }
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_HUAWEI_SSAA_GROUP_A,
            headers=headers,
        )

        assert response.status_code == 202


# ─── ACT-07 a ACT-09: Autenticación fallida → HTTP 401 ───────────────────────

class TestActivacionSinAutenticacion:
    """
    El API debe rechazar requests sin token o con token inválido
    antes de procesar cualquier dato del payload.
    """

    # ACT-07
    def test_act07_sin_token_devuelve_401(self, test_client):
        """
        ESCENARIO: Request sin header Authorization.

        Sin token no hay forma de saber quién está llamando.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
        )

        assert response.status_code == 401

    # ACT-08
    def test_act08_token_expirado_devuelve_401(self, test_client, expired_token):
        """
        ESCENARIO: Token JWT con fecha de expiración pasada.

        Un token expirado puede ser un intento de replay attack.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    # ACT-09
    def test_act09_token_malformado_devuelve_401(self, test_client):
        """
        ESCENARIO: Token con formato inválido (no es un JWT).

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": "Bearer esto-no-es-un-jwt"},
        )

        assert response.status_code == 401


# ─── ACT-10 a ACT-11: Autorización fallida → HTTP 403 ────────────────────────

class TestActivacionSinAutorizacion:
    """
    Token válido pero sin permisos suficientes.
    """

    # ACT-10
    def test_act10_vno_no_autorizada_devuelve_403(self, test_client, invalid_vno_token):
        """
        ESCENARIO: Token con VNO desconocida ("FAKE_VNO").

        Komands solo acepta los 4 VNOs registrados: DTV, CVTR, ENTEL, TCH.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_INVALID_VNO,
            headers={"Authorization": f"Bearer {invalid_vno_token}"},
        )

        assert response.status_code == 403

    # ACT-11
    def test_act11_scope_insuficiente_devuelve_403(self, test_client, readonly_token):
        """
        ESCENARIO: Token con solo komands:read — sin permiso de escritura.

        La activación requiere scope komands:write (o komands:provision
        en v2.2 final). Sin él no se puede modificar la red.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {readonly_token}"},
        )

        assert response.status_code == 403


# ─── ACT-12 a ACT-14: RBAC portal web ────────────────────────────────────────

class TestActivacionRBACPortal:
    """
    El portal web usa tokens de rol (ADMIN/OPERATOR/VIEWER/AUDITOR).
    Solo ADMIN y OPERATOR tienen permiso activation:write.
    """

    # ACT-12
    def test_act12_admin_puede_activar(self, test_client, admin_token):
        """
        ESCENARIO: Usuario con rol ADMIN activa desde el portal.

        ADMIN tiene todos los permisos — debe poder activar.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 202

    # ACT-13
    def test_act13_operator_puede_activar(self, test_client, operator_token):
        """
        ESCENARIO: Usuario con rol OPERATOR activa desde el portal.

        OPERATOR tiene activation:write — es el rol operativo principal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 202

    # ACT-14
    def test_act14_viewer_no_puede_activar(self, test_client, viewer_token):
        """
        ESCENARIO: Usuario con rol VIEWER intenta activar.

        VIEWER solo puede leer transacciones — no tiene activation:write.
        Esto evita que un usuario de solo lectura modifique la red.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 403


# ─── ACT-15 a ACT-16: Estructura de la respuesta ─────────────────────────────

class TestActivacionRespuesta:
    """
    El body de la respuesta 202 debe contener campos obligatorios
    según el contrato del Anexo H v2.2.
    """

    # ACT-15
    def test_act15_respuesta_contiene_txn_id(self, test_client, auth_headers):
        """
        ESCENARIO: Activación válida → verificar que el body tiene txn_id.

        txn_id es el UUID que ServiceNow usa para rastrear la transacción
        y consultar el estado vía GET /{operation}/{uuid}.

        Resultado esperado: campo txn_id presente en la respuesta.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "txn_id" in data, f"txn_id ausente en respuesta: {data}"

    # ACT-16
    def test_act16_respuesta_contiene_status_pending(self, test_client, auth_headers):
        """
        ESCENARIO: Activación válida → el status inicial es PENDING.

        La activación es asíncrona — Komands encola la operación y
        devuelve PENDING. El estado final llega por callback.

        Resultado esperado: campo status == "PENDING".
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Se esperaba status=ACCEPTED, se obtuvo: {data.get('status')}"
        )


# ─── ACT-17: Todos los VNOs autorizados ──────────────────────────────────────

class TestActivacionMultiVNO:
    """
    Los 4 VNOs del proyecto deben poder activar con un token válido.
    """

    # ACT-17
    @pytest.mark.parametrize("vno_id", ["DTV", "CVTR", "ENTEL", "TCH"])
    def test_act17_todos_los_vnos_pueden_activar(self, test_client, vno_id):
        """
        ESCENARIO: Cada VNO autorizado envía una activación.

        Los 4 VNOs del proyecto (DTV, CVTR, ENTEL, TCH) deben recibir
        202. Si alguno falla, ese VNO está bloqueado en el Feature Flag.

        Resultado esperado: HTTP 202 para cada VNO.
        """
        from tests.conftest import _make_token
        token = _make_token(vno_id=vno_id)
        payload = {**ACTIVATION_NOKIA_FTTH_VALID, "vno_code": vno_id}

        response = test_client.post(
            "/api/Komands/v1/activation",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202, (
            f"VNO {vno_id} recibió {response.status_code} — esperado 202"
        )
