"""API tests — POST /api/v1/modification (Modificación FTTH, sin SSAA).

Convención: test_mod<NN>_<vendor>_<operacion>_<escenario>

Qué estamos probando:
    El endpoint de modificación recibe un payload con el tipo de operación
    y devuelve HTTP 202 + txn_id cuando todo es válido.
    También valida autenticación (401), autorización (403) y RBAC.

    Operaciones soportadas: SPEED_CHANGE, BLOCK, UNBLOCK.

    Nota: el servidor es la mini-app de conftest.py (TestClient).
    No se necesita servidor real ni base de datos.

    Scope: Release 1 — solo FTTH, SSAA excluido (confirmado por Pablo).

Fuentes:
    - Plan_Pruebas_Completo_v3_Final.xlsx → Release 1 → PV-MOD-215 a PV-MOD-235
    - LLD ADR-008 → endpoint /modification (sin cambio de nombre)
"""
import pytest

from tests.mocks.payloads import (
    MODIFICATION_SPEED_CHANGE_NOKIA,
    MODIFICATION_BLOCK_NOKIA,
    MODIFICATION_UNBLOCK_NOKIA,
    MODIFICATION_SPEED_CHANGE_HUAWEI,
    MODIFICATION_BLOCK_HUAWEI,
    MODIFICATION_UNBLOCK_HUAWEI,
    MODIFICATION_NOKIA_ONT_NOT_FOUND,
    MODIFICATION_HUAWEI_ONT_NOT_FOUND,
    MODIFICATION_NOKIA_SSH_TIMEOUT,
    MODIFICATION_HUAWEI_SSH_TIMEOUT,
    MODIFICATION_SERVICE_REMOVE_NOKIA,
    MODIFICATION_INVALID_SPEED_PROFILE,
)

pytestmark = pytest.mark.postventa


# ─── MOD-01 a MOD-06: Payloads válidos → HTTP 202 ────────────────────────────

class TestModificacionValida:
    """
    Casos felices — el API debe aceptar las 3 operaciones de modificación
    para Nokia y Huawei, devolviendo 202 + txn_id.
    """

    # MOD-01
    def test_mod01_nokia_speed_change_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Cambio de velocidad Nokia FTTH — nuevo perfil 200M_50M.

        Es la operación de modificación más frecuente en post-venta.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers=auth_headers,
        )

        assert response.status_code == 202, (
            f"Se esperaba 202, se obtuvo {response.status_code}. "
            f"Body: {response.text}"
        )

    # MOD-02
    def test_mod02_nokia_block_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Bloqueo de servicio Nokia FTTH.

        BLOCK suspende el servicio sin borrar la configuración — reversible.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_BLOCK_NOKIA,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # MOD-03
    def test_mod03_nokia_unblock_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Desbloqueo de servicio Nokia FTTH.

        UNBLOCK reactiva un servicio previamente bloqueado.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_UNBLOCK_NOKIA,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # MOD-04
    def test_mod04_huawei_speed_change_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Cambio de velocidad Huawei FTTH.

        Valida que el endpoint acepta modificaciones en equipos Huawei.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_HUAWEI,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # MOD-05
    def test_mod05_huawei_block_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Bloqueo de servicio Huawei FTTH.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_BLOCK_HUAWEI,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # MOD-06
    def test_mod06_huawei_unblock_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Desbloqueo de servicio Huawei FTTH.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_UNBLOCK_HUAWEI,
            headers=auth_headers,
        )

        assert response.status_code == 202


# ─── MOD-07 a MOD-09: Autenticación fallida → HTTP 401 ───────────────────────

