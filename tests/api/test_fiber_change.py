"""API tests — Cambio de fibra FTTH (PV-FIB).

Convención: test_fib<NN>_<escenario>

Qué estamos probando:
    El cambio de fibra ("fiber change") ocurre cuando un cliente FTTH debe
    migrar de un puerto PON a otro, ya sea en la misma OLT o en una OLT
    diferente (cross-vendor incluido).

    A diferencia de una activación nueva, el cliente ya tiene servicios
    activos: Komands debe dar de baja el ONT en la OLT origen y darlo
    de alta con los mismos parámetros en la OLT destino.

    La operación es asíncrona: Komands responde 202 PENDING y notifica
    el resultado por callback a ServiceNow.

Fuentes:
    - Plan_Pruebas_PostVenta_v1_regresion.docx → PV-FIB-001 a PV-FIB-003
    - AnexoH_Especificacion_APIs_v2_2_FINAL.docx → POST /api/Komands/v1/fiber-change
"""
import pytest

pytestmark = [pytest.mark.postventa, pytest.mark.ftth]

FIBER_CHANGE_URL = "/api/Komands/v1/fiber-change"

# Nokia: mismo fabricante en origen y destino (mismo o diferente puerto PON)
_NOKIA = {
    "vno_code": "DTV",
    "external_order_id": "SO-FIB-001",
    "current_olt_name": "OLT-SAN-001",
    "current_slot": 1,
    "current_port": 3,
    "current_ont_id": 45,
    "new_olt_name": "OLT-SAN-001",
    "new_slot": 1,
    "new_port": 4,
    "new_ont_id": 45,
    "serial_ont": "ALCLF1234567",
}

# Huawei: mismo fabricante origen y destino
_HUAWEI = {
    **_NOKIA,
    "external_order_id": "SO-FIB-002",
    "current_olt_name": "OLT-SAN-002",
    "new_olt_name": "OLT-SAN-002",
    "serial_ont": "485754C12345",
}

# Cross-vendor: Nokia origen → Huawei destino (migración de plataforma)
_CROSS_VENDOR = {
    **_NOKIA,
    "external_order_id": "SO-FIB-003",
    "current_olt_name": "OLT-SAN-001",
    "new_olt_name": "OLT-SAN-002",
}


class TestFiberChangeHappyPath:
    """
    Cambio de fibra exitoso en los tres escenarios del plan de pruebas:
    Nokia homogéneo, cross-vendor Nokia→Huawei, y Huawei homogéneo.

    En todos los casos Komands debe aceptar la operación y retornar
    HTTP 202 con status=PENDING y un txn_id para rastrear el resultado.
    """

    # FIB-01
    def test_fib01_nokia_ftth_cambio_puerto_pon_acepta_y_encola(self, test_client, vno_auth_headers, vno_id):
        """
        ESCENARIO: Nokia FTTH — cambio de puerto PON en la misma OLT Nokia.

        El cliente continúa en OLT-SAN-001 pero pasa del puerto 3 al puerto 4
        (por ejemplo, por mantenimiento del puerto de origen).
        Komands debe encolar el cambio y responder 202 con txn_id.

        Resultado esperado: HTTP 202 con status=PENDING y txn_id.
        """
        response = test_client.post(FIBER_CHANGE_URL, json={**_NOKIA, "vno_code": vno_id}, headers=vno_auth_headers)

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Se esperaba status=PENDING, se obtuvo: {data.get('status')}"
        )
        assert data.get("txn_id"), "txn_id ausente — no se puede rastrear el resultado"

    # FIB-02
    def test_fib02_cross_vendor_nokia_a_huawei_acepta_y_encola(self, test_client, vno_auth_headers, vno_id):
        """
        ESCENARIO: Cambio de fibra cross-vendor — OLT Nokia origen, OLT Huawei destino.

        El cliente migra de OLT-SAN-001 (Nokia) a OLT-SAN-002 (Huawei).
        Komands debe soportar la combinación de fabricantes sin rechazar la solicitud.
        La secuencia de comandos en cada OLT es diferente, pero la API es la misma.

        Resultado esperado: HTTP 202 con status=PENDING.
        """
        response = test_client.post(FIBER_CHANGE_URL, json={**_CROSS_VENDOR, "vno_code": vno_id}, headers=vno_auth_headers)

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Se esperaba status=PENDING en cross-vendor, se obtuvo: {data.get('status')}"
        )
        assert data.get("txn_id"), "txn_id ausente en cambio cross-vendor"

    # FIB-03
    def test_fib03_huawei_ftth_cambio_puerto_pon_acepta_y_encola(self, test_client, vno_auth_headers, vno_id):
        """
        ESCENARIO: Huawei FTTH — cambio de puerto PON en la misma OLT Huawei.

        Misma lógica que FIB-01 pero con comandos Huawei (display/undo ont).
        Komands debe manejar la secuencia de comandos Huawei correctamente.

        Resultado esperado: HTTP 202 con status=PENDING y txn_id.
        """
        response = test_client.post(FIBER_CHANGE_URL, json={**_HUAWEI, "vno_code": vno_id}, headers=vno_auth_headers)

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Se esperaba status=PENDING en Huawei, se obtuvo: {data.get('status')}"
        )
        assert data.get("txn_id"), "txn_id ausente — no se puede rastrear el resultado"


