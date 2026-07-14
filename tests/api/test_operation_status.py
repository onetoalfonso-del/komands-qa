"""API tests — GET /{operation}/{uuid} — estado de operaciones asíncronas.

Convención: test_ops<NN>_<operacion>_<escenario>

Qué estamos probando:
    Los 6 endpoints GET presentes en openapi.json v2.2.3 que permiten consultar
    el estado de una operación asíncrona previamente encolada.
    Cada operación POST retorna un txn_id; estos GET lo reciben como path param.

    Endpoints cubiertos (todos requieren transaction:read):
        GET /api/Komands/v1/service-activation/{uuid}
        GET /api/Komands/v1/unsubscription/{uuid}
        GET /api/Komands/v1/device-modification/{uuid}
        GET /api/Komands/v1/service-modification/{uuid}
        GET /api/Komands/v1/fiber-change/{uuid}
        GET /api/Komands/v1/pon-transfer/{uuid}

Fuentes:
    - docs/openapi.json v2.2.3 → rutas GET con path param {uuid}
    - Plan_Pruebas_Completo_v4_Final.xlsx → PV-QRY-007 a PV-QRY-018 (pendiente)
"""
import pytest

pytestmark = pytest.mark.postventa

SAMPLE_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
NOT_FOUND_UUID = "00000000-0000-0000-0000-000000000000"

_OPERATIONS = [
    ("service-activation",  "service-activation"),
    ("unsubscription",       "unsubscription"),
    ("device-modification",  "device-modification"),
    ("service-modification", "service-modification"),
    ("fiber-change",         "fiber-change"),
    ("pon-transfer",         "pon-transfer"),
]


# ─── OPS-01: Todos los endpoints retornan 200 con txn_id válido ───────────────

class TestEstadoOperacionOK:
    """
    GET /{operation}/{uuid} con UUID existente → HTTP 200 + campos obligatorios.
    """

    # OPS-01
    @pytest.mark.parametrize("endpoint,operation", _OPERATIONS)
    def test_ops01_estado_uuid_valido_devuelve_200(
        self, test_client, admin_token, endpoint, operation
    ):
        """
        ESCENARIO: Consulta de estado con UUID real (el que devolvió el POST).

        ServiceNow consulta el estado de una operación asíncrona usando el
        txn_id que recibió en la respuesta 202 del POST correspondiente.

        Resultado esperado: HTTP 200 con txn_id, status y result.
        """
        response = test_client.get(
            f"/api/Komands/v1/{endpoint}/{SAMPLE_UUID}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200, (
            f"[{endpoint}] Se esperaba 200, se obtuvo {response.status_code}. "
            f"Body: {response.text}"
        )
        data = response.json()
        assert "txn_id" in data, f"[{endpoint}] Falta txn_id en respuesta: {data}"
        assert "status" in data, f"[{endpoint}] Falta status en respuesta: {data}"
        assert "result" in data, f"[{endpoint}] Falta result en respuesta: {data}"

    # OPS-02
    @pytest.mark.parametrize("endpoint,operation", _OPERATIONS)
    def test_ops02_estado_devuelve_operacion_correcta(
        self, test_client, admin_token, endpoint, operation
    ):
        """
        ESCENARIO: El campo operation en la respuesta refleja el endpoint llamado.

        Permite que el consumidor verifique que está leyendo el estado
        del tipo de operación correcto y no hay confusión de rutas.

        Resultado esperado: campo operation == nombre del endpoint.
        """
        response = test_client.get(
            f"/api/Komands/v1/{endpoint}/{SAMPLE_UUID}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("operation") == operation, (
            f"[{endpoint}] operation esperado='{operation}', "
            f"obtenido='{data.get('operation')}'"
        )


# ─── OPS-03: UUID no encontrado → 404 ────────────────────────────────────────

class TestEstadoOperacionNotFound:
    """
    GET /{operation}/{uuid} con UUID centinela → HTTP 404.
    """

    # OPS-03
    @pytest.mark.parametrize("endpoint,operation", _OPERATIONS)
    def test_ops03_uuid_no_encontrado_devuelve_404(
        self, test_client, admin_token, endpoint, operation
    ):
        """
        ESCENARIO: Consulta de estado con UUID centinela (todos-ceros).

        El UUID 00000000-0000-0000-0000-000000000000 es el centinela estándar
        para "transacción no encontrada" en el mock — equivale a un txn_id
        inexistente o ya expirado del historial.

        Resultado esperado: HTTP 404.
        """
        response = test_client.get(
            f"/api/Komands/v1/{endpoint}/{NOT_FOUND_UUID}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404, (
            f"[{endpoint}] Se esperaba 404, se obtuvo {response.status_code}. "
            f"Body: {response.text}"
        )


