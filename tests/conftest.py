"""Fixtures compartidos para toda la suite de pruebas Komands QA."""
import html as _html_mod
import json as _json
import logging
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

# Almacena el último request capturado (se sobreescribe en cada test)
_last_req: dict = {}


# ─── Tablas de lenguaje amigable para el reporte ─────────────────────────────

_URL_OPERACION = {
    "/unsuscription":      "Baja de Acceso",
    "/activation":         "Activación de Acceso",
    "/modification":       "Modificación de Servicio",
    "/reset-ont":          "Reset de ONT",
    "/device-modification":"Cambio de Equipo (Swap)",
    "/port-occupancy":     "Consulta Ocupación Puerto PON",
    "/access/":            "Consulta de Acceso",
    "/transaction/":       "Estado de Transacción",
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
    "vno_id":                   "Cliente",
    "olt_vendor":               "Fabricante OLT",
    "olt_name":                 "OLT",
    "product":                  "Producto",
    "operation_type":           "Tipo de operación",
    "old_ont_serial":           "Serial ONT a reemplazar",
    "new_ont_serial":           "Serial ONT nuevo",
    "ont_serial":               "Serial ONT",
    "delete_vlan_on_terminate": "Eliminar VLAN al terminar",
}

_VENDOR_NOMBRE = {"nokia": "Nokia ISAM 7360 FX", "huawei": "Huawei MA5800"}
_PRODUCTO_NOMBRE = {"FTTH": "Fibra residencial (FTTH)", "SSAA": "Empresarial (SSAA)"}
_OPERACION_NOMBRE = {
    "SPEED_CHANGE": "Cambio de velocidad",
    "BLOCK":        "Bloqueo de servicio",
    "UNBLOCK":      "Desbloqueo de servicio",
}


def _operacion_desde_url(url: str) -> str:
    for patron, nombre in _URL_OPERACION.items():
        if patron in url:
            return nombre
    return url


def _descripcion_http(resultado_esperado: str) -> str:
    clave = resultado_esperado.rstrip(".")
    return _HTTP_DESCRIPCION.get(clave, resultado_esperado)


def _datos_amigables(payload: dict) -> str:
    if not payload:
        return ""
    filas = []
    for campo, etiqueta in _CAMPO_ETIQUETA.items():
        if campo not in payload:
            continue
        valor = payload[campo]
        if campo == "olt_vendor":
            valor = _VENDOR_NOMBRE.get(str(valor).lower(), valor)
        elif campo == "product":
            valor = _PRODUCTO_NOMBRE.get(str(valor), valor)
        elif campo == "operation_type":
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
    """TestClient que guarda el último request para mostrarlo en el reporte HTML."""

    def request(self, method, url, **kwargs):
        response = super().request(method, url, **kwargs)
        _last_req.clear()
        _last_req.update({
            "method": method.upper(),
            "url": url,
            "payload": kwargs.get("json"),
            "status_code": response.status_code,
        })
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
            # Extrae el código HTTP del texto original (ej: "HTTP 202" → "202")
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

        # Resultado obtenido: ✅/❌ + código HTTP real recibido
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

        html = (
            "<table style='width:100%;border-collapse:collapse;"
            "font-size:0.9em;margin-top:4px;border:1px solid #e8e8e8'>"
            + "".join(rows)
            + "</table>"
        )
        extra.append(pytest_html.extras.html(html))
        log.info("%s  [%s]  %s", status_icon, case_id or "?", report.nodeid)

    report.extras = extra

# ─── Constantes de entorno de prueba ──────────────────────────────────────────

BASE_URL = "http://localhost:8000/api/v1"

JWT_SECRET = "test-secret-komands-qa"
JWT_ALGORITHM = "HS256"

VNOS = ["DTV", "ClaroVTR", "Entel", "TCH"]

# Permisos por rol — portal web (usuarios humanos)
# Fuente: docs/04_modelo_datos.md → sección ROLES RBAC
ROLE_PERMISSIONS = {
    "ADMIN":    ["activation:write", "transaction:read", "audit:read", "users:write"],
    "OPERATOR": ["activation:write", "transaction:read"],
    "VIEWER":   ["transaction:read"],
    "AUDITOR":  ["audit:read"],
}


# ─── Helpers de JWT ───────────────────────────────────────────────────────────

def _make_token(
    vno_id: str = "DTV",
    scope: str = "komands:write komands:read",
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
    """Token para el portal web (usuarios humanos con rol RBAC).

    Distinto al token de API: en vez de vno_id/scope, lleva rol y permisos.
    Fuente: docs/05_gaps_seguridad.md + Anexo I core/auth.py
    """
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
    return _make_token(scope="komands:read")


# ─── Fixtures de roles RBAC (portal web) ─────────────────────────────────────

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
        "X-VNO-ID": "DTV",
    }


