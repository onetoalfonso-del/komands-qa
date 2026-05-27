# APIs REST de Komands — Contratos

## Base URL
```
DEV:  http://localhost:8000/api/v1
QA:   https://komands-qa.internal/api/v1
PROD: https://komands.onnet.cl/api/v1  (vía Axway APIM)
```

## Autenticación
- **Tipo:** OAuth 2.0 client_credentials → JWT (Bearer token)
- **Header obligatorio:** `Authorization: Bearer <token>`
- **Header trazabilidad:** `X-Correlation-ID: <uuid>` (propagar en toda la cadena)
- **Header VNO:** `X-VNO-ID: DTV | ClaroVTR | Entel | TCH`
- Sin token válido → HTTP 401
- VNO no autorizada → HTTP 403

## JWT claims requeridos
```json
{
  "sub": "servicenow-client",
  "vno_id": "DTV",
  "scope": "komands:write komands:read",
  "exp": 1714000000
}
```

---

## OPERACIONES ASÍNCRONAS (202 + callback)

### POST /api/v1/activation — Alta de servicio

**Request body:**
```json
{
  "txn_id": "uuid-v4-opcional-si-no-se-genera-uno",
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
  "callback_url": "https://servicenow.onnet.cl/api/komands/callback"
}
```

**Campos obligatorios:** vno_id, product, technology, olt_name, olt_vendor, shelf, card, port, logic_pon, ont_serial, services, callback_url

**Respuesta exitosa:**
```json
HTTP 202 Accepted
{
  "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "PENDING",
  "message": "Transacción encolada"
}
```

**Ejemplo SSAA grupos A+C:**
```json
{
  "vno_id": "Entel",
  "product": "SSAA",
  "technology": "GPON",
  "olt_vendor": "huawei",
  "olt_name": "OLT-VAL-003",
  "shelf": 1, "card": 1, "port": 2, "logic_pon": 1, "ont_id": 12,
  "ont_serial": "485754C12345",
  "groups": ["A", "C"],
  "svlan": 100,
  "cvlan_dato": 200,
  "cvlan_internet": 201,
  "cvlan_gestion": 202,
  "speed_profile": "200M_200M",
  "callback_url": "https://servicenow.onnet.cl/api/komands/callback"
}
```

---

### POST /api/v1/deactivation — Baja de acceso

**Request body:**
```json
{
  "vno_id": "DTV",
  "olt_name": "OLT-SAN-001",
  "olt_vendor": "nokia",
  "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
  "callback_url": "https://servicenow.onnet.cl/api/komands/callback"
}
```

**Respuesta:** HTTP 202 + txn_id (igual que activation)

---

### POST /api/v1/device-modification — Cambio de serial ONT (swap)

**Descripción:** Baja ONT anterior + alta ONT nueva con misma configuración

**Request body:**
```json
{
  "vno_id": "DTV",
  "olt_name": "OLT-SAN-001",
  "olt_vendor": "nokia",
  "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
  "old_ont_serial": "ALCLF1234567",
  "new_ont_serial": "ALCLF7654321",
  "callback_url": "https://servicenow.onnet.cl/api/komands/callback"
}
```

---

### POST /api/v1/fiber-modification — Cambio de pelo (puerto PON)

**Descripción:** Mueve servicio de un puerto PON a otro (solo GPON)

**Request body:**
```json
{
  "vno_id": "DTV",
  "olt_vendor": "nokia",
  "source_olt": "OLT-SAN-001",
  "source_shelf": 1, "source_card": 2, "source_port": 3,
  "source_logic_pon": 1, "source_ont_id": 45,
  "target_olt": "OLT-SAN-001",
  "target_shelf": 1, "target_card": 2, "target_port": 4,
  "target_logic_pon": 1,
  "callback_url": "https://servicenow.onnet.cl/api/komands/callback"
}
```

---

### POST /api/v1/modification — Modificación de servicio

**Sub-operaciones (campo `operation_type`):**
- `SPEED_CHANGE` — cambio de velocidad
- `BLOCK` — bloqueo de servicio
- `UNBLOCK` — desbloqueo
- `SERVICE_ADD` — alta de servicio adicional (ej: agregar IPTV)
- `SERVICE_REMOVE` — baja de servicio individual
- `FTTH_TO_SSAA` — migración de producto

**Request body (cambio de velocidad):**
```json
{
  "vno_id": "DTV",
  "operation_type": "SPEED_CHANGE",
  "olt_vendor": "nokia",
  "olt_name": "OLT-SAN-001",
  "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
  "new_speed_profile": "200M_50M",
  "callback_url": "https://servicenow.onnet.cl/api/komands/callback"
}
```

