"""
Levanta la mini app de prueba como servidor local.
Útil para probar manualmente con Postman o cualquier cliente HTTP.

Uso:
    .\.venv\Scripts\python.exe run_dev.py

Luego en Postman apunta a:
    http://localhost:8000/api/v1/activation
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from jose import jwt, JWTError
import time

JWT_SECRET = "test-secret-komands-qa"
JWT_ALGORITHM = "HS256"
VNOS = ["DTV", "ClaroVTR", "Entel", "TCH"]

app = FastAPI(
    title="Komands API — Mini app de prueba",
    description="Simula el API Gateway de Komands para pruebas manuales",
    version="0.1.0",
)


@app.post("/api/v1/activation", status_code=202)
async def activation(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente o malformado")

    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")

    if "vno_id" in payload:
        if payload["vno_id"] not in VNOS:
            raise HTTPException(status_code=403, detail=f"VNO '{payload['vno_id']}' no autorizada")
        if "komands:write" not in payload.get("scope", ""):
            raise HTTPException(status_code=403, detail="Scope insuficiente")
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


@app.get("/api/v1/transaction/{txn_id}")
async def get_transaction(txn_id: str):
    return {"txn_id": txn_id, "status": "COMPLETED", "steps": []}


@app.get("/health")
async def health():
    return {"status": "ok", "app": "komands-mini-dev"}


# ── Endpoint utilitario: genera un token de prueba ────────────────────────────
# Solo existe en esta mini app — NO existirá en Komands real.
# Úsalo para obtener un token válido para pegar en Postman.

@app.get("/dev/token")
async def get_dev_token(vno_id: str = "DTV", role: str = None):
    """Genera un JWT de prueba para usar en Postman."""
    if role:
        payload = {
            "sub": f"user_{role.lower()}@onnet.cl",
            "role": role,
            "permissions": {
                "ADMIN":    ["activation:write", "transaction:read", "audit:read", "users:write"],
                "OPERATOR": ["activation:write", "transaction:read"],
                "VIEWER":   ["transaction:read"],
                "AUDITOR":  ["audit:read"],
            }.get(role, []),
            "exp": int(time.time()) + 3600,
        }
    else:
        payload = {
            "sub": "servicenow-client",
            "vno_id": vno_id,
            "scope": "komands:write komands:read",
            "exp": int(time.time()) + 3600,
        }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {
        "token": token,
        "uso": f"Authorization: Bearer {token}",
        "expira_en": "1 hora",
    }


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Komands Mini App corriendo en http://localhost:8000")
    print("  Docs Swagger: http://localhost:8000/docs")
    print("  Obtener token: http://localhost:8000/dev/token")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
