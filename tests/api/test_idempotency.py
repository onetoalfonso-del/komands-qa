"""Tests PV-IDP — Idempotencia X-Correlation-ID.

Cubre:
  IDP-001: Reintento con mismo X-Correlation-ID → segunda llamada retorna 200 con txn_id original.
  IDP-002: Mismo external_order_id pero distinto X-Correlation-ID → dos transacciones independientes.
  IDP-003: Idempotencia se basa en X-Correlation-ID, NO en external_order_id.

Fuentes:
    - AnexoH v2.2 §Idempotencia (línea 1470): "Si Komands recibe un request con el mismo
      X-Correlation-ID que un request ya procesado, detecta el duplicado y retorna HTTP 200
      (no 202) con el txn_id existente, sin re-ejecutar la operacion en la OLT."
    - HLD §8.11: "Si ServiceNow reenvía un request con el mismo UUID (por timeout, falla de red,
      o reintento manual), Komands detecta el duplicado y retorna el resultado de la ejecución
      original sin re-ejecutar la operación."
"""
import pytest
from tests.mocks.payloads import ACTIVATION_IDEMPOTENCY, ACTIVATION_NOKIA_FTTH_VALID

FIXED_CORR_ID = "idempotency-test-fixed-uuid-001"


class TestIdempotencia:

    # IDP-001
    def test_idp01_correlation_id_duplicado_no_reejcuta_en_olt(self, test_client, auth_headers):
        """
        ESCENARIO: ServiceNow reintenta una activación con el mismo X-Correlation-ID.

        Primera llamada → 202 ACCEPTED con txn_id generado.
        Segunda llamada con mismo X-Correlation-ID → 200 con el txn_id original.
        La OLT solo fue contactada 1 vez (no hay doble ejecución).

        Resultado esperado: Segunda llamada retorna 200 con txn_id idéntico al primero.
        """
        headers_with_corr = {**auth_headers, "X-Correlation-ID": FIXED_CORR_ID}

        # Primera llamada
        r1 = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_IDEMPOTENCY,
            headers=headers_with_corr,
        )
        assert r1.status_code == 202, f"Primera llamada debe ser 202, obtuvo {r1.status_code}"
        txn_id_original = r1.json().get("txn_id")
        assert txn_id_original, "Primera llamada debe retornar txn_id"

        # Segunda llamada — mismo X-Correlation-ID
        r2 = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_IDEMPOTENCY,
            headers=headers_with_corr,
        )
        assert r2.status_code == 200, (
            f"Segunda llamada debe ser 200 (idempotente), obtuvo {r2.status_code}"
        )
        txn_id_repetido = r2.json().get("txn_id")
        assert txn_id_repetido == txn_id_original, (
            f"txn_id debe ser idéntico: esperado={txn_id_original}, obtuvo={txn_id_repetido}"
        )


class TestIdempotenciaExternalOrderId:
    """
    external_order_id NO es clave de idempotencia.

    AnexoH v2.2 y HLD §8.11 son explícitos: la idempotencia se basa exclusivamente
    en el X-Correlation-ID (o UUID de transacción). El external_order_id es solo
    para trazabilidad y agrupación de operaciones de una misma Service Order en
    ServiceNow — enviar dos requests con el mismo external_order_id pero distinto
    X-Correlation-ID genera dos transacciones independientes en la OLT.

    Esto protege contra un malentendido operacional: un operador podría pensar que
    duplicar el external_order_id previene doble ejecución, cuando en realidad no.
    """

    # IDP-02
    def test_idp02_mismo_external_order_id_distinto_correlation_id_genera_dos_transacciones(
        self, test_client, auth_headers
    ):
        """
        ESCENARIO: ServiceNow envía dos requests con el mismo external_order_id
        pero X-Correlation-ID distintos (por ejemplo, al crear dos órdenes de trabajo
        para el mismo cliente en un corto periodo de tiempo).

        Komands trata cada request como transacción independiente porque el
        X-Correlation-ID es diferente.

        Resultado esperado: ambas llamadas retornan HTTP 202, NO hay idempotencia.
        """
        shared_order_id = "SO-SHARED-001"
        payload_1 = {**ACTIVATION_NOKIA_FTTH_VALID, "external_order_id": shared_order_id}
        payload_2 = {**ACTIVATION_NOKIA_FTTH_VALID, "external_order_id": shared_order_id}

        headers_1 = {**auth_headers, "X-Correlation-ID": "corr-idp02-first"}
        headers_2 = {**auth_headers, "X-Correlation-ID": "corr-idp02-second"}

        r1 = test_client.post("/api/Komands/v1/activation", json=payload_1, headers=headers_1)
        r2 = test_client.post("/api/Komands/v1/activation", json=payload_2, headers=headers_2)

        assert r1.status_code == 202, (
            f"Primera llamada (corr-idp02-first) debería ser 202, obtuvo {r1.status_code}"
        )
        assert r2.status_code == 202, (
            f"Segunda llamada (corr-idp02-second) debería ser 202 (no 200), obtuvo {r2.status_code}. "
            "external_order_id no debe bloquear una segunda transacción con distinto X-Correlation-ID"
        )

    # IDP-03
    def test_idp03_external_order_id_no_desencadena_deduplicacion(self, test_client, auth_headers):
        """
        ESCENARIO: Verificación explícita de que el campo external_order_id NO actúa
        como clave de idempotencia en Komands.

        AnexoH v2.2 (línea 1756): "La idempotencia se basa exclusivamente en el
        X-Correlation-ID. Si ServiceNow envía un request idéntico pero con UUID diferente,
        Komands lo trata como una nueva transacción."

        El resultado de este test documenta el comportamiento esperado para evitar
        confusión futura entre external_order_id (agrupación) y X-Correlation-ID
        (deduplicación).

        Resultado esperado: segunda llamada retorna 202 (nueva transacción), NO 200.
        """
        payload = {**ACTIVATION_NOKIA_FTTH_VALID, "external_order_id": "SO-SAME-ORDER-999"}

        r1 = test_client.post(
            "/api/Komands/v1/activation", json=payload,
            headers={**auth_headers, "X-Correlation-ID": "corr-idp03-a"},
        )
        r2 = test_client.post(
            "/api/Komands/v1/activation", json=payload,
            headers={**auth_headers, "X-Correlation-ID": "corr-idp03-b"},
        )

        assert r1.status_code == 202
        assert r2.status_code == 202, (
            "La segunda llamada con distinto X-Correlation-ID debe ser 202 (transacción nueva). "
            "Si retorna 200, external_order_id está siendo usado incorrectamente como clave de idempotencia."
        )
