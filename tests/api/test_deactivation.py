"""API tests — POST /api/v1/unsuscription (Baja FTTH, sin SSAA).

Convención: test_baj<NN>_<vendor>_<vno>_<escenario>

Qué estamos probando:
    El endpoint de baja recibe un payload con los datos del ONT
    y devuelve HTTP 202 + txn_id cuando todo es válido.
    También valida autenticación (401), autorización (403) y RBAC.

    Nota: el servidor es la mini-app de conftest.py (TestClient).
    No se necesita servidor real ni base de datos.

    Scope: Release 1 — solo FTTH, SSAA excluido (confirmado por Pablo).

Fuentes:
    - Plan_Pruebas_Completo_v4_Final.xlsx → Release 1 → PV-BAJ-182 a PV-BAJ-214
    - LLD ADR-008 → endpoint /deactivation renombrado a /unsuscription
    - Plan v3 PV-BAJ → TCH tiene delete_vlan_on_terminate exclusivo
"""
import pytest

from tests.mocks.payloads import (
    DEACTIVATION_NOKIA_VALID,
    DEACTIVATION_NOKIA_CVTR,
    DEACTIVATION_NOKIA_TCH,
    DEACTIVATION_HUAWEI_VALID,
    DEACTIVATION_HUAWEI_INDEX_FAIL,
    DEACTIVATION_HUAWEI_PARTIAL_INDEX,
    DEACTIVATION_NOKIA_ONT_NOT_FOUND,
    DEACTIVATION_HUAWEI_ONT_NOT_FOUND,
    DEACTIVATION_NOKIA_SSH_TIMEOUT,
    DEACTIVATION_HUAWEI_SSH_TIMEOUT,
)

pytestmark = pytest.mark.postventa


# ─── BAJ-01 a BAJ-04: Payloads válidos → HTTP 202 ────────────────────────────

class TestBajaValida:
    """
    Casos felices — el API debe aceptar bajas FTTH de Nokia y Huawei,
    para los 4 VNOs, devolviendo 202 + txn_id.
    """

    # BAJ-01
    def test_baj01_nokia_ftth_dtv_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Baja Nokia FTTH — VNO DTV (caso base).

        Es la baja más básica. Si este caso falla, toda la suite de baja falla.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202, (
            f"Se esperaba 202, se obtuvo {response.status_code}. "
            f"Body: {response.text}"
        )

    # BAJ-02
    def test_baj02_huawei_ftth_dtv_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Baja Huawei FTTH — VNO DTV.

        Valida que el endpoint acepta bajas de equipos Huawei (Riesgo R10).

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_HUAWEI_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # BAJ-03
    def test_baj03_nokia_ftth_clarovtr_devuelve_202(self, test_client):
        """
        ESCENARIO: Baja Nokia FTTH — VNO CVTR (ClaroVTR).

        Valida que el endpoint acepta bajas de CVTR con su propio token.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {
            "Authorization": f"Bearer {_make_token(vno_id='CVTR')}",
            "X-Correlation-ID": "test-baj03",
        }
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_CVTR,
            headers=headers,
        )

        assert response.status_code == 202

    # BAJ-04
    def test_baj04_nokia_ftth_tch_delete_vlan_devuelve_202(self, test_client):
        """
        ESCENARIO: Baja Nokia FTTH — VNO TCH (Movistar) con delete_vlan_on_terminate=True.

        TCH tiene una regla de negocio especial: se elimina la VLAN del cliente
        al dar de baja. El endpoint debe aceptar este campo extra sin error.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {
            "Authorization": f"Bearer {_make_token(vno_id='TCH')}",
            "X-Correlation-ID": "test-baj04",
        }
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_TCH,
            headers=headers,
        )

        assert response.status_code == 202


# ─── BAJ-05 a BAJ-07: Autenticación fallida → HTTP 401 ───────────────────────