class TestModificacionSinAutenticacion:
    """
    El API debe rechazar modificaciones sin token o con token inválido.
    """

    # MOD-07
    def test_mod07_sin_token_devuelve_401(self, test_client):
        """
        ESCENARIO: Request de modificación sin header Authorization.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
        )

        assert response.status_code == 401

    # MOD-08
    def test_mod08_token_expirado_devuelve_401(self, test_client, expired_token):
        """
        ESCENARIO: Token JWT con fecha de expiración pasada.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    # MOD-09
    def test_mod09_token_malformado_devuelve_401(self, test_client):
        """
        ESCENARIO: Token con formato inválido (no es un JWT).

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers={"Authorization": "Bearer esto-no-es-un-jwt"},
        )

        assert response.status_code == 401


# ─── MOD-10 a MOD-11: Autorización fallida → HTTP 403 ────────────────────────

class TestModificacionSinAutorizacion:
    """
    Token válido pero sin permisos suficientes.
    """

    # MOD-10
    def test_mod10_vno_no_autorizada_devuelve_403(self, test_client, invalid_vno_token):
        """
        ESCENARIO: Token con VNO desconocida ("FAKE_VNO").

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers={"Authorization": f"Bearer {invalid_vno_token}"},
        )

        assert response.status_code == 403

    # MOD-11
    def test_mod11_scope_insuficiente_devuelve_403(self, test_client, readonly_token):
        """
        ESCENARIO: Token con solo komands:read — sin permiso de escritura.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers={"Authorization": f"Bearer {readonly_token}"},
        )

        assert response.status_code == 403


# ─── MOD-12 a MOD-14: RBAC portal web ───────────────────────────────────────

class TestModificacionRBACPortal:
    """
    Solo ADMIN y OPERATOR tienen permiso activation:write.
    VIEWER no puede modificar.
    """

    # MOD-12
    def test_mod12_admin_puede_modificar(self, test_client, admin_token):
        """
        ESCENARIO: Usuario con rol ADMIN modifica desde el portal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 202

    # MOD-13
    def test_mod13_operator_puede_modificar(self, test_client, operator_token):
        """
        ESCENARIO: Usuario con rol OPERATOR modifica desde el portal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 202

    # MOD-14
    def test_mod14_viewer_no_puede_modificar(self, test_client, viewer_token):
        """
        ESCENARIO: Usuario con rol VIEWER intenta modificar.

        VIEWER solo puede leer — no puede cambiar velocidades ni bloquear servicios.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 403


# ─── MOD-15 a MOD-16: Estructura de la respuesta ─────────────────────────────

class TestModificacionRespuesta:
    """
    El body de la respuesta 202 debe contener txn_id y status=PENDING.
    """

    # MOD-15
    def test_mod15_respuesta_contiene_txn_id(self, test_client, auth_headers):
        """
        ESCENARIO: Modificación válida → verificar que el body tiene txn_id.

        Resultado esperado: campo txn_id presente en la respuesta.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "txn_id" in data, f"txn_id ausente en respuesta: {data}"

    # MOD-16
    def test_mod16_respuesta_contiene_status_pending(self, test_client, auth_headers):
        """
        ESCENARIO: Modificación válida → el status inicial es PENDING.

        La modificación es asíncrona — el estado final llega por callback.

        Resultado esperado: campo status == "PENDING".
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SPEED_CHANGE_NOKIA,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "PENDING", (
            f"Se esperaba status=PENDING, se obtuvo: {data.get('status')}"
        )


# ─── MOD-17: Todos los VNOs autorizados ──────────────────────────────────────

