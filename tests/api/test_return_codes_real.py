"""Tests RC-xxx — Códigos de negocio reales del servidor KOMANDs.

Cubre los u_return_code confirmados por Jeffrey (equipo KOMANDs):

  RC-001  código 40  OLT con problemas de acceso              (todas)
  RC-002  código 60  Problemas con credenciales SSH           (todas)
  RC-003  código 30  SL ID no asociado a la ruta              (baja, device-mod, mod-servicio)
  RC-004  código 70  Servicio ya activo — alta no ejecutada   (mod-servicio)
  RC-005  código 80  Servicio ya inactivo — baja no ejecutada (mod-servicio)
  RC-006  código 90  Ningún servicio seleccionado             (mod-servicio)
  RC-007  código 100 Tecnología no reconocida                 (activación)
  RC-008  código 11  Par de identificador incompleto          (cambio-fibra)
  RC-009  código 110 Fallo activación PON nueva — paso 1      (cambio-fibra)

Correcciones de mapeo aplicadas:
  - VLAN_CONFLICT (device-modification):  u_return_code "10" → "120"
  - Destino ocupado (fiber-change):       u_return_code "10" → "120"
  - ONT offline (reset-ont mock_server):  u_return_code "20" → "40"

Fuente: tabla de códigos de negocio entregada por Jeffrey (equipo KOMANDs),
        u_return_code / u_return_code_desc en el callback HTTP POST.
"""
import pytest
from tests.mocks.payloads import (
    # código 40
    ACTIVATION_OLT_ACCESS_ERROR,
    DEACTIVATION_OLT_ACCESS_ERROR,
    MODIFICATION_OLT_ACCESS_ERROR,
    DEVICE_MOD_OLT_ACCESS_ERROR,
    FIBER_CHANGE_OLT_ACCESS_ERROR,
    # código 60
    ACTIVATION_SSH_CREDENTIALS_ERROR,
    DEACTIVATION_SSH_CREDENTIALS_ERROR,
    MODIFICATION_SSH_CREDENTIALS_ERROR,
    DEVICE_MOD_SSH_CREDENTIALS_ERROR,
    # código 30
    DEACTIVATION_SLID_NOT_ASSOCIATED,
    MODIFICATION_SLID_NOT_ASSOCIATED,
    DEVICE_MOD_SLID_NOT_ASSOCIATED,
    # códigos 70 / 80 / 90
    MODIFICATION_SERVICE_ALREADY_ACTIVE,
    MODIFICATION_SERVICE_ALREADY_INACTIVE,
    MODIFICATION_NO_SERVICE_SELECTED,
    # código 100
    ACTIVATION_TECH_NOT_RECOGNIZED,
    # códigos 11 / 110
    FIBER_CHANGE_INCOMPLETE_IDENTIFIER,
    FIBER_CHANGE_PON_ACTIVATION_FAIL_STEP1,
)

_ACT  = "/api/Komands/v1/activation"
_UNS  = "/api/Komands/v1/unsubscription"
_MOD  = "/api/Komands/v1/modification"
_DVM  = "/api/Komands/v1/device-modification"
_FIB  = "/api/Komands/v1/fiber-change"


