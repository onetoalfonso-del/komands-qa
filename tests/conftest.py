"""Fixtures compartidos para toda la suite de pruebas Komands QA."""
import html as _html_mod
import json as _json
import logging
import os
import re
import time
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from jose import jwt, JWTError

log = logging.getLogger("komands.qa")

_last_req: dict = {}
_current_case_id: str = ""


def pytest_configure(config):
    """Crea el directorio de logs antes de que pytest empiece."""
    os.makedirs("logs", exist_ok=True)


def pytest_runtest_setup(item):
    """Antes de cada test: escribe un separador en el log con el ID y escenario."""
    global _current_case_id
    _current_case_id = _extract_case_id(item.function.__name__)
    doc = (item.function.__doc__ or "").strip()
    escenario = ""
    for line in doc.splitlines():
        line = line.strip()
        if line.startswith("ESCENARIO:"):
            escenario = line[len("ESCENARIO:"):].strip()
            break
    log.info("=" * 60)
    log.info("TEST  [%s]  %s", _current_case_id or "-", item.nodeid.split("::")[-1])
    if escenario:
        log.info("      %s", escenario)


# ─── Tablas de lenguaje amigable para el reporte ─────────────────────────────

_URL_OPERACION = {
    "/service-activation":  "Activación de Acceso",
    "/activation":          "Activación de Acceso",
    "/unsubscription":      "Baja / Cancelación de Acceso",
    "/unsuscription":       "Baja / Cancelación de Acceso",
    "/service-modification":"Modificación de Servicio",
    "/modification":        "Modificación de Servicio",
    "/reset-ont":           "Reset de ONT",
    "/device-modification": "Cambio de Equipo (Swap)",
    "/fiber-change":        "Cambio de Fibra (Migración OLT)",
    "/pon-transfer":        "Transferencia PON (Cambio de Pelo)",
    "/port-occupancy":      "Consulta Ocupación Puerto PON",
    "/query-access/":       "Consulta de Acceso",
    "/access/":             "Consulta de Acceso",
    "/transaction/":        "Estado de Transacción",
}

_HTTP_DESCRIPCION = {
    "HTTP 202": "Solicitud aceptada y encolada para procesamiento",
    "HTTP 200": "Consulta exitosa",
    "HTTP 401": "Rechazado — se requiere autenticación válida",
    "HTTP 403": "Rechazado — el usuario no tiene permisos suficientes",
    "HTTP 404": "No encontrado — el recurso no existe en el sistema",
    "HTTP 409": "Conflicto — operación duplicada detectada",
}

_CAMPO_ETIQUETA = {
    "vno_code":                 "Cliente",
    "u_id_vno":                 "Cliente",
    "olt_name":                 "OLT",
    "u_olt":                    "OLT",
    "service_type":             "Producto",
    "u_product":                "Producto",
    "modification_type":        "Tipo de operación",
    "u_type":                   "Tipo de operación",
    "new_serial_ont":           "Serial ONT nuevo",
    "u_new_serialnumber":       "Serial ONT nuevo",
    "serial_ont":               "Serial ONT",
    "u_serialnumber":           "Serial ONT",
    "delete_vlan_on_terminate": "Eliminar VLAN al terminar",
}

_PRODUCTO_NOMBRE = {"FTTH": "Fibra residencial (FTTH)", "SSAA": "Empresarial (SSAA)"}
_OPERACION_NOMBRE = {
    "speed_change":   "Cambio de velocidad",
    "SPEED_CHANGE":   "Cambio de velocidad",
    "block":          "Bloqueo de servicio",
    "BLOCK":          "Bloqueo de servicio",
    "unblock":        "Desbloqueo de servicio",
    "UNBLOCK":        "Desbloqueo de servicio",
    "add_service":    "Alta de servicio individual",
    "ADD_SERVICE":    "Alta de servicio individual",
    "remove_service": "Baja de servicio individual",
    "REMOVE_SERVICE": "Baja de servicio individual",
}


def _operacion_desde_url(url: str) -> str:
    for patron, nombre in _URL_OPERACION.items():
        if patron in url:
            return nombre
    return url


def _descripcion_http(resultado_esperado: str) -> str:
    clave = resultado_esperado.rstrip(".")
    return _HTTP_DESCRIPCION.get(clave, resultado_esperado)


def _flatten_body(payload: dict) -> dict:
    """Aplana body jerárquico (familias) para extracción de campos del reporte."""
    flat = dict(payload)
    for family in ("u_routing", "u_identification", "u_action", "u_product",
                   "u_routing_new", "u_hardware", "u_qos", "u_vlan"):
        flat.update(payload.get(family, {}))
    return flat


def _datos_amigables(payload: dict) -> str:
    if not payload:
        return ""
    flat = _flatten_body(payload)
    filas = []
    for campo, etiqueta in _CAMPO_ETIQUETA.items():
        if campo not in flat:
            continue
        valor = flat[campo]
        if campo in ("service_type", "u_product"):
            valor = _PRODUCTO_NOMBRE.get(str(valor), valor)
        elif campo in ("modification_type", "u_type"):
            valor = _OPERACION_NOMBRE.get(str(valor), valor)
        elif campo == "delete_vlan_on_terminate":
            if not valor:
                continue
            valor = "Sí"
        filas.append(
            f"<tr>"
            f"<td style='color:#555;padding:2px 12px 2px 0;white-space:nowrap'>{etiqueta}</td>"
            f"<td style='padding:2px 0;font-weight:bold'>{valor}</td>"
            f"</tr>"
        )
    if not filas:
        return ""
    return (
        "<table style='border-collapse:collapse;font-size:0.88em;margin-top:6px'>"
        + "".join(filas)
        + "</table>"
    )


# ─── TestClient con captura de request/response ───────────────────────────────

class CapturingTestClient(TestClient):
    """TestClient que guarda el último request/response para el reporte y el log."""

    def request(self, method, url, **kwargs):
        response = super().request(method, url, **kwargs)
        payload = kwargs.get("json")
        try:
            resp_body = response.json()
        except Exception:
            resp_body = None

        _last_req.clear()
        _last_req.update({
            "method": method.upper(),
            "url": url,
            "payload": payload,
            "status_code": response.status_code,
            "response_body": resp_body,
        })

        log.info("  >> %s %s", method.upper(), url)
        if payload:
            log.info("     PAYLOAD  %s", _json.dumps(payload, ensure_ascii=False))
        log.info(
            "  << %d  %s",
            response.status_code,
            _json.dumps(resp_body, ensure_ascii=False) if resp_body else response.text[:300],
        )
        return response


# ─── Helper: extrae el ID del caso desde el nombre de la función ──────────────

def _extract_case_id(fn_name: str) -> str:
    match = re.match(r"test_([a-z]+)(\d+)_", fn_name)
    if match:
        return f"{match.group(1).upper()}-{match.group(2)}"
    return ""


