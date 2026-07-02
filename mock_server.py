"""
Mock server standalone para pruebas locales con Newman / Postman.

Reproduce el mismo comportamiento del conftest.py pero como servidor HTTP real,
para que Newman pueda pegarle sin necesitar el servidor Komands real desplegado.

Uso:
    pip install fastapi uvicorn python-jose httpx
    python mock_server.py

Luego en otra terminal:
    newman run "collection Kommand/SN a Kommand.postman_collection.json" \
        -e "collection Kommand/newman-environment-local.json"

Puerto: 8000
JWT Secret: test-secret-komands-qa (solo válido en este mock — no es producción)
Spec: openapi.json v2.2.3
"""
import time
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError

JWT_SECRET = "test-secret-komands-qa"
JWT_ALGORITHM = "HS256"
VNOS = ["DTV", "VTR", "Entel", "ENTEL", "TCH", "Claro", "Genérico", "GTD", "WOM", "CVTR"]
# VNOs verificados en portal real (onf-komands.cl:9010) — 2026-06-17
# Flujos activos: DTV, VTR, Entel, TCH, Claro, Genérico
# GTD/WOM: VNO existe pero sin flujos GPON configurados aún
# CVTR: alias legacy del spec original
_HUAWEI_OLTS = {"OLT-SAN-002", "OLT-VAL-003"}

_FIXED_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
_FIXED_TS = "2026-06-16T00:00:00Z"

app = FastAPI(title="Komands Mock Server — Local QA", version="2.2.3")


# ─── Helpers de respuesta (StandardResponse) ─────────────────────────────────

def _ok(msg: str = "Solicitud aceptada para procesamiento") -> dict:
    return {
        "result": {
            "u_uuid": _FIXED_UUID,
            "u_return_code": "0",
            "u_return_code_desc": msg,
            "u_timestamp": _FIXED_TS,
            "u_time": "0.001s",
            "u_status": "COMPLETED",
        },
        "txn_id": _FIXED_UUID,
        "status": "ACCEPTED",
        "message": msg,
    }


def _err(return_code: str, desc: str, error_code: str, u_status: str = "FAILED", msg: str = "") -> dict:
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
        "error_message": msg or desc,
    }


# ─── Helpers de auth ──────────────────────────────────────────────────────────

