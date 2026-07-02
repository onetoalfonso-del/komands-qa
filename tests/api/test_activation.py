"""API tests — POST /api/Komands/v1/activation.

Convención: test_act<NN>_<vendor>_<producto>_<escenario>

Qué estamos probando:
    El endpoint de activación recibe un payload con los datos del ONT
    y devuelve HTTP 202 + txn_id cuando todo es válido.
    También valida autenticación (401), autorización (403) y
    acceso por rol RBAC (202/403).

    Nota: el servidor usado es la mini-app de conftest.py (TestClient).
    No se necesita servidor real ni base de datos.

Fuentes:
    - AnexoH_Especificacion_APIs_v2_2_FINAL → contrato POST /activation
    - LLD ADR-008 → base path /api/Komands/v1/ (pendiente migrar a /api/Komands/v1/)
    - tests/mocks/payloads.py → payloads reutilizables
"""
import pytest

from tests.mocks.payloads import (
    ACTIVATION_NOKIA_FTTH_VALID,
    ACTIVATION_NOKIA_FTTH_INTERNET_ONLY,
    ACTIVATION_HUAWEI_FTTH_VALID,
    ACTIVATION_HUAWEI_FTTH_WITH_IPTV,
    ACTIVATION_NOKIA_SSAA_GROUP_A,
    ACTIVATION_NOKIA_SSAA_GROUP_AC,
    ACTIVATION_NOKIA_SSAA_GROUP_ACD,
    ACTIVATION_NOKIA_SSAA_GROUP_B,
    ACTIVATION_NOKIA_SSAA_GROUP_BX,
    ACTIVATION_NOKIA_SSAA_GROUP_C,
    ACTIVATION_NOKIA_SSAA_GROUP_D,
    ACTIVATION_NOKIA_SSAA_GROUP_DX,
    ACTIVATION_HUAWEI_SSAA_GROUP_A,
    ACTIVATION_INVALID_VNO,
)


# ─── ACT-01 a ACT-04: Payloads válidos → HTTP 202 ────────────────────────────

class TestActivacionValida:
    """
    Casos felices — el API debe aceptar activaciones válidas de
    Nokia y Huawei, FTTH y SSAA, devolviendo 202 + txn_id.
    """

    # ACT-01
    def test_act01_nokia_ftth_tres_servicios_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia FTTH con INTERNET + VOIP + IPTV.

        Es el caso más completo de Nokia FTTH — tres servicios, cada uno
        con su QoS específico. Si este caso pasa, la ruta básica funciona.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202, (
            f"Se esperaba 202, se obtuvo {response.status_code}. "
            f"Body: {response.text}"
        )

    # ACT-02
    def test_act02_nokia_ftth_internet_only_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia FTTH con solo INTERNET.

        Caso mínimo válido — un solo servicio. Valida que el sistema
        no rechaza activaciones parciales (sin VoIP ni IPTV).

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_INTERNET_ONLY,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # ACT-03
    def test_act03_huawei_ftth_internet_voip_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Huawei FTTH con INTERNET + VOIP.

        Primer caso Huawei — valida que el endpoint acepta ambos vendors.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_HUAWEI_FTTH_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # ACT-04
    def test_act04_huawei_ftth_con_iptv_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Huawei FTTH con INTERNET + VOIP + IPTV.

        Huawei con los tres servicios — incluye gemport 7 para IPTV.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_HUAWEI_FTTH_WITH_IPTV,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # ACT-05
    def test_act05_nokia_ssaa_grupo_a_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA grupo A (B2B).

        SSAA es el producto empresarial. Usa grupos (A/B/C/D/E/BX/DX)
        en vez de servicios (INTERNET/VOIP/IPTV).

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_A,
            headers=auth_headers,
        )

        assert response.status_code == 202

    # ACT-06
    def test_act06_huawei_ssaa_grupo_a_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Huawei SSAA grupo A — VNO CVTR.

        Valida combinación Huawei + SSAA + VNO distinta a DTV.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {
            "Authorization": f"Bearer {_make_token(vno_id='CVTR')}",
            "X-Correlation-ID": "test-act06",
            "X-VNO-ID": "CVTR",
        }
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_HUAWEI_SSAA_GROUP_A,
            headers=headers,
        )

        assert response.status_code == 202