# ─── Hook: reporte HTML en lenguaje no técnico ────────────────────────────────

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin("html")
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, "extras", [])

    if report.when == "call" and pytest_html:
        case_id = _extract_case_id(item.function.__name__)
        doc = (item.function.__doc__ or "").strip()

        escenario = ""
        resultado_esperado = ""
        for line in doc.splitlines():
            line = line.strip()
            if line.startswith("ESCENARIO:"):
                escenario = line[len("ESCENARIO:"):].strip()
            elif line.startswith("Resultado esperado:"):
                resultado_esperado = line[len("Resultado esperado:"):].strip()

        status_icon = "✅ PASS" if report.passed else "❌ FAIL"

        th = (
            "style='width:170px;font-weight:bold;color:#1a5276;"
            "vertical-align:top;padding:4px 8px;white-space:nowrap'"
        )
        td = "style='padding:4px 8px'"

        req = dict(_last_req)
        operacion = _operacion_desde_url(req.get("url", "")) if req else ""
        descripcion_resultado = _descripcion_http(resultado_esperado) if resultado_esperado else ""
        datos_html = _datos_amigables(req.get("payload") or {}) if req else ""

        rows = []
        if case_id:
            rows.append(
                f"<tr><td {th}>Código del caso</td>"
                f"<td {td}><code style='background:#d6eaf8;padding:2px 10px;"
                f"border-radius:4px;font-size:1em;font-weight:bold'>{case_id}</code>"
                f"</td></tr>"
            )
        if operacion:
            rows.append(
                f"<tr><td {th}>Operación</td>"
                f"<td {td}><b>{operacion}</b></td></tr>"
            )
        if escenario:
            rows.append(
                f"<tr><td {th}>Escenario</td><td {td}>{escenario}</td></tr>"
            )
        if datos_html:
            rows.append(
                f"<tr><td {th}>Datos utilizados</td><td {td}>{datos_html}</td></tr>"
            )
        if descripcion_resultado:
            codigo_match = re.search(r"HTTP\s+(\d+)", resultado_esperado)
            badge_esperado = ""
            if codigo_match:
                badge_esperado = (
                    f"&nbsp;<code style='background:#d5f5e3;padding:1px 8px;"
                    f"border-radius:4px;font-size:0.95em;color:#1e8449'>"
                    f"HTTP {codigo_match.group(1)}</code>"
                )
            rows.append(
                f"<tr><td {th}>Resultado esperado</td>"
                f"<td {td}>{descripcion_resultado}{badge_esperado}</td></tr>"
            )

        codigo_real = req.get("status_code") if req else None
        badge_real = ""
        if codigo_real:
            color = "#d5f5e3" if report.passed else "#fadbd8"
            text_color = "#1e8449" if report.passed else "#922b21"
            badge_real = (
                f"&nbsp;<code style='background:{color};padding:1px 8px;"
                f"border-radius:4px;font-size:0.95em;color:{text_color}'>"
                f"HTTP {codigo_real} recibido</code>"
            )
        rows.append(
            f"<tr><td {th}>Resultado obtenido</td>"
            f"<td {td}>{status_icon}{badge_real}</td></tr>"
        )

        if req.get("payload"):
            payload_json = _json.dumps(req["payload"], ensure_ascii=False, indent=2)
            rows.append(
                f"<tr><td {th}>Payload enviado</td>"
                f"<td {td}><pre style='background:#f4f6f7;padding:6px 10px;"
                f"border-radius:4px;font-size:0.8em;margin:0;overflow:auto;"
                f"max-height:160px'>{_html_mod.escape(payload_json)}</pre></td></tr>"
            )

        if req.get("response_body"):
            resp_json = _json.dumps(req["response_body"], ensure_ascii=False, indent=2)
            bg = "#eafaf1" if report.passed else "#fdedec"
            rows.append(
                f"<tr><td {th}>Response recibido</td>"
                f"<td {td}><pre style='background:{bg};padding:6px 10px;"
                f"border-radius:4px;font-size:0.8em;margin:0;overflow:auto;"
                f"max-height:160px'>{_html_mod.escape(resp_json)}</pre></td></tr>"
            )

        html = (
            "<table style='width:100%;border-collapse:collapse;"
            "font-size:0.9em;margin-top:4px;border:1px solid #e8e8e8'>"
            + "".join(rows)
            + "</table>"
        )
        extra.append(pytest_html.extras.html(html))

        log.info("  RESULTADO  %s", "PASS" if report.passed else "FAIL")

    report.extras = extra

# ─── Constantes de entorno de prueba ──────────────────────────────────────────

BASE_URL = "http://localhost:8000/api/Komands/v1"

JWT_SECRET = "test-secret-komands-qa"
JWT_ALGORITHM = "HS256"

# VNOs verificados en portal real onf-komands.cl:9010 — 2026-06-17
# Flujos activos usan: DTV, VTR, Entel, TCH, Claro, Genérico
# CVTR mantenido como alias legacy del spec original
# GTD y WOM: aparecen en documentación pero SIN flujos configurados aún
VNOS = ["DTV", "VTR", "Entel", "ENTEL", "TCH", "Claro", "Genérico", "GTD", "WOM", "CVTR"]

# Códigos de VNO para el flag --vno: 00=TCH | 02=ClaroVTR | 03=Entel | 05=DTV
VNO_CODES = {"00": "TCH", "02": "CVTR", "03": "ENTEL", "05": "DTV"}
_VNO_PARAMETRIZE = list(VNO_CODES.values())
_VNO_IDS = [f"{v}[{c}]" for c, v in VNO_CODES.items()]


def pytest_addoption(parser):
    parser.addoption(
        "--vno",
        default=None,
        metavar="CODIGO",
        help="VNO a probar: 00=TCH | 02=ClaroVTR | 03=Entel | 05=DTV. Sin argumento: todas.",
    )


def pytest_generate_tests(metafunc):
    if "vno_id" not in metafunc.fixturenames:
        return
    # Si el test ya tiene @pytest.mark.parametrize("vno_id", ...) no re-parametrizar
    for marker in metafunc.definition.iter_markers("parametrize"):
        argnames = marker.args[0] if marker.args else ""
        names = [a.strip() for a in argnames.split(",")] if isinstance(argnames, str) else list(argnames)
        if "vno_id" in names:
            return
    code = metafunc.config.getoption("--vno", default=None)
    if code is not None:
        vno = VNO_CODES.get(code)
        if not vno:
            raise ValueError(
                f"--vno '{code}' no reconocido. Opciones válidas: "
                + ", ".join(f"{c}={v}" for c, v in VNO_CODES.items())
            )
        metafunc.parametrize("vno_id", [vno], ids=[f"{vno}[{code}]"])
    else:
        metafunc.parametrize("vno_id", _VNO_PARAMETRIZE, ids=_VNO_IDS)


