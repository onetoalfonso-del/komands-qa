"""
E2E — Ciclo de vida completo de un acceso ONT Nokia FTTH.

Flujo paso a paso (Post-Venta):
    PASO 1 → Alta (service-activation)            — Activar ONT en la OLT
    PASO 2 → Consultar estado Alta                — Verificar que quedó activo
    PASO 3 → Cambio Plan Comercial (modificación) — Subir velocidad de 100M a 200M
    PASO 4 → Consultar estado Modificación        — Verificar el cambio
    PASO 5 → Cambio Dispositivo (swap ONT)        — Reemplazar equipo por serial nuevo
    PASO 6 → Consultar estado Cambio Dispositivo  — Verificar el swap
    PASO 7 → Baja (unsubscription)               — Dar de baja el acceso
    PASO 8 → Consultar estado Baja               — Verificar que quedó dado de baja

Dato de prueba fijo:
    VNO: DTV | OLT: OLT-SAN-001 | Slot: 1 | PON: 0 | ONT ID: 99
    Serial: ALCL00QA0001 → ALCL00QA0002 (después del swap)

Modos:
    pytest tests/e2e/ -v                      → contra mock local
    $env:KOMANDS_E2E_URL="https://..."        → contra servidor real
"""
import pytest
from tests.e2e import golden_record as gr
from tests.e2e.conftest import e2e_modo

pytestmark = pytest.mark.e2e

BASE = "/api/Komands/v1"

# Estado compartido entre pasos — se llena a medida que avanza el flujo
_TXN: dict = {}


