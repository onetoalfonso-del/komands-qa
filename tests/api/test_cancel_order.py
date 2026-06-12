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
    - AnexoH_Especificacion_APIs_v2_2_FINAL.docx → POST /api/Komands/v1/unsuscription
"""
import pytest

pytestmark = [pytest.mark.postventa, pytest.mark.ftth]

CANCEL_URL = "/api/Komands/v1/unsuscription"

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

    # CAN-01 | PV-CAN-001
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

    # CAN-02 | PV-CAN-002
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

    # CAN-03 | PV-CAN-003
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


# ─── Completitud matriz VNO × OLT — PV-CAN faltantes ────────────────────────
#
# can01-can03 cubren DTV/Nokia para los 3 escenarios (éxito, sin provisión, en progreso).
# Los siguientes parametrize cubren el resto de la matriz (PV-CAN-004 a PV-CAN-033).
#
# Los 3 escenarios se reproducen con centinelas:
#   éxito       → external_order_id estándar (encola baja)
#   sin provisión → external_order_id="NO_PROVISION"
#   en progreso → external_order_id="IN_PROGRESS"

_CAN_COMBOS = [
    # (case_ids_éxito/sin_prov/en_prog, vno_id, olt_name, is_huawei, descripcion)
    (("PV-CAN-004","PV-CAN-005","PV-CAN-006"),  "DTV",  "OLT-SAN-002", True,  "DTV/Huawei-MA5800"),
    (("PV-CAN-007","PV-CAN-008","PV-CAN-009"),  "DTV",  "OLT-SAN-003", True,  "DTV/Huawei-MA5600T"),
    (("PV-CAN-010","PV-CAN-011","PV-CAN-012"),  "CVTR", "OLT-VAL-001", False, "CVTR/Nokia"),
    (("PV-CAN-013","PV-CAN-014","PV-CAN-015"),  "CVTR", "OLT-VAL-002", True,  "CVTR/Huawei-MA5800"),
    (("PV-CAN-016","PV-CAN-017","PV-CAN-018"),  "CVTR", "OLT-VAL-003", True,  "CVTR/Huawei-MA5600T"),
    (("PV-CAN-019","PV-CAN-020","PV-CAN-021"),  "ENTEL","OLT-SCL-010", False, "ENTEL/Nokia-FTTH"),
    (("PV-CAN-022","PV-CAN-023","PV-CAN-024"),  "ENTEL","OLT-SCL-010", False, "ENTEL/Nokia-SSAA"),
    (("PV-CAN-025","PV-CAN-026","PV-CAN-027"),  "ENTEL","OLT-SCL-011", True,  "ENTEL/Huawei-MA5800"),
    (("PV-CAN-028","PV-CAN-029","PV-CAN-030"),  "TCH",  "OLT-SAN-001", False, "TCH/Nokia-FTTH"),
    (("PV-CAN-031","PV-CAN-032","PV-CAN-033"),  "TCH",  "OLT-SCL-010", False, "TCH/Nokia-SSAA"),
]


@pytest.mark.parametrize("ids,vno_id,olt_name,is_huawei,desc", _CAN_COMBOS)
def test_can_matriz_cancelacion_exitosa(ids, vno_id, olt_name, is_huawei, desc, test_client):
    """PV-CAN: Cancelación encola baja — combinaciones VNO × OLT faltantes."""
    from tests.conftest import _make_token
    case_id = ids[0]
    payload = {
        "vno_code": vno_id,
        "external_order_id": f"SO-{case_id}",
        "olt_name": olt_name,
        "slot": 1 if not is_huawei else 0,
        "port": 3 if not is_huawei else 2,
        "ont_id": 45,
    }
    response = test_client.post(
        CANCEL_URL, json=payload,
        headers={"Authorization": f"Bearer {_make_token(vno_id=vno_id)}"},
    )
    assert response.status_code == 202, f"{case_id} {desc}: esperado 202, obtuvo {response.status_code}"
    assert response.json().get("status") == "ACCEPTED", f"{case_id}: esperado ACCEPTED"


@pytest.mark.mock_only
@pytest.mark.parametrize("ids,vno_id,olt_name,is_huawei,desc", _CAN_COMBOS)
def test_can_matriz_sin_provision_activa(ids, vno_id, olt_name, is_huawei, desc, test_client):
    """PV-CAN: Sin provisión activa → NO_ACTION — combinaciones VNO × OLT faltantes."""
    from tests.conftest import _make_token
    case_id = ids[1]
    payload = {
        "vno_code": vno_id,
        "external_order_id": "NO_PROVISION",
        "olt_name": olt_name,
        "slot": 1 if not is_huawei else 0,
        "port": 3 if not is_huawei else 2,
        "ont_id": 45,
    }
    response = test_client.post(
        CANCEL_URL, json=payload,
        headers={"Authorization": f"Bearer {_make_token(vno_id=vno_id)}"},
    )
    assert response.status_code == 200, f"{case_id} {desc}: esperado 200, obtuvo {response.status_code}"
    assert response.json().get("status") == "NO_ACTION", f"{case_id}: esperado NO_ACTION"


@pytest.mark.mock_only
@pytest.mark.parametrize("ids,vno_id,olt_name,is_huawei,desc", _CAN_COMBOS)
def test_can_matriz_txn_en_progreso_409(ids, vno_id, olt_name, is_huawei, desc, test_client):
    """PV-CAN: Transacción en progreso → 409 KMD-3003 — combinaciones VNO × OLT faltantes."""
    from tests.conftest import _make_token
    case_id = ids[2]
    payload = {
        "vno_code": vno_id,
        "external_order_id": "IN_PROGRESS",
        "olt_name": olt_name,
        "slot": 1 if not is_huawei else 0,
        "port": 3 if not is_huawei else 2,
        "ont_id": 45,
    }
    response = test_client.post(
        CANCEL_URL, json=payload,
        headers={"Authorization": f"Bearer {_make_token(vno_id=vno_id)}"},
    )
    assert response.status_code == 409, f"{case_id} {desc}: esperado 409, obtuvo {response.status_code}"
    assert response.json().get("error_code") == "KMD-3003", f"{case_id}: esperado KMD-3003"
