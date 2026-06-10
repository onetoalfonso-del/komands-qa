# APIs REST de Komands — Contratos (AnexoH v2.2)

> Fuente de verdad: `AnexoH_Especificacion_APIs_v2_2_FINAL.docx`
> Última actualización: 2026-06-09

## Base URL
```
DEV:  http://localhost:8000/api/v1
QA:   https://komands-qa.internal/api/v1
PROD: https://komands.onnet.cl/api/v1  (vía Axway APIM)
```
> Nota ADR-008: el base path migrará a `/api/Komands/v1/` en una versión futura. Por ahora se usa `/api/v1/`.

---

## Autenticación

- **Tipo:** OAuth 2.0 client_credentials → JWT (Bearer token)
- **Header obligatorio:** `Authorization: Bearer <token>`
- Sin token válido → HTTP 401
- VNO no autorizada → HTTP 403
- Scope insuficiente → HTTP 403

### JWT claims requeridos
```json
{
  "sub": "servicenow-client",
  "vno_id": "DTV",
  "scope": "komands:write komands:read",
  "exp": 1714000000
}
```
> `vno_id` en el JWT es el identificador interno de autenticación (no cambia).
> En el body del request se usa `vno_code` (ver cada endpoint).

### VNOs autorizadas
| vno_code | VNO |
|---|---|
| `DTV` | DirecTV |
| `CVTR` | ClaroVTR |
| `ENTEL` | Entel |
| `TCH` | Movistar (TCH) |

---

## OPERACIONES ASÍNCRONAS

Todas responden `HTTP 202 Accepted` con:
```json
{
  "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "ACCEPTED"
}
```
El resultado final llega por **callback** (POST a ServiceNow).

---

### POST /api/v1/activation — Alta de servicio

**FTTH (Nokia y Huawei):**
```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-ACT-001",
  "service_type": "FTTH",
  "olt_name": "OLT-SAN-001",
  "slot": 1,
  "port": 3,
  "ont_id": 45,
  "serial_ont": "ALCLF1234567",
  "internet": true,
  "voip": true,
  "iptv": true,
  "speed_profile": "100M_20M"
}
```

**SSAA (grupos A/B/C/D/BX):**
```json
{
  "vno_code": "ENTEL",
  "external_order_id": "SO-ACT-003",
  "service_type": "SSAA",
  "olt_name": "OLT-SCL-010",
  "slot": 1,
  "port": 0,
  "ont_id": 5,
  "serial_ont": "ALCLF9999999",
  "services": [
    {"code": "A", "svlan": 100, "cvlan": 200},
    {"code": "C", "svlan": 100, "cvlan": 202}
  ],
  "speed_profile": "200M_200M"
}
```

**Campos obligatorios:** `vno_code`, `external_order_id`, `service_type`, `olt_name`, `slot`, `port`, `ont_id`, `serial_ont`

---

### POST /api/v1/unsuscription — Baja de acceso

> Renombrado desde `/deactivation` (ADR-008). También se usa para **cancelación de orden** (mismo endpoint, distinto `external_order_id`).

```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-BAJ-001",
  "olt_name": "OLT-SAN-001",
  "slot": 1,
  "port": 3,
  "ont_id": 45
}
```

**Variante TCH** (requiere limpieza de VLAN en la OLT):
```json
{
  "vno_code": "TCH",
  "external_order_id": "SO-BAJ-003",
  "olt_name": "OLT-SAN-001",
  "slot": 1,
  "port": 3,
  "ont_id": 45,
  "delete_vlan_on_terminate": true,
  "svlan": 300
}
```

**Casos especiales vía `external_order_id`:**
| Valor | Comportamiento |
|---|---|
| `"NO_PROVISION"` | Sin provisión activa → HTTP 200, `status: NO_ACTION` |
| `"IN_PROGRESS"` | Txn en curso → HTTP 409, `KMD-3003` |

---

### POST /api/v1/modification — Modificación de servicio

**Campo `modification_type` (valores en minúscula):**
| Valor | Descripción |
|---|---|
| `speed_change` | Cambio de perfil de velocidad |
| `block` | Bloqueo de servicio |
| `unblock` | Desbloqueo |
| `add_service` | Agregar servicio (ej: IPTV) |
| `remove_service` | Eliminar servicio individual |
| `migrate_ftth_ssaa` | Migración de producto |

**Cambio de velocidad:**
```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-MOD-001",
  "modification_type": "speed_change",
  "olt_name": "OLT-SAN-001",
  "slot": 1,
  "port": 3,
  "ont_id": 45,
  "new_speed_profile": "200M_50M"
}
```

**Bloqueo / desbloqueo:**
```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-MOD-002",
  "modification_type": "block",
  "olt_name": "OLT-SAN-001",
  "slot": 1,
  "port": 3,
  "ont_id": 45
}
```

**Agregar / quitar servicio:**
```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-MOD-007",
  "modification_type": "add_service",
  "olt_name": "OLT-SAN-001",
  "slot": 1,
  "port": 3,
  "ont_id": 45,
  "service_code": "IPTV"
}
```

---

### POST /api/v1/device-modification — Cambio de equipo (swap ONT)

Baja ONT anterior + alta ONT nueva con la misma configuración de servicios.

```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-ONT-001",
  "olt_name": "OLT-SAN-001",
  "slot": 1,
  "port": 3,
  "ont_id": 45,
  "new_serial_ont": "ALCLF7654321"
}
```

---

### POST /api/v1/reset-ont — Reset de ONT

