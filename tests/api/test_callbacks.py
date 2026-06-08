"""API tests — Mecanismo de callbacks POST-operación (PV-CBK).

Convención: test_cbk<NN>_<escenario>

Qué estamos probando:
    En Komands todas las operaciones son asíncronas: el cliente recibe HTTP 202
    con un txn_id, y el resultado real llega después por callback.

    Cuando el worker de fondo termina (con éxito o con error), Komands debe
    hacer un HTTP POST a la callback_url que ServiceNow incluyó en el request
    original. Este callback es el único mecanismo que tiene ServiceNow para
    saber si la operación en la OLT fue exitosa.

    Probamos dos cosas:
      1. Contrato del payload: los campos que Komands envía a ServiceNow
         tienen los valores correctos (txn_id, status, error_code, etc.)
      2. Resiliencia: si ServiceNow no está disponible, Komands no crashea
         y registra el fallo para poder reintentarlo después.

    respx intercepta el HTTP saliente a ServiceNow para que no necesitemos
    una instancia real de ServiceNow ni conectividad de red.

Fuentes:
    - Plan_Pruebas_Completo_v4_Final.xlsx → Release 1 → PV-CBK-001 a PV-CBK-005
    - LLD ADR-008 → sección Callbacks → campos requeridos por ServiceNow
"""
import json

import httpx
import pytest
import respx

pytestmark = [pytest.mark.postventa, pytest.mark.mock_only]

# URL de callback configurada por ServiceNow en cada request
SERVICENOW_CB_URL = "https://servicenow.onnet.cl/api/komands/callback"

# Payload base para disparar una notificación de completitud
_BASE = {
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "operation": "activation",
    "vno_id": "DTV",
    "callback_url": SERVICENOW_CB_URL,
}


# ─── CBK-01 a CBK-03: Contrato del payload enviado a ServiceNow ──────────────

class TestCallbackContrato:
    """
    ServiceNow necesita campos específicos en cada callback para poder cerrar
    la orden de trabajo o escalar el incidente:

      txn_id    → vincula el callback con la solicitud original
      status    → COMPLETED | FAILED | ROLLED_BACK
      operation → qué operación terminó (activation, deactivation, swap, etc.)
      vno_id    → a qué operador pertenece el acceso afectado

    Para FAILED y ROLLED_BACK también se requiere:
      error_code    → código normalizado para enrutar el escalado
      error_message → descripción legible para el técnico

    Si el callback llega a ServiceNow sin alguno de estos campos, la orden
    queda en estado indeterminado y requiere intervención manual.
    """

    # CBK-01
    @respx.mock
    def test_cbk01_operacion_completada_payload_tiene_campos_requeridos(self, test_client):
        """
        ESCENARIO: Una activación termina con éxito — Komands notifica COMPLETED a ServiceNow.

        El técnico en ServiceNow verá la orden cerrada automáticamente.
        Para eso, el callback debe llegar con txn_id, status, operation y vno_id.

        Resultado esperado: HTTP 200 desde Komands y callback disparado con todos los campos.
        """
        # Interceptamos la llamada HTTP saliente a ServiceNow
        route = respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(200, json={"received": True})
        )

        response = test_client.post(
            "/api/v1/internal/complete",
            json={**_BASE, "status": "COMPLETED"},
        )

        assert response.status_code == 200
        # Si no se llamó a ServiceNow, la orden quedó sin cerrar
        assert route.called, "Komands no disparó el callback a ServiceNow"

        body = json.loads(route.calls[0].request.content)
        assert body.get("txn_id") == "3fa85f64-5717-4562-b3fc-2c963f66afa6", (
            f"txn_id incorrecto en el callback: {body.get('txn_id')}"
        )
        assert body.get("status") == "COMPLETED"
        assert body.get("operation") == "activation"
        assert body.get("vno_id") == "DTV"

    # CBK-02
    @respx.mock
    def test_cbk02_operacion_fallida_callback_incluye_error_code_para_escalado(self, test_client):
        """
        ESCENARIO: Una baja falla con ONT no encontrado — callback notifica FAILED con KMD-2002.

        ServiceNow usa el error_code para saber a quién escalar:
          KMD-2002 → verificar datos en ServiceNow (problema de datos)
          KMD-5010 → escalar a Redes (problema de infraestructura)
          KMD-2004 → escalar a Ingeniería de Redes (swap asimétrico, urgente)

        Sin error_code, el técnico no sabe qué hacer con la orden fallida.

        Resultado esperado: callback disparado con status=FAILED y error_code=KMD-2002.
        """
        route = respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(200, json={"received": True})
        )

        response = test_client.post(
            "/api/v1/internal/complete",
            json={
                **_BASE,
                "status": "FAILED",
                "operation": "deactivation",
                "error_code": "KMD-2002",
                "error_message": "ONT no encontrado en la OLT — verificar ID en ServiceNow",
            },
        )

        assert response.status_code == 200
        assert route.called, "Komands no disparó el callback a ServiceNow"

        body = json.loads(route.calls[0].request.content)
        assert body.get("status") == "FAILED"
        assert body.get("error_code") == "KMD-2002", (
            f"Se esperaba error_code=KMD-2002, se obtuvo: {body.get('error_code')}"
        )
        # error_message no puede estar vacío: el técnico necesita saber qué pasó
        assert body.get("error_message"), "error_message está vacío — el técnico no sabrá qué hacer"

    # CBK-03
    @respx.mock
    def test_cbk03_operacion_rolled_back_callback_notifica_estado_y_error(self, test_client):
        """
        ESCENARIO: Una baja Huawei con INDEX parcial hace rollback — callback notifica ROLLED_BACK.

        ROLLED_BACK es el estado más crítico: Komands empezó a ejecutar,
        algo falló, y tuvo que deshacer. ServiceNow debe abrir un incidente
        porque la red estuvo en estado inconsistente durante el rollback.

        Resultado esperado: callback con status=ROLLED_BACK y error_code=KMD-2002.
        """
        route = respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(200, json={"received": True})
        )

        response = test_client.post(
            "/api/v1/internal/complete",
            json={
                **_BASE,
                "status": "ROLLED_BACK",
                "operation": "deactivation",
                "error_code": "KMD-2002",
                "error_message": "INDEX parcial: 2 de 3 service-ports resueltos — rollback ejecutado",
            },
        )

        assert response.status_code == 200
        assert route.called

        body = json.loads(route.calls[0].request.content)
        assert body.get("status") == "ROLLED_BACK"
        assert body.get("error_code") == "KMD-2002"


