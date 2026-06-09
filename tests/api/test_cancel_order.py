"""API tests — Cancelación de orden FTTH (PV-CAN).

Convención: test_can<NN>_<escenario>

Qué estamos probando:
    La cancelación de orden ocurre cuando ServiceNow necesita anular una
    baja antes de que sea ejecutada en la red.

    Usa el mismo endpoint que la baja (POST /unsuscription) pero con
    semánticas adicionales controladas por external_order_id:

      - Si el acceso ya no tiene provisión activa (NO_PROVISION), Komands
        cierra la orden sin tocar la OLT — HTTP 200, status=NO_ACTION.
      - Si ya hay una transacción IN_PROGRESS, Komands rechaza con 409
        KMD-3003 para evitar condiciones de carrera en la red.
      - En caso normal, la cancelación se encola como cualquier baja.

Fuentes:
    - Plan_Pruebas_PostVenta_v1_regresion.docx → PV-CAN-001 a PV-CAN-003
    - AnexoH_Especificacion_APIs_v2_2_FINAL.docx → POST /api/v1/unsuscription
"""
import pytest

pytestmark = [pytest.mark.postventa, pytest.mark.ftth]

CANCEL_URL = "/api/v1/unsuscription"

_BASE = {
    "vno_code": "DTV",
    "external_order_id": "SO-CAN-001",
    "olt_name": "OLT-SAN-001",
    "slot": 1,
    "port": 3,
    "ont_id": 45,
}


class TestCancelOrderHappyPath:
    """
    Cancelación normal — el acceso tiene provisión activa y se encola correctamente.

    Una cancelación estándar es funcionalmente idéntica a una baja:
    el acceso existe en la OLT y Komands lo dará de baja al ejecutarse.
    """

    # CAN-01
    def test_can01_cancelacion_normal_acepta_y_encola(self, test_client, auth_headers):
        """
        ESCENARIO: Cancelación estándar — el acceso tiene provisión activa en la OLT Nokia.

        ServiceNow solicita la cancelación con external_order_id estándar.
        El acceso existe y Komands lo encola para darlo de baja en la OLT.

        Resultado esperado: HTTP 202 con status=PENDING y txn_id.
        """
        response = test_client.post(CANCEL_URL, json=_BASE, headers=auth_headers)

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Se esperaba status=ACCEPTED, se obtuvo: {data.get('status')}"
        )
        assert data.get("txn_id"), "txn_id ausente — no se puede rastrear el resultado"


class TestCancelOrderCasosEspeciales:
    """
    Casos de cancelación que requieren lógica de negocio especial.

    Estos escenarios dependen de centinelas del mock y no pueden ejecutarse
    contra el servidor real sin acceso a la base de datos de transacciones.
    """

    # CAN-02
    @pytest.mark.mock_only
    def test_can02_sin_provision_activa_cierra_orden_sin_transaccion(self, test_client, auth_headers):
        """
        ESCENARIO: El acceso ya no tiene provisión activa — fue dado de baja previamente.

        ServiceNow puede intentar cancelar una orden cuyo acceso ya no existe en la OLT
        (por ejemplo, si la baja fue ejecutada manualmente). En ese caso Komands no debe
        generar una transacción en la red — solo cierra la orden con HTTP 200 + NO_ACTION.

        El campo external_order_id="NO_PROVISION" actúa como centinela en el mock.

        Resultado esperado: HTTP 200 con status=NO_ACTION (sin txn_id — no hubo operación).
        """
        payload = {**_BASE, "external_order_id": "NO_PROVISION"}
        response = test_client.post(CANCEL_URL, json=payload, headers=auth_headers)

        assert response.status_code == 200, (
            f"Se esperaba HTTP 200 para NO_ACTION, se obtuvo: {response.status_code}"
        )
        data = response.json()
        assert data.get("status") == "NO_ACTION", (
            f"Se esperaba status=NO_ACTION, se obtuvo: {data.get('status')}"
        )

    # CAN-03
    @pytest.mark.mock_only
    def test_can03_txn_en_progreso_rechaza_409_kmd3003(self, test_client, auth_headers):
        """
        ESCENARIO: Ya hay una transacción IN_PROGRESS para este acceso.

        Komands no puede ejecutar dos operaciones simultáneas sobre el mismo acceso —
        hacerlo causaría que los comandos en la OLT se pisen entre sí y la red quede
        en estado inconsistente.

        Devuelve HTTP 409 + KMD-3003 para que ServiceNow espere y reintente una vez
        que la transacción en curso haya terminado.

        El campo external_order_id="IN_PROGRESS" actúa como centinela en el mock.

        Resultado esperado: HTTP 409 con error_code=KMD-3003.
        """
        payload = {**_BASE, "external_order_id": "IN_PROGRESS"}
        response = test_client.post(CANCEL_URL, json=payload, headers=auth_headers)

        assert response.status_code == 409, (
            f"Se esperaba HTTP 409 para conflicto IN_PROGRESS, se obtuvo: {response.status_code}"
        )
        data = response.json()
        assert data.get("error_code") == "KMD-3003", (
            f"Se esperaba KMD-3003 (transacción duplicada), se obtuvo: {data.get('error_code')}"
        )
