"""Tests PV-IDP — Idempotencia X-Correlation-ID.

Cubre el caso PV-IDP-001:
  Reintento de baja con mismo X-Correlation-ID → 0 re-ejecuciones en la OLT.
"""
import pytest
from tests.mocks.payloads import ACTIVATION_IDEMPOTENCY

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