class TestModificacionMultiVNO:
    """
    Los 4 VNOs del proyecto deben poder modificar con un token válido.
    """

    # MOD-17
    @pytest.mark.parametrize("vno_id", ["DTV", "ClaroVTR", "Entel", "TCH"])
    def test_mod17_todos_los_vnos_pueden_modificar(self, test_client, vno_id):
        """
        ESCENARIO: Cada VNO autorizado envía una modificación.

        Los 4 VNOs (DTV, ClaroVTR, Entel, TCH) deben recibir 202.

        Resultado esperado: HTTP 202 para cada VNO.
        """
        from tests.conftest import _make_token
        token = _make_token(vno_id=vno_id)
        payload = {**MODIFICATION_SPEED_CHANGE_NOKIA, "vno_id": vno_id}

        response = test_client.post(
            "/api/v1/modification",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202, (
            f"VNO {vno_id} recibió {response.status_code} — esperado 202"
        )


# ─── MOD-18 a MOD-19: ONT no encontrado en la OLT ────────────────────────────

@pytest.mark.mock_only
class TestModificacionONTNoEncontrado:
    """
    La OLT responde que el ONT ID que enviamos no existe en su base de datos.

    Para una modificación esto es tan bloqueante como para una baja:
    no hay nada a quién aplicarle el cambio de velocidad, bloqueo o desbloqueo.

    Komands aborta antes de enviar comandos y reporta FAILED con KMD-2002.
    El mismo error code que en baja, porque el problema es el mismo: recurso
    no encontrado en la OLT.
    """

    # MOD-18
    def test_mod18_nokia_ont_no_encontrado_retorna_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Cambio de velocidad Nokia FTTH — el ONT ID no existe en la OLT.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-2002.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_NOKIA_ONT_NOT_FOUND,
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

    # MOD-19
    def test_mod19_huawei_ont_no_encontrado_retorna_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Cambio de velocidad Huawei FTTH — el ONT ID no existe en la OLT.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-2002.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_HUAWEI_ONT_NOT_FOUND,
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


# ─── MOD-20 a MOD-21: Timeout SSH a la OLT ───────────────────────────────────

@pytest.mark.mock_only
class TestModificacionSSHTimeout:
    """
    La conexión SSH a la OLT falla por timeout antes de poder ejecutar
    el cambio de velocidad, bloqueo o desbloqueo.

    Al igual que en la baja (BAJ-20/21), Komands captura el socket.timeout
    de Netmiko y reporta KMD-5010. El servicio del cliente no cambia porque
    no se llegó a ejecutar ningún comando en la red.
    """

    # MOD-20
    def test_mod20_nokia_ssh_timeout_retorna_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Modificación Nokia FTTH — timeout de conexión SSH a la OLT.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-5010.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_NOKIA_SSH_TIMEOUT,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "FAILED", (
            f"Se esperaba status=FAILED, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-5010", (
            f"Se esperaba KMD-5010, se obtuvo: {data.get('error_code')}"
        )

    # MOD-21
    def test_mod21_huawei_ssh_timeout_retorna_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Modificación Huawei FTTH — timeout de conexión SSH a la OLT.

        Resultado esperado: HTTP 202 con estado FAILED y error_code KMD-5010.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_HUAWEI_SSH_TIMEOUT,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "FAILED", (
            f"Se esperaba status=FAILED, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-5010", (
            f"Se esperaba KMD-5010, se obtuvo: {data.get('error_code')}"
        )


# ─── MOD-22 a MOD-23: Operaciones especiales / validaciones de payload ────────

@pytest.mark.mock_only
class TestModificacionOperacionesEspeciales:
    """
    Casos donde Komands debe rechazar el payload con HTTP 422 antes de llegar
    a la OLT porque la operación solicitada no es válida.

    Son distintos a los errores KMD-2002/5010: allá llegamos a la OLT y
    algo falla en la red. Acá Komands detecta el problema en el payload
    y nunca intenta conectarse.

    Fuente: Plan v4 ESP-001, ESP-003.
    """

    # MOD-22
    def test_mod22_service_remove_nokia_devuelve_422(self, test_client, auth_headers):
        """
        ESCENARIO: Se intenta hacer SERVICE_REMOVE en Nokia FTTH.

        La OLT Nokia ISAM 7360 no tiene un comando para quitar un servicio
        individualmente en FTTH. Si el cliente quiere cancelar VOIP, hay que
        dar de baja el acceso completo y reactivarlo sin ese servicio.
        Komands rechaza SERVICE_REMOVE antes de conectarse a la OLT.

        Resultado esperado: HTTP 422 con error_code KMD-4002.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_SERVICE_REMOVE_NOKIA,
            headers=auth_headers,
        )

        assert response.status_code == 422, (
            f"Se esperaba 422 (operación no soportada), se obtuvo {response.status_code}"
        )
        data = response.json()
        assert data.get("error_code") == "KMD-4002", (
            f"Se esperaba KMD-4002, se obtuvo: {data.get('error_code')}"
        )

    # MOD-23
    def test_mod23_perfil_velocidad_invalido_devuelve_422(self, test_client, auth_headers):
        """
        ESCENARIO: Cambio de velocidad con perfil que no existe en la OLT.

        Los perfiles de velocidad (100M_20M, 200M_50M, etc.) son plantillas
        configuradas en la OLT. Si ServiceNow envía un nombre que no existe
        en el catálogo, Komands lo detecta en validación y devuelve 422.
        No se envía ningún comando a la red.

        Resultado esperado: HTTP 422 con error_code KMD-4003.
        """
        response = test_client.post(
            "/api/v1/modification",
            json=MODIFICATION_INVALID_SPEED_PROFILE,
            headers=auth_headers,
        )

        assert response.status_code == 422, (
            f"Se esperaba 422 (perfil inválido), se obtuvo {response.status_code}"
        )
        data = response.json()
        assert data.get("error_code") == "KMD-4003", (
            f"Se esperaba KMD-4003, se obtuvo: {data.get('error_code')}"
        )