class TestCodigosRealesJeffrey:

    # ── RC-001 · código 40 · OLT con problemas de acceso ─────────────────────

    def test_rc001a_activacion_olt_access_error(self, test_client, auth_headers):
        """Activación: OLT inaccesible devuelve u_return_code=40."""
        r = test_client.post(_ACT, json=ACTIVATION_OLT_ACCESS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "40", (
            f"Se esperaba u_return_code=40, se obtuvo: {data['result']['u_return_code']}"
        )
        assert data["status"] == "FAILED"

    def test_rc001b_baja_olt_access_error(self, test_client, auth_headers):
        """Baja: OLT inaccesible devuelve u_return_code=40."""
        r = test_client.post(_UNS, json=DEACTIVATION_OLT_ACCESS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "40"

    def test_rc001c_modificacion_olt_access_error(self, test_client, auth_headers):
        """Modificación: OLT inaccesible devuelve u_return_code=40."""
        r = test_client.post(_MOD, json=MODIFICATION_OLT_ACCESS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "40"

    def test_rc001d_device_mod_olt_access_error(self, test_client, auth_headers):
        """Cambio de equipo: OLT inaccesible devuelve u_return_code=40."""
        r = test_client.post(_DVM, json=DEVICE_MOD_OLT_ACCESS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "40"

    def test_rc001e_fiber_change_olt_access_error(self, test_client, auth_headers):
        """Cambio de fibra: OLT inaccesible devuelve u_return_code=40."""
        r = test_client.post(_FIB, json=FIBER_CHANGE_OLT_ACCESS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "40"

    # ── RC-002 · código 60 · Problemas con credenciales SSH ──────────────────

    def test_rc002a_activacion_ssh_credentials_error(self, test_client, auth_headers):
        """Activación: fallo SSH devuelve u_return_code=60."""
        r = test_client.post(_ACT, json=ACTIVATION_SSH_CREDENTIALS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "60"
        assert data["status"] == "FAILED"

    def test_rc002b_baja_ssh_credentials_error(self, test_client, auth_headers):
        """Baja: fallo SSH devuelve u_return_code=60."""
        r = test_client.post(_UNS, json=DEACTIVATION_SSH_CREDENTIALS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "60"

    def test_rc002c_modificacion_ssh_credentials_error(self, test_client, auth_headers):
        """Modificación: fallo SSH devuelve u_return_code=60."""
        r = test_client.post(_MOD, json=MODIFICATION_SSH_CREDENTIALS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "60"

    def test_rc002d_device_mod_ssh_credentials_error(self, test_client, auth_headers):
        """Cambio de equipo: fallo SSH devuelve u_return_code=60."""
        r = test_client.post(_DVM, json=DEVICE_MOD_SSH_CREDENTIALS_ERROR, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "60"

    # ── RC-003 · código 30 · SL ID no asociado a la ruta ────────────────────

    def test_rc003a_baja_slid_not_associated(self, test_client, auth_headers):
        """Baja: SL ID no asociado devuelve u_return_code=30."""
        r = test_client.post(_UNS, json=DEACTIVATION_SLID_NOT_ASSOCIATED, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "30"
        assert data["status"] == "FAILED"

    def test_rc003b_modificacion_slid_not_associated(self, test_client, auth_headers):
        """Modificación: SL ID no asociado devuelve u_return_code=30."""
        r = test_client.post(_MOD, json=MODIFICATION_SLID_NOT_ASSOCIATED, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "30"

    def test_rc003c_device_mod_slid_not_associated(self, test_client, auth_headers):
        """Cambio de equipo: SL ID no asociado devuelve u_return_code=30."""
        r = test_client.post(_DVM, json=DEVICE_MOD_SLID_NOT_ASSOCIATED, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "30"

    # ── RC-004 · código 70 · Servicio ya activo ──────────────────────────────

    def test_rc004_modificacion_servicio_ya_activo(self, test_client, auth_headers):
        """
        Modificación de servicio: el servicio ya está activo en la OLT.

        El servidor real devuelve u_return_code=70 cuando intenta activar un
        servicio que ya figura como activo en la OLT — la OLT rechaza la
        operación y el servidor reporta el estado sin modificar nada.
        """
        r = test_client.post(_MOD, json=MODIFICATION_SERVICE_ALREADY_ACTIVE, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "70", (
            f"Se esperaba u_return_code=70 (servicio ya activo), se obtuvo: {data['result']['u_return_code']}"
        )
        assert data["status"] == "FAILED"

    # ── RC-005 · código 80 · Servicio ya inactivo ────────────────────────────

    def test_rc005_modificacion_servicio_ya_inactivo(self, test_client, auth_headers):
        """
        Modificación de servicio: el servicio ya está inactivo en la OLT.

        El servidor real devuelve u_return_code=80 cuando intenta dar de baja
        un servicio que ya figura como inactivo — operación idempotente pero
        reportada como FAILED para visibilidad.
        """
        r = test_client.post(_MOD, json=MODIFICATION_SERVICE_ALREADY_INACTIVE, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "80", (
            f"Se esperaba u_return_code=80 (servicio ya inactivo), se obtuvo: {data['result']['u_return_code']}"
        )
        assert data["status"] == "FAILED"

    # ── RC-006 · código 90 · Ningún servicio seleccionado ────────────────────

    def test_rc006_modificacion_sin_servicio_seleccionado(self, test_client, auth_headers):
        """
        Modificación de servicio: todos los flags (IPTV/VOZ/DATOS) están en F.

        El servidor real devuelve u_return_code=90 cuando el body tiene todos
        los flags de servicio en F — no hay nada que modificar en la OLT.
        """
        r = test_client.post(_MOD, json=MODIFICATION_NO_SERVICE_SELECTED, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "90", (
            f"Se esperaba u_return_code=90 (ningún servicio), se obtuvo: {data['result']['u_return_code']}"
        )
        assert data["status"] == "FAILED"

    # ── RC-007 · código 100 · Tecnología no reconocida ───────────────────────

    def test_rc007_activacion_tecnologia_no_reconocida(self, test_client, auth_headers):
        """
        Activación: la tecnología del body no es FTTH ni SSAA.

        El servidor real solo admite FTTH y SSAA. Si llega otra tecnología,
        devuelve u_return_code=100 sin ejecutar nada en la OLT.
        """
        r = test_client.post(_ACT, json=ACTIVATION_TECH_NOT_RECOGNIZED, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "100", (
            f"Se esperaba u_return_code=100 (tecnología no reconocida), se obtuvo: {data['result']['u_return_code']}"
        )
        assert data["status"] == "FAILED"

    # ── RC-008 · código 11 · Par de identificador incompleto ─────────────────

    def test_rc008_cambio_fibra_par_identificador_incompleto(self, test_client, auth_headers):
        """
        Cambio de fibra: el par de identificadores (OLT + ONT ID) está incompleto.

        El servidor real devuelve u_return_code=11 cuando no puede resolver
        la ruta de destino por falta de alguno de los campos del par.
        Solo aplica a fiber-change.
        """
        r = test_client.post(_FIB, json=FIBER_CHANGE_INCOMPLETE_IDENTIFIER, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "11", (
            f"Se esperaba u_return_code=11 (par incompleto), se obtuvo: {data['result']['u_return_code']}"
        )
        assert data["status"] == "FAILED"

    # ── RC-009 · código 110 · Fallo activación PON nueva (paso 1) ────────────

    def test_rc009_cambio_fibra_fallo_pon_nueva_paso1(self, test_client, auth_headers):
        """
        Cambio de fibra: fallo en la activación de prueba de la PON nueva (paso 1).

        El servidor real devuelve u_return_code=110 cuando el paso 1 del cambio
        de fibra (activación de prueba en la PON nueva) falla antes de desactivar
        la PON origen. El cliente queda activo en su PON original sin interrupción.
        Solo aplica a fiber-change.
        """
        r = test_client.post(_FIB, json=FIBER_CHANGE_PON_ACTIVATION_FAIL_STEP1, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "110", (
            f"Se esperaba u_return_code=110 (fallo PON nueva paso 1), se obtuvo: {data['result']['u_return_code']}"
        )
        assert data["status"] in ("FAILED", "ROLLED_BACK"), (
            f"Se esperaba FAILED o ROLLED_BACK, se obtuvo: {data['status']}"
        )

    # ── Verificación de correcciones de mapeo ────────────────────────────────

    def test_fix_vlan_conflict_usa_codigo_120(self, test_client, auth_headers):
        """
        VLAN_CONFLICT (device-modification) devuelve u_return_code=120.

        Corrección aplicada: antes se usaba "10" (Ruta no encontrada) que
        es semánticamente incorrecto. El código 120 corresponde a
        'Estado inconsistente: PON antigua baja, nueva falla' según Jeffrey.
        """
        from tests.mocks.payloads import DEVICE_MOD_VLAN_CONFLICT
        r = test_client.post(_DVM, json=DEVICE_MOD_VLAN_CONFLICT, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "120", (
            f"VLAN_CONFLICT debe tener u_return_code=120, se obtuvo: {data['result']['u_return_code']}"
        )
        assert data.get("error_code") == "KMD-3001"

    def test_fix_fiber_change_destino_ocupado_usa_codigo_120(self, test_client, auth_headers):
        """
        Destino ocupado (fiber-change) devuelve u_return_code=120.

        Corrección aplicada: antes se usaba "10" que es incorrecto.
        El código 120 corresponde a 'Estado inconsistente' en Jeffrey's table.
        """
        from tests.mocks.payloads import FIBER_CHANGE_DEST_PORT_OCCUPIED
        r = test_client.post(_FIB, json=FIBER_CHANGE_DEST_PORT_OCCUPIED, headers=auth_headers)
        assert r.status_code == 202
        data = r.json()
        assert data["result"]["u_return_code"] == "120", (
            f"Destino ocupado debe tener u_return_code=120, se obtuvo: {data['result']['u_return_code']}"
        )
        assert data.get("error_code") == "KMD-3003"