Reinicia el ONT sin borrar la configuración. Operación más rápida de post-venta.

```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-RST-001",
  "olt_name": "OLT-SAN-001",
  "slot": 1,
  "port": 3,
  "ont_id": 45
}
```

---

### POST /api/v1/fiber-change — Cambio de fibra

Mueve el servicio de una OLT/puerto a otro. Soporta mismo vendor y cross-vendor.

```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-FIB-001",
  "current_olt_name": "OLT-SAN-001",
  "current_slot": 1,
  "current_port": 3,
  "current_ont_id": 45,
  "new_olt_name": "OLT-SAN-002",
  "new_slot": 1,
  "new_port": 4,
  "new_ont_id": 45,
  "serial_ont": "ALCLF1234567"
}
```

---

### POST /api/v1/fiber-modification — Cambio de pelo (puerto PON)

Mueve el servicio a otro puerto PON dentro de la misma OLT. Solo GPON.

```json
{
  "vno_code": "DTV",
  "external_order_id": "SO-FIBM-001",
  "olt_name": "OLT-SAN-001",
  "current_slot": 1,
  "current_port": 3,
  "current_ont_id": 45,
  "new_slot": 1,
  "new_port": 4
}
```

---

## CONSULTAS SÍNCRONAS

Responden `HTTP 200` directamente, sin callback.

### GET /api/v1/access/{access_id} — Estado de acceso

```
GET /api/v1/access/ACC-12345
```
```json
{
  "access_id": "ACC-12345",
  "status": "ACTIVE",
  "olt_name": "OLT-SAN-001",
  "serial_ont": "ALCLF1234567",
  "services": ["INTERNET", "VOIP"],
  "speed_profile": "100M_20M",
  "last_updated": "2026-04-13T15:30:00Z"
}
```

---

### GET /api/v1/port-occupancy — Ocupación de puerto PON

```
GET /api/v1/port-occupancy?olt_name=OLT-SAN-001&slot=1&port=3
```
```json
{
  "total_capacity": 128,
  "used": 87,
  "available": 41,
  "occupancy_pct": 68
}
```

---

### GET /api/v1/transaction/{txn_id}/status — Estado de transacción

```
GET /api/v1/transaction/3fa85f64-5717-4562-b3fc-2c963f66afa6/status
```
```json
{
  "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "COMPLETED",
  "created_at": "2026-04-13T15:30:00Z",
  "completed_at": "2026-04-13T15:30:45Z",
  "steps": [
    {"step": 1, "name": "create_ont", "status": "OK", "duration_ms": 850},
    {"step": 2, "name": "configure_service_port", "status": "OK", "duration_ms": 1200}
  ]
}
```

**Estados posibles:** `ACCEPTED` → `IN_PROGRESS` → `COMPLETED` / `FAILED` / `ROLLED_BACK` / `ROLLBACK_FAILED`

---

## CONTRATO DE CALLBACK

Komands hace POST al endpoint de ServiceNow al finalizar cada operación asíncrona.

**Operación exitosa:**
```json
{
  "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "correlation_id": "corr-sn-001",
  "external_order_id": "SO-ACT-001",
  "status": "COMPLETED",
  "operation": "activation",
  "vno_code": "DTV",
  "olt_name": "OLT-SAN-001",
  "started_at": "2026-04-13T15:30:00Z",
  "completed_at": "2026-04-13T15:30:45Z",
  "duration_ms": 1250,
  "steps": [
    {"step": 1, "name": "create_ont", "status": "OK", "duration_ms": 850},
    {"step": 2, "name": "configure_service_port", "status": "OK", "duration_ms": 1200}
  ]
}
```

**Operación con rollback:**
```json
{
  "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "ROLLED_BACK",
  "operation": "unsuscription",
  "vno_code": "DTV",
  "error": {
    "code": "KMD-5020",
    "category": "CLI_ERROR",
    "message": "Timeout esperando respuesta de la OLT",
    "retryable": true
  }
}
```

**Política de reintentos:** 3 intentos con backoff exponencial (30s, 60s, 120s).

---

## CÓDIGOS DE ERROR HTTP

| Código | Significado |
|---|---|
| 200 | OK (consultas síncronas / idempotencia) |
| 202 | Accepted (operación encolada) |
| 400 | Bad Request — payload malformado |
| 401 | Unauthorized — token inválido o ausente |
| 403 | Forbidden — VNO, rol o scope no autorizado |
| 404 | Not Found — recurso no existe |
| 409 | Conflict — transacción en curso (KMD-3003) |
| 422 | Unprocessable Entity — campo obligatorio ausente |
| 429 | Too Many Requests — rate limit excedido |
| 500 | Internal Server Error |
| 503 | Service Unavailable — OLT inaccesible |

## CÓDIGOS DE ERROR INTERNOS (KMD-xxxx) — AnexoH v2.2 Tabla 80

| Código | Descripción |
|---|---|
| `KMD-2002` | ONT no encontrado en la OLT |
| `KMD-3001` | Conflicto — ONT ocupado o VLAN en uso |
| `KMD-3003` | Transacción en progreso para este acceso |
| `KMD-4001` | Operación no soportada / Feature flag desactivado → usar BluePlanet |
| `KMD-5020` | Timeout CLI — OLT no respondió (retryable) |
| `KMD-5021` | Timeout en paso crítico — rollback ejecutado |

---

## RATE LIMITING

Por VNO, configurable en Axway APIM. Respuesta 429:
```json
{
  "error": "KMD-4002",
  "message": "Rate limit excedido",
  "retry_after_seconds": 60
}
```