# ─── Fixtures de payload base ─────────────────────────────────────────────────

@pytest.fixture
def txn_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def activation_payload_nokia_ftth() -> dict:
    return {
        "vno_id": "DTV",
        "product": "FTTH",
        "technology": "GPON",
        "olt_name": "OLT-SAN-001",
        "olt_vendor": "nokia",
        "shelf": 1,
        "card": 2,
        "port": 3,
        "logic_pon": 1,
        "ont_id": 45,
        "ont_serial": "ALCLF1234567",
        "services": ["INTERNET", "VOIP", "IPTV"],
        "speed_profile": "100M_20M",
        "callback_url": "https://servicenow.onnet.cl/api/komands/callback",
    }


@pytest.fixture
def activation_payload_huawei_ftth() -> dict:
    return {
        "vno_id": "DTV",
        "product": "FTTH",
        "technology": "GPON",
        "olt_name": "OLT-SAN-002",
        "olt_vendor": "huawei",
        "shelf": 0,
        "card": 1,
        "port": 2,
        "logic_pon": 0,
        "ont_id": 10,
        "ont_serial": "485754C12345",
        "services": ["INTERNET", "VOIP"],
        "speed_profile": "100M_20M",
        "callback_url": "https://servicenow.onnet.cl/api/komands/callback",
    }


@pytest.fixture
def activation_payload_nokia_ssaa() -> dict:
    return {
        "vno_id": "Entel",
        "product": "SSAA",
        "technology": "GPON",
        "olt_name": "OLT-SCL-010",
        "olt_vendor": "nokia",
        "shelf": 1,
        "card": 1,
        "port": 0,
        "logic_pon": 1,
        "ont_id": 5,
        "ont_serial": "ALCLF9999999",
        "groups": ["A", "C"],
        "svlan": 100,
        "cvlan_dato": 200,
        "cvlan_internet": 201,
        "cvlan_gestion": 202,
        "speed_profile": "200M_200M",
        "callback_url": "https://servicenow.onnet.cl/api/komands/callback",
    }


@pytest.fixture
def deactivation_payload_nokia() -> dict:
    return {
        "vno_id": "DTV",
        "olt_name": "OLT-SAN-001",
        "olt_vendor": "nokia",
        "shelf": 1,
        "card": 2,
        "port": 3,
        "logic_pon": 1,
        "ont_id": 45,
        "callback_url": "https://servicenow.onnet.cl/api/komands/callback",
    }


# ─── Mini app de prueba (simula el API Gateway de Komands) ───────────────────
#
# Como el servidor real aún no existe (estamos haciendo TDD), creamos aquí
# una versión mínima del endpoint /activation que solo implementa la lógica
# de autenticación. Cuando el servidor real exista, los tests apuntarán a él.

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


