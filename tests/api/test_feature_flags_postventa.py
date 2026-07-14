"""API tests — Feature Flags e Idempotencia post-venta (PV-FLG + PV-IDP).

Fuentes:
    - Plan_Pruebas_Completo_v4_Final.xlsx → PV-FLG-001..003, PV-IDP-001
    - FF-01: cuando el flag está desactivado, Komands devuelve KMD-4001
    - PV-IDP-001: txn_id duplicado → segundo POST retorna 200 + txn_id original
"""
import uuid
import pytest

pytestmark = pytest.mark.postventa

_BASE_BAJ = {
    "vno_code": "DTV",
    "external_order_id": "SO-FLG-001",
    "olt_name": "OLT-SAN-001",
    "slot": 1,
    "port": 3,
    "ont_id": 45,
}

_BASE_BAJ_HUAWEI = {
    **_BASE_BAJ,
    "external_order_id": "SO-FLG-002",
    "olt_name": "OLT-SAN-002",
}


# ─── FLG-01 a FLG-03: Feature Flags para baja ────────────────────────────────

class TestFeatureFlagsBaja:
    """
    El Feature Flag controla si Komands procesa la operación o redirige a BluePlanet.

    Cuando está activo → 202 + ACCEPTED (Komands procesa).
    Cuando está desactivado → KMD-4001 (ServiceNow debe usar BluePlanet).

    Fuente: docs/05_gaps_seguridad.md → FF-01, FF-03.
    """

    # FLG-01
    def test_flg01_flag_activo_baja_devuelve_202(self, ff_client, vno_token, vno_id):
        """
        ESCENARIO: Conmutación BP→Komands — flag FTTH activado para la VNO seleccionada.

        Cuando el Feature Flag está activo para la VNO+FTTH, Komands debe
        procesar la baja y devolver 202+ACCEPTED. Es la condición normal
        de operación para los VNOs que ya migraron a Komands.

        Resultado esperado: HTTP 202.
        """
        ff_client.post(
            "/test/feature-flags",
            json={"vno_id": vno_id, "product": "FTTH", "enabled": True},
        )
        response = ff_client.post(
            "/api/Komands/v1/unsuscription",
            json={**_BASE_BAJ, "vno_code": vno_id},
            headers={"Authorization": f"Bearer {vno_token}"},
        )
        assert response.status_code == 202, (
            f"Con flag activo se esperaba 202, se obtuvo {response.status_code}"
        )

    # FLG-02 | PV-FLG-002
    def test_flg02_flag_desactivado_baja_retorna_kmd4001(self, ff_client, vno_token, vno_id):
        """
        ESCENARIO: Rollback Komands→BP — flag FTTH desactivado para la VNO seleccionada.

        Cuando el Feature Flag está desactivado, Komands rechaza la operación
        con KMD-4001 y dice a ServiceNow que use BluePlanet.
        Este mecanismo permite un rollback sin deploys.

        Resultado esperado: respuesta con error KMD-4001.
        """
        ff_client.post(
            "/test/feature-flags",
            json={"vno_id": vno_id, "product": "FTTH", "enabled": False},
        )
        response = ff_client.post(
            "/api/Komands/v1/unsuscription",
            json={**_BASE_BAJ, "vno_code": vno_id},
            headers={"Authorization": f"Bearer {vno_token}"},
        )
        data = response.json()
        assert response.status_code != 202, (
            f"Con flag desactivado NO se esperaba 202, se obtuvo {response.status_code}"
        )
        assert data.get("error") == "KMD-4001", (
            f"Con flag desactivado se esperaba KMD-4001, se obtuvo: {data}"
        )
        assert data.get("redirect") == "blueplanet"

    # FLG-03 | PV-FLG-003
    def test_flg03_flag_encendido_luego_apagado_nokia_huawei(self, ff_client):
        """
        ESCENARIO: Flag activo → OLT Nokia retorna 202; flag apagado → OLT Huawei KMD-4001.

        Simula la migración gradual: Nokia primero, Huawei después.
        Activa el flag, verifica OLT Nokia (OLT-SAN-001), apaga el flag,
        verifica OLT Huawei (OLT-SAN-002).

        Resultado esperado: Nokia → 202, Huawei → KMD-4001.
        """
        from tests.conftest import _make_token
        ff_client.post(
            "/test/feature-flags",
            json={"vno_id": "DTV", "product": "FTTH", "enabled": True},
        )
        nokia_resp = ff_client.post(
            "/api/Komands/v1/unsuscription",
            json=_BASE_BAJ,
            headers={"Authorization": f"Bearer {_make_token(vno_id='DTV')}"},
        )
        assert nokia_resp.status_code == 202, "OLT Nokia debe procesar con flag activo"

        ff_client.post(
            "/test/feature-flags",
            json={"vno_id": "DTV", "product": "FTTH", "enabled": False},
        )
        huawei_resp = ff_client.post(
            "/api/Komands/v1/unsuscription",
            json=_BASE_BAJ_HUAWEI,
            headers={"Authorization": f"Bearer {_make_token(vno_id='DTV')}"},
        )
        assert huawei_resp.json().get("error") == "KMD-4001", (
            "Con flag desactivado OLT Huawei debe retornar KMD-4001"
        )


# ─── IDP-01: Idempotencia en baja ────────────────────────────────────────────

class TestIdempotenciaBaja:
    """
    PV-IDP-001: Si ServiceNow envía la misma baja dos veces (mismo txn_id),
    Komands debe procesar la operación solo una vez.

    Segundo POST → HTTP 200 + txn_id original (no 202).
    La OLT no debe ser contactada la segunda vez.

    Fuente: AnexoH v2.2 — duplicado retorna UUID existente con HTTP 200.
    """

    # IDP-01
    def test_idp01_txn_id_duplicado_retorna_200_con_txn_original(
        self, ff_client, vno_token, vno_id
    ):
        """
        ESCENARIO: ServiceNow envía la misma baja dos veces con el mismo txn_id.

        El primer POST registra la transacción y retorna 202.
        El segundo POST detecta el txn_id duplicado y retorna 200 con el
        mismo txn_id — sin volver a contactar la OLT (0 re-ejecuciones).

        Resultado esperado: primer POST → 202, segundo POST → 200, mismo txn_id.
        """
        txn_id_fijo = str(uuid.uuid4())
        payload = {**_BASE_BAJ, "txn_id": txn_id_fijo, "vno_code": vno_id}
        headers = {"Authorization": f"Bearer {vno_token}"}

        resp1 = ff_client.post("/api/Komands/v1/unsuscription", json=payload, headers=headers)
        assert resp1.status_code == 202, (
            f"Primer POST debe retornar 202, retornó {resp1.status_code}"
        )

        resp2 = ff_client.post("/api/Komands/v1/unsuscription", json=payload, headers=headers)
        assert resp2.status_code == 200, (
            f"Segundo POST con mismo txn_id debe retornar 200, retornó {resp2.status_code}"
        )
        assert resp2.json().get("txn_id") == txn_id_fijo, (
            "El segundo POST debe retornar el mismo txn_id original"
        )
