# Komands QA — Suite de Pruebas Automatizadas

Suite de pruebas automatizadas para **Komands**, el sistema de provisioning de fibra óptica FTTH que reemplaza a BluePlanet/Ciena en la red de **ON·NET Fibra Chile**.

> Proyecto: Sunset BluePlanet → Komands | Cliente: ON·NET Fibra | Proveedor: MOS-IT | Sprint 01 — Seguridad

---

## Contexto del proyecto

ON·NET Fibra opera ~618 OLTs y ~2 millones de clientes a través de 4 operadores (VNOs). BluePlanet fallaba constantemente en la activación de fibra óptica. Komands es el reemplazo: una API asíncrona que recibe órdenes de ServiceNow, ejecuta comandos SSH en las OLTs Nokia e Huawei, y notifica el resultado por callback.

```
ServiceNow ──► Axway APIM ──► Komands API ──► OLT Nokia/Huawei
                                   │
                              PostgreSQL 15
                                   │
                    Callback ──► Axway ──► ServiceNow
```

### VNOs soportados

| VNO | Código | Nombre comercial | Tecnología |
|-----|--------|-----------------|-----------|
| DTV | `DTV` | DirecTV | FTTH + SSAA |
| CVTR | `CVTR` | ClaroVTR | FTTH |
| ENTEL | `ENTEL` | Entel | FTTH + SSAA |
| TCH | `TCH` | Telefónica / Movistar | FTTH |

### OLTs soportadas

| Vendor | Modelo | device_type |
|--------|--------|-------------|
| Nokia | ISAM 7360 FX Rel. 6.2 | `nokia_sros` |
| Huawei | MA5800 (V100R020) | `huawei_vrp` |
| Huawei | MA5600T (V800R018) | `huawei_vrp` |

---

## Endpoints de la API (AnexoH v2.2)

### Operaciones asíncronas — ACK HTTP 202 + SSH + Callback

| Endpoint | Operación | SLO P95 |
|----------|-----------|---------|
| `POST /api/Komands/v1/activation` | Alta de acceso FTTH/SSAA | <60s / <180s |
| `POST /api/Komands/v1/unsuscription` | Baja de acceso + Cancelación de orden | <60s |
| `POST /api/Komands/v1/modification` | Cambio velocidad / bloqueo / desbloqueo | <60s |
| `POST /api/Komands/v1/device-modification` | Swap de ONT (cambio de equipo) | <60s |
| `POST /api/Komands/v1/fiber-change` | Cambio de fibra (cross-vendor) | <60s |
| `POST /api/Komands/v1/reset-ont` | Reset de ONT | <15s |

### Operaciones síncronas — HTTP 200 directo

| Endpoint | Operación | SLO |
|----------|-----------|-----|
| `GET /api/Komands/v1/access/{id}` | Estado de ONT por acceso | <10s |
| `GET /api/Komands/v1/port-occupancy` | Ocupación del puerto PON | <10s |
| `GET /api/Komands/v1/transaction/{uuid}/status` | Estado de transacción | <500ms |

> **ADR-008 (Abril 2026):** `/deactivation` fue renombrado a `/unsuscription`. `/reset` fue renombrado a `/reset-ont`. Base path: `/api/Komands/v1/`.

---

## Estructura del proyecto