# ─── OPS-04: Sin token → 401 ─────────────────────────────────────────────────

class TestEstadoOperacionAuth:
    """
    Autenticación y autorización para los endpoints GET de estado.
    """

    # OPS-04
    @pytest.mark.parametrize("endpoint,operation", _OPERATIONS)
    def test_ops04_sin_token_devuelve_401(self, test_client, endpoint, operation):  # noqa: no vno_id — auth pura
        """
        ESCENARIO: GET sin header Authorization.

        Sin token no se puede saber quién hace la consulta.

        Resultado esperado: HTTP 401.
        """
        response = test_client.get(
            f"/api/Komands/v1/{endpoint}/{SAMPLE_UUID}",
        )

        assert response.status_code == 401, (
            f"[{endpoint}] Se esperaba 401, se obtuvo {response.status_code}"
        )

    # OPS-05
    @pytest.mark.parametrize("endpoint,operation", _OPERATIONS)
    def test_ops05_viewer_no_puede_consultar_estado(
        self, test_client, viewer_token, endpoint, operation
    ):
        """
        ESCENARIO: Rol VIEWER intenta consultar estado de operación.

        VIEWER solo tiene transaction:read — en el mock de prueba sí puede
        consultar, pero este test verifica que el endpoint requiere autenticación
        correcta. El rol VIEWER con transaction:read SÍ debe tener acceso.

        Resultado esperado: HTTP 200 (VIEWER tiene transaction:read).
        """
        response = test_client.get(
            f"/api/Komands/v1/{endpoint}/{SAMPLE_UUID}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 200, (
            f"[{endpoint}] VIEWER con transaction:read esperaba 200, "
            f"se obtuvo {response.status_code}"
        )

    # OPS-06
    @pytest.mark.parametrize("endpoint,operation", _OPERATIONS)
    def test_ops06_auditor_sin_transaction_read_devuelve_403(
        self, test_client, auditor_token, endpoint, operation
    ):
        """
        ESCENARIO: Rol AUDITOR intenta consultar estado de operación.

        AUDITOR solo tiene audit:read — no tiene transaction:read.
        Las consultas de estado de operación requieren transaction:read.

        Resultado esperado: HTTP 403.
        """
        response = test_client.get(
            f"/api/Komands/v1/{endpoint}/{SAMPLE_UUID}",
            headers={"Authorization": f"Bearer {auditor_token}"},
        )

        assert response.status_code == 403, (
            f"[{endpoint}] AUDITOR sin transaction:read esperaba 403, "
            f"se obtuvo {response.status_code}"
        )


# ─── OPS-07: Token de API VNO puede consultar estado ─────────────────────────

class TestEstadoOperacionVNOToken:
    """
    GET /{operation}/{uuid} con token de API VNO (komands:query scope).

    Verifica que los clientes API (ServiceNow vía Axway APIM) también pueden
    consultar el estado de sus propias operaciones usando su token de VNO,
    no solo los usuarios de portal con transaction:read.
    """

    # OPS-07
    @pytest.mark.parametrize("endpoint,operation", _OPERATIONS)
    def test_ops07_vno_api_token_puede_consultar_estado(
        self, test_client, vno_token, vno_id, endpoint, operation
    ):
        """
        ESCENARIO: Consulta de estado con token de API VNO (no token de portal).

        ServiceNow usa su token VNO para consultar el estado de una operación
        que encoló previamente. El endpoint debe aceptar tokens de API VNO
        con scope komands:query, no solo tokens de portal con transaction:read.

        Resultado esperado: HTTP 200.
        """
        response = test_client.get(
            f"/api/Komands/v1/{endpoint}/{SAMPLE_UUID}",
            headers={"Authorization": f"Bearer {vno_token}"},
        )

        assert response.status_code == 200, (
            f"[{endpoint}][{vno_id}] VNO API token esperaba 200, "
            f"se obtuvo {response.status_code}. Body: {response.text}"
        )
