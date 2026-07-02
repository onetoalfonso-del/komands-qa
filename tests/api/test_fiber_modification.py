"""API tests — POST /api/Komands/v1/fiber-modification (cambio de pelo/puerto PON).

Convención: test_fm<NN>_<vendor>_<escenario>

Cubre:
  FM-01: Cambio de puerto PON Nokia GPON → 202 ACCEPTED
  FM-02: Cambio de puerto PON Huawei GPON → 202 ACCEPTED
  FM-03: Puerto PON destino sin capacidad → FAILED KMD-1003
  FM-04: Alta en destino falla tras baja exitosa en origen → ROLLED_BACK KMD-5021

Fuentes:
    - AnexoH_Especificacion_APIs_v2_2_FINAL.docx → POST /api/Komands/v1/fiber-modification
    - AnexoE_Especificacion_APIs_Komands_COMPLETO → §fiber-modification (línea 1119–1200)
    - HLD_SunsetBP §19.2 T2/T3: estas pruebas son tipo T2/T3 (mocks) — no requieren OLT real
"""
import pytest

from tests.mocks.payloads import (
    FIBER_MODIFICATION_NOKIA_VALID,
    FIBER_MODIFICATION_HUAWEI_VALID,
    FIBER_MODIFICATION_NO_CAPACITY,
    FIBER_MODIFICATION_ROLLBACK,
)

pytestmark = [pytest.mark.postventa, pytest.mark.mock_only]

FM_URL = "/api/Komands/v1/fiber-modification"


class TestFiberModificationHappyPath:
    """
    Cambio de puerto PON exitoso manteniendo el servicio activo del cliente.

    El cliente ya tiene un servicio activo en una ONT. Se reemplaza el pelo
    físico (fibra) que conecta la ONT con la OLT. Komands da de baja el ONT
    en el puerto origen y lo da de alta en el puerto destino con los mismos
    parámetros de servicio.

    Nokia y Huawei tienen secuencias CLI distintas pero el contrato de API
    es el mismo para ambos vendors.
    """

    # FM-01
    def test_fm01_nokia_gpon_reasignacion_puerto_pon_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Cliente Nokia FTTH en OLT-SAN-001 migra de puerto PON 3 a puerto PON 4
        en la misma OLT (por mantenimiento del puerto origen).

        Komands ejecuta baja en el puerto origen y alta en el puerto destino
        usando comandos Nokia ISAM CLI vía SSH. El servicio del cliente se interrumpe
        brevemente durante el cambio.

        Resultado esperado: HTTP 202 con txn_id para rastrear el resultado.
        """
        response = test_client.post(FM_URL, json=FIBER_MODIFICATION_NOKIA_VALID, headers=auth_headers)

        assert response.status_code == 202, (
            f"Nokia fiber modification devolvió {response.status_code}. Body: {response.text}"
        )
        data = response.json()
        assert data.get("txn_id"), (
            "txn_id ausente — sin txn_id ServiceNow no puede consultar el estado del cambio"
        )

    # FM-02
    def test_fm02_huawei_gpon_reasignacion_puerto_pon_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Cliente Huawei FTTH en OLT-SAN-002 migra de puerto PON 2 a puerto PON 3
        en la misma OLT Huawei.

        Huawei requiere resolver el INDEX dinámico del service-port antes de ejecutar
        los comandos undo/add. Si el INDEX no se puede resolver, la operación falla
        antes de tocar la red.

        Resultado esperado: HTTP 202 con txn_id.
        """
        response = test_client.post(FM_URL, json=FIBER_MODIFICATION_HUAWEI_VALID, headers=auth_headers)

        assert response.status_code == 202, (
            f"Huawei fiber modification devolvió {response.status_code}. Body: {response.text}"
        )
        data = response.json()
        assert data.get("txn_id"), (
            "txn_id ausente — sin txn_id ServiceNow no puede rastrear el cambio Huawei"
        )


class TestFiberModificationErrores:
    """
    Casos de error documentados en AnexoH v2.2 y AnexoE §fiber-modification:

      KMD-1003: El puerto PON de destino no tiene capacidad para registrar
                una nueva ONT (límite de ONTs por puerto alcanzado).

      KMD-5021: El paso de baja en el puerto origen fue exitoso pero el paso
                de alta en el puerto destino falló. Komands ejecuta rollback
                automático y vuelve a dar de alta en el origen.

    La documentación clasifica ambos casos como T3 (mocks de respuestas OLT).
    """

    # FM-03
    def test_fm03_puerto_destino_sin_capacidad_retorna_failed_kmd1003(self, test_client, auth_headers):
        """
        ESCENARIO: El puerto PON de destino ya tiene 128 ONTs (límite Nokia GPON) y
        no puede aceptar una nueva ONT.

        Komands detecta la falta de capacidad en el intento de alta en el puerto
        destino y reporta FAILED. El cliente sigue activo en el puerto origen.

        Resultado esperado: HTTP 202 con status=FAILED y error_code=KMD-1003.
        """
        response = test_client.post(FM_URL, json=FIBER_MODIFICATION_NO_CAPACITY, headers=auth_headers)

        assert response.status_code == 202
        data = response.json()
        assert data.get("error_code") == "KMD-1003", (
            f"Se esperaba KMD-1003 (sin capacidad), se obtuvo: {data.get('error_code')}. "
            f"Body completo: {data}"
        )

    # FM-04
    def test_fm04_alta_en_destino_falla_ejecuta_rollback_rolled_back(self, test_client, auth_headers):
        """
        ESCENARIO: Baja en el puerto origen exitosa, pero el alta en el puerto destino
        falla (comando SSH rechazado por la OLT Nokia).

        Komands detecta el fallo en el paso 2 y ejecuta rollback automático:
        vuelve a dar de alta el servicio en el puerto origen.
        El cliente puede quedar sin servicio durante el rollback, pero queda
        restaurado al estado original.

        Resultado esperado: HTTP 202 con status=ROLLED_BACK y error_code=KMD-5021.
        """
        response = test_client.post(FM_URL, json=FIBER_MODIFICATION_ROLLBACK, headers=auth_headers)

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ROLLED_BACK", (
            f"Se esperaba ROLLED_BACK, se obtuvo: {data.get('status')}. Body: {data}"
        )
        assert data.get("error_code") == "KMD-5021", (
            f"Se esperaba KMD-5021 (SSH fail + rollback), se obtuvo: {data.get('error_code')}"
        )
