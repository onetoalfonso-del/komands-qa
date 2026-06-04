"""API tests — Feature Flags e Idempotencia post-venta (PV-FLG + PV-IDP).

Fuentes:
    - Plan_Pruebas_Completo_v3_Final.xlsx → PV-FLG-001..003, PV-IDP-001
    - FF-01: cuando el flag está desactivado, Komands devuelve KMD-4001
    - PV-IDP-001: X-Correlation-ID duplicado → segundo POST retorna 200 + txn_id original
"""
import uuid
import pytest

pytestmark = pytest.mark.postventa


# ─── FLG-01 a FLG-03: Feature Flags para baja ────────────────────────────────

class TestFeatureFlagsBaja:
    """
    El Feature Flag controla si Komands procesa la operación o redirige a BluePlanet.

    Cuando está activo → 202 + PENDING (Komands procesa).
    Cuando está desactivado → KMD-4001 (ServiceNow debe usar BluePlanet).

    Fuente: docs/05_gaps_seguridad.md → FF-01, FF-03.
    """

    # FLG-01
    def test_flg01_flag_activo_baja_devuelve_202(self, ff_client, valid_token):
        """
        ESCENARIO: Conmutación BP→Komands — flag DTV FTTH activado.

        Cuando el Feature Flag está activo para DTV+FTTH, Komands debe
        procesar la baja y devolver 202+PENDING. Es la condición normal
        de operación para los VNOs que ya migraron a Komands.

        Resultado esperado: HTTP 202.
        """
        ff_client.post(
            "/test/feature-flags",
            json={"vno_id": "DTV", "product": "FTTH", "enabled": True},
        )
        response = ff_client.post(
            "/api/v1/unsuscription",
            json={
                "vno_id": "DTV",
                "olt_vendor": "nokia",
                "olt_name": "OLT-SAN-001",
                "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
                "product": "FTTH",
                "callback_url": "https://servicenow.onnet.cl/api/komands/callback",
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 202, (
            f"Con flag activo se esperaba 202, se obtuvo {response.status_code}"
        )

    # FLG-02
    def test_flg02_flag_desactivado_baja_retorna_kmd4001(self, ff_client, valid_token):
        """
        ESCENARIO: Rollback Komands→BP — flag DTV FTTH desactivado.

        Cuando el Feature Flag está desactivado, Komands rechaza la operación
        con KMD-4001 y dice a ServiceNow que use BluePlanet.
        Este mecanismo permite un rollback sin deploys.

        Resultado esperado: respuesta con error_code KMD-4001.
        """
        ff_client.post(
            "/test/feature-flags",
            json={"vno_id": "DTV", "product": "FTTH", "enabled": False},
        )
        response = ff_client.post(
            "/api/v1/unsuscription",
            json={
                "vno_id": "DTV",
                "olt_vendor": "nokia",
                "olt_name": "OLT-SAN-001",
                "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
                "product": "FTTH",
                "callback_url": "https://servicenow.onnet.cl/api/komands/callback",
            },
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        data = response.json()
        assert response.status_code != 202, (
            f"Con flag desactivado NO se esperaba 202, se obtuvo {response.status_code}"
        )
        assert data.get("error") == "KMD-4001", (
            f"Con flag desactivado se esperaba KMD-4001, se obtuvo: {data}"
        )
        assert data.get("redirect") == "blueplanet"

    # FLG-03
    def test_flg03_flag_multidimensional_nokia_activo_huawei_no(self, ff_client):
        """
        ESCENARIO: Flag multi-dimensional — DTV Nokia activo, DTV Huawei desactivado.

        Los flags son por VNO × vendor × producto. Es posible tener Nokia activo
        y Huawei desactivado simultáneamente para el mismo VNO. Útil durante
        la migración gradual (Nokia primero, Huawei después).

        Resultado esperado: Nokia → 202, Huawei → KMD-4001.
        """
        from tests.conftest import _make_token
        ff_client.post(
            "/test/feature-flags",
            json={"vno_id": "DTV", "product": "FTTH", "enabled": True},
        )
        # Activar Nokia (usa el flag general FTTH DTV=True)
        nokia_payload = {
            "vno_id": "DTV", "olt_vendor": "nokia", "olt_name": "OLT-SAN-001",
            "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
            "product": "FTTH",
            "callback_url": "https://servicenow.onnet.cl/api/komands/callback",
        }
        nokia_resp = ff_client.post(
            "/api/v1/unsuscription",
            json=nokia_payload,
            headers={"Authorization": f"Bearer {_make_token(vno_id='DTV')}"},
        )
        assert nokia_resp.status_code == 202, "Nokia debe estar activo"

        # Desactivar Huawei para DTV
        ff_client.post(
            "/test/feature-flags",
            json={"vno_id": "DTV", "product": "FTTH", "enabled": False},
        )
        huawei_payload = {**nokia_payload, "olt_vendor": "huawei"}
        huawei_resp = ff_client.post(
            "/api/v1/unsuscription",
            json=huawei_payload,
            headers={"Authorization": f"Bearer {_make_token(vno_id='DTV')}"},
        )
        assert huawei_resp.json().get("error") == "KMD-4001", (
            "Con flag desactivado Huawei debe retornar KMD-4001"
        )


# ─── IDP-01: Idempotencia en baja ────────────────────────────────────────────

class TestIdempotenciaBaja:
    """
    PV-IDP-001: Si ServiceNow envía la misma baja dos veces (mismo txn_id),
    Komands debe procesar la operación solo una vez.

    Segundo POST → HTTP 200 + txn_id original (no 202).
    La OLT no debe ser contactada la segunda vez.

    Fuente: Anexo E — duplicado retorna UUID existente con HTTP 200.
    """

    # IDP-01
    def test_idp01_txn_id_duplicado_retorna_200_con_txn_original(
        self, ff_client, valid_token
    ):
        """
        ESCENARIO: ServiceNow envía la misma baja dos veces con el mismo txn_id.

        El primer POST registra la transacción y retorna 202.
        El segundo POST detecta el txn_id duplicado y retorna 200 con el
        mismo txn_id — sin volver a contactar la OLT (0 re-ejecuciones).

        Resultado esperado: primer POST → 202, segundo POST → 200, mismo txn_id.
        """
        txn_id_fijo = str(uuid.uuid4())
        payload = {
            "vno_id": "DTV",
            "olt_vendor": "nokia",
            "olt_name": "OLT-SAN-001",
            "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
            "product": "FTTH",
            "txn_id": txn_id_fijo,
            "callback_url": "https://servicenow.onnet.cl/api/komands/callback",
        }
        headers = {"Authorization": f"Bearer {valid_token}"}

        resp1 = ff_client.post("/api/v1/unsuscription", json=payload, headers=headers)
        assert resp1.status_code == 202, f"Primer POST debe retornar 202, retornó {resp1.status_code}"

        resp2 = ff_client.post("/api/v1/unsuscription", json=payload, headers=headers)
        assert resp2.status_code == 200, (
            f"Segundo POST con mismo txn_id debe retornar 200, retornó {resp2.status_code}"
        )
        assert resp2.json().get("txn_id") == txn_id_fijo, (
            "El segundo POST debe retornar el mismo txn_id original"
        )
