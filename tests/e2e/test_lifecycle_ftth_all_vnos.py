"""
E2E — Ciclo de vida completo FTTH para todas las combinaciones OLT x VNO.

  Nokia  (OLT-SAN-001) x 10 VNOs = 10 x 8 pasos =  80 tests
  Huawei (OLT-SAN-002) x 10 VNOs = 10 x 8 pasos =  80 tests
  Total                            20 combinaciones = 160 tests E2E

Flujo por cada combinacion:
  PASO 1 -> Alta (service-activation)
  PASO 2 -> Consultar estado Alta
  PASO 3 -> Cambio Plan Comercial (service-modification)
  PASO 4 -> Consultar estado Modificacion
  PASO 5 -> Cambio Dispositivo (device-modification)
  PASO 6 -> Consultar estado Cambio Dispositivo
  PASO 7 -> Baja (unsubscription)
  PASO 8 -> Consultar estado Baja

VNOs cubiertos: DTV, VTR, Entel, ENTEL, TCH, Claro, Generico, GTD, WOM, CVTR
Seriales QA Nokia  : ALCL00QA{N:02d}01 / 02  (N = 1-10, slot 1 / pon 0)
Seriales QA Huawei : 485754CQ{N:02d}01 / 02  (N = 1-10, slot 0 / pon 0)
ONT IDs reservados : 81-90 (nunca tocan clientes reales)
"""
import pytest
from tests.e2e.golden_records import ALL_FTTH, GoldenRecord

pytestmark = pytest.mark.e2e

BASE = "/api/Komands/v1"

# UUID fijo que el mock siempre retorna — se usa en todos los GET de estado
_FIXED_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
_STATUS_OK = {"COMPLETED", "ACCEPTED", "PENDING"}


@pytest.mark.parametrize("gr", ALL_FTTH, ids=[r.label for r in ALL_FTTH])
class TestLifecycleFTTHAllVNOs:
    """
    Ciclo de vida FTTH parametrizado: Nokia + Huawei x 10 VNOs x 8 pasos = 160 tests.
    Cada combinacion tiene datos de prueba (ONT ID y serial) unicos y reservados para QA.
    """

    # ── PASO 1 ─────────────────────────────────────────────────────────────────

    def test_e2e_01_alta(self, e2e_client, e2e_headers, gr: GoldenRecord):
        """PASO 1 — Alta de acceso FTTH (service-activation)."""
        resp = e2e_client.post(
            f"{BASE}/service-activation",
            json=gr.payload_alta(),
            headers=e2e_headers,
        )
        assert resp.status_code == 202, (
            f"[{gr.label}] Alta: HTTP {resp.status_code} — {resp.text}"
        )
        data = resp.json()
        assert "txn_id" in data, f"[{gr.label}] Falta txn_id en respuesta: {data}"

    # ── PASO 2 ─────────────────────────────────────────────────────────────────

    def test_e2e_02_estado_alta(self, e2e_client, e2e_headers, gr: GoldenRecord):
        """PASO 2 — Consultar estado Alta."""
        resp = e2e_client.get(
            f"{BASE}/service-activation/{_FIXED_UUID}",
            headers=e2e_headers,
        )
        assert resp.status_code == 200, (
            f"[{gr.label}] Estado alta: HTTP {resp.status_code}"
        )
        assert resp.json().get("status") in _STATUS_OK, (
            f"[{gr.label}] Status inesperado: {resp.json().get('status')}"
        )

    # ── PASO 3 ─────────────────────────────────────────────────────────────────

    def test_e2e_03_modificacion(self, e2e_client, e2e_headers, gr: GoldenRecord):
        """PASO 3 — Cambio Plan Comercial 100M/20M -> 200M/50M (service-modification)."""
        resp = e2e_client.post(
            f"{BASE}/service-modification",
            json=gr.payload_modificacion(),
            headers=e2e_headers,
        )
        assert resp.status_code == 202, (
            f"[{gr.label}] Modificacion: HTTP {resp.status_code} — {resp.text}"
        )
        assert "txn_id" in resp.json()

    # ── PASO 4 ─────────────────────────────────────────────────────────────────

    def test_e2e_04_estado_modificacion(self, e2e_client, e2e_headers, gr: GoldenRecord):
        """PASO 4 — Consultar estado Modificacion."""
        resp = e2e_client.get(
            f"{BASE}/service-modification/{_FIXED_UUID}",
            headers=e2e_headers,
        )
        assert resp.status_code == 200, (
            f"[{gr.label}] Estado modificacion: HTTP {resp.status_code}"
        )
        assert resp.json().get("status") in _STATUS_OK

    # ── PASO 5 ─────────────────────────────────────────────────────────────────

    def test_e2e_05_cambio_dispositivo(self, e2e_client, e2e_headers, gr: GoldenRecord):
        """PASO 5 — Swap ONT: serial original -> serial nuevo (device-modification)."""
        resp = e2e_client.post(
            f"{BASE}/device-modification",
            json=gr.payload_cambio_dispositivo(),
            headers=e2e_headers,
        )
        assert resp.status_code == 202, (
            f"[{gr.label}] Cambio dispositivo: HTTP {resp.status_code} — {resp.text}"
        )
        assert "txn_id" in resp.json()

    # ── PASO 6 ─────────────────────────────────────────────────────────────────

    def test_e2e_06_estado_cambio_dispositivo(self, e2e_client, e2e_headers, gr: GoldenRecord):
        """PASO 6 — Consultar estado Cambio Dispositivo."""
        resp = e2e_client.get(
            f"{BASE}/device-modification/{_FIXED_UUID}",
            headers=e2e_headers,
        )
        assert resp.status_code == 200, (
            f"[{gr.label}] Estado cambio dispositivo: HTTP {resp.status_code}"
        )
        assert resp.json().get("status") in _STATUS_OK

    # ── PASO 7 ─────────────────────────────────────────────────────────────────

    def test_e2e_07_baja(self, e2e_client, e2e_headers, gr: GoldenRecord):
        """PASO 7 — Baja de acceso con serial post-swap (unsubscription)."""
        resp = e2e_client.post(
            f"{BASE}/unsubscription",
            json=gr.payload_baja(),
            headers=e2e_headers,
        )
        assert resp.status_code == 202, (
            f"[{gr.label}] Baja: HTTP {resp.status_code} — {resp.text}"
        )
        assert "txn_id" in resp.json()

    # ── PASO 8 ─────────────────────────────────────────────────────────────────

    def test_e2e_08_estado_baja(self, e2e_client, e2e_headers, gr: GoldenRecord):
        """PASO 8 — Consultar estado Baja. Cierra el ciclo de vida del acceso."""
        resp = e2e_client.get(
            f"{BASE}/unsubscription/{_FIXED_UUID}",
            headers=e2e_headers,
        )
        assert resp.status_code == 200, (
            f"[{gr.label}] Estado baja: HTTP {resp.status_code}"
        )
        assert resp.json().get("status") in _STATUS_OK, (
            f"[{gr.label}] Status inesperado: {resp.json().get('status')}"
        )
