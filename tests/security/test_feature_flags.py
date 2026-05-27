"""
Tests de Feature Flags — FF-01 a FF-04 + IDEM-01 a IDEM-02
=============================================================
Fuente: docs/05_gaps_seguridad.md → secciones "Feature Flags" e "Idempotencia"

Qué son los Feature Flags en Komands:
    Son interruptores en la base de datos que controlan si el tráfico de una
    VNO va a Komands (nuevo) o a BluePlanet (viejo). Se activan VNO por VNO
    durante la migración. Si algo sale mal, se apagan en < 5 minutos sin
    necesitar un nuevo deploy.

    Tabla: komands.feature_flag
    Campos clave: vno_id, product, technology, operation, enabled

Qué es Idempotencia:
    Si ServiceNow envía el mismo txn_id dos veces (reintento, bug, timeout),
    Komands NO ejecuta la operación dos veces en la OLT.
    Devuelve el resultado anterior sin tocar la red.

Por qué se incluye Idempotencia aquí:
    Los docs clasifican IDEM como parte de seguridad — evita que un reintento
    accidental active o desactive un servicio dos veces.
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AppState
from tests.mocks.payloads import (
    ACTIVATION_NOKIA_FTTH_VALID,
    ACTIVATION_NOKIA_SSAA_GROUP_A,
    ACTIVATION_WITH_TXN_ID,
)

# Token válido de ServiceNow (DTV, scope write)
# Lo generamos inline para no depender del fixture valid_token
import time
from jose import jwt

def _token(vno_id="DTV"):
    return jwt.encode(
        {
            "sub": "servicenow-client",
            "vno_id": vno_id,
            "scope": "komands:write komands:read",
            "exp": int(time.time()) + 3600,
        },
        "test-secret-komands-qa",
        algorithm="HS256",
    )


class TestFeatureFlags:
    """
    FF-01 a FF-04: Comportamiento del interruptor de migración.

    Estado inicial de cada test: todos los flags desactivados (AppState vacío).
    Activamos los flags mediante POST /test/feature-flags dentro del test.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # FF-01: Flag DTV desactivado → tráfico va a BluePlanet
    # ──────────────────────────────────────────────────────────────────────────

    def test_ff01_flag_dtv_desactivado_retorna_kmd4001(
        self, ff_client: TestClient, ff_state: AppState
    ):
        """
        ESCENARIO: El flag de DTV está desactivado (como al inicio del proyecto).
                   ServiceNow envía una activación para DTV.

        Resultado esperado:
            Komands responde con KMD-4001 — ServiceNow debe usar BluePlanet.
            ON·NET no nota ningún cambio porque BluePlanet sigue procesando.

        Nota: El flag viene desactivado por defecto (AppState vacío).
        """
        # ARRANGE: desactivamos explícitamente el flag de DTV
        ff_client.post("/test/feature-flags", json={
            "vno_id": "DTV",
            "enabled": False,
        })
        headers = {"Authorization": f"Bearer {_token('DTV')}"}

        # ACT
        response = ff_client.post(
            "/api/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=headers,
        )

        # ASSERT: Komands "aceptó" el request pero dice "usa BluePlanet"
        body = response.json()
        assert body.get("error") == "KMD-4001", (
            f"Flag desactivado debería retornar KMD-4001 pero llegó: {body}"
        )
        assert body.get("redirect") == "blueplanet"

    # ──────────────────────────────────────────────────────────────────────────
    # FF-02: Flag DTV activado → Komands procesa normalmente
    # ──────────────────────────────────────────────────────────────────────────

    def test_ff02_flag_dtv_activado_procesa_en_komands(
        self, ff_client: TestClient
    ):
        """
        ESCENARIO: El flag de DTV se activa (semana 22-23 según calendario).
                   ServiceNow envía una activación para DTV.

        Resultado esperado:
            Komands procesa la operación normalmente → 202 + txn_id.
            ServiceNow no sabe ni le importa el cambio — misma respuesta de antes.
        """
        # ARRANGE: activamos el flag de DTV
        ff_client.post("/test/feature-flags", json={
            "vno_id": "DTV",
            "enabled": True,
        })
        headers = {"Authorization": f"Bearer {_token('DTV')}"}

        # ACT
        response = ff_client.post(
            "/api/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=headers,
        )

        # ASSERT: Komands procesa y responde 202
        assert response.status_code == 202, (
            f"Flag activado debería dar 202 pero llegó {response.status_code}"
        )
        body = response.json()
        assert "txn_id" in body
        assert body["status"] == "PENDING"

    # ──────────────────────────────────────────────────────────────────────────
    # FF-03: FTTH activado, SSAA desactivado → granularidad por producto
    # ──────────────────────────────────────────────────────────────────────────

    def test_ff03_ftth_activado_ssaa_desactivado(
        self, ff_client: TestClient
    ):
        """
        ESCENARIO: DTV migra FTTH primero, pero SSAA todavía va a BluePlanet.
                   Flags: DTV FTTH=enabled, DTV SSAA=disabled.

        Resultado esperado:
            - Activación FTTH de DTV → 202 (Komands procesa)
            - Activación SSAA de DTV → KMD-4001 (BluePlanet procesa)

        Por qué es importante:
            Permite migrar producto por producto sin afectar los otros.
            Si SSAA falla en Komands, solo se apaga ese flag — FTTH sigue.
        """
        # ARRANGE: flag FTTH activado, SSAA desactivado para DTV
        ff_client.post("/test/feature-flags", json={
            "vno_id": "DTV", "product": "FTTH", "enabled": True,
        })
        ff_client.post("/test/feature-flags", json={
            "vno_id": "DTV", "product": "SSAA", "enabled": False,
        })
        headers = {"Authorization": f"Bearer {_token('DTV')}"}

        # ACT 1: activación FTTH
        resp_ftth = ff_client.post(
            "/api/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=headers,
        )
        # ACT 2: activación SSAA
        resp_ssaa = ff_client.post(
            "/api/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_A,
            headers=headers,
        )

        # ASSERT FTTH: Komands procesa
        assert resp_ftth.status_code == 202, (
            f"FTTH con flag=True debería dar 202 pero dio {resp_ftth.status_code}"
        )

        # ASSERT SSAA: BluePlanet procesa
        ssaa_body = resp_ssaa.json()
        assert ssaa_body.get("error") == "KMD-4001", (
            f"SSAA con flag=False debería dar KMD-4001 pero llegó: {ssaa_body}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # FF-04: Rollback de flag — apagarlo en < 5 minutos
    # ──────────────────────────────────────────────────────────────────────────

    def test_ff04_rollback_flag_desvia_a_blueplanet(
        self, ff_client: TestClient
    ):
        """
        ESCENARIO: El flag de DTV estaba activado. Se detecta un problema
                   en producción y se apaga el flag. Las siguientes operaciones
                   deben ir a BluePlanet inmediatamente, sin deploy.

        Este es el mecanismo de contingencia del proyecto:
            Tiempo de rollback objetivo: < 5 minutos (solo cambiar enabled=false en BD).

        Resultado esperado:
            - Antes del rollback: 202 (Komands procesa)
            - Después del rollback: KMD-4001 (BluePlanet procesa)
        """
        headers = {"Authorization": f"Bearer {_token('DTV')}"}

        # ARRANGE: flag activado inicialmente
        ff_client.post("/test/feature-flags", json={
            "vno_id": "DTV", "enabled": True,
        })

        # ACT 1: primera operación — Komands activo
        resp_antes = ff_client.post(
            "/api/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=headers,
        )

        # Rollback: apagamos el flag (simula el cambio en BD)
        ff_client.post("/test/feature-flags", json={
            "vno_id": "DTV", "enabled": False,
        })

        # ACT 2: siguiente operación — debe ir a BluePlanet
        resp_despues = ff_client.post(
            "/api/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=headers,
        )

        # ASSERT antes del rollback: Komands procesó
        assert resp_antes.status_code == 202, (
            f"Antes del rollback debería ser 202 pero fue {resp_antes.status_code}"
        )

        # ASSERT después del rollback: va a BluePlanet
        body_despues = resp_despues.json()
        assert body_despues.get("error") == "KMD-4001", (
            f"Después del rollback debería ser KMD-4001 pero llegó: {body_despues}"
        )


class TestIdempotencia:
    """
    IDEM-01 y IDEM-02: El mismo txn_id no ejecuta la operación dos veces.

    Fuente: Anexo E — "Requests duplicados retornan UUID existente con HTTP 200"
    Por qué importa: evita activar/desactivar un servicio dos veces si
    ServiceNow hace un reintento por timeout.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # IDEM-01: Mismo txn_id → segunda vez devuelve resultado sin re-ejecutar
    # ──────────────────────────────────────────────────────────────────────────

    def test_idem01_txn_id_duplicado_no_reejecutar(
        self, ff_client: TestClient
    ):
        """
        ESCENARIO: ServiceNow envía la misma operación dos veces con el
                   mismo txn_id (reintento por timeout de red).

        Resultado esperado (Anexo E):
            - Primera vez → HTTP 202 (encolado y procesado)
            - Segunda vez → HTTP 200 con el mismo txn_id (sin re-ejecutar)

        La OLT solo recibe los comandos CLI una vez.
        """
        # ARRANGE: flag activo y payload con txn_id fijo
        ff_client.post("/test/feature-flags", json={"vno_id": "DTV", "enabled": True})
        headers = {"Authorization": f"Bearer {_token('DTV')}"}
        payload = ACTIVATION_WITH_TXN_ID  # tiene txn_id fijo en mocks/payloads.py

        # ACT: enviamos el mismo request dos veces
        resp1 = ff_client.post("/api/v1/activation", json=payload, headers=headers)
        resp2 = ff_client.post("/api/v1/activation", json=payload, headers=headers)

        # ASSERT primera vez: 202 (encolado)
        assert resp1.status_code == 202, (
            f"Primera vez debería ser 202 pero fue {resp1.status_code}"
        )

        # ASSERT segunda vez: 200 (mismo resultado, sin re-ejecutar)
        assert resp2.status_code == 200, (
            f"Segunda vez debería ser 200 (idempotente) pero fue {resp2.status_code}"
        )

        # El txn_id devuelto es el mismo en ambas respuestas
        assert resp1.json()["txn_id"] == resp2.json()["txn_id"], (
            "El txn_id debe ser el mismo en ambas respuestas"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # IDEM-02: Mismo txn_id con distinto payload → conflicto
    # ──────────────────────────────────────────────────────────────────────────

    def test_idem02_mismo_txn_id_distinto_payload_es_conflicto(
        self, ff_client: TestClient
    ):
        """
        ESCENARIO: ServiceNow envía el mismo txn_id pero con datos distintos.
                   Esto es un error del cliente — no un reintento legítimo.

        Ejemplo real: mismo txn_id pero distinto olt_name o ont_serial.
        Komands no puede saber cuál de los dos es el correcto, así que
        devuelve el primer resultado registrado sin modificarlo.

        Resultado esperado: HTTP 200 con el resultado original (el segundo
        request se ignora silenciosamente — no hay 409 por diseño en Komands).
        """
        # ARRANGE
        ff_client.post("/test/feature-flags", json={"vno_id": "DTV", "enabled": True})
        headers = {"Authorization": f"Bearer {_token('DTV')}"}

        payload_original = ACTIVATION_WITH_TXN_ID
        payload_distinto = {
            **ACTIVATION_WITH_TXN_ID,
            "olt_name": "OLT-DIFERENTE-999",  # distinto campo
            "ont_serial": "ALCLF9999999",
        }

        # ACT: primera vez con payload original, segunda vez con payload distinto
        resp1 = ff_client.post("/api/v1/activation", json=payload_original, headers=headers)
        resp2 = ff_client.post("/api/v1/activation", json=payload_distinto, headers=headers)

        # ASSERT: ambas respuestas tienen el mismo txn_id (el original gana)
        assert resp2.status_code == 200, (
            "Duplicado con payload distinto debe devolver el resultado original (200)"
        )
        assert resp1.json()["txn_id"] == resp2.json()["txn_id"], (
            "El segundo request debe devolver el txn_id original, no crear uno nuevo"
        )