def _decode(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente o malformado")
    try:
        return jwt.decode(auth.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def _require_provision(payload: dict) -> None:
    if "vno_id" in payload:
        if payload["vno_id"] not in VNOS:
            raise HTTPException(status_code=403, detail="VNO no autorizada")
        if "komands:provision" not in payload.get("scope", ""):
            raise HTTPException(status_code=403, detail="Scope insuficiente — requiere komands:provision")
    elif "role" in payload:
        if "activation:write" not in payload.get("permissions", []):
            raise HTTPException(status_code=403, detail="Sin permiso de escritura")
    else:
        raise HTTPException(status_code=401, detail="Token sin claims reconocidos")


def _require_query(payload: dict) -> None:
    if "vno_id" in payload:
        if payload["vno_id"] not in VNOS:
            raise HTTPException(status_code=403, detail="VNO no autorizada")
        scope = payload.get("scope", "")
        if "komands:query" not in scope and "komands:provision" not in scope:
            raise HTTPException(status_code=403, detail="Scope insuficiente — requiere komands:query")
    elif "role" in payload:
        if "transaction:read" not in payload.get("permissions", []):
            raise HTTPException(status_code=403, detail="Sin permiso de lectura")
    else:
        raise HTTPException(status_code=401, detail="Token sin claims reconocidos")


# ─── Helpers de extracción de campos (family-format con flat fallback) ────────

def _ont_id(body: dict) -> int:
    try:
        val = body.get("ont_id")
        if val is not None:
            return int(val)
    except (ValueError, TypeError):
        pass
    try:
        val = body.get("u_routing", {}).get("u_ontid")
        if val is not None:
            return int(val)
    except (ValueError, TypeError):
        pass
    return 0


def _new_ont_id(body: dict) -> int:
    try:
        val = body.get("new_ont_id")
        if val is not None:
            return int(val)
    except (ValueError, TypeError):
        pass
    try:
        val = body.get("u_routing_new", {}).get("u_ontid")
        if val is not None:
            return int(val)
    except (ValueError, TypeError):
        pass
    return 0


def _new_serial(body: dict) -> str:
    s = body.get("new_serial_ont") or body.get("new_serial") or ""
    if not s:
        s = body.get("u_identification", {}).get("u_new_serialnumber", "")
    return s


def _mod_type(body: dict) -> str:
    t = body.get("modification_type", "")
    if not t:
        t = body.get("u_action", {}).get("u_type", "")
    return t.lower() if t else ""


def _olt_name(body: dict) -> str:
    name = body.get("olt_name", "")
    if not name:
        name = body.get("u_routing", {}).get("u_olt", "")
    return name


def _speed_profile(body: dict) -> str:
    p = body.get("new_speed_profile", "") or body.get("speed_profile", "")
    if not p:
        p = body.get("u_qos", {}).get("u_speed_profile", "")
    return p


# ─── Endpoint de utilidad: genera token para Newman/Postman local ─────────────

@app.get("/test/token")
def get_test_token(vno: str = "DTV", scope: str = "komands:provision komands:query"):
    """Genera un JWT válido para pruebas locales con Newman. NO usar en producción."""
    payload = {
        "sub": "servicenow-client",
        "vno_id": vno,
        "scope": scope,
        "exp": int(time.time()) + 86400,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"token": token, "vno": vno, "expires_in": 86400}


@app.get("/test/token/portal")
def get_portal_token():
    """Genera un JWT de portal web con todos los permisos (para endpoints GET). Solo local."""
    payload = {
        "sub": "admin@onnet.cl",
        "role": "ADMIN",
        "permissions": ["activation:write", "transaction:read", "audit:read", "users:write"],
        "exp": int(time.time()) + 86400,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"token": token, "role": "ADMIN", "expires_in": 86400}


# ─── 01 Baja de acceso ────────────────────────────────────────────────────────

@app.post("/api/Komands/v1/unsubscription", status_code=202)
@app.post("/api/Komands/v1/unsuscription", status_code=202)
async def unsubscription(request: Request):
    _require_provision(_decode(request))
    body = await request.json()
    ont_id = _ont_id(body)

    if ont_id == 9999:
        return _err("20", "No se pudo resolver el INDEX dinámico del service-port Huawei", "KMD-2002")
    if ont_id == 9998:
        return _err("120", "INDEX parcial — rollback ejecutado", "KMD-2002", u_status="ROLLED_BACK")
    if ont_id == 8888:
        return _err("10", "ONT no encontrado en la OLT", "KMD-2002")
    if ont_id == 7777:
        return _err("50", "Timeout esperando respuesta de la OLT", "KMD-5020")

    return _ok("Baja encolada")


# ─── 02 Activación (service-activation) ──────────────────────────────────────

@app.post("/api/Komands/v1/service-activation", status_code=202)
@app.post("/api/Komands/v1/activation", status_code=202)
async def service_activation(request: Request):
    _require_provision(_decode(request))
    return _ok("Activación encolada")


# ─── 03 Modificación de servicio ─────────────────────────────────────────────

@app.post("/api/Komands/v1/service-modification", status_code=202)
@app.post("/api/Komands/v1/modification", status_code=202)
async def service_modification(request: Request):
    _require_provision(_decode(request))
    body = await request.json()
    ont_id = _ont_id(body)
    mod_type = _mod_type(body)
    olt = _olt_name(body)

    if mod_type in ("remove_service", "remove service") and olt not in _HUAWEI_OLTS:
        return JSONResponse(status_code=422, content={
            "error_code": "KMD-4001",
            "error_message": "remove_service no soportado en Nokia FTTH — usar baja completa",
        })
    if _speed_profile(body) == "PERFIL_INVALIDO":
        return JSONResponse(status_code=422, content={
            "error_code": "KMD-2004",
            "error_message": "Perfil de velocidad no encontrado",
        })
    if ont_id == 8888:
        return _err("10", "ONT no encontrado en la OLT", "KMD-2002")
    if ont_id == 7777:
        return _err("50", "Timeout esperando respuesta de la OLT", "KMD-5020")

    return _ok("Modificación encolada")


# ─── 04 Cambio de equipo (swap ONT) ──────────────────────────────────────────

@app.post("/api/Komands/v1/device-modification", status_code=202)
async def device_modification(request: Request):
    _require_provision(_decode(request))
    body = await request.json()
    new_serial = _new_serial(body)
    ont_id = _ont_id(body)

    if new_serial == "FAIL00000000":
        resp = _err("115", "Alta del ONT nuevo falló — escalar a Redes", "KMD-5021", u_status="ROLLED_BACK")
        resp["warning"] = "ONT viejo no recuperable automáticamente"
        return resp
    if new_serial == "VLAN00000000":
        return _err("120", "VLAN_CONFLICT en el puerto de destino", "KMD-3001", u_status="ROLLED_BACK")
    if ont_id == 8888:
        return _err("10", "ONT no encontrado — no se puede iniciar el swap", "KMD-2002")
    if new_serial == "DUPL00000000":
        return _err("20", "Serial duplicado — ONT ya registrado en otra OLT", "KMD-3002", u_status="ROLLED_BACK")

    return _ok("Cambio de equipo encolado")


# ─── 05 Cambio de fibra ───────────────────────────────────────────────────────

@app.post("/api/Komands/v1/fiber-change", status_code=202)
async def fiber_change(request: Request):
    _require_provision(_decode(request))
    body = await request.json()

    if _new_ont_id(body) == 9000:
        return _err("120", "Posición destino ocupada", "KMD-3003", u_status="ROLLED_BACK")

    return _ok("Cambio de fibra encolado")


# ─── 06 Reset ONT ────────────────────────────────────────────────────────────

@app.post("/api/Komands/v1/reset-ont", status_code=202)
async def reset_ont(request: Request):
    _require_provision(_decode(request))
    body = await request.json()
    ont_id = _ont_id(body)

    if ont_id == 8888:
        return _err("10", "ONT no encontrado en la OLT", "KMD-2002")
    if ont_id == 6666:
        return _err("20", "ONT offline — sin señal óptica", "KMD-2003")
    if ont_id == 7777:
        return _err("50", "Timeout esperando respuesta de la OLT", "KMD-5020")

    return _ok("Reset encolado")


# ─── 07 Traspaso PON (pon-transfer) ──────────────────────────────────────────

@app.post("/api/Komands/v1/pon-transfer", status_code=202)
async def pon_transfer(request: Request):
    _require_provision(_decode(request))
    body = await request.json()

    if _new_ont_id(body) == 9000:
        return _err("120", "Posición destino ocupada", "KMD-3003", u_status="ROLLED_BACK")

    return _ok("Traspaso PON encolado")


# ─── 09 Reset ONT ────────────────────────────────────────────────────────────

@app.post("/api/Komands/v1/reset-ont", status_code=202)
async def reset_ont(request: Request):
    _require_provision(_decode(request))
    body = await request.json()
    ont_id = _ont_id(body)

    if ont_id == 8888:
        return _err("10", "ONT no encontrada en la OLT", "KMD-2002")

    return _ok("Reset ONT encolado")


@app.get("/api/Komands/v1/reset-ont/{op_uuid}")
async def get_reset_ont_status(op_uuid: str, request: Request):
    _require_query(_decode(request))
    if op_uuid == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return _op_status(op_uuid, "reset-ont")


# ─── 10 Cancelación ──────────────────────────────────────────────────────────

@app.post("/api/Komands/v1/cancel-order", status_code=202)
async def cancel_order(request: Request):
    _require_provision(_decode(request))
    body = await request.json()
    cancel_target = body.get("cancel_txn_id", "") or body.get("u_action", {}).get("u_cancel_txn_id", "")

    if cancel_target == "00000000-0000-0000-0000-000000000000":
        return _err("10", "Transacción no encontrada o ya finalizada", "KMD-2003")

    return _ok("Cancelación encolada")


# ─── 09 Consultas síncronas ───────────────────────────────────────────────────

@app.get("/api/Komands/v1/transaction/{txn_id}/status")
async def get_transaction_status(txn_id: str, request: Request):
    _require_query(_decode(request))
    if txn_id == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return {
        "txn_id": txn_id,
        "status": "COMPLETED",
        "result": {
            "u_uuid": txn_id,
            "u_return_code": "0",
            "u_return_code_desc": "Operación completada",
            "u_timestamp": _FIXED_TS,
            "u_time": "0.001s",
            "u_status": "COMPLETED",
        },
        "steps": [],
    }


@app.get("/api/Komands/v1/access/{access_id}")
@app.get("/api/Komands/v1/query-access/{access_id}")
async def get_access(access_id: str, request: Request):
    _require_query(_decode(request))
    if access_id == "NOTFOUND":
        raise HTTPException(status_code=404, detail="error_code=KMD-2002")
    return {
        "access_id": access_id,
        "ont_serial": "ALCLF1234567",
        "status": "ACTIVE",
        "olt_name": "OLT-SAN-001",
        "source": "cache",
    }


@app.get("/api/Komands/v1/port-occupancy")
async def port_occupancy(request: Request):
    _require_query(_decode(request))
    return {"max_onts": 128, "active_onts": 87, "available": 41}


# ─── 10 Estado de operaciones asíncronas (openapi.json v2.2.3) ───────────────
# GET /{operation}/{uuid} — presentes en spec real, ausentes en versiones anteriores.

def _op_status(op_uuid: str, operation: str) -> dict:
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
    _require_query(_decode(request))
    if op_uuid == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return _op_status(op_uuid, "service-activation")


@app.get("/api/Komands/v1/unsubscription/{op_uuid}")
async def get_unsubscription_status(op_uuid: str, request: Request):
    _require_query(_decode(request))
    if op_uuid == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return _op_status(op_uuid, "unsubscription")


@app.get("/api/Komands/v1/device-modification/{op_uuid}")
async def get_device_modification_status(op_uuid: str, request: Request):
    _require_query(_decode(request))
    if op_uuid == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return _op_status(op_uuid, "device-modification")


@app.get("/api/Komands/v1/service-modification/{op_uuid}")
async def get_service_modification_status(op_uuid: str, request: Request):
    _require_query(_decode(request))
    if op_uuid == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return _op_status(op_uuid, "service-modification")


@app.get("/api/Komands/v1/fiber-change/{op_uuid}")
async def get_fiber_change_status(op_uuid: str, request: Request):
    _require_query(_decode(request))
    if op_uuid == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return _op_status(op_uuid, "fiber-change")


@app.get("/api/Komands/v1/pon-transfer/{op_uuid}")
async def get_pon_transfer_status(op_uuid: str, request: Request):
    _require_query(_decode(request))
    if op_uuid == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return _op_status(op_uuid, "pon-transfer")


# ─── Arranque ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Komands Mock Server — Local QA  (spec v2.2.3)")
    print("  http://localhost:8000")
    print("  Token: GET http://localhost:8000/test/token")
    print("  VNOs: DTV | VTR | Entel | ENTEL | TCH | Claro | Genérico | GTD | WOM | CVTR")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