class TestFiberChangeAutenticacion:
    """
    El endpoint de cambio de fibra requiere autenticación y autorización válidas.
    Mismo modelo de seguridad que los demás endpoints operacionales de Komands.
    """

    # FIB-04
    def test_fib04_sin_token_rechaza_401(self, test_client):
        """
        ESCENARIO: Request al endpoint de cambio de fibra sin header Authorization.

        Komands no debe procesar la operación sin token válido.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(FIBER_CHANGE_URL, json=_NOKIA)
        assert response.status_code == 401

    # FIB-05
    def test_fib05_token_expirado_rechaza_401(self, test_client, expired_token):
        """
        ESCENARIO: Token JWT expirado enviado al endpoint de cambio de fibra.

        Los tokens tienen TTL corto; una vez vencidos Komands los rechaza.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            FIBER_CHANGE_URL, json=_NOKIA,
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    # FIB-06
    def test_fib06_vno_no_autorizada_rechaza_403(self, test_client, invalid_vno_token):
        """
        ESCENARIO: Token con VNO desconocida (no en lista de VNOs autorizadas)
        intentando ejecutar un cambio de fibra.

        Komands solo acepta VNOs registradas: DTV, CVTR, ENTEL, TCH.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            FIBER_CHANGE_URL, json=_NOKIA,
            headers={"Authorization": f"Bearer {invalid_vno_token}"},
        )
        assert response.status_code == 403


# ─── FIB-07: Posición destino ocupada (PV-FIB-003) ───────────────────────────

# Centinela: new_ont_id=9000 → ONT ID en la posición destino ya está en uso
_DEST_OCCUPIED = {
    "vno_code": "DTV",
    "external_order_id": "SO-FIB-ERR-001",
    "current_olt_name": "OLT-SAN-001",
    "current_slot": 1,
    "current_port": 3,
    "current_ont_id": 45,
    "new_olt_name": "OLT-SAN-001",
    "new_slot": 1,
    "new_port": 5,
    "new_ont_id": 9000,
    "serial_ont": "ALCLF1234567",
}


# ─── FIB-08: Cross-vendor Huawei→Nokia (inverso de FIB-02) ──────────────────

_CROSS_VENDOR_REVERSE = {
    **_NOKIA,
    "external_order_id": "SO-FIB-004",
    "current_olt_name": "OLT-SAN-002",
    "new_olt_name": "OLT-SAN-001",
    "serial_ont": "485754C12345",
}


class TestFiberChangeCrossVendorReverso:
    """
    Cambio de fibra cross-vendor en sentido inverso: Huawei origen → Nokia destino.

    FIB-02 cubre Nokia→Huawei. Este caso cubre el sentido contrario.
    Ocurre cuando un cliente migra desde una OLT Huawei a una OLT Nokia
    (por ejemplo, modernización de infraestructura en una zona).

    La documentación (AnexoE §fiber-modification) especifica que Komands
    maneja este caso internamente seleccionando el adapter correcto para
    cada tramo: adapter Huawei para la baja en origen y adapter Nokia para
    el alta en destino.
    """

    # FIB-08
    def test_fib08_cross_vendor_huawei_a_nokia_acepta_y_encola(self, test_client, vno_auth_headers, vno_id):
        """
        ESCENARIO: Cambio de fibra cross-vendor — OLT Huawei origen (OLT-SAN-002),
        OLT Nokia destino (OLT-SAN-001).

        El cliente migra de plataforma Huawei a Nokia. Komands debe soportar
        la combinación de fabricantes sin rechazar la solicitud: usa el adapter
        Huawei para la baja y el adapter Nokia para el alta.

        Resultado esperado: HTTP 202 con status=ACCEPTED y txn_id.
        """
        response = test_client.post(FIBER_CHANGE_URL, json={**_CROSS_VENDOR_REVERSE, "vno_code": vno_id}, headers=vno_auth_headers)

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Cross-vendor Huawei→Nokia debería retornar ACCEPTED, se obtuvo: {data.get('status')}"
        )
        assert data.get("txn_id"), "txn_id ausente en cambio cross-vendor Huawei→Nokia"


@pytest.mark.mock_only
class TestFiberChangeErrores:
    """
    PV-FIB-003: Cambio de fibra falla porque el ONT ID de destino ya está ocupado.

    El cambio de fibra tiene dos pasos: (1) baja en OLT origen, (2) alta en OLT destino.
    Si el ONT ID de destino ya está asignado a otro cliente, el alta falla.
    Komands debe reportar ROLLED_BACK con KMD-3003 y escalar a Redes para
    que liberen la posición de destino antes de reintentar.

    Diferencia con FIB-01/02/03 (happy path): allá el destino está libre.
    """

    # FIB-07 → PV-FIB-003
    def test_fib07_destino_ont_id_ocupado_retorna_rolled_back(self, test_client, auth_headers):
        """
        ESCENARIO: Cambio de fibra Nokia — el ONT ID en el puerto de destino ya está en uso.

        El técnico planificó mover el cliente al puerto 5 ONT ID 9000,
        pero ese ONT ID ya tiene otro cliente activo.
        Komands detecta la colisión en el paso 2 (alta en destino) y hace
        rollback del paso 1 (re-activa en el origen).

        Resultado esperado: HTTP 202 con estado ROLLED_BACK y error_code KMD-3003.
        """
        response = test_client.post(
            FIBER_CHANGE_URL,
            json=_DEST_OCCUPIED,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ROLLED_BACK", (
            f"Destino ocupado debería retornar ROLLED_BACK, se obtuvo: {data.get('status')}"
        )
        assert data.get("error_code") == "KMD-3003", (
            f"Se esperaba KMD-3003 (posición destino ocupada), se obtuvo: {data.get('error_code')}"
        )