```
Kommand/
├── komands/                        # Módulo bajo prueba
│   ├── __init__.py
│   └── command_builder.py          # Builder de comandos CLI Nokia/Huawei
│
├── tests/
│   ├── conftest.py                 # Fixtures: test_client, tokens, ff_client
│   ├── mocks/
│   │   ├── payloads.py             # Payloads de prueba + centinelas mock
│   │   ├── nokia_responses.py      # Respuestas SSH simuladas Nokia
│   │   └── huawei_responses.py     # Respuestas SSH simuladas Huawei
│   │
│   ├── api/                        # Tests de integración (Release 1 — Post-Venta)
│   │   ├── test_activation.py      # REG-ACT — activación FTTH/SSAA
│   │   ├── test_deactivation.py    # PV-BAJ — baja de acceso (33 casos)
│   │   ├── test_modification.py    # PV-MOD — modificación (33 casos)
│   │   ├── test_device_modification.py  # PV-ONT — swap ONT (22 casos)
│   │   ├── test_reset_ont.py       # PV-RST — reset ONT (22 casos)
│   │   ├── test_cancel_order.py    # PV-CAN — cancelación de orden (33 casos)
│   │   ├── test_callbacks.py       # PV-CBK — callbacks + reintentos (5 casos)
│   │   ├── test_rollback.py        # PV-RBK — rollback automático (4 casos)
│   │   ├── test_queries.py         # PV-QRY — consultas síncronas (6 casos)
│   │   ├── test_feature_flags_postventa.py  # PV-FLG + PV-IDP (4 casos)
│   │   ├── test_database.py        # PV-DB — integridad PostgreSQL (4 casos, skip)
│   │   ├── test_performance.py     # PV-PER — rendimiento bajo carga (4 casos, skip)
│   │   ├── test_par_provision.py   # PV-PAR — paridad Komands≡BluePlanet (33 casos, skip)
│   │   ├── test_fiber_modification.py
│   │   ├── test_fiber_change.py
│   │   └── test_idempotency.py
│   │
│   ├── security/
│   │   ├── test_auth.py            # PV-SEC — JWT, scopes, rate limit (6 casos)
│   │   ├── test_rbac.py            # RBAC 4 roles × endpoints
│   │   └── test_feature_flags.py   # Feature Flags por VNO × producto
│   │
│   ├── unit/
│   │   └── test_command_builder.py # 60 tests unitarios CommandBuilder
│   │
│   └── parity/
│       ├── test_nokia_parity.py    # Paridad CLI Nokia vs referencia
│       └── test_huawei_parity.py   # Paridad CLI Huawei vs referencia
│
├── docs/
│   ├── 01_resumen_proyecto.md      # VNOs, productos, glosario
│   ├── 02_arquitectura.md          # Stack, microservicios, Nokia vs Huawei
│   ├── 03_apis_contratos.md        # Contratos JSON (versión anterior)
│   ├── 04_modelo_datos.md          # 33 tablas PostgreSQL, schemas, RBAC
│   └── 05_gaps_seguridad.md        # Gaps AS-IS/TO-BE, casos de prueba
│
├── check_coverage.py               # Verifica cobertura Excel vs tests (PV-XXX-NNN)
├── count_cases.py                  # Cuenta casos por módulo del Excel
└── PROJECT_CONTEXT.md              # Contexto técnico del proyecto
```

---

## Estado de cobertura

```
MÓDULO    Excel  Con test  Cobertura
────────────────────────────────────
PV-BAJ      33        33     100%   Baja de acceso
PV-CAN      33        33     100%   Cancelación de orden
PV-MOD      33        33     100%   Modificación
PV-ONT      22        22     100%   Swap de ONT
PV-RST      22        22     100%   Reset ONT
PV-CBK       5         5     100%   Callbacks
PV-RBK       4         4     100%   Rollback automático
PV-QRY       6         6     100%   Consultas síncronas
PV-FLG       3         3     100%   Feature Flags
PV-IDP       1         1     100%   Idempotencia
PV-DB        4         4     100%   PostgreSQL (skip: requiere BD)
PV-PER       4         4     100%   Rendimiento (skip: requiere k6)
PV-SEC       6         6     100%   Seguridad JWT
PV-PAR      33        33     100%   Paridad BluePlanet (skip: requiere OLTs)
────────────────────────────────────
TOTAL      209       209     100%

Suite: 351 passed, 44 skipped — 3.3s
```

Los 44 tests `skip` están identificados con sus IDs de caso y se activarán cuando el ambiente correspondiente esté disponible (PostgreSQL DEV, OLTs físicas en QA, herramienta k6).

---

## Cómo ejecutar

### Requisitos

```bash
python -m pip install -r requirements.txt
```

### Todos los tests (modo mock — sin servidor real)

```bash
python -m pytest tests/ -v
```

### Solo un módulo

```bash
python -m pytest tests/api/test_deactivation.py -v
python -m pytest tests/security/ -v
python -m pytest tests/unit/ -v
```

### Por tipo de test

```bash
# Solo tests que requieren mock del servidor (no OLTs reales)
python -m pytest tests/ -m mock_only -v

# Solo tests de post-venta
python -m pytest tests/ -m postventa -v

# Excluir tests bloqueados por infraestructura
python -m pytest tests/ -m "not skip" -v
```

### Verificar cobertura del Plan de Pruebas Excel

```bash
python check_coverage.py
```

Compara los IDs `PV-XXX-NNN` presentes en los archivos de test contra los casos del Excel `Plan_Pruebas_Completo_v4_Final.xlsx`.

### Reporte HTML

```bash
python -m pytest tests/ --cov=komands --cov-report=html
# Abre reporte.html en el browser
```

---

## Arquitectura de tests

### Tipos de test

| Marcador | Descripción | Requiere |
|----------|-------------|---------|
| `🟢 FIXTURE` | Sin servidor — solo fixtures Python | Nada |
| `🔵 MOCK` | Servidor DEV + SSH mockeado | `MOCK_OLT=1` |
| `🟡 BD DEV` | PostgreSQL DEV con schema Komands | PostgreSQL desplegado |
| `🔴 OLT REAL` | OLTs físicas en QA | Ambiente QA completo |

