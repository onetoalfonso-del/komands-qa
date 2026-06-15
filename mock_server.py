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
"""
import time
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError

JWT_SECRET = "test-secret-komands-qa"
JWT_ALGORITHM = "HS256"
VNOS = ["DTV", "CVTR", "ENTEL", "TCH"]
_HUAWEI_OLTS = {"OLT-SAN-002", "OLT-VAL-003"}

app = FastAPI(title="Komands Mock Server — Local QA", version="1.0.0")


# ─── Helpers de auth ──────────────────────────────────────────────────────────

def _decode(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente o malformado")
    try:
        return jwt.decode(auth.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def _require_write(payload: dict) -> None:
    if "vno_id" in payload:
        if payload["vno_id"] not in VNOS:
            raise HTTPException(status_code=403, detail="VNO no autorizada")
        if "komands:write" not in payload.get("scope", ""):
            raise HTTPException(status_code=403, detail="Scope insuficiente")
    elif "role" in payload:
        if "activation:write" not in payload.get("permissions", []):
            raise HTTPException(status_code=403, detail="Sin permiso de escritura")
    else:
        raise HTTPException(status_code=401, detail="Token sin claims reconocidos")


def _require_read(payload: dict) -> None:
    if "vno_id" in payload:
        if payload["vno_id"] not in VNOS:
            raise HTTPException(status_code=403, detail="VNO no autorizada")
        if "komands:read" not in payload.get("scope", "") and "komands:write" not in payload.get("scope", ""):
            raise HTTPException(status_code=403, detail="Scope insuficiente")
    elif "role" in payload:
        if "transaction:read" not in payload.get("permissions", []):
            raise HTTPException(status_code=403, detail="Sin permiso de lectura")
    else:
        raise HTTPException(status_code=401, detail="Token sin claims reconocidos")


def _ack(message: str = "Operación encolada") -> dict:
    return {
        "txn_id": str(uuid.uuid4()),
        "status": "ACCEPTED",
        "message": message,
    }


# ─── Endpoint de utilidad: genera token para Newman/Postman local ─────────────

@app.get("/test/token")
def get_test_token(vno: str = "DTV", scope: str = "komands:write komands:read"):
    """Genera un JWT válido para pruebas locales con Newman. NO usar en producción."""
    payload = {
        "sub": "servicenow-client",
        "vno_id": vno,
        "scope": scope,
        "exp": int(time.time()) + 86400,  # 24 horas
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

@app.post("/api/Komands/v1/unsuscription", status_code=202)
async def unsuscription(request: Request):
    _require_write(_decode(request))
    body = await request.json()
    ont_id = body.get("ont_id")

    if ont_id == 9999:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-2002", "error_message": "No se pudo resolver el INDEX dinámico del service-port Huawei"}
    if ont_id == 9998:
        return {"txn_id": str(uuid.uuid4()), "status": "ROLLED_BACK",
                "error_code": "KMD-2002", "error_message": "INDEX parcial — rollback ejecutado"}
    if ont_id == 8888:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-2002", "error_message": "ONT no encontrado en la OLT"}
    if ont_id == 7777:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-5020", "error_message": "Timeout esperando respuesta de la OLT"}

    return _ack("Baja encolada")


# ─── 02 Activación ───────────────────────────────────────────────────────────

@app.post("/api/Komands/v1/activation", status_code=202)
async def activation(request: Request):
    _require_write(_decode(request))
    return _ack("Activación encolada")


# ─── 03 Modificación ─────────────────────────────────────────────────────────

@app.post("/api/Komands/v1/modification", status_code=202)
async def modification(request: Request):
    _require_write(_decode(request))
    body = await request.json()
    ont_id = body.get("ont_id")
    modification_type = body.get("modification_type", "")
    olt_name = body.get("olt_name", "")

    if modification_type == "remove_service" and olt_name not in _HUAWEI_OLTS:
        return JSONResponse(status_code=422, content={
            "error_code": "KMD-4001",
            "error_message": "remove_service no soportado en Nokia FTTH — usar baja completa"})
    if body.get("new_speed_profile") == "PERFIL_INVALIDO":
        return JSONResponse(status_code=422, content={
            "error_code": "KMD-2004", "error_message": "Perfil de velocidad no encontrado"})
    if ont_id == 8888:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-2002", "error_message": "ONT no encontrado en la OLT"}
    if ont_id == 7777:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-5020", "error_message": "Timeout esperando respuesta de la OLT"}

    return _ack("Modificación encolada")


# ─── 04 Cambio de equipo (swap ONT) ──────────────────────────────────────────

@app.post("/api/Komands/v1/device-modification", status_code=202)
async def device_modification(request: Request):
    _require_write(_decode(request))
    body = await request.json()

    if body.get("new_serial_ont") == "FAIL00000000":
        return {"txn_id": str(uuid.uuid4()), "status": "ROLLED_BACK",
                "error_code": "KMD-5021", "error_message": "Alta del ONT nuevo falló — escalar a Redes"}
    if body.get("new_serial_ont") == "VLAN00000000":
        return {"txn_id": str(uuid.uuid4()), "status": "ROLLED_BACK",
                "error_code": "KMD-3001", "error_message": "VLAN_CONFLICT en el puerto de destino"}
    if body.get("ont_id") == 8888:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-2002", "error_message": "ONT no encontrado — no se puede iniciar el swap"}
    if body.get("new_serial_ont") == "DUPL00000000":
        return {"txn_id": str(uuid.uuid4()), "status": "ROLLED_BACK",
                "error_code": "KMD-3002", "error_message": "Serial duplicado — ONT ya registrado en otra OLT"}

    return _ack("Cambio de equipo encolado")


# ─── 05 Cambio de fibra ───────────────────────────────────────────────────────

@app.post("/api/Komands/v1/fiber-change", status_code=202)
async def fiber_change(request: Request):
    _require_write(_decode(request))
    body = await request.json()

    if body.get("new_ont_id") == 9000:
        return {"txn_id": str(uuid.uuid4()), "status": "ROLLED_BACK",
                "error_code": "KMD-3003", "error_message": "Posición destino ocupada"}

    return _ack("Cambio de fibra encolado")


# ─── 06 Reset ONT ────────────────────────────────────────────────────────────

@app.post("/api/Komands/v1/reset-ont", status_code=202)
async def reset_ont(request: Request):
    _require_write(_decode(request))
    body = await request.json()
    ont_id = body.get("ont_id")

    if ont_id == 8888:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-2002", "error_message": "ONT no encontrado en la OLT"}
    if ont_id == 6666:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-2003", "error_message": "ONT offline — sin señal óptica"}
    if ont_id == 7777:
        return {"txn_id": str(uuid.uuid4()), "status": "FAILED",
                "error_code": "KMD-5020", "error_message": "Timeout esperando respuesta de la OLT"}

    return _ack("Reset encolado")


# ─── 07 Consultas síncronas ───────────────────────────────────────────────────

@app.get("/api/Komands/v1/transaction/{txn_id}/status")
async def get_transaction_status(txn_id: str, request: Request):
    _require_read(_decode(request))
    if txn_id == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=404, detail="error_code=KMD-2003")
    return {"txn_id": txn_id, "status": "COMPLETED", "steps": []}


@app.get("/api/Komands/v1/access/{access_id}")
async def get_access(access_id: str, request: Request):
    _require_read(_decode(request))
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
    _require_read(_decode(request))
    return {"max_onts": 128, "active_onts": 87, "available": 41}


# ─── Arranque ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Komands Mock Server — Local QA")
    print("  http://localhost:8000")
    print("  Token: GET http://localhost:8000/test/token")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