# ─── ACT-07 a ACT-09: Autenticación fallida → HTTP 401 ───────────────────────

class TestActivacionSinAutenticacion:
    """
    El API debe rechazar requests sin token o con token inválido
    antes de procesar cualquier dato del payload.
    """

    # ACT-07
    def test_act07_sin_token_devuelve_401(self, test_client):
        """
        ESCENARIO: Request sin header Authorization.

        Sin token no hay forma de saber quién está llamando.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
        )

        assert response.status_code == 401

    # ACT-08
    def test_act08_token_expirado_devuelve_401(self, test_client, expired_token):
        """
        ESCENARIO: Token JWT con fecha de expiración pasada.

        Un token expirado puede ser un intento de replay attack.

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    # ACT-09
    def test_act09_token_malformado_devuelve_401(self, test_client):
        """
        ESCENARIO: Token con formato inválido (no es un JWT).

        Resultado esperado: HTTP 401.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": "Bearer esto-no-es-un-jwt"},
        )

        assert response.status_code == 401


# ─── ACT-10 a ACT-11: Autorización fallida → HTTP 403 ────────────────────────

class TestActivacionSinAutorizacion:
    """
    Token válido pero sin permisos suficientes.
    """

    # ACT-10
    def test_act10_vno_no_autorizada_devuelve_403(self, test_client, invalid_vno_token):
        """
        ESCENARIO: Token con VNO desconocida ("FAKE_VNO").

        Komands solo acepta VNOs registrados (verificados en portal 2026-06-17):
        DTV, VTR, Entel, ENTEL, TCH, Claro, Genérico. FAKE_VNO no está en esa lista.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_INVALID_VNO,
            headers={"Authorization": f"Bearer {invalid_vno_token}"},
        )

        assert response.status_code == 403

    # ACT-11
    def test_act11_scope_insuficiente_devuelve_403(self, test_client, readonly_token):
        """
        ESCENARIO: Token con solo komands:read — sin permiso de escritura.

        La activación requiere scope komands:write (o komands:provision
        en v2.2 final). Sin él no se puede modificar la red.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {readonly_token}"},
        )

        assert response.status_code == 403


# ─── ACT-12 a ACT-14: RBAC portal web ────────────────────────────────────────

class TestActivacionRBACPortal:
    """
    El portal web usa tokens de rol (ADMIN/OPERATOR/VIEWER/AUDITOR).
    Solo ADMIN y OPERATOR tienen permiso activation:write.
    """

    # ACT-12
    def test_act12_admin_puede_activar(self, test_client, admin_token):
        """
        ESCENARIO: Usuario con rol ADMIN activa desde el portal.

        ADMIN tiene todos los permisos — debe poder activar.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 202

    # ACT-13
    def test_act13_operator_puede_activar(self, test_client, operator_token):
        """
        ESCENARIO: Usuario con rol OPERATOR activa desde el portal.

        OPERATOR tiene activation:write — es el rol operativo principal.

        Resultado esperado: HTTP 202.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {operator_token}"},
        )

        assert response.status_code == 202

    # ACT-14
    def test_act14_viewer_no_puede_activar(self, test_client, viewer_token):
        """
        ESCENARIO: Usuario con rol VIEWER intenta activar.

        VIEWER solo puede leer transacciones — no tiene activation:write.
        Esto evita que un usuario de solo lectura modifique la red.

        Resultado esperado: HTTP 403.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert response.status_code == 403


# ─── ACT-15 a ACT-16: Estructura de la respuesta ─────────────────────────────

