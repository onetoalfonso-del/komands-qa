"""API tests — POST /api/v1/device-modification (Swap de ONT FTTH).

Convención: test_ont<NN>_<vendor>_<vno>_<escenario>

Fuentes:
    - Plan_Pruebas_Completo_v3_Final.xlsx → Release 1 → PV-ONT-248 a PV-ONT-267
    - Swap = baja ONT viejo + alta ONT nuevo con mismo port/id/servicio
    - Riesgo R10: Huawei requiere service_port_index del ONT viejo
"""
import pytest

from tests.mocks.payloads import DEVICE_MOD_NOKIA_VALID, DEVICE_MOD_HUAWEI_VALID

pytestmark = pytest.mark.postventa


# ─── ONT-01 a ONT-04: Payloads válidos → HTTP 202 ────────────────────────────

class TestSwapValido:
    """Casos felices — el API acepta swaps de Nokia y Huawei FTTH."""

    # ONT-01
    def test_ont01_nokia_ftth_dtv_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Swap Nokia FTTH — VNO DTV.

        El swap reemplaza el serial del ONT físico sin interrumpir el servicio
        más de lo necesario. Es la operación más común cuando el ONT falla.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_NOKIA_VALID,
            headers=auth_headers,
        )
        assert response.status_code == 202, (
            f"Se esperaba 202, se obtuvo {response.status_code}. Body: {response.text}"
        )

    # ONT-02
    def test_ont02_huawei_ftth_dtv_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Swap Huawei FTTH — VNO DTV.

        Huawei requiere que el service-port INDEX del ONT viejo se pase
        en el payload (Riesgo R10).

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_HUAWEI_VALID,
            headers=auth_headers,
        )
        assert response.status_code == 202

    # ONT-03
    def test_ont03_nokia_ftth_clarovtr_devuelve_202(self, test_client):
        """
        ESCENARIO: Swap Nokia FTTH — VNO ClaroVTR.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        response = test_client.post(
            "/api/v1/device-modification",
            json={**DEVICE_MOD_NOKIA_VALID, "vno_id": "ClaroVTR"},
            headers={"Authorization": f"Bearer {_make_token(vno_id='ClaroVTR')}"},
        )
        assert response.status_code == 202

    # ONT-04
    def test_ont04_nokia_ftth_tch_devuelve_202(self, test_client):
        """
        ESCENARIO: Swap Nokia FTTH — VNO TCH (Movistar).

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        response = test_client.post(
            "/api/v1/device-modification",
            json={**DEVICE_MOD_NOKIA_VALID, "vno_id": "TCH"},
            headers={"Authorization": f"Bearer {_make_token(vno_id='TCH')}"},
        )
        assert response.status_code == 202


# ─── ONT-05 a ONT-07: Autenticación fallida → HTTP 401 ───────────────────────

class TestSwapSinAutenticacion:

    # ONT-05
    def test_ont05_sin_token_devuelve_401(self, test_client):
        """
        ESCENARIO: Swap sin header Authorization.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post("/api/v1/device-modification", json=DEVICE_MOD_NOKIA_VALID)
        assert response.status_code == 401

    # ONT-06
    def test_ont06_token_expirado_devuelve_401(self, test_client, expired_token):
        """
        ESCENARIO: Token JWT expirado.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_NOKIA_VALID,
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    # ONT-07
    def test_ont07_token_malformado_devuelve_401(self, test_client):
        """
        ESCENARIO: Token con formato inválido.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_NOKIA_VALID,
            headers={"Authorization": "Bearer no-es-un-jwt"},
        )
        assert response.status_code == 401


# ─── ONT-08 a ONT-09: Autorización fallida → HTTP 403 ────────────────────────

class TestSwapSinAutorizacion:

    # ONT-08
    def test_ont08_vno_no_autorizada_devuelve_403(self, test_client, invalid_vno_token):
        """
        ESCENARIO: Token con VNO desconocida.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_NOKIA_VALID,
            headers={"Authorization": f"Bearer {invalid_vno_token}"},
        )
        assert response.status_code == 403

    # ONT-09
    def test_ont09_scope_insuficiente_devuelve_403(self, test_client, readonly_token):
        """
        ESCENARIO: Token con solo komands:read.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_NOKIA_VALID,
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 403


# ─── ONT-10 a ONT-12: RBAC portal web ────────────────────────────────────────

class TestSwapRBACPortal:

    # ONT-10
    def test_ont10_admin_puede_hacer_swap(self, test_client, admin_token):
        """
        ESCENARIO: Rol ADMIN realiza swap desde el portal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_NOKIA_VALID,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 202

    # ONT-11
    def test_ont11_operator_puede_hacer_swap(self, test_client, operator_token):
        """
        ESCENARIO: Rol OPERATOR realiza swap desde el portal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_NOKIA_VALID,
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 202

    # ONT-12
    def test_ont12_viewer_no_puede_hacer_swap(self, test_client, viewer_token):
        """
        ESCENARIO: Rol VIEWER intenta hacer swap.

        VIEWER solo puede leer — no puede reemplazar equipos.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/device-modification",
            json=DEVICE_MOD_NOKIA_VALID,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403


# ─── ONT-13 a ONT-14: Estructura de la respuesta ─────────────────────────────

class TestSwapRespuesta:

    # ONT-13
    def test_ont13_respuesta_contiene_txn_id(self, test_client, auth_headers):
        """
        ESCENARIO: Swap válido → body tiene txn_id.

        Resultado esperado: campo txn_id presente.
        """
        response = test_client.post(
            "/api/v1/device-modification", json=DEVICE_MOD_NOKIA_VALID, headers=auth_headers
        )
        assert response.status_code == 202
        assert "txn_id" in response.json()

    # ONT-14
    def test_ont14_respuesta_contiene_status_pending(self, test_client, auth_headers):
        """
        ESCENARIO: Swap válido → status inicial es PENDING.

        El swap es asíncrono — el estado final llega por callback.

        Resultado esperado: campo status == "PENDING".
        """
        response = test_client.post(
            "/api/v1/device-modification", json=DEVICE_MOD_NOKIA_VALID, headers=auth_headers
        )
        assert response.status_code == 202
        assert response.json().get("status") == "PENDING"


# ─── ONT-15: Todos los VNOs ───────────────────────────────────────────────────

class TestSwapMultiVNO:

    # ONT-15
    @pytest.mark.parametrize("vno_id", ["DTV", "ClaroVTR", "Entel", "TCH"])
    def test_ont15_todos_los_vnos_pueden_hacer_swap(self, test_client, vno_id):
        """
        ESCENARIO: Los 4 VNOs autorizados pueden hacer swap.

        Resultado esperado: HTTP 202 para cada VNO.
        """
        from tests.conftest import _make_token
        response = test_client.post(
            "/api/v1/device-modification",
            json={**DEVICE_MOD_NOKIA_VALID, "vno_id": vno_id},
            headers={"Authorization": f"Bearer {_make_token(vno_id=vno_id)}"},
        )
        assert response.status_code == 202, (
            f"VNO {vno_id} recibió {response.status_code} — esperado 202"
        )