def _build_test_app() -> FastAPI:
    app = FastAPI()

    # ── /activation — acepta dos tipos de token ───────────────────────────────
    #
    # Tipo A — API (ServiceNow → Axway → Komands):
    #   claims: vno_id, scope="komands:write ..."
    #
    # Tipo B — Portal web (usuario humano con rol RBAC):
    #   claims: role="ADMIN"|"OPERATOR", permissions=[..., "activation:write"]
    #
    # Ambos tipos llegan al mismo endpoint en Komands.

    @app.post("/api/v1/activation", status_code=202)
    async def activation(request: Request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token ausente o malformado")
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        # ¿Es token de API (tiene vno_id)?
        if "vno_id" in payload:
            if payload["vno_id"] not in VNOS:
                raise HTTPException(status_code=403, detail="VNO no autorizada")
            if "komands:write" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")

        # ¿Es token de portal (tiene role)?
        elif "role" in payload:
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Rol sin permiso de activación")

        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")

        return {
            "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "PENDING",
            "message": "Transacción encolada",
        }

    # ── Portal web — endpoints con RBAC por rol ───────────────────────────────
    # Estos endpoints usan tokens de portal (role + permissions), no de API.

    @app.get("/api/v1/transaction/{txn_id}")
    async def get_transaction(txn_id: str, request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        return {"txn_id": txn_id, "status": "COMPLETED"}

    @app.get("/api/v1/audit-log")
    async def get_audit_log(request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "audit:read")
        return {"logs": [], "total": 0}

    @app.post("/api/v1/users", status_code=201)
    async def create_user(request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "users:write")
        return {"user_id": 1, "message": "Usuario creado"}

    # ── /unsuscription — baja de ONT FTTH ─────────────────────────────────────
    @app.post("/api/v1/unsuscription", status_code=202)
    async def unsuscription(request: Request):
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
            if "komands:write" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")
        elif "role" in payload:
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Rol sin permiso de baja")
        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")

        body = await request.json()
        vendor = body.get("olt_vendor", "")
        ont_id = body.get("ont_id")

        # Centinela BAJ-16: Huawei no puede resolver el INDEX → KMD-2002
        if vendor == "huawei" and ont_id == 9999:
            return {
                "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "status": "FAILED",
                "error_code": "KMD-2002",
                "error_message": "No se pudo resolver el INDEX dinámico del service-port Huawei",
            }

        # Centinela BAJ-17: INDEX parcial → rollback de los eliminados
        if vendor == "huawei" and ont_id == 9998:
            return {
                "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "status": "ROLLED_BACK",
                "error_code": "KMD-2002",
                "error_message": "INDEX parcial: 2 de 3 service-ports resueltos — rollback ejecutado",
            }

        return {
            "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "PENDING",
            "message": "Baja encolada",
        }

    # ── /modification — speed_change / block / unblock ────────────────────────
    @app.post("/api/v1/modification", status_code=202)
    async def modification(request: Request):
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
            if "komands:write" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")
        elif "role" in payload:
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Rol sin permiso de modificación")
        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")
        return {
            "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "PENDING",
            "message": "Modificación encolada",
        }

    # ── /reset-ont ─────────────────────────────────────────────────────────────
    @app.post("/api/v1/reset-ont", status_code=202)
    async def reset_ont(request: Request):
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
            if "komands:write" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")
        elif "role" in payload:
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Rol sin permiso de reset")
        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")
        return {
            "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "PENDING",
            "message": "Reset encolado",
        }

    # ── /device-modification — swap de ONT ────────────────────────────────────
    @app.post("/api/v1/device-modification", status_code=202)
    async def device_modification(request: Request):
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
            if "komands:write" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")
        elif "role" in payload:
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Rol sin permiso de swap")
        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")

        body = await request.json()

        # Centinela ONT-16: alta del ONT nuevo falla → swap asimétrico → ROLLED_BACK
        if body.get("new_ont_serial") == "FAIL00000000":
            return {
                "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "status": "ROLLED_BACK",
                "error_code": "KMD-2004",
                "error_message": "Baja del ONT viejo exitosa, pero alta del ONT nuevo falló — escalar a Ingeniería de Redes",
                "warning": "ONT viejo no recuperable automáticamente",
            }

        return {
            "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "PENDING",
            "message": "Cambio de equipo encolado",
        }

    # ── GET /access/{access_id} — consulta estado ONT ─────────────────────────
    # Retorna 404 para el access_id centinela "NOTFOUND" (usado en QRY-003)
    @app.get("/api/v1/access/{access_id}")
    async def query_access(access_id: str, request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        if access_id == "NOTFOUND":
            raise HTTPException(status_code=404, detail="error_code=KMD-2002")
        return {
            "access_id": access_id,
            "ont_serial": "ALCLF1234567",
            "status": "ACTIVE",
            "olt_name": "OLT-SAN-001",
            "source": "cache",
        }

    # ── GET /port-occupancy — consulta ocupación PON ──────────────────────────
    @app.get("/api/v1/port-occupancy")
    async def port_occupancy(request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        return {"max_onts": 128, "active_onts": 87, "available": 41}

    # ── GET /transaction/{txn_id} — ya existía, actualizado con 404 ──────────
    # Retorna 404 para el UUID centinela de ceros (usado en QRY-006)
    @app.get("/api/v1/transaction/{txn_id}/status")
    async def get_transaction_status(txn_id: str, request: Request):
        payload = _decode_portal_token(request)
        _require_permission(payload, "transaction:read")
        if txn_id == "00000000-0000-0000-0000-000000000000":
            raise HTTPException(status_code=404, detail="error_code=KMD-2003")
        return {"txn_id": txn_id, "status": "COMPLETED", "steps": []}

    return app


@pytest.fixture(scope="session")
def test_client() -> CapturingTestClient:
    """Cliente HTTP que apunta a la mini app de prueba. No levanta servidor real."""
    return CapturingTestClient(_build_test_app(), raise_server_exceptions=False)


# ─── Mini app con Feature Flags e Idempotencia ────────────────────────────────
#
# Versión separada de la app con dos capacidades extra:
#   1. Feature flags por VNO/producto — activa o desactiva el flujo Komands
#   2. Idempotencia — detecta txn_id duplicados y no re-ejecuta
#
# Se usa una clase AppState para guardar el estado entre requests dentro
# de un mismo test, y se crea una instancia fresca por cada test (función).

class AppState:
    """Estado mutable de la mini app — se resetea por cada test."""
    def __init__(self):
        # {"DTV": {"FTTH": True, "SSAA": False}}
        # Si el producto es None, aplica a todos los productos de esa VNO
        self.flags: dict = {}
        # {txn_id: response_data} — para idempotencia
        self.seen_txns: dict = {}

    def is_enabled(self, vno_id: str, product: str) -> bool:
        """Retorna True si el flujo Komands está activo para esa VNO+producto."""
        vno_flags = self.flags.get(vno_id, {})
        # Primero busca el flag específico de producto
        if product in vno_flags:
            return vno_flags[product]
        # Si no hay flag de producto, busca el flag global de la VNO
        if "_all" in vno_flags:
            return vno_flags["_all"]
        # Sin flag explícito → habilitado por defecto
        return True


def _build_flagged_app(state: AppState) -> FastAPI:
    """Mini app que soporta feature flags e idempotencia."""
    app = FastAPI()

    # Endpoint para controlar flags desde los tests (simula panel admin)
    @app.post("/test/feature-flags")
    async def set_flag(request: Request):
        data = await request.json()
        vno = data["vno_id"]
        product = data.get("product")   # None = aplica a todos
        enabled = data["enabled"]
        if vno not in state.flags:
            state.flags[vno] = {}
        key = product if product else "_all"
        state.flags[vno][key] = enabled
        return {"ok": True, "vno_id": vno, "product": product, "enabled": enabled}

    @app.post("/api/v1/activation", status_code=202)
    async def activation(request: Request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token ausente")
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        # Extraer VNO e identificar tipo de token
        if "vno_id" in payload:
            vno_id = payload["vno_id"]
            if vno_id not in VNOS:
                raise HTTPException(status_code=403, detail="VNO no autorizada")
            if "komands:write" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")
        elif "role" in payload:
            vno_id = "DTV"  # portal web usa VNO del payload del body
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Sin permiso de activación")
        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")

        # Extraer datos del body para verificar feature flag
        body = await request.json()
        product = body.get("product", "FTTH")

        # ── Feature Flag ──────────────────────────────────────────────────────
        # Si el flag está desactivado para esta VNO+producto, Komands no procesa
        # la operación. ServiceNow debe usar BluePlanet en su lugar.
        # Fuente: docs/05_gaps_seguridad.md → FF-01, FF-03
        if not state.is_enabled(vno_id, product):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content={
                "error": "KMD-4001",
                "message": f"Feature flag desactivado para VNO={vno_id} producto={product}",
                "redirect": "blueplanet",
            })

        # ── Idempotencia ──────────────────────────────────────────────────────
        # Si el txn_id ya fue procesado, devolvemos el resultado anterior
        # sin re-ejecutar la operación en la OLT.
        # Fuente: Anexo E → "duplicado retorna UUID existente con HTTP 200"
        txn_id = body.get("txn_id")
        if txn_id and txn_id in state.seen_txns:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content=state.seen_txns[txn_id])

        # Registrar la transacción
        result = {
            "txn_id": txn_id or "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "PENDING",
            "message": "Transacción encolada",
        }
        if txn_id:
            state.seen_txns[txn_id] = result

        return result

    # ── /unsuscription con Feature Flag e Idempotencia ────────────────────────
    @app.post("/api/v1/unsuscription", status_code=202)
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
            if "komands:write" not in payload.get("scope", ""):
                raise HTTPException(status_code=403, detail="Scope insuficiente")
        elif "role" in payload:
            vno_id = "DTV"
            if "activation:write" not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail="Sin permiso")
        else:
            raise HTTPException(status_code=401, detail="Token sin claims reconocidos")

        body = await request.json()
        product = body.get("product", "FTTH")

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
            "txn_id": txn_id or "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "PENDING",
            "message": "Baja encolada",
        }
        if txn_id:
            state.seen_txns[txn_id] = result
        return result

    return app


@pytest.fixture
def ff_state() -> AppState:
    """Estado fresco para cada test de feature flags. Se resetea automáticamente."""
    return AppState()


@pytest.fixture
def ff_client(ff_state: AppState) -> CapturingTestClient:
    """Cliente con app fresca — flags e idempotencia reseteados para cada test."""
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


# ─── Fixture de cliente HTTP ──────────────────────────────────────────────────

@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        yield client