class TestBajaSinAutenticacion:
    """
    El API debe rechazar bajas sin token o con token inválido.
    """

    # BAJ-05
    def test_baj05_sin_token_devuelve_401(self, test_client):
        """
        ESCENARIO: Request de baja sin header Authorization.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
        )

        assert response.status_code == 401

    # BAJ-06
    def test_baj06_token_expirado_devuelve_401(self, test_client, expired_token):
        """
        ESCENARIO: Token JWT con fecha de expiración pasada.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    # BAJ-07
    def test_baj07_token_malformado_devuelve_401(self, test_client):
        """
        ESCENARIO: Token con formato inválido (no es un JWT).

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers={"Authorization": "Bearer esto-no-es-un-jwt"},
        )

        assert response.status_code == 401


# ─── BAJ-08 a BAJ-09: Autorización fallida → HTTP 403 ────────────────────────

class TestBajaSinAutorizacion:
    """
    Token válido pero sin permisos suficientes.
    """

    # BAJ-08
    def test_baj08_vno_no_autorizada_devuelve_403(self, test_client, invalid_vno_token):
        """
        ESCENARIO: Token con VNO desconocida ("FAKE_VNO").

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers={"Authorization": f"Bearer {invalid_vno_token}"},
        )

        assert response.status_code == 403

    # BAJ-09
    def test_baj09_scope_insuficiente_devuelve_403(self, test_client, readonly_token):
        """
        ESCENARIO: Token con solo komands:read — sin permiso de escritura.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers={"Authorization": f"Bearer {readonly_token}"},
        )

        assert response.status_code == 403


# ─── BAJ-10 a BAJ-12: RBAC portal web ────────────────────────────────────────

class TestBajaRBACPortal:
    """
    Solo ADMIN y OPERATOR tienen permiso activation:write.
    VIEWER no puede dar de baja.
    """

    # BAJ-10
    def test_baj10_admin_puede_dar_de_baja(self, test_client, admin_token):
        """
        ESCENARIO: Usuario con rol ADMIN da de baja desde el portal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 202

    # BAJ-11
    def test_baj11_operator_puede_dar_de_baja(self, test_client, operator_token):
        """
        ESCENARIO: Usuario con rol OPERATOR da de baja desde el portal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 202

    # BAJ-12
    def test_baj12_viewer_no_puede_dar_de_baja(self, test_client, viewer_token):
        """
        ESCENARIO: Usuario con rol VIEWER intenta dar de baja.

        VIEWER solo puede leer — no puede modificar la red.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 403


# ─── BAJ-13 a BAJ-14: Estructura de la respuesta ─────────────────────────────

class TestBajaRespuesta:
    """
    El body de la respuesta 202 debe contener txn_id y status=PENDING.
    """

    # BAJ-13
    def test_baj13_respuesta_contiene_txn_id(self, test_client, auth_headers):
        """
        ESCENARIO: Baja válida → verificar que el body tiene txn_id.

        Resultado esperado: campo txn_id presente en la respuesta.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "txn_id" in data, f"txn_id ausente en respuesta: {data}"

    # BAJ-14
    def test_baj14_respuesta_contiene_status_pending(self, test_client, auth_headers):
        """
        ESCENARIO: Baja válida → el status inicial es PENDING.

        La baja es asíncrona — el estado final llega por callback.

        Resultado esperado: campo status == "PENDING".
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Se esperaba status=ACCEPTED, se obtuvo: {data.get('status')}"
        )


# ─── BAJ-15: Todos los VNOs autorizados ──────────────────────────────────────