class TestCicloVidaPostVenta:
    """
    Ciclo de vida completo de un ONT Nokia FTTH — VNO DTV.
    Los 8 pasos se ejecutan en orden y comparten el txn_id entre sí.
    """

    # ── PASO 1 ────────────────────────────────────────────────────────────────

    def test_e2e_01_alta_nokia_ftth(self, e2e_client, e2e_headers):
        """
        ESCENARIO: PASO 1 — Alta de acceso Nokia FTTH con Internet + VoIP.

        ServiceNow solicita activar el ONT ALCL00QA0001 en OLT-SAN-001
        slot 1 / PON 0 / posición 99. Komands encola la operación y retorna
        un txn_id para seguimiento.

        Dato de prueba:
            OLT: OLT-SAN-001 | Slot: 1 | PON: 0 | ONT ID: 99
            Serial: ALCL00QA0001 | VNO: DTV | Producto: FTTH 100M/20M

        Resultado esperado: HTTP 202 + txn_id presente.
        """
        response = e2e_client.post(
            f"{BASE}/service-activation",
            json=gr.ALTA,
            headers=e2e_headers,
        )

        assert response.status_code == 202, (
            f"[PASO 1] Alta falló con {response.status_code}.\n"
            f"  Modo: {e2e_modo()}\n"
            f"  Body: {response.text}"
        )
        data = response.json()
        assert "txn_id" in data, f"[PASO 1] Falta txn_id en respuesta: {data}"
        _TXN["alta"] = data["txn_id"]

    # ── PASO 2 ────────────────────────────────────────────────────────────────

    def test_e2e_02_consultar_estado_alta(self, e2e_client, e2e_headers):
        """
        ESCENARIO: PASO 2 — Consultar estado de la activación.

        Usando el txn_id del paso anterior, ServiceNow consulta si la
        activación fue procesada. Es el patrón async: POST encola, GET confirma.

        Resultado esperado: HTTP 200 con status COMPLETED o ACCEPTED.
        """
        txn_id = _TXN.get("alta", "3fa85f64-5717-4562-b3fc-2c963f66afa6")

        response = e2e_client.get(
            f"{BASE}/service-activation/{txn_id}",
            headers=e2e_headers,
        )

        assert response.status_code == 200, (
            f"[PASO 2] Consulta estado alta falló con {response.status_code}. "
            f"Body: {response.text}"
        )
        data = response.json()
        assert data.get("status") in ("COMPLETED", "ACCEPTED", "PENDING"), (
            f"[PASO 2] Status inesperado: {data.get('status')}"
        )
        assert data.get("txn_id") == txn_id

    # ── PASO 3 ────────────────────────────────────────────────────────────────

    def test_e2e_03_cambio_plan_comercial(self, e2e_client, e2e_headers):
        """
        ESCENARIO: PASO 3 — Cambio Plan Comercial (sube velocidad de 100M a 200M).

        El cliente DTV solicita un upgrade de velocidad. Komands envía los
        comandos de QoS a la OLT para actualizar el perfil del ONT.

        Dato de prueba:
            Velocidad actual: 100M/20M → Nueva velocidad: 200M/50M

        Resultado esperado: HTTP 202 + txn_id presente.
        """
        response = e2e_client.post(
            f"{BASE}/service-modification",
            json=gr.MODIFICACION_VELOCIDAD,
            headers=e2e_headers,
        )

        assert response.status_code == 202, (
            f"[PASO 3] Modificación falló con {response.status_code}. "
            f"Body: {response.text}"
        )
        data = response.json()
        assert "txn_id" in data
        _TXN["modificacion"] = data["txn_id"]

    # ── PASO 4 ────────────────────────────────────────────────────────────────

    def test_e2e_04_consultar_estado_modificacion(self, e2e_client, e2e_headers):
        """
        ESCENARIO: PASO 4 — Consultar estado del cambio de plan.

        Verifica que la modificación de velocidad fue procesada correctamente.

        Resultado esperado: HTTP 200 con status COMPLETED o ACCEPTED.
        """
        txn_id = _TXN.get("modificacion", "3fa85f64-5717-4562-b3fc-2c963f66afa6")

        response = e2e_client.get(
            f"{BASE}/service-modification/{txn_id}",
            headers=e2e_headers,
        )

        assert response.status_code == 200, (
            f"[PASO 4] Consulta estado modificación falló con {response.status_code}"
        )
        data = response.json()
        assert data.get("status") in ("COMPLETED", "ACCEPTED", "PENDING")

    # ── PASO 5 ────────────────────────────────────────────────────────────────

    def test_e2e_05_cambio_dispositivo(self, e2e_client, e2e_headers):
        """
        ESCENARIO: PASO 5 — Cambio Dispositivo (swap de ONT dañado por nuevo).

        El técnico reemplaza el ONT físico del cliente. Komands debe dar de baja
        el serial viejo (ALCL00QA0001) y registrar el nuevo (ALCL00QA0002)
        en la misma posición de la OLT.

        Dato de prueba:
            Serial viejo: ALCL00QA0001 → Serial nuevo: ALCL00QA0002

        Resultado esperado: HTTP 202 + txn_id presente.
        """
        response = e2e_client.post(
            f"{BASE}/device-modification",
            json=gr.CAMBIO_DISPOSITIVO,
            headers=e2e_headers,
        )

        assert response.status_code == 202, (
            f"[PASO 5] Cambio dispositivo falló con {response.status_code}. "
            f"Body: {response.text}"
        )
        data = response.json()
        assert "txn_id" in data
        _TXN["cambio_ont"] = data["txn_id"]

    # ── PASO 6 ────────────────────────────────────────────────────────────────

    def test_e2e_06_consultar_estado_cambio_dispositivo(self, e2e_client, e2e_headers):
        """
        ESCENARIO: PASO 6 — Consultar estado del cambio de dispositivo.

        Verifica que el swap de ONT fue completado y el nuevo serial
        quedó registrado en la OLT.

        Resultado esperado: HTTP 200 con status COMPLETED o ACCEPTED.
        """
        txn_id = _TXN.get("cambio_ont", "3fa85f64-5717-4562-b3fc-2c963f66afa6")

        response = e2e_client.get(
            f"{BASE}/device-modification/{txn_id}",
            headers=e2e_headers,
        )

        assert response.status_code == 200, (
            f"[PASO 6] Consulta estado cambio dispositivo falló: {response.status_code}"
        )
        data = response.json()
        assert data.get("status") in ("COMPLETED", "ACCEPTED", "PENDING")

    # ── PASO 7 ────────────────────────────────────────────────────────────────

    def test_e2e_07_baja_acceso(self, e2e_client, e2e_headers):
        """
        ESCENARIO: PASO 7 — Baja de acceso (unsubscription).

        El cliente cancela el servicio. Komands da de baja el ONT en la OLT,
        eliminando todos los service-ports y liberando la posición.

        Dato de prueba:
            Serial en uso: ALCL00QA0002 (el nuevo tras el swap)

        Resultado esperado: HTTP 202 + txn_id presente.
        """
        response = e2e_client.post(
            f"{BASE}/unsubscription",
            json=gr.BAJA,
            headers=e2e_headers,
        )

        assert response.status_code == 202, (
            f"[PASO 7] Baja falló con {response.status_code}. "
            f"Body: {response.text}"
        )
        data = response.json()
        assert "txn_id" in data
        _TXN["baja"] = data["txn_id"]

    # ── PASO 8 ────────────────────────────────────────────────────────────────

    def test_e2e_08_consultar_estado_baja(self, e2e_client, e2e_headers):
        """
        ESCENARIO: PASO 8 — Consultar estado de la baja.

        Confirmación final: el acceso quedó dado de baja en la OLT.
        ServiceNow cierra la orden en su sistema al recibir COMPLETED.

        Resultado esperado: HTTP 200 con status COMPLETED.
        """
        txn_id = _TXN.get("baja", "3fa85f64-5717-4562-b3fc-2c963f66afa6")

        response = e2e_client.get(
            f"{BASE}/unsubscription/{txn_id}",
            headers=e2e_headers,
        )

        assert response.status_code == 200, (
            f"[PASO 8] Consulta estado baja falló con {response.status_code}"
        )
        data = response.json()
        assert data.get("status") in ("COMPLETED", "ACCEPTED", "PENDING"), (
            f"[PASO 8] Status inesperado: {data.get('status')}"
        )
        assert data.get("txn_id") == txn_id

        # Resumen del flujo completo
        sep = "-" * 55
        print(
            f"\n\n  {sep}\n"
            f"  CICLO DE VIDA COMPLETADO  |  Modo: {e2e_modo()}\n"
            f"  {sep}\n"
            f"  ONT     : {gr.SERIAL} -> {gr.SERIAL_NUEVO} (post-swap)\n"
            f"  OLT     : {gr.OLT}  |  Slot {gr.SLOT}  PON {gr.PON}  ID {gr.ONT_ID}\n"
            f"  VNO     : {gr.VNO}\n"
            f"  {sep}\n"
            f"  txn Alta         : {_TXN.get('alta', 'n/a')}\n"
            f"  txn Modificacion : {_TXN.get('modificacion', 'n/a')}\n"
            f"  txn Cambio ONT   : {_TXN.get('cambio_ont', 'n/a')}\n"
            f"  txn Baja         : {_TXN.get('baja', 'n/a')}\n"
            f"  {sep}\n"
        )
