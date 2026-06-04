"""API tests — POST /api/v1/reset-ont (Reset ONT FTTH).

Convención: test_rst<NN>_<vendor>_<vno>_<escenario>

Fuentes:
    - Plan_Pruebas_Completo_v3_Final.xlsx → Release 1 → PV-RST-270 a PV-RST-289
    - SLO: operación < 15s (P95) — verificable solo con servidor real
    - Error KMD-2002: ONT no encontrado → verificable con servidor real
"""
import pytest

from tests.mocks.payloads import RESET_ONT_NOKIA_VALID, RESET_ONT_HUAWEI_VALID

pytestmark = pytest.mark.postventa


# ─── RST-01 a RST-04: Payloads válidos → HTTP 202 ────────────────────────────

class TestResetValido:
    """Casos felices — el API acepta resets de Nokia y Huawei FTTH."""

    # RST-01
    def test_rst01_nokia_ftth_dtv_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Reset Nokia FTTH — VNO DTV (caso base).

        Reset reinicia el ONT sin borrar la configuración. Es la operación
        más rápida de post-venta: no requiere reconfigurar el servicio.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_NOKIA_VALID,
            headers=auth_headers,
        )
        assert response.status_code == 202, (
            f"Se esperaba 202, se obtuvo {response.status_code}. Body: {response.text}"
        )

    # RST-02
    def test_rst02_huawei_ftth_dtv_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Reset Huawei FTTH — VNO DTV.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_HUAWEI_VALID,
            headers=auth_headers,
        )
        assert response.status_code == 202

    # RST-03
    def test_rst03_nokia_ftth_clarovtr_devuelve_202(self, test_client):
        """
        ESCENARIO: Reset Nokia FTTH — VNO ClaroVTR.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        response = test_client.post(
            "/api/v1/reset-ont",
            json={**RESET_ONT_NOKIA_VALID, "vno_id": "ClaroVTR"},
            headers={"Authorization": f"Bearer {_make_token(vno_id='ClaroVTR')}"},
        )
        assert response.status_code == 202

    # RST-04
    def test_rst04_nokia_ftth_entel_devuelve_202(self, test_client):
        """
        ESCENARIO: Reset Nokia FTTH — VNO Entel.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        response = test_client.post(
            "/api/v1/reset-ont",
            json={**RESET_ONT_NOKIA_VALID, "vno_id": "Entel"},
            headers={"Authorization": f"Bearer {_make_token(vno_id='Entel')}"},
        )
        assert response.status_code == 202


# ─── RST-05 a RST-07: Autenticación fallida → HTTP 401 ───────────────────────

class TestResetSinAutenticacion:

    # RST-05
    def test_rst05_sin_token_devuelve_401(self, test_client):
        """
        ESCENARIO: Reset sin header Authorization.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post("/api/v1/reset-ont", json=RESET_ONT_NOKIA_VALID)
        assert response.status_code == 401

    # RST-06
    def test_rst06_token_expirado_devuelve_401(self, test_client, expired_token):
        """
        ESCENARIO: Token JWT expirado.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_NOKIA_VALID,
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    # RST-07
    def test_rst07_token_malformado_devuelve_401(self, test_client):
        """
        ESCENARIO: Token con formato inválido.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_NOKIA_VALID,
            headers={"Authorization": "Bearer no-es-un-jwt"},
        )
        assert response.status_code == 401


# ─── RST-08 a RST-09: Autorización fallida → HTTP 403 ────────────────────────

class TestResetSinAutorizacion:

    # RST-08
    def test_rst08_vno_no_autorizada_devuelve_403(self, test_client, invalid_vno_token):
        """
        ESCENARIO: Token con VNO desconocida.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_NOKIA_VALID,
            headers={"Authorization": f"Bearer {invalid_vno_token}"},
        )
        assert response.status_code == 403

    # RST-09
    def test_rst09_scope_insuficiente_devuelve_403(self, test_client, readonly_token):
        """
        ESCENARIO: Token con solo komands:read.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_NOKIA_VALID,
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 403


# ─── RST-10 a RST-12: RBAC portal web ────────────────────────────────────────

class TestResetRBACPortal:

    # RST-10
    def test_rst10_admin_puede_resetear(self, test_client, admin_token):
        """
        ESCENARIO: Rol ADMIN resetea desde el portal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_NOKIA_VALID,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 202

    # RST-11
    def test_rst11_operator_puede_resetear(self, test_client, operator_token):
        """
        ESCENARIO: Rol OPERATOR resetea desde el portal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_NOKIA_VALID,
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 202

    # RST-12
    def test_rst12_viewer_no_puede_resetear(self, test_client, viewer_token):
        """
        ESCENARIO: Rol VIEWER intenta resetear.

        VIEWER solo puede leer — no puede modificar la red.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/reset-ont",
            json=RESET_ONT_NOKIA_VALID,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403


# ─── RST-13 a RST-14: Estructura de la respuesta ─────────────────────────────

class TestResetRespuesta:

    # RST-13
    def test_rst13_respuesta_contiene_txn_id(self, test_client, auth_headers):
        """
        ESCENARIO: Reset válido → body tiene txn_id.

        Resultado esperado: campo txn_id presente.
        """
        response = test_client.post(
            "/api/v1/reset-ont", json=RESET_ONT_NOKIA_VALID, headers=auth_headers
        )
        assert response.status_code == 202
        assert "txn_id" in response.json()

    # RST-14
    def test_rst14_respuesta_contiene_status_pending(self, test_client, auth_headers):
        """
        ESCENARIO: Reset válido → status inicial es PENDING.

        Resultado esperado: campo status == "PENDING".
        """
        response = test_client.post(
            "/api/v1/reset-ont", json=RESET_ONT_NOKIA_VALID, headers=auth_headers
        )
        assert response.status_code == 202
        assert response.json().get("status") == "PENDING"


# ─── RST-15: Todos los VNOs ───────────────────────────────────────────────────

class TestResetMultiVNO:

    # RST-15
    @pytest.mark.parametrize("vno_id", ["DTV", "ClaroVTR", "Entel", "TCH"])
    def test_rst15_todos_los_vnos_pueden_resetear(self, test_client, vno_id):
        """
        ESCENARIO: Los 4 VNOs autorizados pueden resetear un ONT.

        Resultado esperado: HTTP 202 para cada VNO.
        """
        from tests.conftest import _make_token
        response = test_client.post(
            "/api/v1/reset-ont",
            json={**RESET_ONT_NOKIA_VALID, "vno_id": vno_id},
            headers={"Authorization": f"Bearer {_make_token(vno_id=vno_id)}"},
        )
        assert response.status_code == 202, (
            f"VNO {vno_id} recibió {response.status_code} — esperado 202"
        )