class TestActivacionRespuesta:
    """
    El body de la respuesta 202 debe contener campos obligatorios
    según el contrato del Anexo H v2.2.
    """

    # ACT-15
    def test_act15_respuesta_contiene_txn_id(self, test_client, auth_headers):
        """
        ESCENARIO: Activación válida → verificar que el body tiene txn_id.

        txn_id es el UUID que ServiceNow usa para rastrear la transacción
        y consultar el estado vía GET /{operation}/{uuid}.

        Resultado esperado: campo txn_id presente en la respuesta.
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "txn_id" in data, f"txn_id ausente en respuesta: {data}"

    # ACT-16
    def test_act16_respuesta_contiene_status_pending(self, test_client, auth_headers):
        """
        ESCENARIO: Activación válida → el status inicial es PENDING.

        La activación es asíncrona — Komands encola la operación y
        devuelve PENDING. El estado final llega por callback.

        Resultado esperado: campo status == "PENDING".
        """
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_FTTH_VALID,
            headers=auth_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert data.get("status") == "ACCEPTED", (
            f"Se esperaba status=ACCEPTED, se obtuvo: {data.get('status')}"
        )


# ─── ACT-17: Todos los VNOs autorizados ──────────────────────────────────────

class TestActivacionMultiVNO:
    """
    Todos los VNOs verificados en el portal real deben poder activar con un token válido.
    """

    # ACT-17
    @pytest.mark.parametrize("vno_id", ["DTV", "VTR", "ENTEL", "TCH", "Claro", "GTD", "WOM", "Genérico"])
    def test_act17_todos_los_vnos_pueden_activar(self, test_client, vno_id):
        """
        ESCENARIO: Cada VNO autorizado envía una activación.

        VNOs verificados en portal real (onf-komands.cl:9010) — 2026-06-17:
        DTV, VTR, ENTEL, TCH, Claro, GTD, WOM, Genérico.
        Si alguno falla con 403, ese VNO no está en la lista del mock.

        Resultado esperado: HTTP 202 para cada VNO.
        """
        from tests.conftest import _make_token
        token = _make_token(vno_id=vno_id)
        payload = {**ACTIVATION_NOKIA_FTTH_VALID, "vno_code": vno_id}

        response = test_client.post(
            "/api/Komands/v1/activation",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 202, (
            f"VNO {vno_id} recibió {response.status_code} — esperado 202"
        )


# ─── ACT-18 a ACT-24: SSAA Grupos B, C, D, BX, DX y combinaciones ────────────

class TestActivacionSSAAGruposExtendidos:
    """
    Activaciones SSAA Nokia con todos los grupos comerciales definidos en HLD §11.8.

    Los grupos SSAA determinan el tipo de service-port y perfil de QoS que Komands
    debe configurar en la OLT. Cada grupo es una combinación distinta de VLAN y
    velocidad garantizada:

      B   → Internet empresarial GPON — dedicado, banda garantizada media
      C   → L2 punto a punto GPON — para enlaces entre sedes
      D   → Video/Streaming GPON — QoS optimizado para multicast
      BX  → Banda asegurada XGSPON — alta velocidad garantizada (ya cubierto)
      DX  → Best effort XGSPON — alta velocidad no garantizada

    Combinaciones válidas (misma ONT, múltiples service-ports):
      A+C     → Internet básico + L2 punto a punto (2 service-ports)
      A+C+D   → Internet + L2 + Video (3 service-ports)

    Fuente: HLD §19.2 T2 — "~320 combinaciones CLI sin OLTs", Plan QA §3.1
    """

    # ACT-18
    def test_act18_nokia_ssaa_grupo_b_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA grupo B — internet empresarial GPON.

        El grupo B configura un service-port con banda garantizada media.
        Diferente del grupo A (básico) en el perfil de QoS y CVLAN.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {**auth_headers, "Authorization": f"Bearer {_make_token(vno_id='ENTEL')}"}
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_B,
            headers=headers,
        )
        assert response.status_code == 202, (
            f"SSAA Grupo B devolvió {response.status_code}. Body: {response.text}"
        )

    # ACT-19
    def test_act19_nokia_ssaa_grupo_c_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA grupo C — L2 punto a punto GPON.

        El grupo C es para servicios de transporte L2 entre sedes empresariales.
        Usa una CVLAN diferente y sin QoS de consumidor final.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {**auth_headers, "Authorization": f"Bearer {_make_token(vno_id='ENTEL')}"}
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_C,
            headers=headers,
        )
        assert response.status_code == 202, (
            f"SSAA Grupo C devolvió {response.status_code}. Body: {response.text}"
        )

    # ACT-20
    def test_act20_nokia_ssaa_grupo_d_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA grupo D — video/streaming GPON.

        El grupo D configura multicast habilitado con QoS para video corporativo.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {**auth_headers, "Authorization": f"Bearer {_make_token(vno_id='ENTEL')}"}
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_D,
            headers=headers,
        )
        assert response.status_code == 202, (
            f"SSAA Grupo D devolvió {response.status_code}. Body: {response.text}"
        )

    # ACT-21
    def test_act21_nokia_ssaa_grupo_bx_xgspon_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA grupo BX — banda asegurada XGSPON.

        BX es la variante XGSPON del grupo B: misma semántica de servicio pero
        sobre tecnología de 10G. Requiere que la OLT tenga tarjetas XGSPON.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {**auth_headers, "Authorization": f"Bearer {_make_token(vno_id='ENTEL')}"}
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_BX,
            headers=headers,
        )
        assert response.status_code == 202, (
            f"SSAA Grupo BX devolvió {response.status_code}. Body: {response.text}"
        )

    # ACT-22
    def test_act22_nokia_ssaa_grupo_dx_xgspon_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA grupo DX — best effort XGSPON.

        DX es la variante XGSPON del grupo D: velocidad alta sin garantía.
        Usado para clientes empresariales con alto volumen pero tolerantes a jitter.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {**auth_headers, "Authorization": f"Bearer {_make_token(vno_id='ENTEL')}"}
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_DX,
            headers=headers,
        )
        assert response.status_code == 202, (
            f"SSAA Grupo DX devolvió {response.status_code}. Body: {response.text}"
        )

    # ACT-23
    def test_act23_nokia_ssaa_grupos_ac_combo_dos_service_ports_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA con grupos A+C combinados — 2 service-ports.

        Una misma ONT empresarial puede necesitar Internet básico (A) y un enlace
        L2 punto a punto (C) simultáneamente. Komands debe configurar ambos
        service-ports en la OLT en una sola transacción.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {**auth_headers, "Authorization": f"Bearer {_make_token(vno_id='ENTEL')}"}
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_AC,
            headers=headers,
        )
        assert response.status_code == 202, (
            f"SSAA Grupos A+C (combo) devolvió {response.status_code}. Body: {response.text}"
        )

    # ACT-24
    def test_act24_nokia_ssaa_grupos_acd_combo_tres_service_ports_devuelve_202(self, test_client, auth_headers):
        """
        ESCENARIO: Activación Nokia SSAA con grupos A+C+D combinados — 3 service-ports.

        Es el caso más complejo de SSAA Nokia: Internet + L2 + Video en una sola ONT.
        Komands configura 3 service-ports con VLANs y perfiles de QoS distintos.
        Si falla alguno de los 3 pasos, Komands hace rollback de los pasos previos.

        Resultado esperado: HTTP 202.
        """
        from tests.conftest import _make_token
        headers = {**auth_headers, "Authorization": f"Bearer {_make_token(vno_id='ENTEL')}"}
        response = test_client.post(
            "/api/Komands/v1/activation",
            json=ACTIVATION_NOKIA_SSAA_GROUP_ACD,
            headers=headers,
        )
        assert response.status_code == 202, (
            f"SSAA Grupos A+C+D (combo 3 service-ports) devolvió {response.status_code}. Body: {response.text}"
        )
