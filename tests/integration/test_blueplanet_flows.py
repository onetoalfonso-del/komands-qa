"""
Suite de integración contra APIM PRE-PROD — VNO 03 (Entel).

Flujos automatizados:
  1. DeviceModification  sincrónico
  2. DeviceModification  asincrónico
  3. Modification        sincrónica
  4. Modification        asincrónica
  5. Baja de Acceso

Ejecutar:
    pytest tests/integration/ -v -m integration --no-cov
    pytest tests/integration/ -v -m integration --no-cov --run-id 3
"""
import pytest

pytestmark = pytest.mark.integration

_ACCEPTED = {200, 202}


class TestAPIMFlowsVNO03:

    # ── 1. DeviceModification sincrónico ──────────────────────────────────────

    def test_device_modification_sync(self, apim_client, apim_headers, apim_vno, apim_access_id, apim_serial):
        resp = apim_client.post(
            "/fullFillment-deviceModification/v1/deviceModification",
            json={
                "u_id_vno":        apim_vno,
                "u_access_id_vno": apim_access_id,
                "u_serial_number": apim_serial,
            },
            headers={**apim_headers, "vnoId": apim_vno},
        )
        assert resp.status_code in _ACCEPTED, (
            f"DeviceModification SYNC: HTTP {resp.status_code} — {resp.text}"
        )
        assert "result" in resp.json(), f"Sin campo 'result': {resp.json()}"

    # ── 2. DeviceModification asincrónico ─────────────────────────────────────

    def test_device_modification_async(self, apim_client, apim_headers, apim_vno, apim_access_id, apim_serial):
        resp = apim_client.post(
            "/fullFillment-deviceModificationAsync/v1/deviceModificationAsync",
            json={
                "u_id_vno":        apim_vno,
                "u_access_id_vno": apim_access_id,
                "u_serial_number": apim_serial,
            },
            headers={**apim_headers, "vnoId": apim_vno},
        )
        assert resp.status_code in _ACCEPTED, (
            f"DeviceModification ASYNC: HTTP {resp.status_code} — {resp.text}"
        )
        assert "result" in resp.json(), f"Sin campo 'result': {resp.json()}"

    # ── 3. Modification sincrónica ────────────────────────────────────────────

    def test_modification_sync(self, apim_client, apim_headers, apim_vno, apim_access_id, apim_speed_plan):
        resp = apim_client.post(
            "/fullFillment-modification/v1/registrationModification",
            json={
                "u_id_vno":         apim_vno,
                "u_access_id_vno":  apim_access_id,
                "u_operation_type": "M",
                "u_speed_plan":     apim_speed_plan,
            },
            headers={**apim_headers, "vnoId": apim_vno},
        )
        assert resp.status_code in _ACCEPTED, (
            f"Modification SYNC: HTTP {resp.status_code} — {resp.text}"
        )
        assert "result" in resp.json(), f"Sin campo 'result': {resp.json()}"

    # ── 4. Modification asincrónica ───────────────────────────────────────────

    def test_modification_async(self, apim_client, apim_headers, apim_vno, apim_access_id, apim_speed_plan):
        resp = apim_client.post(
            "/fullFillment-ModificationSSAA/v1/registrationModificationSSAA",
            json={
                "u_id_vno":         apim_vno,
                "u_access_id_vno":  apim_access_id,
                "u_operation_type": "Modificacion",
                "u_speed_plan":     apim_speed_plan,
            },
            headers={**apim_headers, "vnoId": apim_vno},
        )
        assert resp.status_code in _ACCEPTED, (
            f"Modification ASYNC: HTTP {resp.status_code} — {resp.text}"
        )
        assert "result" in resp.json(), f"Sin campo 'result': {resp.json()}"

    # ── 5. Baja de Acceso ─────────────────────────────────────────────────────

    def test_baja_acceso(self, apim_client, apim_headers, apim_vno, apim_access_id):
        resp = apim_client.post(
            "/fullFillment-accessDeregistrationAsync/v1/accessDeregistrationAsync",
            json={
                "u_id_vno":        apim_vno,
                "u_access_id_vno": apim_access_id,
                "u_service_type":  "FTTH",
            },
            headers={**apim_headers, "vnoId": apim_vno},
        )
        assert resp.status_code in _ACCEPTED, (
            f"Baja de Acceso: HTTP {resp.status_code} — {resp.text}"
        )
        assert "result" in resp.json(), f"Sin campo 'result': {resp.json()}"
