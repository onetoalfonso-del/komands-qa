"""Tests PV-RBK — Rollback automático Komands.

Cubre:
  RBK-001: Nokia activación paso crítico falla → ROLLED_BACK
  RBK-002: Huawei activación paso crítico falla → ROLLED_BACK
  RBK-003: Rollback también falla → ROLLBACK_FAILED KMD-5030
  RBK-004: Paso NO crítico falla → operación continúa → ACCEPTED
  RBK-005: Service-modification Nokia paso crítico falla → ROLLED_BACK
  RBK-006: Unsubscription Nokia paso crítico falla → ROLLED_BACK

Fuentes:
    - HLD §8.12: "Cuando una transacción falla y el rollback automático también falla,
      la transacción queda en estado ROLLBACK_FAILED. El Orchestrator registra el estado
      en PostgreSQL con detalle de qué pasos fallaron."
    - Plan QA T3: rollback se prueba con mocks de respuestas OLT (no requiere OLT real).
"""
import pytest
from tests.mocks.payloads import (
    ACTIVATION_NOKIA_ROLLBACK,
    ACTIVATION_HUAWEI_ROLLBACK,
    ACTIVATION_ROLLBACK_FAILED,
    ACTIVATION_NON_CRITICAL_FAIL,
    MODIFICATION_NOKIA_ROLLBACK,
    DEACTIVATION_NOKIA_ROLLBACK,
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


class TestRollbackEnOtrasOperaciones:
    """
    Rollback automático en service-modification y unsubscription.

    Los tests RBK-001 a RBK-004 cubren rollback en activación.
    Este módulo verifica que el mecanismo de rollback también funciona
    correctamente en las operaciones de modificación y baja.

    El comportamiento esperado es el mismo que en activación: si un paso
    crítico falla, Komands revierte los pasos ejecutados y retorna ROLLED_BACK
    con el código de error KMD-5021 (fallo de ejecución CLI con rollback exitoso).

    Fuente: HLD §8.12, Plan QA T3 (mocks sin OLT real).
    """

    # RBK-005
    def test_rbk05_modification_nokia_paso_critico_falla_retorna_rolled_back(
        self, test_client, auth_headers
    ):
        """
        ESCENARIO: Service-modification Nokia (cambio de velocidad) — paso crítico
        falla durante la ejecución CLI en la OLT.

        Komands había iniciado la modificación del perfil de velocidad (paso 1 OK)
        pero el paso 2 (aplicar nuevo QoS) falla. Komands revierte el paso 1
        (restaura el perfil de velocidad original) y retorna ROLLED_BACK.

        El cliente sigue con su velocidad anterior — no queda en estado inconsistente.

        Resultado esperado: HTTP 202 con status=ROLLED_BACK y error_code=KMD-5021.
        """
        response = test_client.post(
            "/api/Komands/v1/modification",
            json=MODIFICATION_NOKIA_ROLLBACK,
            headers=auth_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ROLLED_BACK", (
            f"Se esperaba ROLLED_BACK en modification, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-5021", (
            f"Se esperaba KMD-5021, se obtuvo: {data.get('error_code')}"
        )

    # RBK-006
    def test_rbk06_unsubscription_nokia_paso_critico_falla_retorna_rolled_back(
        self, test_client, auth_headers
    ):
        """
        ESCENARIO: Unsubscription Nokia — paso crítico falla durante la baja CLI.

        Komands había iniciado la baja del servicio (paso 1 OK) pero el paso 2
        (eliminar service-port) falla. Komands revierte el paso 1 (re-activa el
        service-port) y retorna ROLLED_BACK.

        El cliente queda con el servicio activo — no queda desconectado sin que
        la baja se haya completado.

        Resultado esperado: HTTP 202 con status=ROLLED_BACK y error_code=KMD-5021.
        """
        response = test_client.post(
            "/api/Komands/v1/unsubscription",
            json=DEACTIVATION_NOKIA_ROLLBACK,
            headers=auth_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ROLLED_BACK", (
            f"Se esperaba ROLLED_BACK en unsubscription, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-5021", (
            f"Se esperaba KMD-5021, se obtuvo: {data.get('error_code')}"
        )