ROLE_PERMISSIONS = {
    "ADMIN":    ["activation:write", "transaction:read", "audit:read", "users:write"],
    "OPERATOR": ["activation:write", "transaction:read"],
    "VIEWER":   ["transaction:read"],
    "AUDITOR":  ["audit:read"],
}

# UUID fijo para respuestas del mock (equivale a u_uuid en prod)
_FIXED_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
_FIXED_TS = "2026-06-16T00:00:00Z"


# ─── Helpers JWT ──────────────────────────────────────────────────────────────

def _make_token(
    vno_id: str = "DTV",
    scope: str = "komands:provision komands:query",
    exp_offset: int = 3600,
    sub: str = "servicenow-client",
) -> str:
    """Token para el canal API (ServiceNow → Axway → Komands)."""
    payload = {
        "sub": sub,
        "vno_id": vno_id,
        "scope": scope,
        "exp": int(time.time()) + exp_offset,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _make_portal_token(role: str, exp_offset: int = 3600) -> str:
    """Token para el portal web (usuarios humanos con rol RBAC)."""
    payload = {
        "sub": f"user_{role.lower()}@onnet.cl",
        "role": role,
        "permissions": ROLE_PERMISSIONS.get(role, []),
        "exp": int(time.time()) + exp_offset,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ─── Fixtures de autenticación ────────────────────────────────────────────────

@pytest.fixture
def valid_token() -> str:
    return _make_token()


@pytest.fixture
def expired_token() -> str:
    return _make_token(exp_offset=-60)


@pytest.fixture
def invalid_vno_token() -> str:
    return _make_token(vno_id="FAKE_VNO")


@pytest.fixture
def readonly_token() -> str:
    return _make_token(scope="komands:query")


@pytest.fixture
def admin_token() -> str:
    return _make_portal_token("ADMIN")


@pytest.fixture
def operator_token() -> str:
    return _make_portal_token("OPERATOR")


@pytest.fixture
def viewer_token() -> str:
    return _make_portal_token("VIEWER")


@pytest.fixture
def auditor_token() -> str:
    return _make_portal_token("AUDITOR")


@pytest.fixture
def auth_headers(valid_token: str) -> dict:
    return {
        "Authorization": f"Bearer {valid_token}",
        "X-Correlation-ID": str(uuid.uuid4()),
        "X-Source-System": "ServiceNow",
        "X-Source-System-ID": "SN-PROD-001",
        "X-User-ID": "sn-integration",
        "X-User-Role": "API_CLIENT",
        "X-User-Organization": "DTV",
    }


@pytest.fixture
def vno_token(vno_id: str) -> str:
    """Token de API VNO para la VNO seleccionada con --vno o parametrizada."""
    return _make_token(vno_id=vno_id)


@pytest.fixture
def vno_auth_headers(vno_token: str, vno_id: str) -> dict:
    """Headers completos de ServiceNow para la VNO seleccionada."""
    return {
        "Authorization": f"Bearer {vno_token}",
        "X-Correlation-ID": str(uuid.uuid4()),
        "X-Source-System": "ServiceNow",
        "X-Source-System-ID": "SN-PROD-001",
        "X-User-ID": "sn-integration",
        "X-User-Role": "API_CLIENT",
        "X-User-Organization": vno_id,
    }


# ─── Fixtures de payload base ─────────────────────────────────────────────────

@pytest.fixture
def txn_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def activation_payload_nokia_ftth() -> dict:
    return {
        "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
        "u_routing": {
            "u_id_vno": "DTV",
            "u_olt": "OLT-SAN-001",
            "u_slot": "1",
            "u_pon": "3",
            "u_ontid": "45",
            "u_product": "FTTH",
            "u_technology": "GPON",
        },
        "u_identification": {
            "u_serialnumber": "ALCLF1234567",
        },
        "u_action": {
            "u_iptv": "T",
            "u_voz": "T",
            "u_gestion": "F",
        },
        "u_product": {
            "u_speed_plan": "100M/20M",
        },
    }


@pytest.fixture
def activation_payload_huawei_ftth() -> dict:
    return {
        "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
        "u_routing": {
            "u_id_vno": "DTV",
            "u_olt": "OLT-SAN-002",
            "u_slot": "0",
            "u_pon": "2",
            "u_ontid": "10",
            "u_product": "FTTH",
            "u_technology": "GPON",
        },
        "u_identification": {
            "u_serialnumber": "485754C12345",
        },
        "u_action": {
            "u_iptv": "F",
            "u_voz": "T",
            "u_gestion": "F",
        },
        "u_product": {
            "u_speed_plan": "100M/20M",
        },
    }


@pytest.fixture
def activation_payload_nokia_ssaa() -> dict:
    return {
        "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
        "u_routing": {
            "u_id_vno": "ENTEL",
            "u_olt": "OLT-SCL-010",
            "u_slot": "1",
            "u_pon": "0",
            "u_ontid": "5",
            "u_product": "SSAA",
            "u_technology": "GPON",
        },
        "u_identification": {
            "u_serialnumber": "ALCLF9999999",
        },
        "u_product": {
            "u_speed_plan": "200M/200M",
        },
    }


@pytest.fixture
def deactivation_payload_nokia() -> dict:
    return {
        "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
        "u_routing": {
            "u_id_vno": "DTV",
            "u_olt": "OLT-SAN-001",
            "u_slot": "1",
            "u_pon": "3",
            "u_ontid": "45",
            "u_product": "FTTH",
            "u_technology": "GPON",
        },
        "u_identification": {
            "u_serialnumber": "ALCLF1234567",
        },
    }


# ─── Helpers para leer campos del body (soporta formato plano y jerárquico) ───

def _body_ont_id(body: dict) -> int:
    """Extrae ont_id como int. Prioridad: plano explícito > u_routing.u_ontid."""
    if not isinstance(body, dict):
        return 0
    try:
        val = body.get("ont_id")
        if val is not None:
            return int(val)
    except (ValueError, TypeError):
        pass
    try:
        routing = body.get("u_routing")
        if isinstance(routing, dict):
            val = routing.get("u_ontid")
            if val is not None:
                return int(val)
    except (ValueError, TypeError):
        pass
    return 0


def _body_new_ont_id(body: dict) -> int:
    """Extrae new_ont_id como int. Prioridad: plano explícito > u_routing_new.u_ontid."""
    if not isinstance(body, dict):
        return 0
    try:
        val = body.get("new_ont_id")
        if val is not None:
            return int(val)
    except (ValueError, TypeError):
        pass
    try:
        routing = body.get("u_routing_new")
        if isinstance(routing, dict):
            val = routing.get("u_ontid")
            if val is not None:
                return int(val)
    except (ValueError, TypeError):
        pass
    return 0


def _body_new_serial(body: dict) -> str:
    """Extrae serial del ONT nuevo. Prioridad: plano explícito > u_identification."""
    if not isinstance(body, dict):
        return ""
    ident = body.get("u_identification")
    return (
        body.get("new_serial_ont")
        or (isinstance(ident, dict) and ident.get("u_new_serialnumber") or "")
    )


def _body_cancel_sentinel(body: dict) -> str:
    """Extrae centinela de cancelación. Prioridad: plano explícito > u_identification."""
    if not isinstance(body, dict):
        return ""
    ident = body.get("u_identification")
    return (
        body.get("external_order_id")
        or (isinstance(ident, dict) and ident.get("u_access_id") or "")
    )


def _body_olt_name(body: dict) -> str:
    """Extrae nombre de la OLT. Prioridad: plano explícito > u_routing.u_olt."""
    if not isinstance(body, dict):
        return ""
    routing = body.get("u_routing")
    return body.get("olt_name") or (isinstance(routing, dict) and routing.get("u_olt") or "")


def _body_mod_type(body: dict) -> str:
    """Extrae tipo de modificación. Prioridad: plano explícito > u_action.u_type."""
    if not isinstance(body, dict):
        return ""
    action = body.get("u_action")
    return body.get("modification_type") or (isinstance(action, dict) and action.get("u_type") or "")


def _body_speed_profile(body: dict) -> str:
    """Extrae perfil de velocidad nuevo. Prioridad: plano explícito > u_product.u_speed_plan."""
    if not isinstance(body, dict):
        return ""
    product = body.get("u_product")
    return body.get("new_speed_profile") or (isinstance(product, dict) and product.get("u_speed_plan") or "")


def _body_product(body: dict) -> str:
    """Extrae tipo de producto (FTTH/SSAA). Prioridad: plano explícito > u_routing.u_product."""
    if not isinstance(body, dict):
        return "FTTH"
    routing = body.get("u_routing")
    return body.get("service_type") or (isinstance(routing, dict) and routing.get("u_product") or "FTTH")


async def _safe_json(request) -> dict:
    """Lee el body JSON del request; retorna {} ante cualquier error de parseo.

    Protege contra bytes inválidos (Schemathesis fuzzing), JSON no-objeto, etc.
    """
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ─── Helpers de respuesta StandardResponse + campos legacy ───────────────────
#
# El mock retorna AMBOS formatos:
#   - Nuevo: {"result": {"u_uuid", "u_return_code", ...}}  ← spec real v2.2.3
#   - Legacy: {"txn_id", "status", "error_code", ...}      ← retrocompat tests

def _ok_response(u_status: str = "COMPLETED", msg: str = "Transacción encolada") -> dict:
    return {
        "result": {
            "u_uuid": _FIXED_UUID,
            "u_return_code": "0",
            "u_return_code_desc": "Solicitud aceptada para procesamiento",
            "u_timestamp": _FIXED_TS,
            "u_time": "0.001s",
            "u_status": u_status,
        },
        "txn_id": _FIXED_UUID,
        "status": "ACCEPTED",
        "message": msg,
    }


def _err_response(
    return_code: str,
    desc: str,
    error_code: str,
    u_status: str = "FAILED",
    msg: str = "",
) -> dict:
    return {
        "result": {
            "u_uuid": _FIXED_UUID,
            "u_return_code": return_code,
            "u_return_code_desc": desc,
            "u_timestamp": _FIXED_TS,
            "u_time": "0.001s",
            "u_status": u_status,
            "u_error_code": error_code,
        },
        "txn_id": _FIXED_UUID,
        "status": u_status,
        "error_code": error_code,
        "error_message": msg,
    }


# ─── Helper de auth para endpoints de escritura ───────────────────────────────

def _check_write_auth(request: Request) -> dict:
    """Valida JWT de escritura (API o portal). Lanza HTTPException si falla."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente o malformado")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    if "vno_id" in payload:
        if payload["vno_id"] not in VNOS:
            raise HTTPException(status_code=403, detail="VNO no autorizada")
        if "komands:provision" not in payload.get("scope", ""):
            raise HTTPException(status_code=403, detail="Scope insuficiente")
    elif "role" in payload:
        if "activation:write" not in payload.get("permissions", []):
            raise HTTPException(status_code=403, detail="Rol sin permiso de escritura")
    else:
        raise HTTPException(status_code=401, detail="Token sin claims reconocidos")

    return payload


def _decode_portal_token(request: Request) -> dict:
    """Extrae y valida el JWT del portal web. Lanza HTTPException si hay error."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    token = auth.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def _require_permission(payload: dict, permission: str) -> None:
    """Verifica que el token tenga el permiso requerido. Lanza 403 si no."""
    perms = payload.get("permissions", [])
    if permission not in perms:
        role = payload.get("role", "sin rol")
        raise HTTPException(
            status_code=403,
            detail=f"Rol '{role}' no tiene permiso '{permission}'",
        )


def _decode_any_token(request: Request) -> dict:
    """Acepta token de portal (role+permissions) o de API VNO (vno_id+komands:query).

    Usado en endpoints de consulta que deben ser accesibles tanto desde el
    portal web como desde clientes API (ServiceNow via Axway).
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    if "role" in payload:
        if "transaction:read" not in payload.get("permissions", []):
            raise HTTPException(
                status_code=403,
                detail=f"Rol '{payload.get('role')}' no tiene transaction:read",
            )
    elif "vno_id" in payload:
        if payload["vno_id"] not in VNOS:
            raise HTTPException(status_code=403, detail="VNO no autorizada")
        if "komands:query" not in payload.get("scope", ""):
            raise HTTPException(status_code=403, detail="Scope insuficiente para consultas")
    else:
        raise HTTPException(status_code=401, detail="Token sin claims reconocidos")
    return payload


# ─── Mini app de prueba ───────────────────────────────────────────────────────

def _build_test_app() -> FastAPI:
    app = FastAPI()

    # ── POST /service-activation  (alias: /activation) ───────────────────────
    @app.post("/api/Komands/v1/service-activation", status_code=202)
    @app.post("/api/Komands/v1/activation", status_code=202)
    async def service_activation(request: Request):
        _check_write_auth(request)
        body = await _safe_json(request)
        ont_id = _body_ont_id(body)

        if ont_id == 6661:
            return _err_response("115", "Fallo en paso crítico Nokia — rollback ejecutado",
                                 "KMD-5021", "ROLLED_BACK",
                                 "Paso crítico Nokia falló — rollback ejecutado correctamente")

        if ont_id == 6662:
            return _err_response("115", "Fallo en paso crítico Huawei — rollback ejecutado",
                                 "KMD-5021", "ROLLED_BACK",
                                 "Paso crítico Huawei falló — rollback ejecutado correctamente")

        if ont_id == 6663:
            return _err_response("120", "Fallo crítico sin rollback posible",
                                 "KMD-5030", "ROLLBACK_FAILED",
                                 "Paso crítico falló y rollback también falló — intervención manual requerida")

        if ont_id == 6664:
            return _ok_response("ACCEPTED", "Paso no crítico omitido — operación continúa")

        if ont_id == 2100:
            return _err_response("100", "Tecnología no reconocida — solo FTTH/SSAA",
                                 "KMD-4001", "FAILED",
                                 "Tecnología no reconocida — solo se admite FTTH o SSAA")

        if ont_id == 5555:
            return _err_response("40", "OLT con problemas de acceso",
                                 "KMD-2003", "FAILED",
                                 "OLT con problemas de acceso — verificar conectividad o escalar a Redes")

        if ont_id == 4444:
            return _err_response("60", "Problemas con credenciales SSH en la OLT",
                                 "KMD-5020", "FAILED",
                                 "Problemas con credenciales SSH — verificar configuración de acceso a la OLT")

        corr_id = request.headers.get("X-Correlation-ID", "")
        if corr_id == "idempotency-test-fixed-uuid-001":
            _idempotency_store = getattr(app.state, "idempotency_store", {})
            if corr_id in _idempotency_store:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=200, content={
                    "txn_id": _idempotency_store[corr_id],
                    "status": "ACCEPTED",
                    "message": "Solicitud duplicada — txn_id original devuelto",
                    "result": {
                        "u_uuid": _idempotency_store[corr_id],
                        "u_return_code": "0",
                        "u_return_code_desc": "Idempotente — resultado original",
                        "u_timestamp": _FIXED_TS,
                        "u_time": "0.001s",
                        "u_status": "COMPLETED",
                    },
                })
            _idempotency_store[corr_id] = _FIXED_UUID
            app.state.idempotency_store = _idempotency_store

        return _ok_response(msg="Activación encolada")

    # ── POST /unsubscription  (alias: /unsuscription) ─────────────────────────
    @app.post("/api/Komands/v1/unsubscription", status_code=202)
    @app.post("/api/Komands/v1/unsuscription", status_code=202)
    async def unsubscription(request: Request):
        _check_write_auth(request)
        body = await _safe_json(request)
        ont_id = _body_ont_id(body)

        if ont_id == 9999:
            return _err_response("20", "No se pudo resolver INDEX dinámico Huawei",
                                 "KMD-2002", "FAILED",
                                 "No se pudo resolver el INDEX dinámico del service-port Huawei")

        if ont_id == 9998:
            return _err_response("20", "INDEX parcial — rollback ejecutado",
                                 "KMD-2002", "ROLLED_BACK",
                                 "INDEX parcial: 2 de 3 service-ports resueltos — rollback ejecutado")

        if ont_id == 8888:
            return _err_response("10", "ONT no encontrado en la OLT",
                                 "KMD-2002", "FAILED",
                                 "ONT no encontrado en la OLT — verificar que el ID sea correcto en ServiceNow")

        if ont_id == 7777:
            return _err_response("50", "Timeout esperando respuesta de la OLT",
                                 "KMD-5020", "FAILED",
                                 "Timeout esperando respuesta de la OLT — reintentar más tarde o escalar a Redes")

        if ont_id == 6667:
            return _err_response("115", "Fallo en paso crítico de baja — rollback ejecutado",
                                 "KMD-5021", "ROLLED_BACK",
                                 "Paso crítico de baja Nokia falló — servicio restaurado al estado activo")

        if ont_id == 5555:
            return _err_response("40", "OLT con problemas de acceso",
                                 "KMD-2003", "FAILED",
                                 "OLT con problemas de acceso — verificar conectividad o escalar a Redes")

        if ont_id == 4444:
            return _err_response("60", "Problemas con credenciales SSH en la OLT",
                                 "KMD-5020", "FAILED",
                                 "Problemas con credenciales SSH — verificar configuración de acceso a la OLT")

        if ont_id == 3333:
            return _err_response("30", "SL ID no asociado a la ruta",
                                 "KMD-2002", "FAILED",
                                 "SL ID no asociado a la ruta — verificar datos del acceso en ServiceNow")

        cancel_sentinel = _body_cancel_sentinel(body)
        if cancel_sentinel == "NO_PROVISION":
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content={
                "status": "NO_ACTION",
                "message": "Sin provisión activa — orden cerrada por ServiceNow",
            })

        if cancel_sentinel == "IN_PROGRESS":
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=409, content={
                "error_code": "KMD-3003",
                "error_message": "Transacción en progreso para este acceso — reintentar en 30 segundos",
            })

        return _ok_response(msg="Baja encolada")

    # ── POST /service-modification  (alias: /modification) ───────────────────
    @app.post("/api/Komands/v1/service-modification", status_code=202)
    @app.post("/api/Komands/v1/modification", status_code=202)
    async def service_modification(request: Request):
        from fastapi.responses import JSONResponse
        _check_write_auth(request)
        body = await _safe_json(request)
        ont_id = _body_ont_id(body)
        mod_type = _body_mod_type(body)
        speed_profile = _body_speed_profile(body)
        olt_name = _body_olt_name(body)

        _HUAWEI_OLTS = {"OLT-SAN-002", "OLT-VAL-003"}
        if mod_type in ("remove_service", "REMOVE_SERVICE") and olt_name not in _HUAWEI_OLTS:
            return JSONResponse(status_code=422, content={
                "error_code": "KMD-4001",
                "error_message": "SERVICE_REMOVE no soportado en FTTH — usar baja completa si el cliente no quiere ningún servicio",
            })

        if speed_profile == "PERFIL_INVALIDO":
            return JSONResponse(status_code=422, content={
                "error_code": "KMD-2004",
                "error_message": "Perfil de velocidad no encontrado — verificar catálogo de perfiles en la OLT",
            })

        if ont_id == 8888:
            return _err_response("10", "ONT no encontrado en la OLT",
                                 "KMD-2002", "FAILED",
                                 "ONT no encontrado en la OLT — verificar que el ID sea correcto en ServiceNow")

        if ont_id == 7777:
            return _err_response("50", "Timeout esperando respuesta de la OLT",
                                 "KMD-5020", "FAILED",
                                 "Timeout esperando respuesta de la OLT — reintentar más tarde o escalar a Redes")

        if ont_id == 6665:
            return _err_response("115", "Paso crítico de modificación falló — rollback ejecutado",
                                 "KMD-5021", "ROLLED_BACK",
                                 "Modificación falló en ejecución CLI — servicio restaurado al perfil anterior")

        if ont_id == 2070:
            return _err_response("70", "Servicio ya activo — alta no ejecutada",
                                 "KMD-4001", "FAILED",
                                 "El servicio ya está activo en la OLT — alta no ejecutada")

        if ont_id == 2080:
            return _err_response("80", "Servicio ya inactivo — baja no ejecutada",
                                 "KMD-4001", "FAILED",
                                 "El servicio ya está inactivo en la OLT — baja no ejecutada")

        if ont_id == 2090:
            return _err_response("90", "Ningún servicio seleccionado (flags en F)",
                                 "KMD-4001", "FAILED",
                                 "Todos los flags de servicio están en F — no hay nada que modificar")

        if ont_id == 5555:
            return _err_response("40", "OLT con problemas de acceso",
                                 "KMD-2003", "FAILED",
                                 "OLT con problemas de acceso — verificar conectividad o escalar a Redes")

        if ont_id == 4444:
            return _err_response("60", "Problemas con credenciales SSH en la OLT",
                                 "KMD-5020", "FAILED",
                                 "Problemas con credenciales SSH — verificar configuración de acceso a la OLT")

        if ont_id == 3333:
            return _err_response("30", "SL ID no asociado a la ruta",
                                 "KMD-2002", "FAILED",
                                 "SL ID no asociado a la ruta — verificar datos del acceso en ServiceNow")

        return _ok_response(msg="Modificación encolada")

    # ── POST /reset-ont  (mock-only: no está en el API real) ──────────────────
    @app.post("/api/Komands/v1/reset-ont", status_code=202)
    async def reset_ont(request: Request):
        _check_write_auth(request)
        body = await _safe_json(request)
        ont_id = _body_ont_id(body)

        if ont_id == 8888:
            return _err_response("10", "ONT no encontrado en la OLT",
                                 "KMD-2002", "FAILED",
                                 "ONT no encontrado en la OLT — verificar que el ID sea correcto en ServiceNow")

        if ont_id == 6666:
            return _err_response("40", "ONT offline — sin señal óptica",
                                 "KMD-2003", "FAILED",
                                 "ONT offline — sin señal óptica. Verificar alimentación y fibra del cliente")

        if ont_id == 7777:
            return _err_response("50", "Timeout esperando respuesta de la OLT",
                                 "KMD-5020", "FAILED",
                                 "Timeout esperando respuesta de la OLT — reintentar más tarde o escalar a Redes")

        if ont_id == 5555:
            return _err_response("40", "OLT con problemas de acceso",
                                 "KMD-2003", "FAILED",
                                 "OLT con problemas de acceso — verificar conectividad o escalar a Redes")

        if ont_id == 4444:
            return _err_response("60", "Problemas con credenciales SSH en la OLT",
                                 "KMD-5020", "FAILED",
                                 "Problemas con credenciales SSH — verificar configuración de acceso a la OLT")

        return _ok_response(msg="Reset encolado")

    # ── POST /device-modification ──────────────────────────────────────────────
    @app.post("/api/Komands/v1/device-modification", status_code=202)
    async def device_modification(request: Request):
        _check_write_auth(request)
        body = await _safe_json(request)
        new_serial = _body_new_serial(body)
        ont_id = _body_ont_id(body)

        if new_serial == "FAIL00000000":
            resp = _err_response("115", "Alta del ONT nuevo falló — rollback ejecutado",
                                 "KMD-5021", "ROLLED_BACK",
                                 "Baja del ONT viejo exitosa, pero alta del ONT nuevo falló — escalar a Ingeniería de Redes")
            resp["warning"] = "ONT viejo no recuperable automáticamente"
            return resp

        if new_serial == "VLAN00000000":
            return _err_response("120", "VLAN_CONFLICT — VLAN asignada ya en uso",
                                 "KMD-3001", "ROLLED_BACK",
                                 "VLAN_CONFLICT: la VLAN asignada al nuevo ONT ya está en uso en este puerto PON")

        if ont_id == 8888:
            return _err_response("10", "ONT no encontrado en la OLT",
                                 "KMD-2002", "FAILED",
                                 "ONT no encontrado en la OLT — no se puede iniciar el swap sin el equipo origen")

        if new_serial == "DUPL00000000":
            return _err_response("20", "Serial duplicado en otra OLT",
                                 "KMD-3002", "ROLLED_BACK",
                                 "Serial duplicado: el ONT nuevo ya está registrado en otra OLT")

        if ont_id == 5555:
            return _err_response("40", "OLT con problemas de acceso",
                                 "KMD-2003", "FAILED",
                                 "OLT con problemas de acceso — verificar conectividad o escalar a Redes")

        if ont_id == 4444:
            return _err_response("60", "Problemas con credenciales SSH en la OLT",
                                 "KMD-5020", "FAILED",
                                 "Problemas con credenciales SSH — verificar configuración de acceso a la OLT")

        if ont_id == 3333:
            return _err_response("30", "SL ID no asociado a la ruta",
                                 "KMD-2002", "FAILED",
                                 "SL ID no asociado a la ruta — verificar datos del acceso en ServiceNow")

        return _ok_response(msg="Cambio de equipo encolado")

    # ── POST /fiber-change ─────────────────────────────────────────────────────
    @app.post("/api/Komands/v1/fiber-change", status_code=202)
    async def fiber_change(request: Request):
        _check_write_auth(request)
        body = await _safe_json(request)
        new_ont_id = _body_new_ont_id(body)

        if new_ont_id == 9000:
            return _err_response("120", "Posición destino ocupada",
                                 "KMD-3003", "ROLLED_BACK",
                                 "Posición destino ocupada: ONT ID en el puerto de destino ya está asignado a otro cliente")

        if new_ont_id == 1011:
            return _err_response("11", "Par de identificador incompleto",
                                 "KMD-2002", "FAILED",
                                 "Par de identificador incompleto — verificar u_ontid y u_olt en los datos del cambio de fibra")

        if new_ont_id == 1110:
            return _err_response("110", "Fallo activación prueba PON nueva (paso 1)",
                                 "KMD-5021", "ROLLED_BACK",
                                 "Fallo en la activación de prueba de la PON nueva — cliente mantenido en PON origen")

        ont_id = _body_ont_id(body)
        if ont_id == 5555 or new_ont_id == 5555:
            return _err_response("40", "OLT con problemas de acceso",
                                 "KMD-2003", "FAILED",
                                 "OLT con problemas de acceso — verificar conectividad o escalar a Redes")

        if ont_id == 4444 or new_ont_id == 4444:
            return _err_response("60", "Problemas con credenciales SSH en la OLT",
                                 "KMD-5020", "FAILED",
                                 "Problemas con credenciales SSH — verificar configuración de acceso a la OLT")

        return _ok_response(msg="Cambio de fibra encolado")

    # ── POST /pon-transfer (Cambio de Pelo) ───────────────────────────────────
    @app.post("/api/Komands/v1/pon-transfer", status_code=202)
    async def pon_transfer(request: Request):
        _check_write_auth(request)
        return _ok_response(msg="Transferencia PON encolada")

    # ── POST /fiber-modification (Reasignación puerto PON, AnexoH v2.2) ───────
    # Sentinelas en u_routing_new.u_ontid:
    #   5001 → puerto PON destino sin capacidad → FAILED KMD-1003
    #   5002 → alta en destino falla tras baja exitosa en origen → ROLLED_BACK KMD-5021
    @app.post("/api/Komands/v1/fiber-modification", status_code=202)
    async def fiber_modification(request: Request):
        _check_write_auth(request)
        body = await _safe_json(request)
        new_ont_id = _body_new_ont_id(body)

        if new_ont_id == 5001:
            return _err_response("10", "Puerto PON destino sin capacidad disponible",
                                 "KMD-1003", "FAILED",
                                 "Puerto PON destino sin capacidad — seleccionar otro puerto o esperar a que se libere")
        if new_ont_id == 5002:
            return _err_response("115", "Alta en OLT destino falló — rollback ejecutado",
                                 "KMD-5021", "ROLLED_BACK",
                                 "Baja en origen exitosa, pero alta en destino falló — cliente restaurado en origen")

        return _ok_response(msg="Modificación de fibra encolada")

    @app.post("/api/Komands/v1/reset-ont", status_code=202)
    async def reset_ont(request: Request):
        _check_write_auth(request)
        return _ok_response(msg="Reset ONT encolado")

    # ── Portal web — endpoints con RBAC por rol ───────────────────────────────

    @app.get("/api/Komands/v1/transaction/{txn_id_path}")
    async def get_transaction(txn_id_path: str, request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        return {"txn_id": txn_id_path, "status": "COMPLETED"}

    @app.get("/api/Komands/v1/audit-log")
    async def get_audit_log(request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "audit:read")
        return {"logs": [], "total": 0}

    @app.post("/api/Komands/v1/users", status_code=201)
    async def create_user(request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "users:write")
        return {"user_id": 1, "message": "Usuario creado"}

    # ── GET /query-access/{u_id} ──────────────────────────────────────────────
    @app.get("/api/Komands/v1/query-access/{u_id}")
    async def query_access_v2(u_id: str, request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        if "NOTFOUND" in u_id.upper():
            raise HTTPException(status_code=404, detail="error_code=KMD-2002")
        parts = u_id.split("_")
        return {
            "result": {
                "u_uuid": _FIXED_UUID,
                "u_return_code": "0",
                "u_return_code_desc": "Consulta exitosa",
                "u_timestamp": _FIXED_TS,
                "u_time": "0.001s",
            },
            "u_id": u_id,
            "u_olt": parts[0] if parts else u_id,
            "u_ont_status": "ACTIVE",
            "u_serialnumber": "ALCLF1234567",
        }

    # ── GET /access/{access_id} (mock-only, retrocompat test_queries.py) ──────
    @app.get("/api/Komands/v1/access/{access_id}")
    async def query_access(access_id: str, request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        if access_id == "NOTFOUND":
            raise HTTPException(status_code=404, detail="error_code=KMD-2002")
        source = request.query_params.get("source", "cache")
        return {
            "access_id": access_id,
            "ont_serial": "ALCLF1234567",
            "status": "ACTIVE",
            "olt_name": "OLT-SAN-001",
            "source": source,
        }

    # ── GET /port-occupancy (mock-only) ───────────────────────────────────────
    @app.get("/api/Komands/v1/port-occupancy")
    async def port_occupancy(request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        return {"max_onts": 128, "active_onts": 87, "available": 41}

    # ── GET /transaction/{txn_id}/status (mock-only, retrocompat test_queries) ─
    @app.get("/api/Komands/v1/transaction/{txn_id_path}/status")
    async def get_transaction_status(txn_id_path: str, request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        if txn_id_path == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return {"txn_id": txn_id_path, "status": "COMPLETED", "steps": []}

    # ── GET /{operation}/{uuid} — estado de operación asíncrona (spec real) ────
    # Endpoints presentes en openapi.json v2.2.3 pero ausentes en mocks anteriores.
    # Auth: portal token con transaction:read (en prod acepta también vno+komands:query).

    def _operation_status_response(op_uuid: str, operation: str) -> dict:
        return {
            "txn_id": op_uuid,
            "operation": operation,
            "status": "COMPLETED",
            "result": {
                "u_uuid": op_uuid,
                "u_return_code": "0",
                "u_return_code_desc": "Operación completada",
                "u_timestamp": _FIXED_TS,
                "u_time": "0.001s",
                "u_status": "COMPLETED",
            },
            "steps": [],
        }

    @app.get("/api/Komands/v1/service-activation/{op_uuid}")
    async def get_activation_status(op_uuid: str, request: Request):
        _decode_any_token(request)
        if op_uuid == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return _operation_status_response(op_uuid, "service-activation")

    @app.get("/api/Komands/v1/unsubscription/{op_uuid}")
    async def get_unsubscription_status(op_uuid: str, request: Request):
        _decode_any_token(request)
        if op_uuid == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return _operation_status_response(op_uuid, "unsubscription")

    @app.get("/api/Komands/v1/device-modification/{op_uuid}")
    async def get_device_modification_status(op_uuid: str, request: Request):
        _decode_any_token(request)
        if op_uuid == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return _operation_status_response(op_uuid, "device-modification")

    @app.get("/api/Komands/v1/service-modification/{op_uuid}")
    async def get_service_modification_status(op_uuid: str, request: Request):
        _decode_any_token(request)
        if op_uuid == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return _operation_status_response(op_uuid, "service-modification")

    @app.get("/api/Komands/v1/fiber-change/{op_uuid}")
    async def get_fiber_change_status(op_uuid: str, request: Request):
        _decode_any_token(request)
        if op_uuid == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return _operation_status_response(op_uuid, "fiber-change")

    @app.get("/api/Komands/v1/pon-transfer/{op_uuid}")
    async def get_pon_transfer_status(op_uuid: str, request: Request):
        _decode_any_token(request)
        if op_uuid == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return _operation_status_response(op_uuid, "pon-transfer")

    @app.get("/api/Komands/v1/reset-ont/{op_uuid}")
    async def get_reset_ont_status(op_uuid: str, request: Request):
        _decode_any_token(request)
        if op_uuid == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return _operation_status_response(op_uuid, "reset-ont")

    # ── POST /internal/complete — simula worker terminado → callback ──────────
    @app.post("/api/Komands/v1/internal/complete", status_code=200)
    async def complete_operation(request: Request):
        body = await _safe_json(request)
        txn_id = body.get("txn_id", _FIXED_UUID)
        status = body.get("status", "COMPLETED")
        callback_url = body.get("callback_url")

        callback_payload = {
            "txn_id": txn_id,
            "correlation_id": body.get("correlation_id", str(uuid.uuid4())),
            "external_order_id": body.get("external_order_id", "ORD-TEST-001"),
            "status": status,
            "operation": body.get("operation", "activation"),
            "vno_code": body.get("vno_code", body.get("vno_id", "DTV")),
            "olt_name": body.get("olt_name", "OLT-SAN-001"),
            "started_at": body.get("started_at", "2026-06-16T10:00:00Z"),
            "completed_at": body.get("completed_at", "2026-06-16T10:00:45Z"),
            "duration_ms": body.get("duration_ms", 1250),
            "steps": body.get("steps", []),
        }
        if status in ("FAILED", "ROLLED_BACK", "ROLLED_BACK_FAILED"):
            callback_payload["error"] = {
                "code": body.get("error_code", ""),
                "category": body.get("error_category", "CLI_ERROR"),
                "message": body.get("error_message", ""),
                "retryable": body.get("error_retryable", False),
            }

        if not callback_url:
            return {"ok": True, "callback_http_status": None}

        attempt = body.get("attempt", 1)
        max_attempts = body.get("max_attempts", 5)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(callback_url, json=callback_payload)
                if resp.status_code >= 400:
                    if attempt >= max_attempts:
                        return {
                            "ok": False,
                            "callback_http_status": resp.status_code,
                            "exhausted": True,
                            "status": "CALLBACK_FAILED",
                        }
                    return {"ok": False, "callback_http_status": resp.status_code}
                return {"ok": True, "callback_http_status": resp.status_code}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "callback_http_status": None}

    return app


@pytest.fixture(scope="session")
def test_client() -> CapturingTestClient:
    """Cliente HTTP que apunta a la mini app de prueba. No levanta servidor real."""
    return CapturingTestClient(_build_test_app(), raise_server_exceptions=False)


# ─── Mini app con Feature Flags e Idempotencia ────────────────────────────────

class AppState:
    """Estado mutable de la mini app — se resetea por cada test."""
    def __init__(self):
        self.flags: dict = {}
        self.seen_txns: dict = {}
        self.seen_orders: dict = {}

    def is_enabled(self, vno_id: str, product: str) -> bool:
        vno_flags = self.flags.get(vno_id, {})
        if product in vno_flags:
            return vno_flags[product]
        if "_all" in vno_flags:
            return vno_flags["_all"]
        return True


def _build_flagged_app(state: AppState) -> FastAPI:
    """Mini app que soporta feature flags e idempotencia."""
    app = FastAPI()

    @app.post("/test/feature-flags")
    async def set_flag(request: Request):
        data = await request.json()
        vno = data["vno_id"]
        product = data.get("product")
        enabled = data["enabled"]
        if vno not in state.flags:
            state.flags[vno] = {}
        key = product if product else "_all"
        state.flags[vno][key] = enabled
        return {"ok": True, "vno_id": vno, "product": product, "enabled": enabled}

    @app.post("/api/Komands/v1/service-activation", status_code=202)
    @app.post("/api/Komands/v1/activation", status_code=202)
    async def activation_flagged(request: Request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token ausente")
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        if "vno_id" in payload:
            vno_id = payload["vno_id"]
            if vno_id not in VNOS:
                raise HTTPException(status_code=403, detail="VNO no autorizada")
            if "komands:provision" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")
        elif "role" in payload:
            vno_id = "DTV"
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Sin permiso de activación")
        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")

        body = await _safe_json(request)
        product = _body_product(body)

        if not state.is_enabled(vno_id, product):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content={
                "error": "KMD-4001",
                "message": f"Feature flag desactivado para VNO={vno_id} producto={product}",
                "redirect": "blueplanet",
            })

        txn_id = body.get("txn_id")
        if txn_id and txn_id in state.seen_txns:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content=state.seen_txns[txn_id])

        external_order_id = (
            body.get("u_identification", {}).get("u_access_id")
            or body.get("external_order_id")
        )
        if not txn_id and external_order_id and external_order_id in state.seen_orders:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content=state.seen_orders[external_order_id])

        assigned_txn_id = txn_id or _FIXED_UUID
        result = {
            "result": {
                "u_uuid": assigned_txn_id,
                "u_return_code": "0",
                "u_return_code_desc": "Solicitud aceptada",
                "u_timestamp": _FIXED_TS,
                "u_time": "0.001s",
                "u_status": "COMPLETED",
            },
            "txn_id": assigned_txn_id,
            "status": "ACCEPTED",
            "message": "Transacción encolada",
        }
        if txn_id:
            state.seen_txns[txn_id] = result
        if external_order_id:
            state.seen_orders[external_order_id] = result

        return result

    @app.post("/api/Komands/v1/unsubscription", status_code=202)
    @app.post("/api/Komands/v1/unsuscription", status_code=202)
    async def unsuscription_flagged(request: Request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token ausente")
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        if "vno_id" in payload:
            vno_id = payload["vno_id"]
            if vno_id not in VNOS:
                raise HTTPException(status_code=403, detail="VNO no autorizada")
            if "komands:provision" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")
        elif "role" in payload:
            vno_id = "DTV"
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Sin permiso")
        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")

        body = await _safe_json(request)
        product = _body_product(body)

        if not state.is_enabled(vno_id, product):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content={
                "error": "KMD-4001",
                "message": f"Feature flag desactivado para VNO={vno_id} producto={product}",
                "redirect": "blueplanet",
            })

        txn_id = body.get("txn_id")
        if txn_id and txn_id in state.seen_txns:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content=state.seen_txns[txn_id])

        result = {
            "result": {
                "u_uuid": txn_id or _FIXED_UUID,
                "u_return_code": "0",
                "u_return_code_desc": "Solicitud aceptada",
                "u_timestamp": _FIXED_TS,
                "u_time": "0.001s",
                "u_status": "COMPLETED",
            },
            "txn_id": txn_id or _FIXED_UUID,
            "status": "ACCEPTED",
            "message": "Baja encolada",
        }
        if txn_id:
            state.seen_txns[txn_id] = result
        return result

    return app


@pytest.fixture
def ff_state() -> AppState:
    return AppState()


@pytest.fixture
def ff_client(ff_state: AppState) -> CapturingTestClient:
    return CapturingTestClient(_build_flagged_app(ff_state), raise_server_exceptions=False)


# ─── Fixtures de mock OLT (SSH/Netmiko) ──────────────────────────────────────

@pytest.fixture
def mock_nokia_ssh():
    with patch("netmiko.ConnectHandler") as mock_connect:
        conn = MagicMock()
        conn.send_command.return_value = "OK"
        conn.send_config_set.return_value = "OK"
        conn.is_alive.return_value = True
        mock_connect.return_value.__enter__ = lambda s: conn
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        yield conn


@pytest.fixture
def mock_huawei_ssh():
    with patch("netmiko.ConnectHandler") as mock_connect:
        conn = MagicMock()
        conn.send_command.return_value = "OK"
        conn.send_config_set.return_value = "OK"
        conn.is_alive.return_value = True
        mock_connect.return_value.__enter__ = lambda s: conn
        mock_connect.return_value.__exit__ = MagicMock(return_value=False)
        yield conn


@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        yield client