### Centinelas del mock (valores especiales de ont_id)

| Valor | Comportamiento simulado | Error code |
|-------|------------------------|-----------|
| `ont_id=8888` | ONT no encontrado en la OLT | `KMD-2002` |
| `ont_id=7777` | Timeout SSH al conectar a la OLT | `KMD-5020` |
| `ont_id=6666` | ONT offline (no responde) | `KMD-2003` |
| `new_serial_ont="FAIL00000000"` | Alta del ONT nuevo falla → ROLLED_BACK | `KMD-5021` |

### Convención de IDs de caso

Todos los tests tienen comentarios `# PV-XXX-NNN` que los vinculan al Excel:

```python
# PV-BAJ-182 | PV-BAJ-191
def test_baj01_nokia_ftth_dtv_devuelve_202(self, test_client, auth_headers):
    ...
```

`check_coverage.py` escanea estos comentarios con el patrón `PV-([A-Z]+)-(\d+)` para calcular cobertura.

---

## Seguridad y autenticación

- **OAuth 2.0 client_credentials + JWT RS256** firmado por Axway APIM
- **RBAC:** 4 roles — `ADMIN`, `OPERATOR`, `VIEWER`, `AUDITOR`
- **Scopes JWT:** `komands:provision` (operaciones de red) | `komands:query` (consultas)
- **Rate limiting:** 20.000 tx/h global | 5.000 tx/h por VNO
- **Idempotencia:** campo `X-Correlation-ID` — duplicado retorna HTTP 200 con UUID existente

---

## Ambientes

| Ambiente | URL | Disponibilidad |
|----------|-----|----------------|
| DEV | `https://edevapi.onnetfibra.cl/komands` | Semana 3 |
| QA | `https://eqapi.onnetfibra.cl/komands` | Semana 10 |
| PROD | `https://api.onnetfibra.cl/komands` | Semana 26 |

---

## Códigos de error KMD

| Código | Descripción |
|--------|-------------|
| `KMD-2002` | Recurso no encontrado (ONT, acceso, etc.) |
| `KMD-2003` | ONT offline — no responde |
| `KMD-3001` | Conflicto VLAN — ya en uso en el puerto PON |
| `KMD-3002` | Serial ONT duplicado en otra OLT |
| `KMD-3003` | Transacción en progreso — conflicto de concurrencia |
| `KMD-4001` | Operación no soportada (ej: remove_service Nokia) |
| `KMD-5020` | Timeout SSH al conectar a la OLT |
| `KMD-5021` | Error en paso crítico — rollback ejecutado (ROLLED_BACK) |
| `KMD-5030` | Rollback fallido — OLT en estado inconsistente (ROLLBACK_FAILED) |

---

## Riesgos críticos del plan

| ID | Riesgo | Impacto |
|----|--------|---------|
| R-01 | INDEX dinámico Huawei `_resolve_dynamic_ids` falla | Crítico |
| R-02 | DeviceModification asimétrico (baja OK, alta falla) | Crítico |
| R-03 | ROLLBACK_FAILED deja OLT inconsistente | Crítico |
| R-04 | CALLBACK_FAILED sin reconciliación ServiceNow | Alto |
| R-05 | Feature Flag conmutado con transacciones IN_PROGRESS | Alto |

---

## Criterios de salida (Go-Live)

- 100% casos de prioridad Alta en PASS
- < 5% casos Medios en FAIL (todos con bug report)
- 0 defectos P1/P2 abiertos sin plan de mitigación
- SLOs P95 cumplidos en QA bajo carga (k6)
- Feature Flag: conmutación BP → Komands + rollback en < 5 minutos
- Suite de regresión Release 0 en 0 FAIL

---

## Documentación de referencia

| Documento | Descripción |
|-----------|-------------|
| `AnexoH_Especificacion_APIs_v2_2_FINAL.docx` | OpenAPI 3.0 — contratos JSON definitivos |
| `AnexoG_Modelo_Datos_v2_2_FINAL.docx` | DDL SQL — 33 tablas PostgreSQL |
| `LLD_Sunset_BP_v2_2_FINAL.docx` | LLD completo — ADRs, flujos SN, Feature Flags |
| `Plan_Pruebas_PostVenta_v1_regresion.docx` | Plan de pruebas Release 1 |
| `plan_trabajo_qa_sunset_blueplanet_1.docx` | Plan QA formal v1.0 |

> Los `.docx` residen en SharePoint y no están incluidos en el repositorio.

---

## Equipo

- **Cliente:** ON·NET Fibra Chile
- **QA Lead / Automatización:** MOS-IT
- **Rama activa:** `qa/sprint-01-security`
- **Branch principal:** `main`
