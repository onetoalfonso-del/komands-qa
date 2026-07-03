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
      1. Contrato del payload (AnexoH v2.2): todos los campos requeridos están
         presentes y tienen los tipos/valores correctos.
      2. Resiliencia: si ServiceNow no está disponible, Komands no crashea
         y registra el fallo para poder reintentarlo después.

    respx intercepta el HTTP saliente a ServiceNow para que no necesitemos
    una instancia real de ServiceNow ni conectividad de red.

Fuentes:
    - Plan_Pruebas_Completo_v4_Final.xlsx → Release 1 → PV-CBK-001 a PV-CBK-005
    - AnexoH_Especificacion_APIs_v2_2_FINAL.docx → sección Callbacks — contrato completo
"""
import json

import httpx
import pytest
import respx

pytestmark = [pytest.mark.postventa, pytest.mark.mock_only]


@pytest.fixture(scope="module", autouse=True)
def _aviso_mock_callbacks():
    import sys
    out = sys.__stdout__
    sep = "=" * 64
    out.write("\n" + sep + "\n")
    out.write("  [MOCK ONLY] test_callbacks.py\n")
    out.write("  Valida el CONTRATO del payload JSON que Komands enviaria\n")
    out.write("  a ServiceNow: campos requeridos, tipos y estructura\n")
    out.write("  segun AnexoH v2.2. NO prueba la entrega real.\n")
    out.write("  Entrega real = T4 (requiere OLTs lab + SN disponible).\n")
    out.write(sep + "\n")
    out.flush()
    yield

# URL de callback configurada por ServiceNow en cada request
SERVICENOW_CB_URL = "https://servicenow.onnet.cl/api/komands/callback"

# Payload base para disparar una notificación de completitud.
# Incluye todos los campos requeridos por AnexoH v2.2 para que el mock
# pueda construir el payload de callback completo.
_BASE = {
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "correlation_id": "corr-test-001",
    "external_order_id": "ORD-SN-TEST-001",
    "operation": "activation",
    "vno_id": "DTV",
    "vno_code": "DTV",
    "olt_name": "OLT-SAN-001",
    "started_at": "2026-06-09T10:00:00Z",
    "completed_at": "2026-06-09T10:00:45Z",
    "duration_ms": 1250,
    "steps": [],
    "callback_url": SERVICENOW_CB_URL,
}


# ─── CBK-01 a CBK-03: Contrato del payload enviado a ServiceNow ──────────────

class TestCallbackContrato:
    """
    ServiceNow cierra órdenes de trabajo en base al payload del callback.
    AnexoH v2.2 define un contrato estricto — cada campo tiene un propósito:

      txn_id           → vincula el callback con la solicitud original
      correlation_id   → traza el request entre sistemas (X-Correlation-ID)
      external_order_id→ ID de la orden en ServiceNow — para cerrarla
      status           → COMPLETED | FAILED | ROLLED_BACK | ROLLED_BACK_FAILED
      operation        → qué operación terminó (activation, deactivation, …)
      vno_code         → operador afectado (DTV, CVTR, ENTEL, TCH)
      olt_name         → OLT donde ocurrió la operación
      started_at       → inicio de ejecución (ISO 8601)
      completed_at     → fin de ejecución (ISO 8601)
      duration_ms      → duración total en milisegundos
      steps            → lista de pasos ejecutados (auditoría)

    Para FAILED / ROLLED_BACK también se requiere:
      error.code       → código normalizado (KMD-xxxx) para enrutar escalado
      error.message    → descripción legible para el técnico
      error.retryable  → true si ServiceNow puede reintentar automáticamente

    Si falta cualquier campo, ServiceNow no puede cerrar la orden
    automáticamente y requiere intervención manual.
    """

    # CBK-01
    @respx.mock
    def test_cbk01_operacion_completada_payload_contiene_contrato_completo(self, test_client):
        """
        ESCENARIO: Una activación termina con éxito — Komands notifica COMPLETED a ServiceNow
        con el contrato completo de AnexoH v2.2.

        El técnico en ServiceNow verá la orden cerrada automáticamente.
        Para eso, el callback debe incluir todos los campos del contrato.

        Resultado esperado: HTTP 200 desde Komands y callback con todos los campos requeridos.
        """
        route = respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(200, json={"received": True})
        )

        response = test_client.post(
            "/api/Komands/v1/internal/complete",
            json={**_BASE, "status": "COMPLETED"},
        )

        assert response.status_code == 200
        assert route.called, "Komands no disparó el callback a ServiceNow"

        body = json.loads(route.calls[0].request.content)

        # Campos de identidad y trazabilidad
        assert body.get("txn_id") == "3fa85f64-5717-4562-b3fc-2c963f66afa6", (
            f"txn_id incorrecto: {body.get('txn_id')}"
        )
        assert body.get("correlation_id") == "corr-test-001", (
            "correlation_id ausente — no se puede vincular con X-Correlation-ID del request original"
        )
        assert body.get("external_order_id") == "ORD-SN-TEST-001", (
            "external_order_id ausente — ServiceNow no podrá cerrar la orden de trabajo"
        )

        # Campos de resultado
        assert body.get("status") == "COMPLETED"
        assert body.get("operation") == "activation"
        assert body.get("vno_code") == "DTV", (
            f"vno_code incorrecto (AnexoH v2.2 usa vno_code, no vno_id): {body.get('vno_code')}"
        )
        assert body.get("olt_name") == "OLT-SAN-001", (
            "olt_name ausente — ServiceNow no sabrá qué OLT ejecutó la operación"
        )

        # Campos de temporización
        assert body.get("started_at"), "started_at ausente — auditoría requiere timestamp de inicio"
        assert body.get("completed_at"), "completed_at ausente — auditoría requiere timestamp de fin"
        assert isinstance(body.get("duration_ms"), int), (
            f"duration_ms debe ser entero, se obtuvo: {type(body.get('duration_ms'))}"
        )
        assert body.get("duration_ms") > 0, "duration_ms debe ser positivo"

        # Auditoría de pasos
        assert isinstance(body.get("steps"), list), (
            "steps debe ser lista — requerido por AnexoH v2.2 aunque esté vacía"
        )

    # CBK-02 | PV-CBK-004
    @respx.mock
    def test_cbk02_operacion_fallida_callback_incluye_error_object_con_retryable(self, test_client):
        """
        ESCENARIO: Una baja falla con ONT no encontrado — callback notifica FAILED
        con el objeto error completo de AnexoH v2.2.

        ServiceNow usa error.code para enrutar el escalado:
          KMD-2002 → equipo de datos (problema de inventario)
          KMD-5020 → redes (timeout SSH, problema de infraestructura)
        error.retryable indica si el scheduler puede reintentar automáticamente.

        Resultado esperado: callback con status=FAILED y error.{code, message, retryable}.
        """
        route = respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(200, json={"received": True})
        )

        response = test_client.post(
            "/api/Komands/v1/internal/complete",
            json={
                **_BASE,
                "status": "FAILED",
                "operation": "deactivation",
                "error_code": "KMD-2002",
                "error_message": "ONT no encontrado en la OLT — verificar ID en ServiceNow",
                "error_retryable": False,
            },
        )

        assert response.status_code == 200
        assert route.called, "Komands no disparó el callback a ServiceNow"

        body = json.loads(route.calls[0].request.content)
        assert body.get("status") == "FAILED"

        # Verifica que se use el objeto error (no campos planos error_code/error_message)
        error = body.get("error")
        assert error is not None, (
            "Campo 'error' ausente en el callback — AnexoH v2.2 requiere objeto error para FAILED"
        )
        assert error.get("code") == "KMD-2002", (
            f"error.code incorrecto: {error.get('code')}"
        )
        assert error.get("message"), "error.message vacío — el técnico no sabrá qué ocurrió"
        assert isinstance(error.get("retryable"), bool), (
            f"error.retryable debe ser booleano, se obtuvo: {type(error.get('retryable'))}"
        )
        assert error.get("retryable") is False, (
            "KMD-2002 (dato incorrecto) no es reintentable — solo reintentables son errores transitorios"
        )

    # CBK-03
    @respx.mock
    def test_cbk03_operacion_rolled_back_callback_notifica_estado_y_error(self, test_client):
        """
        ESCENARIO: Una baja Huawei con INDEX parcial hace rollback — callback notifica
        ROLLED_BACK con el objeto error completo.

        ROLLED_BACK es el estado más crítico: Komands empezó a ejecutar,
        algo falló, y tuvo que deshacer los cambios.
        ServiceNow debe abrir un incidente porque la red estuvo en estado
        inconsistente durante el rollback.

        Resultado esperado: callback con status=ROLLED_BACK y error.code=KMD-2002.
        """
        route = respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(200, json={"received": True})
        )

        response = test_client.post(
            "/api/Komands/v1/internal/complete",
            json={
                **_BASE,
                "status": "ROLLED_BACK",
                "operation": "deactivation",
                "error_code": "KMD-2002",
                "error_message": "INDEX parcial: 2 de 3 service-ports resueltos — rollback ejecutado",
                "error_retryable": False,
            },
        )

        assert response.status_code == 200
        assert route.called

        body = json.loads(route.calls[0].request.content)
        assert body.get("status") == "ROLLED_BACK"

        error = body.get("error")
        assert error is not None, "Campo 'error' ausente para ROLLED_BACK"
        assert error.get("code") == "KMD-2002"
        assert isinstance(error.get("retryable"), bool), (
            "error.retryable debe ser booleano incluso en ROLLED_BACK"
        )


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

    # CBK-04 | PV-CBK-002
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
            "/api/Komands/v1/internal/complete",
            json={**_BASE, "status": "COMPLETED"},
        )

        assert response.status_code == 200, (
            f"Komands devolvió {response.status_code} — se esperaba 200 aunque ServiceNow fallara"
        )
        data = response.json()
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
            "/api/Komands/v1/internal/complete",
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


# ─── CBK-06: CALLBACK_FAILED tras 5 reintentos agotados (PV-CBK-003) ─────────

class TestCallbackRetriesAgotados:
    """
    PV-CBK-003: Después de 5 intentos fallidos de entrega, Komands marca la
    transacción como CALLBACK_FAILED.

    El sistema de reintentos está controlado por las propiedades del sistema:
      x_komands.retry.max_attempts = 5
      x_komands.retry.interval_seconds = 10
      x_komands.retry.retryable_return_codes = "40,50"

    Si ServiceNow devuelve 503 en los 5 intentos, Komands:
      1. Registra cada intento fallido.
      2. Al agotar los reintentos, marca la transacción como CALLBACK_FAILED.
      3. Reporta ok=False con exhausted=True para que el operador sepa
         que el callback necesita intervención manual.

    No hay re-ejecución de la operación en la OLT — la red ya fue modificada.
    El problema es solo la notificación a ServiceNow.
    """

    # CBK-06 → PV-CBK-003
    @respx.mock
    def test_cbk06_callback_failed_tras_reintentos_agotados(self, test_client):
        """
        ESCENARIO: ServiceNow devuelve 503 en todos los intentos de callback.

        Komands ha intentado 5 veces entregar la notificación. En el último
        intento (attempt=5 de max_attempts=5), el scheduler marca la transacción
        como CALLBACK_FAILED y detiene los reintentos.

        ServiceNow tendrá que reconciliar el estado manualmente consultando
        GET /transaction/{txn_id}/status.

        Resultado esperado: HTTP 200 desde Komands, ok=False, exhausted=True
        (o status=CALLBACK_FAILED en el body).
        """
        respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(503, json={"error": "Service Unavailable"})
        )

        response = test_client.post(
            "/api/Komands/v1/internal/complete",
            json={
                **_BASE,
                "status": "COMPLETED",
                "attempt": 5,
                "max_attempts": 5,
            },
        )

        assert response.status_code == 200, (
            f"Komands devolvió {response.status_code} — se esperaba 200 incluso al agotar reintentos"
        )
        data = response.json()
        assert data.get("ok") is False, (
            "Con reintentos agotados, ok debe ser False"
        )
        # El sistema debe marcar el intento como final (exhausted=True o status=CALLBACK_FAILED)
        assert data.get("exhausted") is True or data.get("status") == "CALLBACK_FAILED", (
            f"Tras agotar los {5} reintentos, Komands debe marcar la transacción como CALLBACK_FAILED. "
            f"Body recibido: {data}"
        )


# ─── CBK-07: ROLLED_BACK_FAILED — rollback también falló (PV-RBK-003) ────────

class TestRollbackFailed:
    """
    PV-RBK-003: La operación falló Y el rollback automático también falló.

    Es el peor escenario operacional: Komands intentó ejecutar una operación,
    algo salió mal en la OLT, intentó deshacer los cambios, y la reversión
    también falló. La red quedó en estado parcialmente modificado.

    Estado resultante: ROLLED_BACK_FAILED (distinto de ROLLED_BACK).
      - ROLLED_BACK: operación falló, rollback exitoso → red en estado original.
      - ROLLED_BACK_FAILED: operación falló, rollback también falló → red en
        estado desconocido, requiere intervención manual de Redes.

    Este estado se notifica a ServiceNow vía callback con error.code=KMD-5030.
    ServiceNow debe abrir un incidente P1 porque el cliente puede tener
    servicio parcial o sin servicio.
    """

    # CBK-07 → PV-RBK-003
    @respx.mock
    def test_cbk07_rolled_back_failed_callback_contiene_estado_critico(self, test_client):
        """
        ESCENARIO: Una baja Huawei falló y el rollback también falló.
        Komands notifica ROLLED_BACK_FAILED a ServiceNow con KMD-5030.

        ServiceNow debe abrir un incidente P1 automáticamente cuando recibe
        este estado — el cliente puede estar con servicio parcial.
        El objeto error debe incluir retryable=False porque no hay recuperación
        automática posible; requiere intervención manual de Redes.

        Resultado esperado: HTTP 200 desde Komands y callback con
        status=ROLLED_BACK_FAILED y error.code=KMD-5030.
        """
        route = respx.post(SERVICENOW_CB_URL).mock(
            return_value=httpx.Response(200, json={"received": True})
        )

        response = test_client.post(
            "/api/Komands/v1/internal/complete",
            json={
                **_BASE,
                "status": "ROLLED_BACK_FAILED",
                "operation": "unsuscription",
                "error_code": "KMD-5030",
                "error_message": (
                    "Rollback falló: no se pudo restaurar el service-port en la OLT. "
                    "Cliente en estado parcial — requiere intervención manual de Redes."
                ),
                "error_retryable": False,
            },
        )

        assert response.status_code == 200
        assert route.called, "Komands no disparó el callback a ServiceNow para ROLLED_BACK_FAILED"

        body = json.loads(route.calls[0].request.content)

        assert body.get("status") == "ROLLED_BACK_FAILED", (
            f"El callback debe notificar ROLLED_BACK_FAILED, se obtuvo: {body.get('status')}"
        )

        error = body.get("error")
        assert error is not None, (
            "Campo 'error' ausente para ROLLED_BACK_FAILED — ServiceNow no puede abrir el incidente"
        )
        assert error.get("code") == "KMD-5030", (
            f"Se esperaba KMD-5030 (rollback fallido), se obtuvo: {error.get('code')}"
        )
        assert error.get("retryable") is False, (
            "ROLLED_BACK_FAILED no es reintentable — requiere intervención manual de Redes"
        )