---

## CONSULTAS SÍNCRONAS (200 directo)

### GET /api/v1/access/{id} — Consulta de acceso

**Response:**
```json
HTTP 200
{
  "access_id": "ACC-12345",
  "status": "ACTIVE",
  "olt_name": "OLT-SAN-001",
  "ont_serial": "ALCLF1234567",
  "services": ["INTERNET", "VOIP"],
  "speed_profile": "100M_20M",
  "last_updated": "2026-04-13T15:30:00Z"
}
```

---

### POST /api/v1/query/pon-info — Info por posición PON

**Request:**
```json
{
  "olt_name": "OLT-SAN-001",
  "olt_vendor": "nokia",
  "shelf": 1, "card": 2, "port": 3, "logic_pon": 1
}
```

---

### GET /api/v1/port-occupancy — Ocupación de puerto PON

**Query params:** `olt_name`, `shelf`, `card`, `port`

**Response:**
```json
{
  "total_capacity": 128,
  "used": 87,
  "available": 41,
  "occupancy_pct": 68
}
```

---

### GET /api/v1/transaction/{uuid} — Estado de transacción

**Response:**
```json
{
  "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "COMPLETED",
  "created_at": "2026-04-13T15:30:00Z",
  "completed_at": "2026-04-13T15:30:45Z",
  "steps": [
    { "step": 1, "name": "create_ont", "status": "OK", "duration_ms": 850 },
    { "step": 2, "name": "configure_service_port", "status": "OK", "duration_ms": 1200 }
  ]
}
```

**Estados posibles:** PENDING, IN_PROGRESS, COMPLETED, FAILED, ROLLBACK, ROLLBACK_FAILED

---

## CONTRATO DE CALLBACK

Komands hace POST a `callback_url` al terminar cada operación asíncrona.

```json
{
  "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "COMPLETED",
  "operation": "activation",
  "vno_id": "DTV",
  "completed_at": "2026-04-13T15:30:45Z",
  "steps": [
    {
      "step": 1,
      "name": "create_ont",
      "status": "OK",
      "command": "configure equipment ont...",
      "response": "ONT created successfully",
      "duration_ms": 850
    }
  ]
}
```

**Callback con error y rollback:**
```json
{
  "txn_id": "...",
  "status": "ROLLBACK",
  "failed_step": 3,
  "error_code": "KMD-2003",
  "error_message": "Timeout ejecutando comando en OLT",
  "steps": [...]
}
```

**Política de reintentos callback:** 3 intentos, backoff exponencial (30s, 60s, 120s)

---

## CÓDIGOS DE ERROR HTTP
| Código | Significado |
|--------|-------------|
| 200 | OK (consultas síncronas) |
| 202 | Accepted (operaciones asíncronas encoladas) |
| 400 | Bad Request — payload malformado |
| 401 | Unauthorized — token inválido o ausente |
| 403 | Forbidden — VNO o scope no autorizado |
| 404 | Not Found — recurso no existe |
| 409 | Conflict — txn_id duplicado |
| 422 | Unprocessable Entity — campo obligatorio ausente o inválido |
| 429 | Too Many Requests — rate limit excedido |
| 500 | Internal Server Error |
| 503 | Service Unavailable — OLT inaccesible |

## CÓDIGOS DE ERROR INTERNOS (KMD-xxxx)
| Código | Descripción |
|--------|-------------|
| KMD-1001 | OLT no encontrada en inventario |
| KMD-1002 | ONT serial inválido o ya existe |
| KMD-1003 | Puerto PON no disponible |
| KMD-1004 | Perfil de velocidad no configurado para VNO |
| KMD-2001 | Error de conexión SSH a OLT |
| KMD-2002 | Autenticación SSH fallida |
| KMD-2003 | Timeout ejecutando comando CLI |
| KMD-2004 | Respuesta inesperada de OLT (parse error) |
| KMD-3001 | Rollback exitoso |
| KMD-3002 | Rollback fallido — intervención manual requerida |
| KMD-4001 | Feature flag desactivado para esta VNO |
| KMD-4002 | Rate limit excedido para VNO |

## RATE LIMITING
- Por VNO: configurable en Axway
- Respuesta 429:
```json
{
  "error": "KMD-4002",
  "message": "Rate limit excedido",
  "retry_after_seconds": 60
}
```
