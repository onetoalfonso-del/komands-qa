# PROYECTO: Komands QA — Contexto para Claude Code

## Instrucción para Claude Code
Antes de cualquier tarea de este proyecto, lee los siguientes archivos en orden:
1. `docs/01_resumen_proyecto.md` — qué es el proyecto, VNOs, productos, glosario
2. `docs/02_arquitectura.md` — stack, microservicios, flujos, Nokia vs Huawei
3. `docs/03_apis_contratos.md` — 9 endpoints, contratos JSON, callbacks, errores
4. `docs/04_modelo_datos.md` — 33 tablas PostgreSQL, schemas, RBAC
5. `docs/05_gaps_seguridad.md` — gaps AS-IS vs TO-BE, casos de prueba de seguridad

## Propósito de este repositorio
Suite de pruebas automatizadas para la plataforma **Komands** del proyecto **Sunset BluePlanet**.
Komands reemplaza BluePlanet (Ciena) como plataforma de ejecución de comandos CLI hacia OLTs de fibra óptica.

## Stack de pruebas
- Python 3.11+
- pytest + pytest-asyncio
- httpx (cliente HTTP async para tests de API)
- unittest.mock (mocks de SSH/Netmiko y OLTs)
- FastAPI TestClient (para tests sin servidor real)

## Estructura del proyecto de tests
```
komands-qa/
├── PROJECT_CONTEXT.md          ← este archivo
├── docs/                       ← contexto del proyecto
├── requirements.txt            ← dependencias
├── pytest.ini                  ← configuración pytest
├── tests/
│   ├── conftest.py             ← fixtures compartidos
│   ├── mocks/
│   │   ├── nokia_responses.py  ← respuestas SSH falsas Nokia
│   │   ├── huawei_responses.py ← respuestas SSH falsas Huawei
│   │   └── payloads.py         ← payloads JSON de ejemplo
│   ├── unit/
│   │   └── test_command_builder.py
│   ├── api/
│   │   ├── test_activation.py
│   │   ├── test_deactivation.py
│   │   ├── test_modification.py
│   │   ├── test_device_modification.py
│   │   ├── test_fiber_modification.py
│   │   └── test_queries.py
│   ├── parity/
│   │   ├── test_nokia_parity.py
│   │   └── test_huawei_parity.py
│   └── security/
│       ├── test_auth.py
│       ├── test_rbac.py
│       └── test_feature_flags.py
```

## Principio más importante del proyecto
**Paridad funcional**: Komands debe producir exactamente los mismos resultados
que BluePlanet. Los tests de paridad son la prioridad #1.

## Convenciones de nomenclatura en tests
- `test_<operacion>_<vendor>_<producto>_<escenario>`
- Ejemplo: `test_activation_nokia_ftth_valid_payload`
- Ejemplo: `test_activation_huawei_ssaa_group_a_rollback_step2`

## Vendors soportados
- `nokia` → Nokia ISAM 7360 FX (Rel. 6.2) — device_type Netmiko: "nokia_sros"
- `huawei` → Huawei MA5800 / MA5600T — device_type Netmiko: "huawei_vrp"

## Productos soportados
- `FTTH` — residencial (INTERNET, VOIP, IPTV)
- `SSAA` — empresas B2B (grupos A, B, C, D, E, BX, DX)