class TestBajaMultiVNO:
    """
    Los 4 VNOs del proyecto deben poder dar de baja con un token válido.
    """

    # BAJ-15
    @pytest.mark.parametrize("vno_id", ["DTV", "CVTR", "ENTEL", "TCH"])
    def test_baj15_todos_los_vnos_pueden_dar_de_baja(self, test_client, vno_id):
        """
        ESCENARIO: Cada VNO autorizado envía una baja.

        Los 4 VNOs (DTV, CVTR, ENTEL, TCH) deben recibir 202.

        Resultado esperado: HTTP 202 para cada VNO.
        """
        from tests.conftest import _make_token
        token = _make_token(vno_id=vno_id)
        payload = {**DEACTIVATION_NOKIA_VALID, "vno_code": vno_id}

        response = test_client.post(
            "/api/v1/unsuscription",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202, (
            f"VNO {vno_id} recibió {response.status_code} — esperado 202"
        )


# ─── BAJ-18 a BAJ-19: ONT no encontrado en la OLT ───────────────────────────

@pytest.mark.mock_only
class TestBajaONTNoEncontrado:
    """
    La OLT responde que el ONT ID que enviamos no existe en su base de datos.

    Esto pasa en dos situaciones reales:
      1. El ONT fue eliminado manualmente desde la OLT sin pasar por Komands,
         y ServiceNow sigue teniendo el ID como activo.
      2. El técnico ingresó el ID incorrecto en la orden de servicio.

    En ambos casos, Komands no puede ejecutar la baja porque no hay nada
    que eliminar. Reporta FAILED con KMD-2002 sin tocar nada en la red.

    Diferencia con BAJ-16: allá el ONT existe pero no tiene INDEX (Huawei).
    Acá el ONT simplemente no existe, y aplica a Nokia y Huawei por igual.
    """

    # BAJ-18
    def test_baj18_nokia_ont_no_encontrado_retorna_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Baja Nokia FTTH — el ONT ID no existe en la OLT.

        Komands consulta la OLT por el ONT y recibe respuesta "no encontrado".
        Sin ONT al que apuntar, la operación se aborta antes de enviar comandos.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-2002.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_ONT_NOT_FOUND,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()

        # La operación no se ejecutó, pero la solicitud fue recibida → 202
        assert data.get("status") == "FAILED", (
            f"Se esperaba status=FAILED, se obtuvo: {data.get('status')}"
        )
        # KMD-2002 cubre todos los casos de "recurso no encontrado en OLT"
        assert data.get("error_code") == "KMD-2002", (
            f"Se esperaba KMD-2002, se obtuvo: {data.get('error_code')}"
        )

    # BAJ-19
    def test_baj19_huawei_ont_no_encontrado_retorna_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Baja Huawei FTTH — el ONT ID no existe en la OLT.

        Mismo escenario que BAJ-18 pero para equipos Huawei MA5800.
        El error es el mismo código porque el problema es de negocio, no del vendor.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-2002.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_HUAWEI_ONT_NOT_FOUND,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "FAILED", (
            f"Se esperaba status=FAILED, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-2002", (
            f"Se esperaba KMD-2002, se obtuvo: {data.get('error_code')}"
        )


# ─── BAJ-20 a BAJ-21: Timeout SSH a la OLT ───────────────────────────────────

@pytest.mark.mock_only
class TestBajaSSHTimeout:
    """
    La OLT no responde al comando CLI dentro del tiempo límite configurado.

    Netmiko envía el comando pero la OLT no retorna respuesta (ocupada, saturada
    o con problemas). Komands captura el timeout y reporta KMD-5020.
    KMD-5020 (CLI_TIMEOUT) es distinto a KMD-5010 (CLI_ERROR/comando rechazado):
      - KMD-5010: la OLT respondió pero rechazó el comando.
      - KMD-5020: la OLT no respondió dentro del tiempo límite.

    Ambos casos dejan el cliente sin cambios en la red, pero KMD-5020
    puede indicar un problema de infraestructura (OLT saturada, pérdida
    de sesión SSH) que hay que escalar a Redes.
    """

    # BAJ-20
    def test_baj20_nokia_ssh_timeout_retorna_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Baja Nokia FTTH — timeout de conexión SSH a la OLT.

        Netmiko no logra establecer la sesión SSH dentro del tiempo límite.
        Komands aborta la operación sin haber ejecutado ningún comando.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-5020.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_NOKIA_SSH_TIMEOUT,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()

        assert data.get("status") == "FAILED", (
            f"Se esperaba status=FAILED, se obtuvo: {data.get('status')}"
        )
        # KMD-5020 = CLI_TIMEOUT: timeout esperando respuesta de la OLT (AnexoH v2.2)
        assert data.get("error_code") == "KMD-5020", (
            f"Se esperaba KMD-5020, se obtuvo: {data.get('error_code')}"
        )

    # BAJ-21
    def test_baj21_huawei_ssh_timeout_retorna_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Baja Huawei FTTH — timeout de conexión SSH a la OLT.

        Mismo escenario que BAJ-20 pero para equipos Huawei MA5800.
        El código de error es el mismo: el problema es la red, no el vendor.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-5020.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_HUAWEI_SSH_TIMEOUT,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "FAILED", (
            f"Se esperaba status=FAILED, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-5020", (
            f"Se esperaba KMD-5020, se obtuvo: {data.get('error_code')}"
        )


# ─── BAJ-16 a BAJ-17: Errores de negocio Huawei ──────────────────────────────

@pytest.mark.mock_only
class TestBajaErroresNegocioHuawei:
    """
    Huawei requiere resolver un INDEX dinámico antes de ejecutar la baja.
    Si esa resolución falla (total o parcialmente), Komands no puede completar
    la operación y debe reportar el error sin dejar la OLT en estado inconsistente.

    Riesgo R-01 del plan de pruebas post-venta (Crítico).
    """

    # BAJ-16
    def test_baj16_huawei_index_no_resuelto_retorna_kmd2002(self, test_client, auth_headers):
        """
        ESCENARIO: Baja Huawei FTTH — OLT no entrega el INDEX del service-port.

        Antes de ejecutar cualquier comando en la OLT, Komands consulta el INDEX
        dinámico del service-port del cliente. Si la OLT no responde o el INDEX
        no existe, Komands aborta la operación con error KMD-2002 sin tocar nada.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-2002.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_HUAWEI_INDEX_FAIL,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "FAILED", (
            f"Se esperaba status=FAILED, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-2002", (
            f"Se esperaba error_code=KMD-2002, se obtuvo: {data.get('error_code')}"
        )

    # BAJ-17
    def test_baj17_huawei_index_parcial_retorna_rolled_back(self, test_client, auth_headers):
        """
        ESCENARIO: Baja Huawei FTTH — cliente con 3 service-ports, solo 2 tienen INDEX.

        Komands resuelve el INDEX de 2 service-ports y los elimina de la OLT.
        El 3ro no tiene INDEX y no se puede eliminar. Para no dejar al cliente
        con servicio parcial, Komands hace rollback de los 2 que ya borró.

        Resultado esperado: HTTP 202 con estado ROLLED_BACK.
        """
        response = test_client.post(
            "/api/v1/unsuscription",
            json=DEACTIVATION_HUAWEI_PARTIAL_INDEX,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ROLLED_BACK", (
            f"Se esperaba status=ROLLED_BACK, se obtuvo: {data.get('status')}"
        )
