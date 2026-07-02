"""API tests — Consultas síncronas (PV-QRY).

Convención: test_qry<NN>_<escenario>

Fuentes:
    - Plan_Pruebas_Completo_v4_Final.xlsx → Release 1 → PV-QRY-001 a PV-QRY-006
    - Endpoints síncronos: responden directo sin encolar en Redis
    - Los SLOs de tiempo (< 100ms, < 10s) requieren servidor real

Endpoints cubiertos:
    GET /api/Komands/v1/access/{access_id}     — estado de ONT por ID de acceso
    GET /api/Komands/v1/port-occupancy         — ocupación del puerto PON
    GET /api/Komands/v1/transaction/{txn_id}/status — estado de transacción
"""
import pytest

pytestmark = pytest.mark.postventa

NOT_FOUND_ACCESS_ID = "NOTFOUND"
NOT_FOUND_TXN_ID = "00000000-0000-0000-0000-000000000000"


# ─── QRY-01 a QRY-03: Consulta de acceso ONT ─────────────────────────────────

class TestConsultaAcceso:
    """
    GET /api/Komands/v1/access/{access_id}

    Retorna el estado del ONT asociado a un ID de acceso.
    Usado por ServiceNow para verificar el estado antes de una operación.
    """

    # QRY-01
    def test_qry01_acceso_existente_devuelve_200(self, test_client, admin_token):
        """
        ESCENARIO: Consulta de acceso con access_id válido (source=cache).

        El dato se entrega desde cache Redis. Es la respuesta normal
        cuando la OLT fue consultada recientemente (< 5 min).

        Resultado esperado: HTTP 200 con datos del ONT.
        """
        response = test_client.get(
            "/api/Komands/v1/access/ACC-DTV-00123",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, (
            f"Se esperaba 200, se obtuvo {response.status_code}. Body: {response.text}"
        )
        data = response.json()
        assert "access_id" in data
        assert "status" in data

    # QRY-02 | PV-QRY-002
    def test_qry02_respuesta_contiene_campos_obligatorios(self, test_client, admin_token):
        """
        ESCENARIO: Consulta válida — verificar contrato de respuesta.

        La respuesta debe incluir: access_id, ont_serial, status, olt_name, source.
        Estos campos los consume el FlowDesigner de ServiceNow.

        Resultado esperado: HTTP 200 con todos los campos presentes.
        """
        response = test_client.get(
            "/api/Komands/v1/access/ACC-DTV-00123",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        for campo in ["access_id", "ont_serial", "status", "olt_name", "source"]:
            assert campo in data, f"Campo '{campo}' ausente en la respuesta"

    # QRY-07 | G-05 / PV-QRY-002 (source=live)
    def test_qry07_acceso_source_live_devuelve_200(self, test_client, admin_token):
        """
        ESCENARIO: Consulta de acceso con source=live (PV-QRY-002).

        Con source=live Komands dispara SSH a la OLT y retorna el estado
        en tiempo real, sin pasar por caché Redis. Es más lento que cache
        pero garantiza datos actualizados. El mock devuelve source=live
        en la respuesta para confirmar que el parámetro fue procesado.

        Resultado esperado: HTTP 200 con campo source == "live".
        """
        response = test_client.get(
            "/api/Komands/v1/access/ACC-DTV-00123?source=live",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, (
            f"source=live debería retornar 200, se obtuvo {response.status_code}. "
            f"Body: {response.text}"
        )
        data = response.json()
        assert data.get("source") == "live", (
            f"Se esperaba source=live, se obtuvo: {data.get('source')}"
        )

    # QRY-03 | PV-QRY-003
    def test_qry03_acceso_inexistente_devuelve_404(self, test_client, admin_token):
        """
        ESCENARIO: Consulta con access_id que no existe en el sistema.

        El sistema debe devolver 404 con error_code=KMD-2002.
        ServiceNow usa este error para saber que no hay ONT que operar.

        Resultado esperado: HTTP 404.
        """
        response = test_client.get(
            f"/api/Komands/v1/access/{NOT_FOUND_ACCESS_ID}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404, (
            f"Access_id inexistente debe devolver 404, se obtuvo {response.status_code}"
        )


# ─── QRY-04: Ocupación PON ────────────────────────────────────────────────────

class TestConsultaOcupacionPON:
    """
    GET /api/Komands/v1/port-occupancy

    Retorna cuántos ONTs están activos en un puerto PON.
    Se usa antes de activar para verificar que hay capacidad disponible.
    """

    # QRY-04 | PV-QRY-004
    def test_qry04_ocupacion_pon_devuelve_200(self, test_client, admin_token):
        """
        ESCENARIO: Consulta de ocupación de puerto PON.

        Retorna max_onts (128), active_onts (87) y available (41).
        Si available == 0, la activación fallará por falta de capacidad.

        Resultado esperado: HTTP 200 con max_onts y active_onts.
        """
        response = test_client.get(
            "/api/Komands/v1/port-occupancy",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, (
            f"Se esperaba 200, se obtuvo {response.status_code}. Body: {response.text}"
        )
        data = response.json()
        assert "max_onts" in data
        assert "active_onts" in data


# ─── QRY-05 a QRY-06: Estado de transacción ──────────────────────────────────

class TestConsultaTransaccion:
    """
    GET /api/Komands/v1/transaction/{txn_id}/status

    Retorna el estado actual de una transacción asíncrona.
    ServiceNow consulta este endpoint mientras espera el callback.
    """

    # QRY-05 | PV-QRY-005
    def test_qry05_transaccion_existente_devuelve_200_completed(self, test_client, admin_token):
        """
        ESCENARIO: Consulta de transacción completada.

        ServiceNow consulta el estado de una transacción ya completada.
        Debe recibir status=COMPLETED con los steps de ejecución.

        Resultado esperado: HTTP 200, status=COMPLETED.
        """
        response = test_client.get(
            "/api/Komands/v1/transaction/3fa85f64-5717-4562-b3fc-2c963f66afa6/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200, (
            f"Se esperaba 200, se obtuvo {response.status_code}. Body: {response.text}"
        )
        data = response.json()
        assert data.get("status") == "COMPLETED"

    # QRY-06
    def test_qry06_transaccion_inexistente_devuelve_404(self, test_client, admin_token):
        """
        ESCENARIO: Consulta de transacción con UUID que no existe.

        Si ServiceNow pregunta por un txn_id que nunca se creó,
        el sistema debe devolver 404 con error_code=KMD-2003.

        Resultado esperado: HTTP 404.
        """
        response = test_client.get(
            f"/api/Komands/v1/transaction/{NOT_FOUND_TXN_ID}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404, (
            f"txn_id inexistente debe devolver 404, se obtuvo {response.status_code}"
        )