# ─── CBK-04 a CBK-05: Resiliencia cuando ServiceNow no está disponible ────────

class TestCallbackResiliencia:
    """
    En producción, ServiceNow puede estar en mantenimiento o la red entre
    Komands y ServiceNow puede tener problemas. Komands no debe crashear
    en esos casos — la operación en la OLT ya se ejecutó correctamente y
    ese resultado no debe perderse.

    El comportamiento esperado:
      - Komands responde HTTP 200 (el endpoint de Komands funcionó)
      - ok=False en el body (el callback no llegó a ServiceNow)
      - El error queda registrado para que el sistema de reintentos lo procese
    """

    # CBK-04
    @respx.mock
    def test_cbk04_servicenow_responde_503_komands_informa_el_fallo(self, test_client):
        """
        ESCENARIO: ServiceNow está en mantenimiento y responde 503 al recibir el callback.

        Esto ocurre en ventanas de mantenimiento programadas.
        Komands registra que el callback falló (ok=False, callback_http_status=503)
        para que el scheduler lo reintente después.

        Resultado esperado: HTTP 200 desde Komands, ok=False, callback_http_status=503.
        """
        respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(503, json={"error": "Service Unavailable"})
        )

        response = test_client.post(
            "/api/v1/internal/complete",
            json={**_BASE, "status": "COMPLETED"},
        )

        # Komands no debe devolver 500 aunque ServiceNow haya fallado
        assert response.status_code == 200, (
            f"Komands devolvió {response.status_code} — se esperaba 200 aunque ServiceNow fallara"
        )
        data = response.json()
        # Komands informa el HTTP status que recibió de ServiceNow
        assert data.get("callback_http_status") == 503, (
            f"Se esperaba callback_http_status=503, se obtuvo: {data.get('callback_http_status')}"
        )

    # CBK-05
    @respx.mock
    def test_cbk05_servicenow_inaccesible_komands_no_crashea(self, test_client):
        """
        ESCENARIO: ServiceNow no responde — conexión rechazada o timeout de red.

        Ocurre cuando hay un corte de red entre el datacenter de Komands y
        el de ServiceNow. Es más grave que el 503 porque no hay ni respuesta.

        Komands debe manejar el ConnectError de httpx sin lanzar excepción
        no controlada, y reportar ok=False con el mensaje del error.

        Resultado esperado: HTTP 200 desde Komands, ok=False, campo error presente.
        """
        respx.post(SERVICENOW_CB_URL).mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        response = test_client.post(
            "/api/v1/internal/complete",
            json={**_BASE, "status": "COMPLETED"},
        )

        assert response.status_code == 200, (
            f"Komands devolvió {response.status_code} — se esperaba 200 aunque la red fallara"
        )
        data = response.json()
        assert data.get("ok") is False, (
            "Komands debería reportar ok=False cuando el callback no llegó a ServiceNow"
        )
        assert data.get("error"), "Komands debería incluir el mensaje del error para el log"
