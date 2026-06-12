"""Tests PV-RBK — Rollback automático Komands.

Cubre los 4 casos del módulo PV-RBK del Plan de Pruebas Post-Venta:
  RBK-001: Nokia paso crítico falla → ROLLED_BACK
  RBK-002: Huawei paso crítico falla → ROLLED_BACK
  RBK-003: Rollback también falla → ROLLBACK_FAILED KMD-5030
  RBK-004: Paso NO crítico falla → operación continúa → COMPLETED
"""
import pytest
from tests.mocks.payloads import (
    ACTIVATION_NOKIA_ROLLBACK,
    ACTIVATION_HUAWEI_ROLLBACK,
    ACTIVATION_ROLLBACK_FAILED,
    ACTIVATION_NON_CRITICAL_FAIL,
)


class TestRollbackAutomatico:

    # RBK-001 | PV-RBK-001
    def test_rbk01_nokia_paso_critico_falla_retorna_rolled_back(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia — paso crítico falla a mitad de ejecución.

        Komands ejecuta paso 1 OK. Paso 2 lanza excepción SSH.
        Al ser crítico, Komands revierte el paso 1 (rollback inverso).

        Resultado esperado: HTTP 202 con status=ROLLED_BACK y error_code=KMD-5021.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_ROLLBACK,
            headers=auth_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ROLLED_BACK", (
            f"Se esperaba ROLLED_BACK, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-5021", (
            f"Se esperaba KMD-5021, se obtuvo: {data.get('error_code')}"
        )

    # RBK-002 | PV-RBK-002
    def test_rbk02_huawei_paso_critico_falla_retorna_rolled_back(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Huawei — pasos 1 y 2 OK, paso 3 lanza excepción SSH.

        Komands revierte pasos 2 y 1 en orden inverso (rollback asimétrico Huawei).

        Resultado esperado: HTTP 202 con status=ROLLED_BACK y error_code=KMD-5021.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_HUAWEI_ROLLBACK,
            headers=auth_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ROLLED_BACK", (
            f"Se esperaba ROLLED_BACK, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-5021", (
            f"Se esperaba KMD-5021, se obtuvo: {data.get('error_code')}"
        )

    # RBK-003 | PV-RBK-003
    def test_rbk03_rollback_tambien_falla_retorna_rollback_failed(self, test_client, auth_headers):
        """
        ESCENARIO: Paso crítico falla Y el rollback de ese paso también falla.

        La OLT queda en estado inconsistente. Komands no puede recuperarla
        automáticamente y escala a Ingeniería de Redes.

        Resultado esperado: HTTP 202 con status=ROLLBACK_FAILED y error_code=KMD-5030.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_ROLLBACK_FAILED,
            headers=auth_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ROLLBACK_FAILED", (
            f"Se esperaba ROLLBACK_FAILED, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-5030", (
            f"Se esperaba KMD-5030, se obtuvo: {data.get('error_code')}"
        )

    # RBK-004 | PV-RBK-004
    def test_rbk04_paso_no_critico_falla_operacion_continua(self, test_client, auth_headers):
        """
        ESCENARIO: Un paso marcado como NO crítico lanza excepción SSH.

        Komands lo omite (SKIPPED en steps[]) y continúa con los pasos siguientes.
        La operación se completa aunque ese paso no se ejecutó.

        Resultado esperado: HTTP 202 con status=ACCEPTED (operación encolada, continuará).
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NON_CRITICAL_FAIL,
            headers=auth_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Se esperaba ACCEPTED (operación continúa), se obtuvo: {data.get('status')}"
        )
