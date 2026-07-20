#!/usr/bin/env python3
"""
KOMANDs QA Test Runner
Servidor web local para ejecutar el plan de pruebas desde el navegador.

Uso:  python test_runner.py
URL:  http://localhost:8001

Prerequisito: pip install fastapi "uvicorn[standard]"
"""

import asyncio
import json
import os
import queue as _queue
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT      = Path(__file__).parent
COLL_DIR  = ROOT / "collection Kommand"
BP_DIR    = ROOT / "collection Blueplanet"
QA_DIR    = ROOT / "collection QA"
QA_VNO_ENV_MAP = {
    "00": "00-TCH QA.postman_environment.json",
    "02": "02 QA_KAO.postman_environment.json",
    "03": "03-B1_vnoid03 QA.postman_environment.json",
    "05": "05 QA_DTV.postman_environment.json",
}
QA_FACTIBILIDAD_FOLDER_MAP = {
    "00": "feasibility-TCH DIR",
    "02": "feasibility-KAO",
    "03": "feasibility-Entel",
    "05": "feasibility-DTV",
}
QA_ASSIGNMENT_FOLDER_MAP = {
    "00": "assigment-TCH",
    "02": "assigment- KAO",
    "03": "assigment-Entel",
    "05": "assigment-DTV",
}
QA_IA_VNO_SUBFOLDER = {
    "00": "TCH",
    "02": "KAO",
    "03": "ENTEL",
    "05": "DTV",
}

PY     = sys.executable
NEWMAN = shutil.which("newman") or "newman"

# ─── Suites ──────────────────────────────────────────────────────────────────
SUITES = [
    {
        "id": "t1", "group": "hidden",
        "label": "T1 — Spec API + Regresión",
        "desc":  "675 casos pytest",
        "note":  [
            "================================================================",
            "  T1 - Especificacion API + Regresion completa",
            "  Cubre: activacion, baja, modificacion, fiber-change, rollback,",
            "         idempotencia, callbacks (contrato), seguridad headers.",
            "  Entorno: mock en memoria (TestClient FastAPI) - sin OLTs reales.",
            "  Excluidos: test_database.py (T5), test_performance.py (T8),",
            "             test_par_provision.py (T6 - paridad Komands/BluePlanet),",
            "             test_auth_infra.py (T4/T5/T7 - requiere infra real).",
            "================================================================",
        ],
        "cmd":   [PY, "-u", "-m", "pytest", "tests/", "-v", "--tb=short",
                  "--color=no", "--no-header", "-q",
                  "--ignore=tests/integration",
                  "--ignore=tests/contract",
                  "--ignore=tests/api/test_database.py",
                  "--ignore=tests/api/test_par_provision.py",
                  "--ignore=tests/api/test_performance.py",
                  "--ignore=tests/security/test_auth_infra.py",
                  "--html=reporte_t1.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_t1.html"), "requires": None,
        "vno_support": True,
    },
    {
        "id": "t1-contract", "group": "hidden",
        "label": "T1-C — Contrato OpenAPI (Schemathesis)",
        "desc":  "docs/openapi.json v2.2.3 · genera casos automáticos · mock",
        "note":  [
            "================================================================",
            "  T1-C - Contrato OpenAPI con Schemathesis (property-based)",
            "  Genera casos automaticos desde openapi.json v2.2.3.",
            "  Verifica que el mock responde conforme al esquema definido.",
            "  max_examples=15 por endpoint (ajustable, mas = mas lento).",
            "  Entorno: mock en memoria - NO prueba el servidor :9016 real.",
            "================================================================",
        ],
        "cmd":   [PY, "-u", "-m", "pytest", "tests/contract/", "-v", "--tb=short",
                  "--color=no", "--no-header",
                  "--html=reporte_t1c.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_t1c.html"), "requires": None,
    },
    {
        "id": "t1c-real", "group": "hidden",
        "label": "T1-C — Contrato OpenAPI (Real)",
        "desc":  "Schemathesis → onf-komands.cl:9016 · servidor real",
        "note":  [
            "================================================================",
            "  T1-C Real - Schemathesis contra servidor REAL :9016",
            "  Genera casos automaticos desde openapi.json v2.2.3 y los",
            "  ejecuta contra onf-komands.cl:9016 (DEV/QA).",
            "  Auth: token HS256 de prueba (puede retornar 401).",
            "  Valida: nunca 5xx, Content-Type JSON, codigos documentados.",
            "  Codigos permitidos: 200 202 400 401 403 404 409 422.",
            "  Requiere conexion activa a onf-komands.cl:9016.",
            "================================================================",
        ],
        "cmd":   [PY, "-u", "-m", "pytest", "tests/contract/", "-v", "--tb=short",
                  "--color=no", "--no-header",
                  "--html=reporte_t1c_real.html", "--self-contained-html"],
        "cwd":   str(ROOT),
        "report": str(ROOT / "reporte_t1c_real.html"),
        "requires": None,
        "env_extra": {
            "KOMANDS_TEST_URL":      os.environ.get("DEV_BASE_URL", "https://onf-komands.cl:9016"),
            "KOMANDS_CLIENT_ID":     os.environ.get("DEV_CLIENT_ID", ""),
            "KOMANDS_CLIENT_SECRET": os.environ.get("DEV_CLIENT_SECRET", ""),
        },
    },
    {
        "id": "t2", "group": "hidden",
        "label": "T2 — Comandos CLI",
        "desc":  "Nokia/Huawei · comandos CLI",
        "note":  [
            "================================================================",
            "  T2 - Validacion de comandos CLI Nokia / Huawei",
            "  Valida que Komands genera los comandos CLI correctos por vendor",
            "  y VNO para activacion, baja, modificacion y post-venta.",
            "  Entorno: mock en memoria (TestClient FastAPI).",
            "  Excluidos: test_par_provision.py (T6), test_performance.py (T8),",
            "             test_auth_infra.py (T4/T5/T7 - requiere infra real).",
            "================================================================",
        ],
        "cmd":   [PY, "-u", "-m", "pytest", "tests/api/", "tests/unit/", "-v", "--tb=short",
                  "--color=no", "--no-header",
                  "--ignore=tests/api/test_database.py",
                  "--ignore=tests/api/test_par_provision.py",
                  "--ignore=tests/api/test_performance.py",
                  "--ignore=tests/security/test_auth_infra.py",
                  "--html=reporte_t2.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_t2.html"), "requires": None,
        "vno_support": True,
    },
    {
        "id": "t3", "group": "hidden",
        "label": "T3 — Respuesta OLT",
        "desc":  "Parseo Nokia + INDEX Huawei",
        "note":  [
            "================================================================",
            "  T3 - Parseo de respuestas OLT + contrato de callbacks",
            "  test_operation_status.py: valida el parseo de respuestas CLI",
            "    que retornarian Nokia (display ont) y Huawei (display board).",
            "  test_callbacks.py: valida el contrato del payload JSON que",
            "    Komands enviaria a ServiceNow (campos, tipos, estructura).",
            "  IMPORTANTE: ambos archivos usan mocks - sin OLTs reales.",
            "  Entrega real de callbacks = T4 (bloqueado, requiere lab OLT).",
            "================================================================",
        ],
        "cmd":   [PY, "-u", "-m", "pytest",
                  "tests/api/test_operation_status.py",
                  "tests/api/test_callbacks.py",
                  "-v", "--tb=short",
                  "--color=no", "--no-header",
                  "--html=reporte_t3.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_t3.html"), "requires": None,
    },
    {
        "id": "newman-dev", "group": "hidden",
        "label": "Endpoints Kommand Dev",
        "desc":  "Contrato API real · onf-komands.cl:9016",
        "note":  [
            "================================================================",
            "  Endpoints Kommand Dev - Coleccion Postman vs servidor REAL",
            "  Ejecuta requests reales contra onf-komands.cl:9016 (DEV/QA).",
            "  Verifica estructura de respuesta, status codes y campos JSON.",
            "  NOTA: :9016 es el servidor DEV/QA de Komands (mockup funcional,",
            "    no requiere OLTs fisicas). Requiere conexion activa a :9016.",
            "================================================================",
        ],
        "cmd":   [NEWMAN, "run",
                  "KOMANDs API v2.2.3.postman_collection.json",
                  "-e", "newman-environment-dev.json",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export",  "reporte_funcional.html",
                  "--reporter-htmlextra-template", "reporte-template-es.hbs"],
        "cwd":   str(COLL_DIR),
        "report": str(COLL_DIR / "reporte_funcional.html"),
        "requires": None,
        "olt_config": {
            "positions": [
                {"olt": "NCOR_OLT_3", "vendor": "Nokia",  "slot": "1", "pon": "1", "ontid": "3", "vno": "DTV",   "serial": "TEST:AONETO"},
                {"olt": "NCOR_OLT_1", "vendor": "Huawei", "slot": "7", "pon": "6", "ontid": "2", "vno": "DTV",   "serial": "TEST:AONETO"},
            ],
            "active": 1,
        },
    },
    {
        "id": "apim-vno03", "group": "hidden",
        "label": "Endpoints SN — VNO-03 Entel",
        "desc":  "APIM PRE VNO-03 Entel · auto-token",
        "cmd":   [NEWMAN, "run",
                  "Komands — APIM PRE VNOs 02-03 Claro-Entel (Auto-Token).postman_collection.json",
                  "-e", "VnoB1_vnoid03 PRE.postman_environment.json",
                  "--env-var", "accessId=03-TESTPREPROD-DIR02873675-8",
                  "--env-var", "serial=SCOM13032001",
                  "--env-var", "speedPlan=940/940",
                  "--env-var", "addressId=DIR02873675",
                  "--env-var", "addressMcd=OSP",
                  "--env-var", "serviceType=FTTH",
                  "--env-var", "run_phase=all",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_apim_vno03.html"],
        "cwd":   str(BP_DIR),
        "report": str(BP_DIR / "reporte_apim_vno03.html"),
        "requires": str(BP_DIR / "VnoB1_vnoid03 PRE.postman_environment.json"),
        "params": [
            {"key": "accessId",   "label": "Access ID",     "default": "03-TESTPREPROD-DIR02873675-8"},
            {"key": "serial",     "label": "Serial ONT",    "default": "SCOM13032001"},
            {"key": "speedPlan",  "label": "Speed Plan",    "default": "940/940"},
            {"key": "addressId",  "label": "Address ID",    "default": "DIR02873675"},
            {"key": "addressMcd", "label": "Address MCD",   "default": "OSP"},
            {"key": "serviceType","label": "Tipo Servicio", "default": "FTTH"},
        ],
    },
    {
        "id": "apim-vno02", "group": "hidden",
        "label": "Endpoints SN — VNO-02 ClaroVTR",
        "desc":  "APIM PRE VNO-02 ClaroVTR · auto-token",
        "cmd":   [NEWMAN, "run",
                  "Komands — APIM PRE VNOs 02-03 Claro-Entel (Auto-Token).postman_collection.json",
                  "-e", "VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json",
                  "--env-var", "accessId=02-TESTPREPROD-DIR02803674-2",
                  "--env-var", "serial=SCOM13022002",
                  "--env-var", "speedPlan=600/600",
                  "--env-var", "addressId=DIR02803638",
                  "--env-var", "addressMcd=OSP",
                  "--env-var", "serviceType=FTTH",
                  "--env-var", "run_phase=all",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_apim_vno02.html"],
        "cwd":   str(BP_DIR),
        "report": str(BP_DIR / "reporte_apim_vno02.html"),
        "requires": str(BP_DIR / "VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json"),
        "params": [
            {"key": "accessId",   "label": "Access ID",     "default": "02-TESTPREPROD-DIR02803674-2"},
            {"key": "serial",     "label": "Serial ONT",    "default": "SCOM13022002"},
            {"key": "speedPlan",  "label": "Speed Plan",    "default": "600/600"},
            {"key": "addressId",  "label": "Address ID",    "default": "DIR02803638"},
            {"key": "addressMcd", "label": "Address MCD",   "default": "OSP"},
            {"key": "serviceType","label": "Tipo Servicio", "default": "FTTH"},
        ],
    },
    {
        "id": "apim-vno05", "group": "hidden",
        "label": "Endpoints SN — VNO-05 DTV",
        "desc":  "APIM PRE VNO-05 DTV · auto-token",
        "cmd":   [NEWMAN, "run",
                  "Komands — APIM PRE VNOs 02-03 Claro-Entel (Auto-Token).postman_collection.json",
                  "-e", "VnoB1_vnoid05 PRE.postman_environment.json",
                  "--env-var", "accessId=05-TESTPREPROD-",
                  "--env-var", "serial=",
                  "--env-var", "speedPlan=",
                  "--env-var", "addressId=",
                  "--env-var", "addressMcd=OSP",
                  "--env-var", "serviceType=FTTH",
                  "--env-var", "run_phase=all",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_apim_vno05.html"],
        "cwd":   str(BP_DIR),
        "report": str(BP_DIR / "reporte_apim_vno05.html"),
        "requires": str(BP_DIR / "VnoB1_vnoid05 PRE.postman_environment.json"),
        "params": [
            {"key": "accessId",   "label": "Access ID",     "default": "05-TESTPREPROD-"},
            {"key": "serial",     "label": "Serial ONT",    "default": ""},
            {"key": "speedPlan",  "label": "Speed Plan",    "default": ""},
            {"key": "addressId",  "label": "Address ID",    "default": ""},
            {"key": "addressMcd", "label": "Address MCD",   "default": "OSP"},
            {"key": "serviceType","label": "Tipo Servicio", "default": "FTTH"},
        ],
    },
    {
        "id": "apim-vno00", "group": "hidden",
        "label": "Endpoints SN — VNO-00 TCH",
        "desc":  "APIM PRE VNO-00 TCH · auto-token",
        "cmd":   [NEWMAN, "run",
                  "Komands — APIM PRE VNOs 02-03 Claro-Entel (Auto-Token).postman_collection.json",
                  "-e", "VnoB1_vnoid00 PRE.postman_environment.json",
                  "--env-var", "accessId=00-TESTPREPROD-",
                  "--env-var", "serial=",
                  "--env-var", "speedPlan=",
                  "--env-var", "addressId=",
                  "--env-var", "addressMcd=OSP",
                  "--env-var", "serviceType=FTTH",
                  "--env-var", "run_phase=all",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_apim_vno00.html"],
        "cwd":   str(BP_DIR),
        "report": str(BP_DIR / "reporte_apim_vno00.html"),
        "requires": str(BP_DIR / "VnoB1_vnoid00 PRE.postman_environment.json"),
        "params": [
            {"key": "accessId",   "label": "Access ID",     "default": "00-TESTPREPROD-"},
            {"key": "serial",     "label": "Serial ONT",    "default": ""},
            {"key": "speedPlan",  "label": "Speed Plan",    "default": ""},
            {"key": "addressId",  "label": "Address ID",    "default": ""},
            {"key": "addressMcd", "label": "Address MCD",   "default": "OSP"},
            {"key": "serviceType","label": "Tipo Servicio", "default": "FTTH"},
        ],
    },
    {
        "id": "apim-parallel", "group": "hidden",
        "label": "Endpoints Services Now",
        "desc":  "VNO-02 ClaroVTR · VNO-03 Entel · VNO-05 DTV · VNO-00 TCH · elige uno o varios",
        "note":  [
            "================================================================",
            "  Endpoints Services Now - Coleccion APIM vs PREPROD Axway",
            "  Ejecuta el flujo de activacion real via Axway API Management",
            "  en ambiente PREPROD contra OLTs de laboratorio.",
            "  VNO-03 Entel · VNO-02 ClaroVTR · VNO-05 DTV · VNO-00 TCH",
            "  Fase 1 — Provisioning : Factibilidad + Consulta + Asignacion + Activacion",
            "  Fase 2 — Operaciones  : DevMod Sync/Async + Modification Sync/Async",
            "  Fase 3 — Baja         : Desregistracion del acceso FTTH",
            "================================================================",
        ],
        "cmd": None, "cwd": None, "report": None, "requires": None,
        "parallel": ["apim-vno03", "apim-vno02", "apim-vno05", "apim-vno00"],
    },
    {
        "id": "t7", "group": "hidden",
        "label": "T7 — Seguridad OWASP",
        "desc":  "JWT · Headers · Métodos HTTP · onf-komands.cl:9016",
        "note":  [
            "================================================================",
            "  T7 - Pruebas de seguridad OWASP vs servidor REAL :9016",
            "  Verifica: autenticacion JWT, headers de seguridad HTTP,",
            "    metodos HTTP no permitidos, tokens invalidos/expirados.",
            "  Ejecuta contra onf-komands.cl:9016 (DEV/QA) - requiere conexion.",
            "  Hallazgos reportados en docs/reporte-seguridad-headers.html.",
            "================================================================",
        ],
        "cmd":   [NEWMAN, "run",
                  "KOMANDs Security Tests v1.0.postman_collection.json",
                  "-e", "newman-environment-dev.json",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export",  "reporte_seguridad_t7.html",
                  "--reporter-htmlextra-template", "reporte-template-es.hbs"],
        "cwd":   str(COLL_DIR),
        "report": str(COLL_DIR / "reporte_seguridad_t7.html"),
        "requires": None,
    },
    {
        "id": "t5", "group": "hidden",
        "label": "T5 — Base de Datos PostgreSQL",
        "desc":  "transaction_listener · audit_log · UUID únicos",
        "blocker": "Requiere PostgreSQL DEV con schema Komands desplegado",
        "note":  [
            "================================================================",
            "  T5 - Validacion PostgreSQL (BLOQUEADO)",
            "  Prueba: transaction_listener, audit_log, unicidad de UUIDs.",
            "  BLOQUEADO: requiere PostgreSQL DEV con schema Komands activo.",
            "  El test_database.py esta marcado con @pytest.mark.skip en T1/T2.",
            "================================================================",
        ],
        "cmd":   [PY, "-u", "-m", "pytest", "tests/api/test_database.py", "-v",
                  "--tb=short", "--color=no", "--no-header",
                  "--html=reporte_t5.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_t5.html"), "requires": None,
    },
    {
        "id": "t4", "group": "hidden",
        "label": "T4 — Flujo E2E OLTs reales",
        "desc":  "POST→callback no disponible aún",
        "blocker": "Requiere endpoint de callback accesible desde servidor DEV",
        "note":  [
            "================================================================",
            "  T4 - Flujo E2E con OLTs reales (BLOQUEADO)",
            "  Prueba el ciclo completo: activacion en OLT fisica -> Komands",
            "    ejecuta CLI en OLT -> OLT responde -> Komands notifica a",
            "    ServiceNow via callback HTTP POST.",
            "  BLOQUEADO: requiere OLTs de laboratorio + endpoint callback SN",
            "    accesible desde el servidor DEV.",
            "  Cobertura actual de callbacks: T3 (contrato payload, con mock).",
            "================================================================",
        ],
        "cmd": None, "cwd": None, "report": None, "requires": None,
    },
    {
        "id": "t6", "group": "hidden",
        "label": "T6 — Paridad VNO + OLT",
        "desc":  "VNO-02 ClaroVTR · VNO-03 Entel",
        "blocker": "Requiere datos reales de VNO-02 y VNO-03",
        "note":  [
            "================================================================",
            "  T6 - Paridad VNO + OLT (BLOQUEADO)",
            "  Valida que Komands produce el mismo resultado que BluePlanet",
            "  en la OLT para cada VNO: DTV, CVTR (VNO-02), ENTEL (VNO-03), TCH.",
            "  Casos: PV-PAR-292 a PV-PAR-324 (test_par_provision.py, 33 casos).",
            "  BLOQUEADO: requiere OLTs fisicas Nokia/Huawei en ambiente QA.",
            "================================================================",
        ],
        "cmd": None, "cwd": None, "report": None, "requires": None,
    },
    {
        "id": "t8", "group": "hidden",
        "label": "T8 — Performance k6 / SLOs",
        "desc":  "Latencia p95 · throughput · error rate",
        "blocker": "Requiere ambiente dedicado y SLOs definidos",
        "note":  [
            "================================================================",
            "  T8 - Performance y SLOs con k6 (BLOQUEADO)",
            "  Mide latencia p95, throughput (req/s) y error rate bajo carga.",
            "  Casos: test_performance.py (carga sostenida, pico, pre-activacion).",
            "  BLOQUEADO: requiere ambiente de performance dedicado y SLOs",
            "    formalmente definidos con el equipo de arquitectura.",
            "================================================================",
        ],
        "cmd": None, "cwd": None, "report": None, "requires": None,
    },
    {
        "id": "t-flg", "group": "hidden",
        "label": "T-FLG — Feature Flags Komands ↔ BluePlanet",
        "desc":  "PV-FLG-001/003 · REG-FF-001/004 · conmutación < 5 min",
        "blocker": "Requiere tabla feature_flag en PostgreSQL DEV",
        "note":  [
            "================================================================",
            "  T-FLG - Feature Flags y Conmutacion Komands <-> BluePlanet",
            "  Casos PV-FLG-001: Flag ON  -> Komands atiende el request.",
            "  Casos PV-FLG-002: Flag OFF -> BluePlanet (legacy) atiende.",
            "  Casos PV-FLG-003: Conmutacion completa + rollback < 5 min.",
            "  Casos REG-FF-001: Ruta BluePlanet responde OK con Flag OFF.",
            "  Casos REG-FF-002: Pre-condicion 0 IN_PROGRESS antes de conmutar.",
            "  Casos REG-FF-003: Txns activas al conmutar -> estado INTERRUPTED.",
            "  Casos REG-FF-004: audit_log registra cambio de flag + inmutabilidad.",
            "  BLOQUEADO: requiere PostgreSQL DEV con schema Komands desplegado.",
            "    Variable requerida: KOMANDS_DEV_DB_URL=postgresql+asyncpg://...",
            "    URL DEV esperada: https://edevapi.onnetfibra.cl/komands (Sem 3).",
            "================================================================",
        ],
        "cmd":   [PY, "-u", "-m", "pytest", "tests/feature_flags/", "-v",
                  "--tb=short", "--color=no", "--no-header",
                  "--html=reporte_tflg.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_tflg.html"), "requires": None,
    },
    # ─── Suites QA OnnetFibra ──────────────────────────────────────────────────
    {
        "id": "qa-tch", "group": "hidden",
        "label": "QA FulFillment — VNO-00 TCH",
        "desc":  "TCH · FulFillment QA · eqapi.onnetfibra.cl",
        "cmd":   [NEWMAN, "run",
                  "01-FulFillment.postman_collection.json",
                  "-e", "00-TCH QA.postman_environment.json",
                  "--env-var", "addressId=",
                  "--env-var", "serial=",
                  "--env-var", "speedPlan=",
                  "--env-var", "addressMcd=OSP",
                  "--env-var", "serviceType=FTTH",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_qa_tch.html"],
        "cwd":   str(QA_DIR),
        "report": str(QA_DIR / "reporte_qa_tch.html"),
        "requires": str(QA_DIR / "00-TCH QA.postman_environment.json"),
        "params": [
            {"key": "addressId",   "label": "Address ID",    "default": ""},
            {"key": "serial",      "label": "Serial ONT",    "default": ""},
            {"key": "speedPlan",   "label": "Speed Plan",    "default": ""},
            {"key": "addressMcd",  "label": "Address MCD",   "default": "OSP"},
            {"key": "serviceType", "label": "Tipo Servicio", "default": "FTTH"},
        ],
    },
    {
        "id": "qa-kao", "group": "hidden",
        "label": "QA FulFillment — VNO-02 KAO",
        "desc":  "KAO · FulFillment QA · eqapi.onnetfibra.cl",
        "cmd":   [NEWMAN, "run",
                  "01-FulFillment.postman_collection.json",
                  "-e", "02 QA_KAO.postman_environment.json",
                  "--env-var", "addressId=",
                  "--env-var", "serial=",
                  "--env-var", "speedPlan=",
                  "--env-var", "addressMcd=OSP",
                  "--env-var", "serviceType=FTTH",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_qa_kao.html"],
        "cwd":   str(QA_DIR),
        "report": str(QA_DIR / "reporte_qa_kao.html"),
        "requires": str(QA_DIR / "02 QA_KAO.postman_environment.json"),
        "params": [
            {"key": "addressId",   "label": "Address ID",    "default": ""},
            {"key": "serial",      "label": "Serial ONT",    "default": ""},
            {"key": "speedPlan",   "label": "Speed Plan",    "default": ""},
            {"key": "addressMcd",  "label": "Address MCD",   "default": "OSP"},
            {"key": "serviceType", "label": "Tipo Servicio", "default": "FTTH"},
        ],
    },
    {
        "id": "qa-b1", "group": "hidden",
        "label": "QA FulFillment — VNO-03 B1/Entel",
        "desc":  "B1/Entel · FulFillment QA · eqapi.onnetfibra.cl",
        "cmd":   [NEWMAN, "run",
                  "01-FulFillment.postman_collection.json",
                  "-e", "03-B1_vnoid03 QA.postman_environment.json",
                  "--env-var", "addressId=",
                  "--env-var", "serial=",
                  "--env-var", "speedPlan=",
                  "--env-var", "addressMcd=OSP",
                  "--env-var", "serviceType=FTTH",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_qa_b1.html"],
        "cwd":   str(QA_DIR),
        "report": str(QA_DIR / "reporte_qa_b1.html"),
        "requires": str(QA_DIR / "03-B1_vnoid03 QA.postman_environment.json"),
        "params": [
            {"key": "addressId",   "label": "Address ID",    "default": ""},
            {"key": "serial",      "label": "Serial ONT",    "default": ""},
            {"key": "speedPlan",   "label": "Speed Plan",    "default": ""},
            {"key": "addressMcd",  "label": "Address MCD",   "default": "OSP"},
            {"key": "serviceType", "label": "Tipo Servicio", "default": "FTTH"},
        ],
    },
    {
        "id": "qa-dtv", "group": "hidden",
        "label": "QA FulFillment — VNO-05 DTV",
        "desc":  "DTV · FulFillment QA · eqapi.onnetfibra.cl",
        "cmd":   [NEWMAN, "run",
                  "01-FulFillment.postman_collection.json",
                  "-e", "05 QA_DTV.postman_environment.json",
                  "--env-var", "addressId=",
                  "--env-var", "serial=",
                  "--env-var", "speedPlan=",
                  "--env-var", "addressMcd=OSP",
                  "--env-var", "serviceType=FTTH",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_qa_dtv.html"],
        "cwd":   str(QA_DIR),
        "report": str(QA_DIR / "reporte_qa_dtv.html"),
        "requires": str(QA_DIR / "05 QA_DTV.postman_environment.json"),
        "params": [
            {"key": "addressId",   "label": "Address ID",    "default": ""},
            {"key": "serial",      "label": "Serial ONT",    "default": ""},
            {"key": "speedPlan",   "label": "Speed Plan",    "default": ""},
            {"key": "addressMcd",  "label": "Address MCD",   "default": "OSP"},
            {"key": "serviceType", "label": "Tipo Servicio", "default": "FTTH"},
        ],
    },
    {
        "id": "qa-fulfillment", "group": "disponible",
        "label": "QA FulFillment",
        "desc":  "VNO-00 TCH · VNO-02 KAO · VNO-03 B1/Entel · VNO-05 DTV · elige uno o varios",
        "cmd": None, "cwd": None, "report": None, "requires": None,
        "parallel": ["qa-tch", "qa-kao", "qa-b1", "qa-dtv"],
    },
    {
        "id": "qa-consultas", "group": "hidden",
        "label": "QA Consultas",
        "desc":  "ConsultaDataONT · RetrieveAccess · DiagnosticoAcceso · EstadoVecino",
        "cmd":   [NEWMAN, "run",
                  "03-Consultas.postman_collection.json",
                  "-e", "02 QA_KAO.postman_environment.json",
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_qa_consultas.html"],
        "cwd":   str(QA_DIR),
        "report": str(QA_DIR / "reporte_qa_consultas.html"),
        "requires": str(QA_DIR / "02 QA_KAO.postman_environment.json"),
    },
    {
        "id": "qa-endpoints", "group": "disponible",
        "label": "Endpoints QA",
        "desc":  "FulFillment · Consultas · ejecución individual por VNO",
        "type":  "ep-explorer",
        "cmd": None, "cwd": None, "report": None, "requires": None,
    },
    # ── QA FulFillment — endpoints individuales ──────────────────────
    {"id":"qa-ep-factibilidad",  "group":"qa-child","parent":"qa-fulfillment",
     "label":"Factibilidad",    "desc":"feasibility · chequeo de puerto OLT",
     "env_type":"qa_factibilidad","folder":"01-Factibilidad",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_factibilidad.html"),"requires":None},
    {"id":"qa-ep-assignment",    "group":"qa-child","parent":"qa-fulfillment",
     "label":"Assignment",      "desc":"asignación de recursos ONT",
     "env_type":"qa_assignment","folder":"02-Assignment",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_assignment.html"),"requires":None},
    {"id":"qa-ep-ia",            "group":"qa-child","parent":"qa-fulfillment",
     "label":"IA Inicio",          "desc":"assuredIntervention · inicio de intervención",
     "env_type":"qa_ia","folder":"03-IntervencionAsegurada",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_ia.html"),"requires":None},
    {"id":"qa-ep-ia-fin",        "group":"qa-child","parent":"qa-fulfillment",
     "label":"IA Finalización",  "desc":"interventionFinalization · cierre de intervención",
     "env_type":"qa_ia_fin","folder":"03-IntervencionAsegurada",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_ia_fin.html"),"requires":None},
    {"id":"qa-ep-activacion",    "group":"qa-child","parent":"qa-fulfillment",
     "label":"Activación",      "desc":"activación ONT FTTH",
     "env_type":"qa_vno","folder":"04-Activacion",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_activacion.html"),"requires":None},
    {"id":"qa-ep-fiberchange",   "group":"qa-child","parent":"qa-fulfillment",
     "label":"Fiber Change",    "desc":"cambio de fibra sincrónico",
     "env_type":"qa_vno","folder":"05-FiberChange",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_fiberchange.html"),"requires":None},
    {"id":"qa-ep-devmod",        "group":"qa-child","parent":"qa-fulfillment",
     "label":"Device Modification","desc":"modificación de dispositivo",
     "env_type":"qa_vno","folder":"06-DeviceModification",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_devmod.html"),"requires":None},
    {"id":"qa-ep-modificacion",  "group":"qa-child","parent":"qa-fulfillment",
     "label":"Modificación Acceso","desc":"modificación de acceso FTTH",
     "env_type":"qa_vno","folder":"07-Modificacion De Acceso",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_modificacion.html"),"requires":None},
    {"id":"qa-ep-cancel",        "group":"qa-child","parent":"qa-fulfillment",
     "label":"Cancel Orden Servicio","desc":"cancelación de orden de servicio",
     "env_type":"qa_vno","folder":"08-CancelOrdenServicio",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_cancel.html"),"requires":None},
    {"id":"qa-ep-unsub",         "group":"qa-child","parent":"qa-fulfillment",
     "label":"Unsubscription",  "desc":"desuscripción / baja de acceso",
     "env_type":"qa_vno","folder":"10-Unsubscription",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_unsub.html"),"requires":None},
    {"id":"qa-ep-reinicio",      "group":"qa-child","parent":"qa-fulfillment",
     "label":"Reinicio ONT",    "desc":"reinicio de ONT · masivo",
     "env_type":"qa_vno","folder":"11-Reinicio ONT",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_reinicio.html"),"requires":None},
    {"id":"qa-ep-precutovertch", "group":"qa-child","parent":"qa-fulfillment",
     "label":"APIs TCH Pre-Cutover","desc":"GuaranteedIntervention · Cancela · Finalización",
     "env_type":"qa_vno","folder":"12-APIS TCH PRE-CUTOVER",
     "collection":"01-FulFillment.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_ep_precutovertch.html"),"requires":None},
    # ── QA Consultas — endpoints individuales ──────────────────────────────────
    {"id":"qa-cons-dataont",     "group":"qa-child","parent":"qa-consultas",
     "label":"ConsultaDataONT", "desc":"consulta datos ONT",
     "env_type":"qa_vno","folder":"ConsultaDataONT",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_dataont.html"),"requires":None},
    {"id":"qa-cons-retrievetch", "group":"qa-child","parent":"qa-consultas",
     "label":"RetrieveAccess TCH","desc":"retrieve access VNO TCH",
     "env_type":"qa_vno","folder":"RetrieveAccess (TCH)",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_retrievetch.html"),"requires":None},
    {"id":"qa-cons-retrievetch-mas","group":"qa-child","parent":"qa-consultas",
     "label":"RetrieveAccess TCH Masivo","desc":"retrieve access masivo TCH",
     "env_type":"qa_vno","folder":"RetrieveAccess (TCH) MASIVO",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_retrievetch_mas.html"),"requires":None},
    {"id":"qa-cons-consultaacceso","group":"qa-child","parent":"qa-consultas",
     "label":"ConsultaAcceso",  "desc":"consulta de acceso",
     "env_type":"qa_vno","folder":"ConsultaAcceso",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_consultaacceso.html"),"requires":None},
    {"id":"qa-cons-diagnostico", "group":"qa-child","parent":"qa-consultas",
     "label":"DiagnosticoAcceso","desc":"diagnóstico de acceso FTTH",
     "env_type":"qa_vno","folder":"DiagnosticoAcceso",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_diagnostico.html"),"requires":None},
    {"id":"qa-cons-accessstate", "group":"qa-child","parent":"qa-consultas",
     "label":"AccessStateResponse","desc":"estado del acceso",
     "env_type":"qa_vno","folder":"AccessStateResponse",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_accessstate.html"),"requires":None},
    {"id":"qa-cons-cevvecino",   "group":"qa-child","parent":"qa-consultas",
     "label":"CEVEstadoVecino",  "desc":"estado vecino CEV",
     "env_type":"qa_vno","folder":"CEVEstadoVecino",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_cevvecino.html"),"requires":None},
    {"id":"qa-cons-estadovecino","group":"qa-child","parent":"qa-consultas",
     "label":"EstadoVecino",    "desc":"estado vecino V",
     "env_type":"qa_vno","folder":"EstadoVecino V",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_estadovecino.html"),"requires":None},
    {"id":"qa-cons-queryneighbors","group":"qa-child","parent":"qa-consultas",
     "label":"QueryNeighborsState","desc":"query neighbors state response",
     "env_type":"qa_vno","folder":"QueryNeighborsStateResponse",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_queryneighbors.html"),"requires":None},
    {"id":"qa-cons-retrievekao", "group":"qa-child","parent":"qa-consultas",
     "label":"RetrieveAccess KAO","desc":"retrieve access VNO KAO",
     "env_type":"qa_vno","folder":"RetrieveAccess KAO",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_retrievekao.html"),"requires":None},
    {"id":"qa-cons-modification","group":"qa-child","parent":"qa-consultas",
     "label":"Modification",    "desc":"modification request",
     "env_type":"qa_vno","folder":"Modification",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_modification.html"),"requires":None},
    {"id":"qa-cons-reinicio",   "group":"qa-child","parent":"qa-consultas",
     "label":"ReinicioONT",     "desc":"reinicio ONT",
     "env_type":"qa_vno","folder":"ReinicioONT",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_reinicio.html"),"requires":None},
    {"id":"qa-cons-fiberchange", "group":"qa-child","parent":"qa-consultas",
     "label":"Fiber Change",    "desc":"fiber change request",
     "env_type":"qa_vno","folder":"Fiber Change",
     "collection":"03-Consultas.postman_collection.json",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"rp_qa_cons_fiberchange.html"),"requires":None},
]

SUITE_MAP = {s["id"]: s for s in SUITES}

# ─── Subprocess en hilo (evita problemas asyncio/Windows) ─────────────────────
ANSI_RE = re.compile(r"\x1b(?:\[[0-9;]*[a-zA-Z]|\][^\x07]*\x07|[^[\]])")

def _worker(cmd, cwd, env, q: _queue.SimpleQueue):
    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        while True:
            raw = proc.stdout.readline()
            if not raw:
                break
            line = ANSI_RE.sub("", raw.decode("utf-8", errors="replace")).rstrip()
            if line:
                q.put(("L", line))
        proc.wait()
        q.put(("D", proc.returncode))
    except Exception as ex:
        q.put(("E", str(ex)))


async def _iter_proc(cmd, cwd, env):
    """Async generator que lee la salida del subprocess sin bloquear el event loop."""
    import asyncio
    q: _queue.SimpleQueue = _queue.SimpleQueue()
    threading.Thread(target=_worker, args=(cmd, cwd, env, q), daemon=True).start()
    loop = asyncio.get_event_loop()
    while True:
        kind, val = await loop.run_in_executor(None, q.get)
        yield kind, val
        if kind in ("D", "E"):
            return


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _apply_params(cmd: list, overrides: dict) -> list:
    """Reemplaza valores de --env-var key=val con los overrides dados."""
    cmd = list(cmd)
    for i, arg in enumerate(cmd):
        if arg == "--env-var" and i + 1 < len(cmd):
            key = cmd[i + 1].split("=", 1)[0]
            if key in overrides and overrides[key]:
                cmd[i + 1] = f"{key}={overrides[key]}"
    return cmd


# ─── FastAPI ──────────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
    import uvicorn
except ImportError:
    print("Instalar: pip install fastapi \"uvicorn[standard]\"")
    sys.exit(1)

app = FastAPI(title="Pruebas de Regresion ambiente QA OnnetFibra")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/api/suites")
async def api_suites():
    result = []
    for s in SUITES:
        d = dict(s)
        req = s.get("requires")
        d["locked"] = bool(req and not Path(req).exists())
        result.append(d)
    return result


@app.get("/api/debug")
async def api_debug():
    import platform
    return {
        "suites_count": len(SUITES),
        "suite_ids": [s["id"] for s in SUITES],
        "groups": {s["id"]: s.get("group") for s in SUITES},
        "python": platform.python_version(),
        "railway_env": os.environ.get("RAILWAY_ENVIRONMENT", "no-set"),
    }


@app.get("/api/run/{suite_id}")
async def api_run(suite_id: str, request: Request):
    suite = SUITE_MAP.get(suite_id)
    if not suite:
        return JSONResponse({"error": "Suite no encontrada"}, status_code=404)
    if suite["group"] == "bloqueado":
        return JSONResponse({"error": "Suite bloqueada: " + suite.get("blocker", "")}, status_code=400)

    overrides = dict(request.query_params)

    if suite.get("env_type") == "qa_vno":
        vno_code = overrides.pop("vno", "02")
        env_file = QA_VNO_ENV_MAP.get(vno_code, QA_VNO_ENV_MAP["02"])
        json_out = str(QA_DIR / f"rsp_{suite_id}.json")
        rp_out   = str(QA_DIR / f"rp_{suite_id}.html")
        suite = dict(suite,
            cmd=[NEWMAN, "run", suite["collection"],
                 "-e", env_file,
                 "--folder", suite["folder"],
                 "--insecure",
                 "--reporters", "cli,json,htmlextra",
                 "--reporter-json-export", json_out,
                 "--reporter-htmlextra-export", rp_out],
            report=rp_out,
            requires=None,
        )
    elif suite.get("env_type") == "qa_factibilidad":
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp
        vno_code     = overrides.pop("vno", "02")
        address_id   = overrides.pop("address_id", "DIR06762531")
        address_mcd  = overrides.pop("address_mcd", "OSP")
        service_type = overrides.pop("service_type", "FTTH")
        env_file     = QA_VNO_ENV_MAP.get(vno_code, QA_VNO_ENV_MAP["02"])
        folder_name  = QA_FACTIBILIDAD_FOLDER_MAP.get(vno_code, "feasibility-KAO")
        if vno_code == "03" and service_type == "SSAA":
            folder_name = "feasibility-Entel SSAA"
        json_out = str(QA_DIR / f"rsp_{suite_id}.json")
        rp_out   = str(QA_DIR / f"rp_{suite_id}.html")
        # 1. Read credentials from env file
        env_data = _j.load(open(QA_DIR / env_file, encoding="utf-8"))
        ev       = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = ev.get("apimURL", "")
        auth_b64 = _b64.b64encode(f"{ev.get('consumerKey','')}:{ev.get('consumerSecret','')}".encode()).decode()
        # 2. Get fresh Bearer token
        token = ""
        try:
            body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
            tok_req = _ur.Request(f"{apim_url}/token", data=body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as _te:
            print(f"[GetToken] error: {_te}", flush=True)
        # 3. Build temp collection with substituted body
        col_src  = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
        col_tmp  = _cp.deepcopy(col_src)
        new_body = _j.dumps({
            "u_id_vno": vno_code,
            "u_operation_type": "Direccion Exacta",
            "u_address_id": address_id,
            "u_address_mcd": address_mcd,
            "u_service_type": service_type,
        }, indent=4, ensure_ascii=False)
        for sec in col_tmp.get("item", []):
            if "Factibilidad" in sec.get("name", ""):
                for req in sec.get("item", []):
                    if req.get("name", "") == folder_name:
                        b = req.get("request", {}).get("body", {})
                        if b.get("mode") == "raw":
                            b["raw"] = new_body
        tmp_col = str(QA_DIR / f"_tmp_fact_{vno_code}.json")
        _j.dump(col_tmp, open(tmp_col, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        _logo_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="44">'
            b'<rect width="220" height="44" rx="4" fill="#0D1B3E"/>'
            b'<text x="12" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="700" fill="#00C8FF">ONNET</text>'
            b'<text x="105" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="400" fill="#ffffff">FIBRA</text>'
            b'</svg>'
        )
        _logo_uri = "data:image/svg+xml;base64," + _b64.b64encode(_logo_svg).decode()
        suite = dict(suite,
            cmd=[NEWMAN, "run", tmp_col,
                 "-e", env_file,
                 "--folder", folder_name,
                 "--env-var", f"Token={token}",
                 "--env-var", f"idvno={vno_code}",
                 "--insecure",
                 "--reporters", "cli,json,htmlextra",
                 "--reporter-json-export", json_out,
                 "--reporter-htmlextra-export", rp_out,
                 "--reporter-htmlextra-title", "Reporte QA - OnnetFibra",
                 "--reporter-htmlextra-logo", _logo_uri],
            report=rp_out,
            requires=None,
        )

    elif suite.get("env_type") == "qa_assignment":
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp
        vno_code      = overrides.pop("vno", "02")
        access_id_vno = overrides.pop("access_id_vno", "")
        address_id    = overrides.pop("address_id", "")
        speed_plan    = overrides.pop("speed_plan", "600/600")
        service_ba    = overrides.pop("service_ba", "true") == "true"
        service_voip  = overrides.pop("service_voip", "true") == "true"
        service_iptv  = overrides.pop("service_iptv", "true") == "true"
        env_file      = QA_VNO_ENV_MAP.get(vno_code, QA_VNO_ENV_MAP["02"])
        folder_name   = QA_ASSIGNMENT_FOLDER_MAP.get(vno_code, "assigment- KAO")
        json_out = str(QA_DIR / f"rsp_{suite_id}.json")
        rp_out   = str(QA_DIR / f"rp_{suite_id}.html")
        env_data = _j.load(open(QA_DIR / env_file, encoding="utf-8"))
        ev       = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = ev.get("apimURL", "")
        auth_b64 = _b64.b64encode(f"{ev.get('consumerKey','')}:{ev.get('consumerSecret','')}".encode()).decode()
        token = ""
        try:
            body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
            tok_req = _ur.Request(f"{apim_url}/token", data=body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as _te:
            print(f"[GetToken] error: {_te}", flush=True)
        col_src = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
        col_tmp = _cp.deepcopy(col_src)
        new_body = _j.dumps({
            "u_access_id_vno": access_id_vno,
            "u_id_vno": vno_code,
            "u_operation_type": "Alta",
            "u_scenario": "Alta de acceso",
            "u_speed_plan": speed_plan,
            "u_address_id": address_id,
            "u_address_mcd": "OSP",
            "u_service_ba": service_ba,
            "u_service_voip": service_voip,
            "u_service_iptv": service_iptv,
            "u_service_type": "FTTH",
        }, indent=4, ensure_ascii=False)
        for sec in col_tmp.get("item", []):
            if "Assignment" in sec.get("name", ""):
                for req in sec.get("item", []):
                    if req.get("name", "") == folder_name:
                        b = req.get("request", {}).get("body", {})
                        if b.get("mode") == "raw":
                            b["raw"] = new_body
        tmp_col = str(QA_DIR / f"_tmp_asig_{vno_code}.json")
        _j.dump(col_tmp, open(tmp_col, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        _logo_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="44">'
            b'<rect width="220" height="44" rx="4" fill="#0D1B3E"/>'
            b'<text x="12" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="700" fill="#00C8FF">ONNET</text>'
            b'<text x="105" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="400" fill="#ffffff">FIBRA</text>'
            b'</svg>'
        )
        _logo_uri = "data:image/svg+xml;base64," + _b64.b64encode(_logo_svg).decode()
        suite = dict(suite,
            cmd=[NEWMAN, "run", tmp_col,
                 "-e", env_file,
                 "--folder", folder_name,
                 "--env-var", f"Token={token}",
                 "--env-var", f"idvno={vno_code}",
                 "--insecure",
                 "--reporters", "cli,json,htmlextra",
                 "--reporter-json-export", json_out,
                 "--reporter-htmlextra-export", rp_out,
                 "--reporter-htmlextra-title", "Reporte QA - OnnetFibra",
                 "--reporter-htmlextra-logo", _logo_uri],
            report=rp_out,
            requires=None,
        )

    elif suite.get("env_type") == "qa_ia":
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp
        vno_code      = overrides.pop("vno", "02")
        access_id_vno = overrides.pop("access_id_vno", "")
        scenario      = overrides.pop("scenario", "Instalación")
        service_type  = overrides.pop("service_type", "FTTH")
        env_file      = QA_VNO_ENV_MAP.get(vno_code, QA_VNO_ENV_MAP["02"])
        vno_subfolder = QA_IA_VNO_SUBFOLDER.get(vno_code, "KAO")
        json_out = str(QA_DIR / f"rsp_{suite_id}.json")
        rp_out   = str(QA_DIR / f"rp_{suite_id}.html")
        env_data = _j.load(open(QA_DIR / env_file, encoding="utf-8"))
        ev       = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = ev.get("apimURL", "")
        auth_b64 = _b64.b64encode(f"{ev.get('consumerKey','')}:{ev.get('consumerSecret','')}".encode()).decode()
        token = ""
        try:
            body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
            tok_req = _ur.Request(f"{apim_url}/token", data=body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as _te:
            print(f"[GetToken] error: {_te}", flush=True)
        col_src = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
        col_tmp = _cp.deepcopy(col_src)
        new_body = _j.dumps({
            "u_id_vno": vno_code,
            "u_access_id_vno": access_id_vno,
            "u_scenario": scenario,
            "u_service_type": service_type,
        }, indent=4, ensure_ascii=False)
        for sec in col_tmp.get("item", []):
            if "Interven" in sec.get("name", ""):
                # Keep only the target VNO subfolder, substitute 01-Inicio body
                sec["item"] = [sf for sf in sec.get("item", []) if sf.get("name", "") == vno_subfolder]
                for subfolder in sec.get("item", []):
                    for req in subfolder.get("item", []):
                        nm = req.get("name", "")
                        if nm == "01-Inicio Intervención" or nm == "01-Inicio Intervencion":
                            b = req.get("request", {}).get("body", {})
                            if b.get("mode") == "raw":
                                b["raw"] = new_body
        tmp_col = str(QA_DIR / f"_tmp_ia_{vno_code}.json")
        _j.dump(col_tmp, open(tmp_col, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        _logo_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="44">'
            b'<rect width="220" height="44" rx="4" fill="#0D1B3E"/>'
            b'<text x="12" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="700" fill="#00C8FF">ONNET</text>'
            b'<text x="105" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="400" fill="#ffffff">FIBRA</text>'
            b'</svg>'
        )
        _logo_uri = "data:image/svg+xml;base64," + _b64.b64encode(_logo_svg).decode()
        suite = dict(suite,
            cmd=[NEWMAN, "run", tmp_col,
                 "-e", env_file,
                 "--folder", "01-Inicio Intervención",
                 "--env-var", f"Token={token}",
                 "--env-var", f"idvno={vno_code}",
                 "--insecure",
                 "--reporters", "cli,json,htmlextra",
                 "--reporter-json-export", json_out,
                 "--reporter-htmlextra-export", rp_out,
                 "--reporter-htmlextra-title", "Reporte QA - OnnetFibra",
                 "--reporter-htmlextra-logo", _logo_uri],
            report=rp_out,
            requires=None,
        )

    elif suite.get("env_type") == "qa_ia_fin":
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp
        vno_code      = overrides.pop("vno", "02")
        access_id_vno = overrides.pop("access_id_vno", "")
        scenario      = overrides.pop("scenario", "Instalación")
        service_type  = overrides.pop("service_type", "FTTH")
        env_file      = QA_VNO_ENV_MAP.get(vno_code, QA_VNO_ENV_MAP["02"])
        vno_subfolder = QA_IA_VNO_SUBFOLDER.get(vno_code, "KAO")
        json_out = str(QA_DIR / f"rsp_{suite_id}.json")
        rp_out   = str(QA_DIR / f"rp_{suite_id}.html")
        env_data = _j.load(open(QA_DIR / env_file, encoding="utf-8"))
        ev       = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = ev.get("apimURL", "")
        auth_b64 = _b64.b64encode(f"{ev.get('consumerKey','')}:{ev.get('consumerSecret','')}".encode()).decode()
        token = ""
        try:
            body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
            tok_req = _ur.Request(f"{apim_url}/token", data=body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as _te:
            print(f"[GetToken] error: {_te}", flush=True)
        col_src = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
        col_tmp = _cp.deepcopy(col_src)
        new_body = _j.dumps({
            "u_id_vno": vno_code,
            "u_access_id_vno": access_id_vno,
            "u_scenario": scenario,
            "u_service_type": service_type,
        }, indent=4, ensure_ascii=False)
        for sec in col_tmp.get("item", []):
            if "Interven" in sec.get("name", ""):
                sec["item"] = [sf for sf in sec.get("item", []) if sf.get("name", "") == vno_subfolder]
                for subfolder in sec.get("item", []):
                    for req in subfolder.get("item", []):
                        nm = req.get("name", "")
                        if "Finaliz" in nm and "Masiva" not in nm:
                            b = req.get("request", {}).get("body", {})
                            if b.get("mode") == "raw":
                                b["raw"] = new_body
        tmp_col = str(QA_DIR / f"_tmp_ia_fin_{vno_code}.json")
        _j.dump(col_tmp, open(tmp_col, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        _logo_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="44">'
            b'<rect width="220" height="44" rx="4" fill="#0D1B3E"/>'
            b'<text x="12" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="700" fill="#00C8FF">ONNET</text>'
            b'<text x="105" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="400" fill="#ffffff">FIBRA</text>'
            b'</svg>'
        )
        _logo_uri = "data:image/svg+xml;base64," + _b64.b64encode(_logo_svg).decode()
        suite = dict(suite,
            cmd=[NEWMAN, "run", tmp_col,
                 "-e", env_file,
                 "--folder", "03-Finalización Intervención",
                 "--env-var", f"Token={token}",
                 "--env-var", f"idvno={vno_code}",
                 "--insecure",
                 "--reporters", "cli,json,htmlextra",
                 "--reporter-json-export", json_out,
                 "--reporter-htmlextra-export", rp_out,
                 "--reporter-htmlextra-title", "Reporte QA - OnnetFibra",
                 "--reporter-htmlextra-logo", _logo_uri],
            report=rp_out,
            requires=None,
        )

    async def sse():
        yield f"data: {json.dumps({'e':'start','id':suite_id,'label':suite['label']})}\n\n"

        for note_line in suite.get("note", []):
            yield f"data: {json.dumps({'e':'line','t':note_line})}\n\n"

        req = suite.get("requires")
        if req and not Path(req).exists():
            _generate_env_files()
        if req and not Path(req).exists():
            msg = f"Archivo no encontrado: {req}\nVerifica las variables de entorno en Railway."
            yield f"data: {json.dumps({'e':'error','t':msg})}\n\n"
            return

        env = {**os.environ,
               "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
               "PYTHONUNBUFFERED": "1",
               "NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0",
               **suite.get("env_extra", {})}

        cmd = _apply_params(suite["cmd"], overrides)
        vno_code = overrides.get("vno", "").strip()
        if vno_code and suite.get("vno_support") and "pytest" in str(cmd):
            cmd = list(cmd) + ["--vno", vno_code]
        passed = failed = requests = 0

        async for kind, val in _iter_proc(cmd, suite["cwd"], env):
            if kind == "L":
                m = re.search(r"(\d+) passed", val)
                if m: passed = int(m.group(1))
                m = re.search(r"(\d+) failed", val)
                if m: failed = int(m.group(1))
                m = re.search(r"requests\s*\│\s*(\d+)", val)
                if m: requests = int(m.group(1))
                m = re.search(r"assertions\s*\│\s*(\d+)\s*\│\s*(\d+)", val)
                if m: failed = max(failed, int(m.group(2)))
                yield f"data: {json.dumps({'e':'line','t':val})}\n\n"
            elif kind == "D":
                rp = suite.get("report") or ""
                has_rp = bool(rp and Path(rp).exists())
                yield f"data: {json.dumps({'e':'done','code':val,'passed':passed,'failed':failed,'requests':requests,'has_report':has_rp,'report_id':suite_id})}\n\n"
                await asyncio.sleep(0.15)
            elif kind == "E":
                yield f"data: {json.dumps({'e':'error','t':val})}\n\n"
                await asyncio.sleep(0.15)

    return StreamingResponse(sse(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform",
                 "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"})



@app.get("/api/response/{suite_id}")
async def api_response(suite_id: str):
    json_path = QA_DIR / f"rsp_{suite_id}.json"
    if not json_path.exists():
        return JSONResponse({"error": "no run yet"}, status_code=404)
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    responses = []
    for ex in data.get("run", {}).get("executions", []):
        item = ex.get("item", {})
        resp = ex.get("response") or {}
        # Newman json reporter stores body as stream Buffer, not plain "body"
        stream = resp.get("stream") or {}
        if isinstance(stream, dict) and stream.get("type") == "Buffer":
            try:
                body = bytes(stream["data"]).decode("utf-8", errors="replace")
            except Exception:
                body = ""
        else:
            body = resp.get("body", "") or ""
        try:
            body_json = json.loads(body) if body else None
        except Exception:
            body_json = None
        req = ex.get("request") or {}
        url_obj = req.get("url") or {}
        url_raw = url_obj.get("raw", "") if isinstance(url_obj, dict) else str(url_obj)
        responses.append({
            "name":     item.get("name", ""),
            "method":   req.get("method", "GET"),
            "url":      url_raw,
            "code":     resp.get("code", 0),
            "status":   resp.get("status", ""),
            "time_ms":  resp.get("responseTime", 0),
            "body_raw": body[:8192],
            "body_json": body_json,
        })
    return JSONResponse({"responses": responses})

@app.get("/api/run-parallel")
async def api_run_parallel(request: Request):
    """Ejecuta suites APIM VNO dinámicamente según parámetros runXX=true/false."""
    import asyncio
    params = dict(request.query_params)
    phase = params.pop("phase", "all")

    # Detect enabled VNOs from runXX=true/false params
    vno_enabled = {}
    for k in list(params.keys()):
        m = re.match(r'^run(\d{2})$', k)
        if m:
            vno_enabled[m.group(1)] = params.pop(k).lower() != "false"

    suite_type = params.pop("suite_type", "apim")
    _QA_CODE_MAP = {'00': 'qa-tch', '02': 'qa-kao', '03': 'qa-b1', '05': 'qa-dtv'}
    to_run = []
    for code, enabled in vno_enabled.items():
        if not enabled:
            continue
        if suite_type == "qa":
            suite = SUITE_MAP.get(_QA_CODE_MAP.get(code, ''))
            run_label = f"QA VNO-{code}"
        else:
            suite = SUITE_MAP.get(f"apim-vno{code}")
            run_label = f"VNO-{code}"
        if not suite:
            continue
        overrides = {k[3:]: v for k, v in params.items() if k.startswith(f"{code}_")}
        overrides["run_phase"] = phase
        to_run.append((suite, run_label, overrides))

    async def sse():
        _par_id = 'qa-fulfillment' if suite_type == 'qa' else 'apim-parallel'
        _par_label = 'QA FulFillment' if suite_type == 'qa' else 'Endpoints Services Now'
        yield f"data: {json.dumps({'e':'start','id':_par_id,'label':_par_label})}\n\n"

        apim_suite = SUITE_MAP.get(_par_id, {})
        for note_line in apim_suite.get("note", []):
            yield f"data: {json.dumps({'e':'line','t':note_line})}\n\n"

        env = {**os.environ,
               "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
               "PYTHONUNBUFFERED": "1",
               "NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}

        if not to_run:
            yield f"data: {json.dumps({'e':'error','t':'Ningún VNO habilitado'})}\n\n"
            return

        for s, label, _ in to_run:
            req = s.get("requires")
            if req and not Path(req).exists():
                _generate_env_files()
            if req and not Path(req).exists():
                yield f"data: {json.dumps({'e':'error','t':f'[{label}] Archivo no encontrado: {req}. Verifica las variables SN_CONSUMER_KEY y SN_CONSUMER_SECRET en Railway.'})}\n\n"
                return

        q: asyncio.Queue = asyncio.Queue()

        async def _feed(suite, label, overrides):
            cmd = _apply_params(suite["cmd"], overrides)
            async for kind, val in _iter_proc(cmd, suite["cwd"], env):
                await q.put((label, kind, val))
            await q.put((label, "_DONE", 0))

        tasks = [asyncio.create_task(_feed(s, lbl, ov)) for s, lbl, ov in to_run]
        passed = failed = requests = 0
        exit_codes = []
        done = 0
        total = len(tasks)

        while done < total:
            label, kind, val = await q.get()
            if kind == "_DONE":
                done += 1
            elif kind == "L":
                m = re.search(r"(\d+) passed", val)
                if m: passed += int(m.group(1))
                m = re.search(r"(\d+) failed", val)
                if m: failed += int(m.group(1))
                m = re.search(r"requests\s*\│\s*(\d+)", val)
                if m: requests += int(m.group(1))
                m = re.search(r"assertions\s*\│\s*(\d+)\s*\│\s*(\d+)", val)
                if m: failed += int(m.group(2))
                yield f"data: {json.dumps({'e':'line','t':val,'vno':label})}\n\n"
            elif kind == "D":
                exit_codes.append(val)
            elif kind == "E":
                yield f"data: {json.dumps({'e':'line','t':'ERROR: '+val,'vno':label})}\n\n"
                exit_codes.append(1)

        await asyncio.gather(*tasks, return_exceptions=True)
        exit_code = max(exit_codes) if exit_codes else 0
        reports = {}
        for s_item, lbl, _ in to_run:
            vno_code = s_item["id"].replace("apim-vno", "")
            rp = s_item.get("report", "")
            reports[vno_code] = bool(rp and Path(rp).exists())
        has_rp = any(reports.values())
        if suite_type == "qa":
            rp_id = next((_QA_CODE_MAP.get(c,'') for c, ok in reports.items() if ok), _par_id)
        else:
            rp_id = next((f"apim-vno{c}" for c, ok in reports.items() if ok), "apim-parallel")
        yield f"data: {json.dumps({'e':'done','code':exit_code,'passed':passed,'failed':failed,'requests':requests,'has_report':has_rp,'report_id':rp_id,'reports':reports})}\n\n"
        await asyncio.sleep(0.15)

    return StreamingResponse(sse(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform",
                 "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"})


_CONFIG_FILE      = Path("/tmp/komands-apim.json")
_BUILD_CONFIG_FILE = ROOT / "apim-config.json"

def _load_persisted_config():
    """Carga credenciales desde config de build (Dockerfile ARG) o runtime (/tmp/)."""
    for path in [_CONFIG_FILE, _BUILD_CONFIG_FILE]:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("ck") and data.get("cs"):
                    os.environ["SN_CONSUMER_KEY"] = data["ck"]
                    os.environ["SN_CONSUMER_SECRET"] = data["cs"]
                    if data.get("url"):
                        os.environ["APIM_URL"] = data["url"]
                    print(f"  [env] Credenciales cargadas desde: {path.name}")
                    return True
            except Exception:
                pass
    return False

@app.post("/api/config")
async def api_config(request: Request):
    """Guarda credenciales APIM en /tmp/ (persiste en la sesión del contenedor)."""
    body = await request.json()
    ck = body.get("consumer_key", "").strip()
    cs = body.get("consumer_secret", "").strip()
    if not ck or not cs:
        return JSONResponse({"error": "consumer_key y consumer_secret son requeridos"}, status_code=400)
    try:
        _CONFIG_FILE.write_text(json.dumps({"ck": ck, "cs": cs}), encoding="utf-8")
    except Exception as e:
        return JSONResponse({"error": f"No se pudo guardar: {e}"}, status_code=500)
    os.environ["SN_CONSUMER_KEY"] = ck
    os.environ["SN_CONSUMER_SECRET"] = cs
    _generate_env_files()
    vno03 = (BP_DIR / "VnoB1_vnoid03 PRE.postman_environment.json").exists()
    vno02 = (BP_DIR / "VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json").exists()
    return JSONResponse({"ok": True, "vno03": vno03, "vno02": vno02})


@app.get("/api/health")
async def api_health():
    import traceback
    status = {
        "bp_dir": str(BP_DIR),
        "bp_dir_exists": BP_DIR.exists(),
        "bp_dir_writable": False,
        "env_vars": {
            "SN_CONSUMER_KEY": "NOT_SET" if "SN_CONSUMER_KEY" not in os.environ else ("EMPTY" if not os.environ["SN_CONSUMER_KEY"] else f"SET(len={len(os.environ['SN_CONSUMER_KEY'])})"),
            "SN_CONSUMER_SECRET": "NOT_SET" if "SN_CONSUMER_SECRET" not in os.environ else ("EMPTY" if not os.environ["SN_CONSUMER_SECRET"] else f"SET(len={len(os.environ['SN_CONSUMER_SECRET'])})"),
            "APIM_URL": "NOT_SET" if "APIM_URL" not in os.environ else os.environ["APIM_URL"],
            "all_custom_keys": [k for k in os.environ if k.startswith(("SN_", "APIM_", "DEV_", "VNO"))],
            "railway_keys": [k for k in os.environ if "RAILWAY" in k],
            "port": os.environ.get("PORT", "NOT_SET"),
            "all_non_railway_keys": sorted([k for k in os.environ if "RAILWAY" not in k and k not in ("PATH","HOME","USER","SHELL","TERM","LANG","LC_ALL","PWD","OLDPWD","SHLVL","_")]),
        },
        "env_files": {},
        "write_test": None,
        "generate_result": None,
    }
    # Test write permission
    test_path = BP_DIR / "_write_test.tmp"
    try:
        BP_DIR.mkdir(parents=True, exist_ok=True)
        test_path.write_text("ok")
        test_path.unlink()
        status["bp_dir_writable"] = True
    except Exception as e:
        status["write_test"] = str(e)
    # Try generating env files
    try:
        _generate_env_files()
        status["generate_result"] = "ok"
    except Exception as e:
        status["generate_result"] = str(e)
    # Check each env file
    for fname in [
        "VnoB1_vnoid03 PRE.postman_environment.json",
        "VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json",
    ]:
        p = BP_DIR / fname
        status["env_files"][fname] = p.exists()
    return JSONResponse(status)


@app.get("/api/report/{suite_id}")
async def api_report(suite_id: str):
    suite = SUITE_MAP.get(suite_id)
    if not suite:
        return JSONResponse({"error": "Suite no encontrada"}, status_code=404)
    rp = suite.get("report")
    if not rp or not Path(rp).exists():
        rp_fallback = str(QA_DIR / f"rp_{suite_id}.html")
        if Path(rp_fallback).exists():
            rp = rp_fallback
    if not rp or not Path(rp).exists():
        return JSONResponse({"error": "Reporte no generado aún."}, status_code=404)
    filename = f"reporte_{suite_id}.html"
    return FileResponse(rp, media_type="text/html", headers={
        "Content-Disposition": f'inline; filename="{filename}"'
    })


# ─── UI ───────────────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pruebas de Regresion ambiente QA OnnetFibra</title>
<style>
:root{
  --bg:#13132A;--side:#1A1A3E;--sideh:#20204A;--card:#181836;--term:#0D0D20;
  --brd:#262558;--brdl:#1E1E46;
  --acc:#00C8D4;--accd:rgba(0,200,212,.13);
  --ok:#3DD68C;--okd:rgba(61,214,140,.13);--okb:rgba(61,214,140,.3);
  --err:#FF6B6B;--errd:rgba(255,107,107,.12);--errb:rgba(255,107,107,.28);
  --warn:#FFB347;
  --txt:#DCE2F6;--txt2:#6272A4;--txt3:#353665;
  --mono:'Cascadia Code','Consolas','Courier New',monospace;
  --sans:'Segoe UI Variable Display','Segoe UI',system-ui,sans-serif;
  --logo-dark:#DCE2F6;--logo-light:#0D1B3E;
}
body.light{
  --bg:#F2F5FB;--side:#FFFFFF;--sideh:#EBF5F9;--card:#FFFFFF;--term:#F4F7FC;
  --brd:#DDE4EF;--brdl:#EEF2FA;
  --acc:#00A8B4;--accd:rgba(0,168,180,.10);
  --ok:#1A9E5E;--okd:rgba(26,158,94,.10);--okb:rgba(26,158,94,.25);
  --err:#D94F4F;--errd:rgba(217,79,79,.10);--errb:rgba(217,79,79,.25);
  --warn:#B87200;
  --txt:#0D1B3E;--txt2:#4A5A80;--txt3:#9AAAC8;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;font-size:13px}
body{background:var(--bg);color:var(--txt);font-family:var(--sans)}
button{font-family:inherit;cursor:pointer}
button:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.layout{display:flex;height:100vh}

/* SIDEBAR */
.sb{width:258px;min-width:258px;background:var(--side);border-right:1px solid var(--brd);display:flex;flex-direction:column;overflow:hidden}
.sb-head{padding:14px 14px 13px;border-bottom:1px solid var(--brd);flex-shrink:0}
.sb-logo{display:flex;align-items:center;gap:0;line-height:1}
.sb-logo .k-text{font-size:.95rem;font-weight:800;letter-spacing:.04em;color:var(--txt);font-family:var(--sans)}
.sb-logo .k-toggle{display:inline-flex;align-items:center;justify-content:center;width:22px;height:14px;border:2px solid var(--acc);border-radius:14px;position:relative;margin:0 1px;vertical-align:middle;flex-shrink:0}
.sb-logo .k-toggle::after{content:'';position:absolute;width:8px;height:8px;background:var(--acc);border-radius:50%;right:1px;transition:background .2s}
.sb-logo .k-suffix{font-size:.95rem;font-weight:800;letter-spacing:.04em;color:var(--acc);font-family:var(--sans)}
.sb-tagline{font-size:.6rem;color:var(--txt2);margin-top:4px;letter-spacing:.01em}
.sb-tagline span{color:var(--acc)}
.sb-sub{font-size:.62rem;color:var(--txt3);margin-top:2px;letter-spacing:.01em}
.sb-list{flex:1;overflow-y:auto;padding:8px 0}
.sb-list::-webkit-scrollbar{width:3px}
.sb-list::-webkit-scrollbar-thumb{background:var(--brd);border-radius:2px}
.grp{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--txt3);padding:10px 13px 4px}
.si{display:flex;align-items:center;gap:9px;padding:8px 13px;border-left:2px solid transparent;transition:background .12s,border-color .12s;cursor:pointer}
.si:hover:not(.si-blk){background:var(--sideh)}
.si.active{background:var(--accd);border-left-color:var(--acc)}
.si-blk{cursor:default;opacity:.42}
.si-blk:hover .si-desc{color:var(--warn)}
.si-ico{width:18px;height:18px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:.65rem;background:var(--brd);color:var(--txt3);transition:background .15s}
.si-ico.running{background:var(--accd);color:var(--acc)}
.si-ico.passed{background:var(--okd);color:var(--ok)}
.si-ico.failed{background:var(--errd);color:var(--err)}
@keyframes spin{to{transform:rotate(360deg)}}
.spin{display:inline-block;animation:spin .7s linear infinite}
.si-txt{flex:1;overflow:hidden}
.si-name{font-size:.77rem;font-weight:500;color:var(--txt);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.si-desc{font-size:.66rem;color:var(--txt2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}
.run-all{margin:10px 12px 12px;padding:7px;border-radius:6px;background:var(--acc);border:none;color:#0D1B3E;font-size:.76rem;font-weight:700;transition:opacity .15s;flex-shrink:0}
.run-all:hover{opacity:.85}
.run-all:disabled{opacity:.35;cursor:not-allowed}

/* MAIN */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.topbar{padding:10px 16px;border-bottom:1px solid var(--brd);display:flex;align-items:center;gap:10px;flex-shrink:0;background:var(--card);min-height:44px;position:relative}
.topbar::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;background:linear-gradient(90deg,var(--acc),rgba(0,200,212,.3) 60%,transparent);opacity:.35;pointer-events:none}
.theme-btn{width:26px;height:26px;border-radius:50%;border:1px solid var(--brd);background:var(--side);color:var(--txt2);font-size:.8rem;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:border-color .15s,color .15s;padding:0}
.theme-btn:hover{border-color:var(--acc);color:var(--acc)}
.top-title{font-size:.85rem;font-weight:600;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.top-status{font-size:.68rem;padding:3px 9px;border-radius:100px;border:1px solid var(--brd);color:var(--txt2);white-space:nowrap;flex-shrink:0;transition:all .2s}
.top-status.running{border-color:var(--acc);color:var(--acc);background:var(--accd)}
.top-status.passed{border-color:var(--okb);color:var(--ok);background:var(--okd)}
.top-status.failed{border-color:var(--errb);color:var(--err);background:var(--errd)}
.exec-btn{padding:4px 14px;border-radius:5px;border:none;background:var(--acc);color:#0D1B3E;font-size:.73rem;font-weight:700;transition:opacity .15s;flex-shrink:0;cursor:pointer}
.exec-btn:disabled{opacity:.28;cursor:not-allowed}
.exec-btn:hover:not(:disabled){opacity:.82}
.rpt-btn{padding:4px 11px;border-radius:5px;border:1px solid var(--brd);background:var(--side);color:var(--txt2);font-size:.7rem;transition:all .12s;display:none;flex-shrink:0}
.rpt-btn.show{display:block}
.rpt-btn:hover{border-color:var(--acc);color:var(--acc)}
.clr-btn{padding:4px 11px;border-radius:5px;border:1px solid var(--brd);background:var(--side);color:var(--txt3);font-size:.7rem;transition:all .12s;flex-shrink:0}
.si-child{padding-left:28px!important;border-left:2px solid var(--brdl)}
.si-child-grp{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--txt3);padding:6px 10px 2px 28px}
.epf-card{background:var(--card);border:1px solid var(--brdl);border-radius:7px;padding:20px 22px;max-width:500px}
.epf-title{font-size:.88rem;font-weight:700;color:var(--txt1);margin-bottom:2px}
.epf-folder{font-size:.65rem;color:var(--txt3);margin-bottom:18px;font-family:monospace}
.epf-folder span{color:var(--acc)}
.epf-field{margin-bottom:14px}
.epf-label{font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--txt3);margin-bottom:5px;display:block}
.epf-readonly{font-size:.74rem;padding:6px 8px;border-radius:4px;background:var(--bg2);border:1px solid var(--brdl)}
.epf-select{width:100%;background:var(--bg2);border:1px solid var(--brdl);border-radius:4px;padding:7px 8px;color:var(--txt1);font-size:.74rem;outline:none}
.epf-input{width:100%;background:var(--bg2);border:1px solid var(--brdl);border-radius:4px;padding:7px 8px;color:var(--txt1);font-size:.74rem;box-sizing:border-box;outline:none}
.epf-chips{display:flex;gap:6px}
.epf-chip{padding:5px 14px;border-radius:4px;border:1px solid var(--brdl);background:transparent;color:var(--txt2);font-size:.72rem;cursor:pointer;transition:all .12s}
.epf-chip.active{border-color:var(--acc);color:var(--acc);background:rgba(78,201,176,.1);font-weight:700}
.epf-exec{margin-top:20px;padding:8px 22px;border-radius:5px;border:none;background:var(--acc);color:#0D1B3E;font-size:.76rem;font-weight:700;cursor:pointer;transition:opacity .12s}
.epf-exec:hover{opacity:.85}
.epf-exec:disabled{opacity:.28;cursor:not-allowed}

.ep-section{margin-bottom:14px}
.ep-section-hdr{font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--txt3);padding:4px 2px 8px;border-bottom:1px solid var(--brdl);margin-bottom:6px}
.ep-row{display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:5px;border:1px solid var(--brdl);margin-bottom:5px;background:var(--card);transition:border-color .15s}
.ep-row:hover{border-color:var(--brd)}
.ep-row-ico{width:16px;height:16px;border-radius:50%;background:var(--brd);flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:.6rem}
.ep-row-txt{flex:1;min-width:0}
.ep-row-name{font-size:.74rem;font-weight:600;color:var(--txt1)}
.ep-row-desc{font-size:.64rem;color:var(--txt3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ep-run-btn{padding:3px 11px;border-radius:4px;border:none;background:var(--acc);color:#0D1B3E;font-size:.68rem;font-weight:700;cursor:pointer;flex-shrink:0;transition:opacity .15s}
.ep-run-btn:hover{opacity:.82}
.ep-run-btn:disabled{opacity:.28;cursor:not-allowed}

.si-child .si-name{font-size:.72rem}
.si-child .si-desc{font-size:.64rem}
.acc-toggle{background:none;border:none;color:var(--txt3);cursor:pointer;padding:0 4px;font-size:.65rem;flex-shrink:0;transition:color .15s}
.acc-toggle:hover{color:var(--acc)}
.vno-bar{display:none;align-items:center;gap:6px;padding:7px 14px;border-bottom:1px solid var(--brd);flex-wrap:wrap;flex-shrink:0}
.vno-bar-lbl{font-size:.66rem;color:var(--txt3);font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-right:4px}
.vnobtn{padding:3px 13px;border-radius:4px;border:1px solid var(--brd);background:transparent;color:var(--txt2);font-size:.72rem;cursor:pointer;transition:all .15s}
.vnobtn.active{font-weight:700}
.resp-panel{display:none;overflow-y:auto;padding:8px 10px;border-top:1px solid var(--brd);flex-shrink:0;max-height:42vh}
.resp-card{border:1px solid var(--brd);border-radius:5px;margin-bottom:6px;overflow:hidden}
.resp-card-hdr{display:flex;align-items:center;gap:8px;padding:6px 10px;background:var(--card);cursor:pointer;user-select:none}
.resp-status{font-family:var(--mono);font-size:.7rem;font-weight:700;min-width:36px}
.resp-name{font-size:.72rem;color:var(--txt1);flex:1}
.resp-time{font-size:.66rem;color:var(--txt3)}
.resp-body{display:none;background:var(--term);padding:8px 12px;overflow-x:auto}
.resp-body pre{margin:0;font-family:var(--mono);font-size:.71rem;line-height:1.55;color:var(--txt1);white-space:pre-wrap;word-break:break-all}
.clr-btn:hover{color:var(--txt2)}
.vno-sel{display:none;padding:3px 8px;border-radius:5px;border:1px solid var(--brd);background:var(--side);color:var(--txt);font-size:.7rem;font-family:var(--sans);cursor:pointer;outline:none;transition:border-color .15s;min-width:130px}
.vno-sel:hover,.vno-sel:focus{border-color:var(--acc)}
.vno-sel.show{display:block}

/* TOGGLE */
.tog{position:relative;width:32px;height:18px;flex-shrink:0;display:inline-block}
.tog input{opacity:0;width:0;height:0;position:absolute}
.tog-sl{position:absolute;inset:0;background:var(--brd);border-radius:18px;cursor:pointer;transition:background .2s}
.tog-sl::before{content:'';position:absolute;width:12px;height:12px;left:3px;bottom:3px;background:#555;border-radius:50%;transition:transform .2s,background .2s}
.tog input:checked+.tog-sl{background:rgba(61,214,140,.35)}
.tog input:checked+.tog-sl::before{transform:translateX(14px);background:var(--ok)}

/* SHARED INPUT GROUP */
.pp-group{display:flex;flex-direction:column;gap:4px}
.pp-group label{font-size:.6rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--txt2)}
.pp-group input{background:var(--term);border:1px solid var(--brd);border-radius:5px;padding:5px 9px;color:var(--txt);font-family:var(--mono);font-size:.75rem;outline:none;transition:border-color .15s;width:100%}
.pp-group input:focus{border-color:var(--acc)}
.pp-group input:disabled{opacity:.4}

/* SN FORM */
.sn-form{display:none;flex-shrink:0;background:var(--card);border-bottom:1px solid var(--brd);padding:12px 16px;flex-direction:column;gap:10px}
.sn-form.show{display:flex}
.sn-cards{display:flex;gap:12px;flex-wrap:wrap}
.sn-card{flex:1;min-width:210px;background:var(--side);border:1px solid var(--brd);border-radius:7px;padding:11px 13px;display:flex;flex-direction:column;gap:8px;transition:opacity .2s}
.sn-card.off{opacity:.32}.sn-card.off .sn-inp{pointer-events:none}
.sn-card-hdr{display:flex;justify-content:space-between;align-items:center}
.sn-name{font-size:.8rem;font-weight:700;display:flex;align-items:center;gap:8px}
.sn-badge{font-size:.58rem;font-weight:700;letter-spacing:.05em;padding:2px 7px;border-radius:100px;background:var(--brd);color:var(--txt2)}
.sn-run{width:100%;padding:7px;border-radius:6px;background:var(--ok);border:none;color:#fff;font-size:.77rem;font-weight:700;cursor:pointer;transition:opacity .15s}
.sn-run:hover{opacity:.85}
.sn-run:disabled{opacity:.35;cursor:not-allowed}
.sn-phases{display:flex;gap:8px;flex-wrap:wrap}
.sn-phase-btn{flex:1;min-width:140px;padding:8px 12px;border-radius:6px;border:1px solid var(--brd);background:var(--side);color:var(--txt2);font-size:.72rem;font-weight:700;cursor:pointer;transition:all .15s;text-align:left;line-height:1.5}
.sn-phase-btn:hover:not(:disabled){border-color:var(--acc);color:var(--txt);background:var(--accd)}
.sn-phase-btn:disabled{opacity:.28;cursor:not-allowed}
.sn-phase-btn.ph-provisioning:hover:not(:disabled){border-color:#4EC9B0;color:#4EC9B0;background:rgba(78,201,176,.07)}
.sn-phase-btn.ph-operations:hover:not(:disabled){border-color:var(--ok);color:var(--ok);background:rgba(61,214,140,.07)}
.sn-phase-btn.ph-baja:hover:not(:disabled){border-color:var(--err);color:var(--err);background:rgba(214,80,80,.07)}
.sn-phase-num{display:block;font-size:.57rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;opacity:.5;margin-bottom:1px}
.sn-phase-name{display:block;font-size:.77rem;font-weight:700}
.sn-phase-desc{display:block;font-size:.6rem;font-weight:400;opacity:.6;margin-top:2px;line-height:1.35}

/* APIM CONFIG */
.apim-cfg{background:var(--side);border:1px solid var(--brd);border-radius:7px;padding:10px 13px;margin-bottom:8px}
.apim-cfg-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.apim-cfg-title{font-size:.75rem;font-weight:700;color:var(--txt2)}
.apim-status{font-size:.68rem;font-weight:600}
.apim-fields{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}
.apim-fields .pp-group{flex:1;min-width:160px}
.apim-fields .sn-run{flex-shrink:0;padding:5px 14px;font-size:.72rem}

/* SN MULTI TERMINAL */
.sn-terms{display:flex;flex:1;overflow-x:auto;overflow-y:hidden;min-height:0}
.sn-term{flex:1;min-width:280px;display:flex;flex-direction:column;overflow:hidden;border-right:1px solid var(--brd)}
.sn-term:last-child{border-right:none}
.sn-thdr{padding:6px 13px;font-size:.7rem;font-weight:600;flex-shrink:0;background:var(--card);border-bottom:1px solid var(--brd);display:flex;align-items:center;gap:7px}
.sn-thdr .ico{width:14px;height:14px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:.55rem;background:var(--brd);color:var(--txt3)}

/* OLT INFO BAR */
.olt-info-bar{flex-shrink:0;display:flex;align-items:center;gap:8px;padding:6px 14px;background:var(--side);border-bottom:1px solid var(--brd);flex-wrap:wrap;font-size:.71rem;font-family:var(--mono)}
.olt-info-bar .oib-label{color:var(--txt3);margin-right:2px;font-style:italic}
.olt-info-bar .oib-chip{display:inline-flex;align-items:center;gap:5px;padding:2px 9px;border-radius:100px;border:1px solid var(--brd);background:var(--card);color:var(--txt);cursor:pointer;transition:border-color .15s,background .15s}
.olt-info-bar .oib-chip:hover{border-color:var(--acc)}
.olt-info-bar .oib-chip.active{border-color:var(--acc);background:var(--accd);color:var(--acc)}
.olt-info-bar .oib-pos{font-weight:700;color:var(--acc)}
.olt-info-bar .oib-vno{color:var(--ok)}
.olt-info-bar .oib-vendor{color:var(--txt2)}
/* TERMINAL */
.terminal{flex:1;overflow-y:auto;overflow-x:hidden;padding:12px 16px;background:var(--term);font-family:var(--mono);font-size:.76rem;line-height:1.6}
.terminal::-webkit-scrollbar{width:4px}
.terminal::-webkit-scrollbar-thumb{background:var(--brd);border-radius:2px}
.terminal:empty::after{content:"Selecciona una suite del panel izquierdo para ejecutar";color:var(--txt3);font-family:var(--sans);font-size:.8rem}
.tl{display:block;white-space:pre-wrap;word-break:break-all}
.tl.ok{color:var(--ok)}.tl.err{color:var(--err)}.tl.warn{color:var(--warn)}
.tl.skip{color:var(--warn);opacity:.75}
.tl.acc{color:var(--acc)}.tl.dim{color:var(--txt3)}.tl.bold{font-weight:700}
.tl.sum-ok{color:var(--ok);font-weight:700}.tl.sum-err{color:var(--err);font-weight:700}
.tl.vno02{color:#4EC9B0}.tl.vno03{color:#C586C0}

/* SUMMARY */
.summary{flex-shrink:0;border-top:1px solid var(--brd);padding:8px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:var(--card);min-height:40px}
.sum-stat{display:flex;align-items:center;gap:5px;font-size:.73rem}
.sdot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.sdot.ok{background:var(--ok)}.sdot.err{background:var(--err)}.sdot.acc{background:var(--acc)}
.sn{font-weight:700;font-variant-numeric:tabular-nums}.sl{color:var(--txt2)}
.st{margin-left:auto;font-size:.68rem;color:var(--txt3)}
.sum-idle{font-size:.72rem;color:var(--txt3)}
</style>
</head>
<body>
<div class="layout">
  <aside class="sb">
    <div class="sb-head">
      <div class="sb-logo">
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAlgAAACWCAYAAAACG/YxAAAACXBIWXMAACxKAAAsSgF3enRNAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAHc1JREFUeJzt3XmYXFWd//H393bXvd3ZqiqJCwgDIoMLIiAzP4Xxx6gw4AiICPgbR1F+yOagoiwGAQm4ICCgwoAEcEHUYYjCKLiBGw/CgIiDqKg4IirKICF1KwvdVdVV3/mjqpNO0tXpqjpV1Z18Xs/D86SWPuebptP96XvP+R5zd0REREQknKjfBYiIiIhsaRSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAhvs18Tz1/DMsTF2rcJzI2ORz4KwZ86IG0+483Alx0MOpa7NtZrFmRo7bOZtXsnyU4dqt+oIbWgVO9ecbLPXK1kedKi0M3ZS4CUekZnqPYNVnnh6IY+1M36/TPX3GnBWjOT4/VQfHxfZqzuVzVw2xtrSIn618fNzV7BNJcO2/aipn8pZ7m/l/TP1ayaCdDTLbzf3vonfPwdrPPl0nj9MZ/zhlB2qxmKASsTvfT4rOqu4N6b58yKYyCiWSvyPP4M1vZqzmXlreVZ5jO3GH8+k7/Hm7j2bLC6yF85bzDgQ54U9m7g7RhzuxrmpMsANvoCVIQePixxvzrJpvPWnbry91W+g/ZKkfA04pNnrg2M8Z+1i/tzm2H+C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Lm597QpsjLWd/OYZwtwVbFPJ1A+unUw5y/29rKcVScq5438u5db/ebaY+P1zsMaT0w0rwyk71OobtF7S1QIncla48cvIub2U57Z2dtFN/PtO53tCN9kqFmac5wLg1Cbreznxe1s8yGNr5vJEj8tsaqP6q+UcD7Q9Vr8CloiIiMiWSguQRURERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQnsfwGGC9wjxnoqDgAAAABJRU5ErkJggg==" alt="OnnetFibra QA" style="height:32px;max-width:200px;object-fit:contain">
      </div>
      <div class="sb-tagline">OnnetFibra <span>QA</span></div>
      <div class="sb-sub">Pruebas de Regresión</div>
    </div>
    <div class="sb-list" id="sb-list"></div>
    <button class="run-all" id="run-all" onclick="runAll()">&#9654;&nbsp; Ejecutar todos</button>
  </aside>
  <main class="main">
    <div class="topbar">
      <span class="top-title" id="top-title">Pruebas de Regresion ambiente QA OnnetFibra</span>
      <span class="top-status" id="top-status">Listo</span>
      <select class="vno-sel" id="vno-sel" title="VNO a probar (solo suites con soporte VNO)">
        <option value="">Todas las VNOs</option>
        <option value="00">00 — TCH</option>
        <option value="02">02 — ClaroVTR</option>
        <option value="03">03 — Entel</option>
        <option value="05">05 — DTV</option>
      </select>
      <button class="exec-btn" id="exec-btn" onclick="executeSelected()" disabled>&#9654; Ejecutar</button>
      <button class="rpt-btn" id="rpt-btn" onclick="openReport()">&#128196; Ver reporte</button>
      <button class="rpt-btn" id="dl-btn" onclick="downloadReport()">&#11015; Descargar</button>
      <button class="clr-btn" onclick="clearTerm()">Limpiar</button>
      <button class="theme-btn" id="theme-btn" onclick="toggleTheme()" title="Cambiar tema">☀</button>
    </div>
    <!-- Vista estándar -->
    <div id="std-view" style="display:flex;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div class="olt-info-bar" id="olt-info-bar" style="display:none"></div>
      <div class="vno-bar" id="vno-bar"></div>
      <div class="terminal" id="term"></div>
      <div class="resp-panel" id="resp-panel"></div>
    </div>
    <!-- Vista Endpoints QA — acordeon individual -->
    <!-- Vista formulario parametros endpoint -->
    <div id="ep-form-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div class="vno-bar" id="epf-vno-bar"></div>
      <div style="flex:1;overflow-y:auto;padding:16px 18px" id="epf-container"></div>
    </div>
    <div id="ep-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div class="vno-bar" id="ep-vno-bar"></div>
      <div style="flex:1;overflow-y:auto;padding:10px 14px" id="ep-list"></div>
    </div>
    <!-- Vista Services Now — doble terminal -->
    <div id="sn-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div class="sn-form" id="sn-form"></div>
      <div class="sn-terms" id="sn-terms"></div>
    </div>
    <div class="summary" id="summary">
      <span class="sum-idle">Ejecuta una suite para ver resultados</span>
    </div>
  </main>
</div>

<script>
var suites=[], currentEs=null, running=false, queue=[], tStart=0, selectedId=null, runningId=null;
var SN_VNO_DEFS=[
  {code:'03',label:'Entel',   color:'#C586C0',suiteId:'apim-vno03'},
  {code:'02',label:'ClaroVTR',color:'#4EC9B0',suiteId:'apim-vno02'},
  {code:'05',label:'DTV',     color:'#CE9178',suiteId:'apim-vno05'},
  {code:'00',label:'TCH',     color:'#569CD6',suiteId:'apim-vno00'},
];
var QA_VNO_DEFS=[
  {code:'00',label:'TCH',     color:'#569CD6',suiteId:'qa-tch'},
  {code:'02',label:'KAO',     color:'#4EC9B0',suiteId:'qa-kao'},
  {code:'03',label:'B1/Entel',color:'#C586C0',suiteId:'qa-b1'},
  {code:'05',label:'DTV',     color:'#CE9178',suiteId:'qa-dtv'},
];
var _activeDefs=SN_VNO_DEFS;
var _activeParallelId='apim-parallel';
var _globalVNO='02';
var _QA_VNO_COLORS={'00':'#569CD6','02':'#4EC9B0','03':'#C586C0','05':'#CE9178'};
var _QA_VNO_LABELS={'00':'TCH','02':'KAO','03':'B1/Entel','05':'DTV'};
var _accordionOpen={};
var _isQAChild=false;
var snEnabled={};
var suiteLogs={};      // { suiteId: [{text,cls}] }
var suiteSummaries={}; // { suiteId: htmlString }
var suiteReports={};   // { suiteId: rid }
var suiteTopState={};  // { suiteId: {cls,title,status} }

function loadSuites(attempt){
  attempt=attempt||1;
  fetch('/api/suites').then(function(r){
    if(!r.ok) throw new Error('HTTP '+r.status);
    return r.json();
  }).then(function(data){
    suites=data;
    if(!suites||!suites.length){
      document.getElementById('sb-list').innerHTML='<div style="padding:8px;color:#e06c75;font-size:.7rem">ERROR: /api/suites devolvió vacío</div>';
      return;
    }
    renderSB();
  }).catch(function(err){
    if(attempt<6){
      setTimeout(function(){loadSuites(attempt+1);}, 1200*attempt);
    } else {
      document.getElementById('sb-list').innerHTML='<div style="padding:8px;color:#e06c75;font-size:.7rem">Error cargando suites — refresca la página</div>';
      console.error('[loadSuites] FALLO definitivo:', err);
    }
  });
}
loadSuites();

function renderSB(){
  var el=document.getElementById('sb-list'); el.innerHTML='';
  [{key:'disponible',lbl:'Disponibles'},{key:'bloqueado',lbl:'Bloqueados'}].forEach(function(g){
    var items=suites.filter(function(s){return s.group===g.key;});
    if(!items.length) return;
    var d=document.createElement('div'); d.className='grp'; d.textContent=g.lbl; el.appendChild(d);
    items.forEach(function(s){
      var row=document.createElement('div');
      row.id='si-'+s.id;
      row.className='si'+(s.group==='bloqueado'?' si-blk':'');
      row.title=s.group==='bloqueado'?('Bloqueado: '+(s.blocker||'')):s.label;
      if(s.id==='qa-endpoints'){
        var isOpen=!!_accordionOpen[s.id];
        row.innerHTML='<div class="si-ico" id="ico-'+s.id+'">&#183;</div>'
          +'<div class="si-txt" style="flex:1">'
          +'<div class="si-name">'+esc(s.label)+'</div>'
          +'<div class="si-desc">'+esc(s.desc)+'</div></div>'
          +'<button class="acc-toggle" title="Expandir endpoints">'
          +(isOpen?'&#9660;':'&#9654;')+'</button>';
        row.querySelector('.si-txt').onclick=(function(sid){return function(){selectSuite(sid);};})(s.id);
        row.querySelector('.acc-toggle').onclick=(function(pid){return function(e){e.stopPropagation();toggleAccordion(pid);};})(s.id);
        el.appendChild(row);
        if(isOpen){
          var _sections=[{lbl:'FulFillment',par:'qa-fulfillment'},{lbl:'Consultas',par:'qa-consultas'}];
          _sections.forEach(function(sec){
            var kids=suites.filter(function(c){return c.parent===sec.par;});
            if(!kids.length) return;
            var gh=document.createElement('div'); gh.className='si-child-grp'; gh.textContent=sec.lbl; el.appendChild(gh);
            kids.forEach(function(c){
              var crow=document.createElement('div');
              crow.id='si-'+c.id; crow.className='si si-child';
              crow.onclick=(function(cid){return function(){selectSuite(cid);};})(c.id);
              crow.innerHTML='<div class="si-ico" id="ico-'+c.id+'">&#183;</div>'
                +'<div class="si-txt"><div class="si-name">'+esc(c.label)+'</div>'
                +'<div class="si-desc">'+esc(c.desc)+'</div></div>';
              el.appendChild(crow);
            });
          });
        }
      } else {
        if(s.group!=='bloqueado') row.onclick=(function(sid){return function(){selectSuite(sid);};})(s.id);
        row.innerHTML='<div class="si-ico" id="ico-'+s.id+'">&#183;</div>'
          +'<div class="si-txt"><div class="si-name">'+esc(s.label)+'</div>'
          +'<div class="si-desc">'+esc(s.desc)+'</div></div>';
        el.appendChild(row);
      }
    });
  });
}

function toggleAccordion(pid){
  _accordionOpen[pid]=!_accordionOpen[pid];
  renderSB();
  if(selectedId) setActive(selectedId);
}

function selectSuite(id){
  var s=suites.find(function(x){return x.id===id;});
  if(!s||s.group==='bloqueado') return;
  selectedId=id;
  setActive(id);
  if(id==='qa-ep-factibilidad'){
    _isQAChild=true;
    switchView('ep-form');
    renderEPFVNOBar();
    renderFactibilidadForm();
    setTop('','Factibilidad','Configura los parámetros y ejecuta');
    var _eb0=document.getElementById('exec-btn'); if(_eb0) _eb0.disabled=true;
    return;
  }
  if(id==='qa-ep-assignment'){
    _isQAChild=true;
    switchView('ep-form');
    renderEPFVNOBar();
    renderAssignmentForm();
    setTop('','Assignment','Configura los parámetros y ejecuta');
    var _eb0a=document.getElementById('exec-btn'); if(_eb0a) _eb0a.disabled=true;
    return;
  }
  if(id==='qa-ep-ia'){
    _isQAChild=true;
    switchView('ep-form');
    renderEPFVNOBar();
    renderIAForm();
    setTop('','IA Inicio','assuredIntervention · configura y ejecuta');
    var _eb0b=document.getElementById('exec-btn'); if(_eb0b) _eb0b.disabled=true;
    return;
  }
  if(id==='qa-ep-ia-fin'){
    _isQAChild=true;
    switchView('ep-form');
    renderEPFVNOBar();
    renderIAFinForm();
    setTop('','IA Finalización','interventionFinalization · configura y ejecuta');
    var _eb0c=document.getElementById('exec-btn'); if(_eb0c) _eb0c.disabled=true;
    return;
  }
  if(id==='qa-endpoints'){
    switchView('ep');
    renderEPVNOBar();
    renderEPView();
    setTop('','Endpoints QA','Selecciona un endpoint y ejecuta');
    var _eb=document.getElementById('exec-btn'); if(_eb) _eb.disabled=true;
    return;
  }
  if(id==='apim-parallel'){
    _activeDefs=SN_VNO_DEFS;_activeParallelId='apim-parallel';
    switchView('sn');
    renderSNForm();
  }else if(id==='qa-fulfillment'){
    _activeDefs=QA_VNO_DEFS;_activeParallelId='qa-fulfillment';
    switchView('sn');
    renderSNForm();
  } else {
    _isQAChild = !!(s.env_type==='qa_vno');
    switchView('std');
    var vbar=document.getElementById('vno-bar');
    var rpanel=document.getElementById('resp-panel');
    if(_isQAChild){ renderVNOBar(); } else { vbar.style.display='none'; }
    if(rpanel) rpanel.style.display='none';
    // Restaurar log guardado para esta suite
    var term=document.getElementById('term');
    term.innerHTML='';
    (suiteLogs[id]||[]).forEach(function(l){
      var sp=document.createElement('span');
      sp.className='tl'+(l.cls?' '+l.cls:'');
      sp.textContent=l.text;
      term.appendChild(sp);
    });
    term.scrollTop=term.scrollHeight;
    // Restaurar summary
    var sumEl=document.getElementById('summary');
    sumEl.innerHTML=suiteSummaries[id]||'<span class="sum-idle">Ejecuta una suite para ver resultados</span>';
    // Restaurar botones de reporte
    var rb=document.getElementById('rpt-btn'), db=document.getElementById('dl-btn');
    if(suiteReports[id]){
      rb.classList.add('show');rb.dataset.rid=suiteReports[id];
      db.classList.add('show');db.dataset.rid=suiteReports[id];
    } else {
      rb.classList.remove('show'); db.classList.remove('show');
    }
    // Restaurar estado del topbar
    if(suiteTopState[id]){
      setTop(suiteTopState[id].cls,suiteTopState[id].title,suiteTopState[id].status);
    } else {
      setTop('',s.label,'Seleccionado — presiona Ejecutar');
    }
  }
  var eb=document.getElementById('exec-btn');
  if(eb) eb.disabled=running;
  // Mostrar selector VNO solo para suites que lo soportan
  var vnoSel=document.getElementById('vno-sel');
  if(vnoSel) vnoSel.classList.toggle('show', !!(s&&s.vno_support));
  // Barra de info OLT para newman-dev
  _renderOltBar(s);
}

function _renderOltBar(s){
  var bar=document.getElementById('olt-info-bar');
  if(!bar) return;
  var cfg=s&&s.olt_config;
  if(!cfg){bar.style.display='none';return;}
  var activeIdx=cfg.active||0;
  var h='<span class="oib-label">OLT activa:</span>';
  cfg.positions.forEach(function(p,i){
    var isActive=(i===activeIdx);
    h+='<span class="oib-chip'+(isActive?' active':'')+'" onclick="_setOltActive('+i+')" title="Click para marcar como activa">';
    h+='<span class="oib-vendor">'+esc(p.vendor)+'</span>';
    h+=' <span class="oib-pos">'+esc(p.olt)+'</span>';
    h+=' <span style="color:var(--txt3)">'+esc(p.slot)+'/'+esc(p.pon)+'/'+esc(p.ontid)+'</span>';
    h+=' <span class="oib-vno">'+esc(p.vno)+'</span>';
    h+=' <span style="color:var(--txt3);font-size:.67rem">'+esc(p.serial)+'</span>';
    h+='</span>';
  });
  bar.innerHTML=h;
  bar.style.display='flex';
}

function _setOltActive(idx){
  var s=suites.find(function(x){return x.id==='newman-dev';});
  if(!s||!s.olt_config) return;
  s.olt_config.active=idx;
  _renderOltBar(s);
}

var VNO_NAMES={'00':'TCH','02':'ClaroVTR','03':'Entel','05':'DTV'};

function _vnoParams(){
  var vnoSel=document.getElementById('vno-sel');
  if(!vnoSel||!vnoSel.classList.contains('show')||!vnoSel.value) return {params:{},suffix:''};
  var code=vnoSel.value;
  return {params:{vno:code}, suffix:' ['+(VNO_NAMES[code]||code)+']'};
}

function executeSelected(){
  if(running||!selectedId) return;
  if(selectedId==='apim-parallel'||selectedId==='qa-fulfillment'){ executeSN(); return; }
  var s=suites.find(function(x){return x.id===selectedId;});
  if(!s||s.group==='bloqueado') return;
  switchView('std');
  var v=_vnoParams();
  var xparams=Object.assign({},v.params,s.env_type==='qa_vno'?{vno:_globalVNO}:{});
  var sRun=v.suffix?Object.assign({},s,{label:s.label+v.suffix}):s;
  _doRun('/api/run/'+selectedId, xparams, sRun);
}

function run(id){
  if(running) return;
  var s=suites.find(function(x){return x.id===id;});
  if(!s||s.group==='bloqueado') return;
  selectedId=id;
  setActive(id);
  if(id==='qa-endpoints'){ selectSuite(id); return; }
  if(id==='apim-parallel'){ _activeDefs=SN_VNO_DEFS;_activeParallelId='apim-parallel'; switchView('sn'); renderSNForm(); return; }
  if(id==='qa-fulfillment'){ _activeDefs=QA_VNO_DEFS;_activeParallelId='qa-fulfillment'; switchView('sn'); renderSNForm(); return; }
  _isQAChild = !!(s.env_type==='qa_vno');
  switchView('std');
  var _vbar=document.getElementById('vno-bar');
  if(_isQAChild){ renderVNOBar(); } else { _vbar.style.display='none'; }
  var _rp2=document.getElementById('resp-panel'); if(_rp2) _rp2.style.display='none';
  var _runParams=_isQAChild?{vno:_globalVNO}:{};
  _doRun('/api/run/'+id, _runParams, s);
}

function switchView(mode){
  var _vs=["std-view","sn-view","ep-view","ep-form-view"];
  _vs.forEach(function(vid){var el=document.getElementById(vid);if(el)el.style.display="none";});
  var target={"sn":"sn-view","ep":"ep-view","ep-form":"ep-form-view"}[mode]||"std-view";
  var el=document.getElementById(target);
  if(el){el.style.display="flex";el.style.flexDirection="column";}
}

function renderSNForm(){
  var sf=document.getElementById('sn-form');
  var termsCont=document.getElementById('sn-terms');

  // Build card HTML for each VNO
  snEnabled={};
  var h='<div class="sn-cards">';
  _activeDefs.forEach(function(def){
    var s=suites.find(function(x){return x.id===def.suiteId;})||{params:[],id:def.suiteId};
    var locked=!!(s.locked);
    snEnabled[def.code]=!locked;
    if(locked){
      h+='<div class="sn-card off locked" id="sn-card-'+def.code+'" title="Pendiente: archivo de entorno">';
      h+='<div class="sn-card-hdr">';
      h+='<div class="sn-name" style="color:'+def.color+';opacity:.45">';
      h+='&#128274; '+esc(def.label);
      h+='</div>';
      h+='<span class="sn-badge" style="opacity:.35">VNO '+def.code+'</span>';
      h+='</div>';
      h+='<div style="font-size:.72rem;color:var(--txt3);padding:6px 13px 10px">Archivo de entorno pendiente</div>';
      h+='</div>';
    } else {
      h+='<div class="sn-card" id="sn-card-'+def.code+'">';
      h+='<div class="sn-card-hdr">';
      h+='<div class="sn-name" style="color:'+def.color+'">';
      h+='<label class="tog"><input type="checkbox" id="sn-tog-'+def.code+'" checked>';
      h+='<span class="tog-sl"></span></label>';
      h+=esc(def.label);
      h+='</div>';
      h+='<span class="sn-badge">VNO '+def.code+'</span>';
      h+='</div>';
      (s.params||[]).forEach(function(p){
        h+='<div class="pp-group">';
        h+='<label>'+esc(p.label)+'</label>';
        h+='<input class="sn-inp" id="sn-'+def.code+'-'+p.key+'" value="'+esc(p.default)+'" placeholder="'+esc(p.label)+'">';
        h+='</div>';
      });
      h+='</div>';
    }
  });
  h+='</div>';
  if(_activeParallelId==='apim-parallel'){
    h+='<div class="sn-phases">';
    h+='<button class="sn-phase-btn ph-provisioning" data-phase="provisioning">';
    h+='<span class="sn-phase-num">Fase 1</span>';
    h+='<span class="sn-phase-name">&#9654; Provisioning</span>';
    h+='<span class="sn-phase-desc">Factibilidad &rarr; Consulta &rarr; Asignaci&oacute;n &rarr; Activaci&oacute;n</span>';
    h+='</button>';
    h+='<button class="sn-phase-btn ph-operations" data-phase="operations">';
    h+='<span class="sn-phase-num">Fase 2</span>';
    h+='<span class="sn-phase-name">&#9654; Operaciones</span>';
    h+='<span class="sn-phase-desc">DevMod Sync/Async &middot; Modification Sync/Async</span>';
    h+='</button>';
    h+='<button class="sn-phase-btn ph-baja" data-phase="baja">';
    h+='<span class="sn-phase-num">Fase 3</span>';
    h+='<span class="sn-phase-name">&#9654; Baja de Acceso</span>';
    h+='<span class="sn-phase-desc">Desregistraci&oacute;n del acceso &mdash; irreversible</span>';
    h+='</button>';
    h+='</div>';
  } else {
    h+='<div class="sn-phases">';
    h+='<button class="sn-phase-btn ph-provisioning" data-phase="all">';
    h+='<span class="sn-phase-name">&#9654; Ejecutar</span>';
    h+='</button>';
    h+='</div>';
  }
  sf.innerHTML=h; sf.classList.add('show');
  sf.querySelectorAll('.sn-phase-btn').forEach(function(b){
    b.onclick=function(){executeSN(b.getAttribute('data-phase'));};
  });
  _activeDefs.forEach(function(def){
    if(snEnabled[def.code]){
      var tog=document.getElementById('sn-tog-'+def.code);
      if(tog) tog.onchange=function(){toggleVNO(def.code);};
    }
  });

  // Rebuild terminals (only for non-locked VNOs)
  if(termsCont){
    var th='';
    _activeDefs.forEach(function(def){
      if(!snEnabled[def.code]) return;
      th+='<div class="sn-term">';
      th+='<div class="sn-thdr" style="color:'+def.color+'">';
      th+='<div class="ico" id="ico-sn'+def.code+'">&#183;</div>VNO-'+def.code+' '+esc(def.label);
      th+='<button id="rpt-sn'+def.code+'" class="rpt-btn" style="margin-left:auto;font-size:.65rem;padding:3px 9px">&#128196; Reporte</button>';
      th+='</div>';
      th+='<div class="terminal" id="term-'+def.code+'"></div>';
      th+='</div>';
    });
    termsCont.innerHTML=th;
  }

  var _snSuite=suites.find(function(x){return x.id===_activeParallelId;});
  setTop('',_snSuite?_snSuite.label:'',_activeParallelId==='apim-parallel'?'Selecciona una fase y ejecuta':'Selecciona una VNO y ejecuta');
}

function checkApimConfig(){
  fetch('/api/health').then(function(r){return r.json();}).then(function(d){
    var ok=d.env_files&&d.env_files['VnoB1_vnoid03 PRE.postman_environment.json'];
    var st=document.getElementById('apim-status');
    var fields=document.getElementById('apim-fields');
    if(!st) return;
    if(ok){
      st.textContent='✓ Configurado';st.style.color='var(--ok)';
      if(fields) fields.style.display='none';
    }
  });
}
function saveApimConfig(){
  var ck=(document.getElementById('apim-ck')||{}).value||'';
  var cs=(document.getElementById('apim-cs')||{}).value||'';
  if(!ck.trim()||!cs.trim()){alert('Ingresa Consumer Key y Consumer Secret');return;}
  var st=document.getElementById('apim-status');
  if(st){st.textContent='Guardando…';st.style.color='var(--warn)';}
  fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({consumer_key:ck.trim(),consumer_secret:cs.trim()})
  }).then(function(r){return r.json();}).then(function(d){
    if(d.ok){
      if(st){st.textContent='✓ Configurado';st.style.color='var(--ok)';}
      var fields=document.getElementById('apim-fields');
      if(fields) fields.style.display='none';
    } else {
      alert('Error: '+(d.error||'Desconocido'));
      if(st){st.textContent='⚠ Error';st.style.color='var(--err)';}
    }
  }).catch(function(e){
    alert('Error de red: '+e);
    if(st){st.textContent='⚠ Error';st.style.color='var(--err)';}
  });
}
function toggleVNO(vno){
  var tog=document.getElementById('sn-tog-'+vno);
  var card=document.getElementById('sn-card-'+vno);
  snEnabled[vno]=tog.checked;
  card.classList.toggle('off',!tog.checked);
  card.querySelectorAll('.sn-inp').forEach(function(inp){inp.disabled=!tog.checked;});
}

function executeSN(phase){
  if(running) return;
  var anyEnabled=_activeDefs.some(function(def){return snEnabled[def.code];});
  if(!anyEnabled){alert('Habilita al menos un VNO');return;}
  var params={phase:phase||'all',suite_type:(_activeParallelId==='qa-fulfillment'?'qa':'apim')};
  _activeDefs.forEach(function(def){
    params['run'+def.code]=snEnabled[def.code]?'true':'false';
    if(snEnabled[def.code]){
      var s=suites.find(function(x){return x.id===def.suiteId;});
      if(s){
        (s.params||[]).forEach(function(p){
          var el=document.getElementById('sn-'+def.code+'-'+p.key);
          if(el) params[def.code+'_'+p.key]=el.value;
        });
      }
    }
  });
  var sp=suites.find(function(x){return x.id===_activeParallelId;});
  var phaseLabels={provisioning:'Fase 1 — Provisioning',operations:'Fase 2 — Operaciones',baja:'Fase 3 — Baja',all:'Completo'};
  _doRunSN(params,sp,phaseLabels[params.phase]||params.phase);
}

function _doRunSN(params,s,phaseLabel){
  running=true; tStart=Date.now();
  var topLabel=phaseLabel?s.label+' — '+phaseLabel:s.label;
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',topLabel,'Ejecutando'); setIco(s.id,'running');
  document.querySelectorAll('.sn-phase-btn').forEach(function(b){b.disabled=true;});
  document.getElementById('run-all').disabled=true;
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _activeDefs.forEach(function(def){if(snEnabled[def.code]) setSnIco(def.code,'running');});

  var qs=Object.keys(params).map(function(k){return encodeURIComponent(k)+'='+encodeURIComponent(params[k]);}).join('&');
  var url='/api/run-parallel'+(qs?'?'+qs:'');

  if(currentEs){currentEs.close();currentEs=null;}
  var es=new EventSource(url);
  currentEs=es;

  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.vno){
        snTerm(d.vno.replace('VNO-',''),d.t);
      } else {
        _activeDefs.forEach(function(def){if(snEnabled[def.code]) snTerm(def.code,d.t);});
      }
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      var ok=d.e==='done'&&d.code===0;
      if(d.e==='error'){
        _activeDefs.forEach(function(def){if(snEnabled[def.code]) snTerm(def.code,'ERROR: '+d.t);});
      }
      onDone(d.e==='error'?{code:1,passed:0,failed:0,requests:0,has_report:false}:d, s);
      _activeDefs.forEach(function(def){
        if(snEnabled[def.code]) setSnIco(def.code,ok?'passed':'failed');
      });
      document.querySelectorAll('.sn-phase-btn').forEach(function(b){b.disabled=false;});
      var reports=d.reports||{};
      _activeDefs.forEach(function(def){
        var rb=document.getElementById('rpt-sn'+def.code);
        if(rb){
          var hasRp=!!(reports[def.code]);
          rb.classList.toggle('show',hasRp);
          if(hasRp){(function(c){rb.onclick=function(){openSnReport('apim-vno'+c);};})(def.code);}
        }
      });
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){
      currentEs=null; es.close();
      var first=_activeDefs.find(function(def){return snEnabled[def.code];});
      if(first) snTerm(first.code,'[Conexión interrumpida]');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      _activeDefs.forEach(function(def){if(snEnabled[def.code]) setSnIco(def.code,'failed');});
      document.querySelectorAll('.sn-phase-btn').forEach(function(b){b.disabled=false;});
    }
  };
}

function snTerm(vno,text){
  var term=document.getElementById('term-'+vno); if(!term) return;
  if(!text){term.innerHTML='';return;}
  var sp=document.createElement('span');
  sp.className='tl '+col(text); sp.textContent=text;
  term.appendChild(sp); term.scrollTop=term.scrollHeight;
}

function setSnIco(vno,state){
  var ico=document.getElementById('ico-sn'+vno); if(!ico) return;
  ico.className='ico '+state;
  if(state==='running') ico.innerHTML='<span class="spin" style="font-size:.7rem">◌</span>';
  else if(state==='passed') ico.textContent='✓';
  else if(state==='failed') ico.textContent='✗';
  else ico.textContent='·';
}

function _doRun(url, params, s){
  if(running) return;
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('term').innerHTML='';
  document.getElementById('rpt-btn').classList.remove('show');
  document.getElementById('dl-btn').classList.remove('show');
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando'); setIco(s.id,'running'); setActive(s.id);
  document.getElementById('run-all').disabled=true;
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  app('▶ '+s.label,'acc bold'); app('','');

  var qs=Object.keys(params).map(function(k){return encodeURIComponent(k)+'='+encodeURIComponent(params[k]);}).join('&');
  if(qs) url+='?'+qs;

  if(currentEs){currentEs.close();currentEs=null;}
  var es=new EventSource(url);
  currentEs=es;

  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      app(d.t,col(d.t));
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error'){app('ERROR: '+d.t,'err');onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);}
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){
      currentEs=null; es.close();
      app('[Conexión interrumpida antes de recibir respuesta]','warn');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
    }
  };
}

function onDone(d,s){
  running=false; runningId=null;
  var elapsed=((Date.now()-tStart)/1000).toFixed(1)+'s';
  var ok=d.code===0;
  app('',''); app('── Fin: '+s.label+' '+'─'.repeat(30),'dim');
  app('Código de salida: '+d.code+'  Tiempo: '+elapsed, ok?'ok bold':'err bold');
  setIco(s.id, ok?'passed':'failed');
  var topCls=ok?'passed':'failed', topStatus=ok?'Completado ✓':'Falló ✗';
  setTop(topCls, s.label, topStatus);
  suiteTopState[s.id]={cls:topCls, title:s.label, status:topStatus};
  var h='';
  if(d.requests) h+=stat('acc',d.requests,'requests')+'&nbsp;&nbsp;';
  h+=stat('ok',d.passed||0,'pasados')+'&nbsp;&nbsp;'+stat('err',d.failed||0,'fallidos');
  h+='<span class="st">'+esc(elapsed)+'</span>';
  document.getElementById('summary').innerHTML=h;
  suiteSummaries[s.id]=h;
  if(d.has_report){
    var rb=document.getElementById('rpt-btn');rb.classList.add('show');rb.dataset.rid=d.report_id;
    var db=document.getElementById('dl-btn');db.classList.add('show');db.dataset.rid=d.report_id;
    suiteReports[s.id]=d.report_id;
  }
  document.getElementById('run-all').disabled=false;
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=false;
  if(_isQAChild){
    fetch('/api/response/'+s.id)
      .then(function(r){return r.json();})
      .then(function(data){renderResponsePanel(data);})
      .catch(function(){});
  }
  if(queue.length){var nx=queue.shift();setTimeout(()=>run(nx),350);}
}

// Direcciones de Factibilidad por VNO 17-07-2026
var QA_FACTIBILIDAD_ADDRESSES={
  '00':['DIR00048870','DIR05088327','DIR02803636'],
  '02':['DIR06762531','DIR05088327','DIR00765048','DIR00048878','DIR00048884','DIR06469749','DIR00046860','DIR02803636'],
  '03':['DIR05088327','DIR00765048','DIR00046860','DIR02803636'],
  '05':['DIR00048870','DIR00046860','DIR02803636'],
};
var QA_FACTIBILIDAD_FOLDER={
  '00':'feasibility-TCH DIR',
  '02':'feasibility-KAO',
  '03':'feasibility-Entel',
  '05':'feasibility-DTV',
};
function renderEPFVNOBar(){
  var bar=document.getElementById("epf-vno-bar");
  if(!bar) return;
  bar.innerHTML='<span class="vno-bar-lbl">VNO:</span>';
  ['00','02','03','05'].forEach(function(code){
    var active=code===_globalVNO;
    var clr=_QA_VNO_COLORS[code];
    var btn=document.createElement("button");
    btn.className="vnobtn"+(active?" active":"");
    btn.style.borderColor=active?clr:"var(--brd)";
    btn.style.color=active?clr:"var(--txt2)";
    btn.style.background=active?clr+"22":"transparent";
    btn.style.fontWeight=active?'700':'400';
    btn.textContent=_QA_VNO_LABELS[code];
    btn.onclick=(function(c){return function(){
      _globalVNO=c;
      renderEPFVNOBar();
      renderVNOBar();
      renderEPVNOBar();
      if(selectedId==='qa-ep-assignment') renderAssignmentForm();
      else if(selectedId==='qa-ep-ia') renderIAForm();
      else if(selectedId==='qa-ep-ia-fin') renderIAFinForm();
      else renderFactibilidadForm();
    };})(code);
    bar.appendChild(btn);
  });
  bar.style.display="flex";
}
function renderFactibilidadForm(){
  var container=document.getElementById("epf-container");
  if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO;
  var addrs=QA_FACTIBILIDAD_ADDRESSES[vno]||[];
  var fldr=QA_FACTIBILIDAD_FOLDER[vno]||"";
  var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="Factibilidad";
  var sf=document.createElement("div"); sf.className="epf-folder";
  sf.innerHTML='Folder: <span>'+fldr+'</span>';
  card.appendChild(tt); card.appendChild(sf);
  var f1=document.createElement("div"); f1.className="epf-field";
  var l1=document.createElement("label"); l1.className="epf-label"; l1.textContent="u_id_vno (auto)";
  var v1=document.createElement("div"); v1.className="epf-readonly";
  v1.style.color=clr; v1.textContent=vno+" — "+(_QA_VNO_LABELS[vno]||vno);
  f1.appendChild(l1); f1.appendChild(v1); card.appendChild(f1);
  var f2=document.createElement("div"); f2.className="epf-field";
  var l2=document.createElement("label"); l2.className="epf-label"; l2.textContent="u_address_id";
  var sel=document.createElement("select"); sel.className="epf-select"; sel.id="epf-address";
  addrs.forEach(function(a){var o=document.createElement("option");o.value=a;o.textContent=a;sel.appendChild(o);});
  f2.appendChild(l2); f2.appendChild(sel); card.appendChild(f2);
  var f3=document.createElement("div"); f3.className="epf-field";
  var l3=document.createElement("label"); l3.className="epf-label"; l3.textContent="u_address_mcd";
  var inp=document.createElement("input"); inp.type="text"; inp.className="epf-input"; inp.id="epf-mcd"; inp.value="OSP";
  f3.appendChild(l3); f3.appendChild(inp); card.appendChild(f3);
  var f4=document.createElement("div"); f4.className="epf-field";
  var l4=document.createElement("label"); l4.className="epf-label"; l4.textContent="u_service_type";
  var cg=document.createElement("div"); cg.className="epf-chips";
  ['FTTH','SSAA'].forEach(function(st){
    var ch=document.createElement("button"); ch.className="epf-chip"+(st==="FTTH"?" active":"");
    ch.id="epf-svc-"+st; ch.textContent=st;
    ch.onclick=function(){
      document.querySelectorAll(".epf-chip").forEach(function(b){b.classList.remove("active");});
      ch.classList.add("active");
    };
    cg.appendChild(ch);
  });
  f4.appendChild(l4); f4.appendChild(cg); card.appendChild(f4);
  var fop=document.createElement("div"); fop.className="epf-field";
  var lop=document.createElement("label"); lop.className="epf-label"; lop.textContent="u_operation_type (fijo)";
  var vop=document.createElement("div"); vop.className="epf-readonly";
  vop.style.color="var(--txt3)"; vop.style.borderStyle="dashed";
  vop.textContent="Direccion Exacta";
  fop.appendChild(lop); fop.appendChild(vop); card.appendChild(fop);
  var eb=document.createElement("button"); eb.className="epf-exec"; eb.textContent="▶ Ejecutar";
  eb.disabled=running;
  eb.onclick=function(){
    var addrEl=document.getElementById("epf-address");
    var mcdEl=document.getElementById("epf-mcd");
    var svcChip=document.querySelector(".epf-chip.active");
    if(!addrEl||!mcdEl||!svcChip) return;
    runFactibilidad({vno:_globalVNO,address_id:addrEl.value,address_mcd:mcdEl.value||"OSP",service_type:svcChip.textContent});
  };
  card.appendChild(eb);
  container.appendChild(card);
}
function runFactibilidad(params){
  if(running) return;
  var sid="qa-ep-factibilidad";
  var s=suites.find(function(x){return x.id===sid;});
  if(!s) return;
  selectedId=sid; _isQAChild=true;
  switchView("std");
  renderVNOBar();
  var rp=document.getElementById("resp-panel"); if(rp) rp.style.display="none";
  suiteLogs[sid]=[];
  document.getElementById("term").innerHTML="";
  _doRun("/api/run/"+sid,params,s);
}
var QA_ASSIGNMENT_FOLDER={
  '00':'assigment-TCH',
  '02':'assigment- KAO',
  '03':'assigment-Entel',
  '05':'assigment-DTV',
};
var QA_SPEED_PLANS=['100/100','300/300','400/400','600/600','800/800','1000/1000'];
function renderAssignmentForm(){
  var container=document.getElementById("epf-container");
  if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO;
  var fldr=QA_ASSIGNMENT_FOLDER[vno]||"";
  var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="Assignment";
  var sf=document.createElement("div"); sf.className="epf-folder";
  sf.innerHTML='Folder: <span>'+fldr+'</span>';
  card.appendChild(tt); card.appendChild(sf);
  // u_id_vno (auto)
  var f1=document.createElement("div"); f1.className="epf-field";
  var l1=document.createElement("label"); l1.className="epf-label"; l1.textContent="u_id_vno (auto)";
  var v1=document.createElement("div"); v1.className="epf-readonly";
  v1.style.color=clr; v1.textContent=vno+" — "+(_QA_VNO_LABELS[vno]||vno);
  f1.appendChild(l1); f1.appendChild(v1); card.appendChild(f1);
  // u_access_id_vno (text)
  var f2=document.createElement("div"); f2.className="epf-field";
  var l2=document.createElement("label"); l2.className="epf-label"; l2.textContent="u_access_id_vno";
  var i2=document.createElement("input"); i2.type="text"; i2.className="epf-input"; i2.id="epf-asig-access";
  i2.placeholder="ej. 02-AOQACAP-01";
  f2.appendChild(l2); f2.appendChild(i2); card.appendChild(f2);
  // u_address_id (text)
  var f3=document.createElement("div"); f3.className="epf-field";
  var l3=document.createElement("label"); l3.className="epf-label"; l3.textContent="u_address_id";
  var i3=document.createElement("input"); i3.type="text"; i3.className="epf-input"; i3.id="epf-asig-addr";
  i3.placeholder="ej. DIR02796497";
  f3.appendChild(l3); f3.appendChild(i3); card.appendChild(f3);
  // u_speed_plan (select)
  var f4=document.createElement("div"); f4.className="epf-field";
  var l4=document.createElement("label"); l4.className="epf-label"; l4.textContent="u_speed_plan";
  var s4=document.createElement("select"); s4.className="epf-select"; s4.id="epf-asig-speed";
  QA_SPEED_PLANS.forEach(function(sp){
    var o=document.createElement("option"); o.value=sp; o.textContent=sp;
    if(sp==="600/600") o.selected=true;
    s4.appendChild(o);
  });
  f4.appendChild(l4); f4.appendChild(s4); card.appendChild(f4);
  // u_service_ba (select true/false)
  var f5=document.createElement("div"); f5.className="epf-field";
  var l5=document.createElement("label"); l5.className="epf-label"; l5.textContent="u_service_ba";
  var s5=document.createElement("select"); s5.className="epf-select"; s5.id="epf-asig-ba";
  ['true','false'].forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;if(v==="true")o.selected=true;s5.appendChild(o);});
  f5.appendChild(l5); f5.appendChild(s5); card.appendChild(f5);
  // u_service_voip (select true/false)
  var f6=document.createElement("div"); f6.className="epf-field";
  var l6=document.createElement("label"); l6.className="epf-label"; l6.textContent="u_service_voip";
  var s6=document.createElement("select"); s6.className="epf-select"; s6.id="epf-asig-voip";
  ['true','false'].forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;if(v==="true")o.selected=true;s6.appendChild(o);});
  f6.appendChild(l6); f6.appendChild(s6); card.appendChild(f6);
  // u_service_iptv (select true/false)
  var f7=document.createElement("div"); f7.className="epf-field";
  var l7=document.createElement("label"); l7.className="epf-label"; l7.textContent="u_service_iptv";
  var s7=document.createElement("select"); s7.className="epf-select"; s7.id="epf-asig-iptv";
  ['true','false'].forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;if(v==="true")o.selected=true;s7.appendChild(o);});
  f7.appendChild(l7); f7.appendChild(s7); card.appendChild(f7);
  // fixed fields
  [['u_operation_type','Alta'],['u_scenario','Alta de acceso'],['u_address_mcd','OSP'],['u_service_type','FTTH']].forEach(function(pair){
    var fx=document.createElement("div"); fx.className="epf-field";
    var lx=document.createElement("label"); lx.className="epf-label"; lx.textContent=pair[0]+" (fijo)";
    var vx=document.createElement("div"); vx.className="epf-readonly";
    vx.style.color="var(--txt3)"; vx.style.borderStyle="dashed"; vx.textContent=pair[1];
    fx.appendChild(lx); fx.appendChild(vx); card.appendChild(fx);
  });
  var eb=document.createElement("button"); eb.className="epf-exec"; eb.textContent="▶ Ejecutar";
  eb.disabled=running;
  eb.onclick=function(){
    var accessEl=document.getElementById("epf-asig-access");
    var addrEl=document.getElementById("epf-asig-addr");
    var speedEl=document.getElementById("epf-asig-speed");
    var baEl=document.getElementById("epf-asig-ba");
    var voipEl=document.getElementById("epf-asig-voip");
    var iptvEl=document.getElementById("epf-asig-iptv");
    if(!accessEl||!addrEl||!speedEl) return;
    runAssignment({
      vno:_globalVNO,
      access_id_vno:accessEl.value,
      address_id:addrEl.value,
      speed_plan:speedEl.value,
      service_ba:baEl.value,
      service_voip:voipEl.value,
      service_iptv:iptvEl.value,
    });
  };
  card.appendChild(eb);
  container.appendChild(card);
}
function runAssignment(params){
  if(running) return;
  var sid="qa-ep-assignment";
  var s=suites.find(function(x){return x.id===sid;});
  if(!s) return;
  selectedId=sid; _isQAChild=true;
  switchView("std");
  renderVNOBar();
  var rp=document.getElementById("resp-panel"); if(rp) rp.style.display="none";
  suiteLogs[sid]=[];
  document.getElementById("term").innerHTML="";
  _doRun("/api/run/"+sid,params,s);
}
var QA_IA_SUBFOLDER={'00':'TCH','02':'KAO','03':'ENTEL','05':'DTV'};
function _buildIACard(title, folderLabel, inputId, placeholder, runFn){
  var container=document.getElementById("epf-container");
  if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO;
  var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent=title;
  var sf=document.createElement("div"); sf.className="epf-folder";
  sf.innerHTML='Folder: <span>03-IntervencionAsegurada / '+QA_IA_SUBFOLDER[vno]+' / '+folderLabel+'</span>';
  card.appendChild(tt); card.appendChild(sf);
  // u_id_vno (auto)
  var f1=document.createElement("div"); f1.className="epf-field";
  var l1=document.createElement("label"); l1.className="epf-label"; l1.textContent="u_id_vno (auto)";
  var v1=document.createElement("div"); v1.className="epf-readonly";
  v1.style.color=clr; v1.textContent=vno+" — "+(_QA_VNO_LABELS[vno]||vno);
  f1.appendChild(l1); f1.appendChild(v1); card.appendChild(f1);
  // u_access_id_vno (text)
  var f2=document.createElement("div"); f2.className="epf-field";
  var l2=document.createElement("label"); l2.className="epf-label"; l2.textContent="u_access_id_vno";
  var i2=document.createElement("input"); i2.type="text"; i2.className="epf-input"; i2.id=inputId;
  i2.placeholder=placeholder;
  f2.appendChild(l2); f2.appendChild(i2); card.appendChild(f2);
  // u_scenario (chips)
  var f3=document.createElement("div"); f3.className="epf-field";
  var l3=document.createElement("label"); l3.className="epf-label"; l3.textContent="u_scenario";
  var cg3=document.createElement("div"); cg3.className="epf-chips";
  ['Instalación','Reparación'].forEach(function(sc,idx){
    var ch=document.createElement("button"); ch.className="epf-chip"+(idx===0?" active":"");
    ch.dataset.val=sc; ch.textContent=sc;
    ch.onclick=function(){cg3.querySelectorAll(".epf-chip").forEach(function(b){b.classList.remove("active");}); ch.classList.add("active");};
    cg3.appendChild(ch);
  });
  f3.appendChild(l3); f3.appendChild(cg3); card.appendChild(f3);
  // u_service_type (chips)
  var f4=document.createElement("div"); f4.className="epf-field";
  var l4=document.createElement("label"); l4.className="epf-label"; l4.textContent="u_service_type";
  var cg4=document.createElement("div"); cg4.className="epf-chips";
  ['FTTH','SSAA'].forEach(function(st,idx){
    var ch=document.createElement("button"); ch.className="epf-chip"+(idx===0?" active":"");
    ch.dataset.val=st; ch.textContent=st;
    ch.onclick=function(){cg4.querySelectorAll(".epf-chip").forEach(function(b){b.classList.remove("active");}); ch.classList.add("active");};
    cg4.appendChild(ch);
  });
  f4.appendChild(l4); f4.appendChild(cg4); card.appendChild(f4);
  var eb=document.createElement("button"); eb.className="epf-exec"; eb.textContent="▶ Ejecutar";
  eb.disabled=running;
  eb.onclick=function(){
    var accessEl=document.getElementById(inputId);
    var scChip=cg3.querySelector(".epf-chip.active");
    var svcChip=cg4.querySelector(".epf-chip.active");
    if(!accessEl||!scChip||!svcChip) return;
    runFn({vno:_globalVNO,access_id_vno:accessEl.value,scenario:scChip.dataset.val,service_type:svcChip.dataset.val});
  };
  card.appendChild(eb);
  container.appendChild(card);
}
function renderIAForm(){
  _buildIACard("IA Inicio","01-Inicio Intervención","epf-ia-access","ej. 02-QASM-2307-1",runIA);
}
function renderIAFinForm(){
  _buildIACard("IA Finalización","03-Finalización Intervención","epf-ia-fin-access","ej. 00QA-JOSEF-SM-01",runIAFin);
}
function runIA(params){
  if(running) return;
  var sid="qa-ep-ia";
  var s=suites.find(function(x){return x.id===sid;});
  if(!s) return;
  selectedId=sid; _isQAChild=true;
  switchView("std"); renderVNOBar();
  var rp=document.getElementById("resp-panel"); if(rp) rp.style.display="none";
  suiteLogs[sid]=[]; document.getElementById("term").innerHTML="";
  _doRun("/api/run/"+sid,params,s);
}
function runIAFin(params){
  if(running) return;
  var sid="qa-ep-ia-fin";
  var s=suites.find(function(x){return x.id===sid;});
  if(!s) return;
  selectedId=sid; _isQAChild=true;
  switchView("std"); renderVNOBar();
  var rp=document.getElementById("resp-panel"); if(rp) rp.style.display="none";
  suiteLogs[sid]=[]; document.getElementById("term").innerHTML="";
  _doRun("/api/run/"+sid,params,s);
}
function renderEPVNOBar(){
  var bar=document.getElementById('ep-vno-bar');
  if(!bar) return;
  bar.innerHTML='<span class="vno-bar-lbl">VNO:</span>';
  ['00','02','03','05'].forEach(function(code){
    var active=code===_globalVNO;
    var clr=_QA_VNO_COLORS[code];
    var btn=document.createElement('button');
    btn.className='vnobtn'+(active?' active':'');
    btn.id='ep-vnobtn-'+code;
    btn.style.borderColor=active?clr:'var(--brd)';
    btn.style.color=active?clr:'var(--txt2)';
    btn.style.background=active?clr+'22':'transparent';
    btn.style.fontWeight=active?'700':'400';
    btn.textContent=_QA_VNO_LABELS[code];
    btn.onclick=(function(c){return function(){_globalVNO=c;renderEPVNOBar();renderVNOBar();};})(code);
    bar.appendChild(btn);
  });
  bar.style.display='flex';
}
function renderEPView(){
  var list=document.getElementById('ep-list');
  if(!list) return;
  var ff=suites.filter(function(s){return s.parent==='qa-fulfillment';}).length;
  var cons=suites.filter(function(s){return s.parent==='qa-consultas';}).length;
  list.innerHTML='<div style="padding:24px 10px;color:var(--txt3);font-size:.78rem;line-height:1.7">'
    +'<div style="font-size:.85rem;font-weight:600;color:var(--txt2);margin-bottom:8px">'+String.fromCharCode(8592)+' Selecciona un endpoint del menú lateral</div>'
    +'<div>Expande la suite <strong style="color:var(--acc)">Endpoints QA</strong> en el panel izquierdo</div>'
    +'<div style="margin-top:12px;display:flex;gap:16px">'
    +'<span style="padding:4px 10px;border:1px solid var(--brdl);border-radius:4px">FulFillment: '+ff+'</span>'
    +'<span style="padding:4px 10px;border:1px solid var(--brdl);border-radius:4px">Consultas: '+cons+'</span>'
    +'</div></div>';
}
function runEndpoint(id,btn){
  if(running) return;
  var s=suites.find(function(x){return x.id===id;});
  if(!s) return;
  selectedId=id; _isQAChild=true;
  // Update icon in ep-view
  var eico=document.getElementById('ep-ico-'+id);
  if(eico) eico.textContent='►';
  // Disable all ep-run-btns
  document.querySelectorAll('.ep-run-btn').forEach(function(b){b.disabled=true;});
  // Switch to std view to show log
  switchView('std');
  renderVNOBar();
  var rpanel=document.getElementById('resp-panel'); if(rpanel) rpanel.style.display='none';
  suiteLogs[id]=[];
  document.getElementById('term').innerHTML='';
  _doRun('/api/run/'+id,{vno:_globalVNO},s);
}
function renderVNOBar(){
  var bar=document.getElementById('vno-bar');
  bar.innerHTML='<span class="vno-bar-lbl">VNO:</span>';
  ['00','02','03','05'].forEach(function(code){
    var active=code===_globalVNO;
    var clr=_QA_VNO_COLORS[code];
    var btn=document.createElement('button');
    btn.className='vnobtn'+(active?' active':'');
    btn.id='vnobtn-'+code;
    btn.style.borderColor=active?clr:'var(--brd)';
    btn.style.color=active?clr:'var(--txt2)';
    btn.style.background=active?clr+'22':'transparent';
    btn.style.fontWeight=active?'700':'400';
    btn.textContent=_QA_VNO_LABELS[code];
    btn.onclick=(function(c){return function(){setGlobalVNO(c);};})(code);
    bar.appendChild(btn);
  });
  bar.style.display='flex';
}
function setGlobalVNO(code){
  _globalVNO=code; renderVNOBar();
}
function renderResponsePanel(data){
  var panel=document.getElementById('resp-panel');
  if(!data||!data.responses||!data.responses.length){panel.style.display='none';return;}
  panel.innerHTML='';
  data.responses.forEach(function(r){
    var ok=r.code>=200&&r.code<300;
    var card=document.createElement('div'); card.className='resp-card';
    var hdr=document.createElement('div'); hdr.className='resp-card-hdr';
    var body=r.body_json?JSON.stringify(r.body_json,null,2):(r.body_raw||'(sin body)');
    var bdiv=document.createElement('div'); bdiv.className='resp-body';
    var pre=document.createElement('pre'); pre.textContent=body;
    bdiv.appendChild(pre);
    hdr.onclick=function(){bdiv.style.display=bdiv.style.display==='block'?'none':'block';};
    var st=document.createElement('span'); st.className='resp-status';
    st.style.color=ok?'var(--ok)':'var(--err)'; st.textContent=r.code;
    var nm=document.createElement('span'); nm.className='resp-name'; nm.textContent=r.name;
    var tm=document.createElement('span'); tm.className='resp-time'; tm.textContent=r.time_ms+'ms';
    hdr.appendChild(st); hdr.appendChild(nm); hdr.appendChild(tm);
    card.appendChild(hdr); card.appendChild(bdiv);
    panel.appendChild(card);
  });
  panel.style.display='block';
}
function stat(cls,n,lbl){
  return '<div class="sum-stat"><div class="sdot '+cls+'"></div><span class="sn">'+n+'</span><span class="sl">&nbsp;'+lbl+'</span></div>';
}
function runAll(){
  if(running) return;
  var ids=suites.filter(s=>s.group==='disponible'&&s.id!=='apim-parallel'&&s.id!=='qa-fulfillment').map(s=>s.id);
  if(!ids.length) return;
  ids.forEach(id=>setIco(id,'idle'));
  queue=ids.slice(1); run(ids[0]);
}
function openReport(){
  var rid=document.getElementById('rpt-btn').dataset.rid;
  if(!rid) return;
  window.open('/api/report/'+rid,'_blank');
}
function openSnReport(rid){
  window.open('/api/report/'+rid,'_blank');
}
function downloadReport(){
  var rid=document.getElementById('rpt-btn').dataset.rid;
  if(!rid) return;
  var a=document.createElement('a');
  a.href='/api/report/'+rid;
  a.download='reporte_'+rid+'.html';
  a.click();
}
function toggleTheme(){
  var isLight=document.body.classList.toggle('light');
  document.getElementById('theme-btn').textContent=isLight?'☾':'☀';
  localStorage.setItem('kmq-theme',isLight?'light':'dark');
}
(function(){
  if(localStorage.getItem('kmq-theme')==='light'){
    document.body.classList.add('light');
    document.getElementById('theme-btn').textContent='☾';
  }
})();
function clearTerm(){
  if(selectedId){
    suiteLogs[selectedId]=[];
    delete suiteSummaries[selectedId];
    delete suiteReports[selectedId];
    delete suiteTopState[selectedId];
  }
  document.getElementById('term').innerHTML='';
  document.getElementById('rpt-btn').classList.remove('show');
  document.getElementById('dl-btn').classList.remove('show');
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecuta una suite para ver resultados</span>';
  setTop('','Pruebas de Regresion ambiente QA OnnetFibra','Listo');
}
function app(text,cls){
  var logId=runningId||selectedId;
  if(logId){
    if(!suiteLogs[logId]) suiteLogs[logId]=[];
    suiteLogs[logId].push({text:text,cls:cls||''});
  }
  if(!runningId||runningId===selectedId){
    var term=document.getElementById('term');
    var sp=document.createElement('span');
    sp.className='tl'+(cls?' '+cls:''); sp.textContent=text;
    term.appendChild(sp); term.scrollTop=term.scrollHeight;
  }
}
function col(t){
  if(/^\\s+√/.test(t)||/^\\s+✔/.test(t)) return 'ok';
  if(/^\\s+\\d+\\.\\s+[A-Z]/.test(t)&&!/GET|POST|PUT|DELETE|PATCH/.test(t)) return 'err';
  if(/^\\s+(GET|POST|PUT|DELETE|PATCH)\\s+https?:/.test(t)) return 'acc';
  if(/expected\\s+|AssertionError/.test(t)) return 'err';
  if(/PASSED/.test(t)) return 'ok';
  if(/SKIPPED/.test(t)) return 'skip';
  if(/FAILED|^ERROR /.test(t)) return 'err';
  if(/^E\\s/.test(t)) return 'err';
  if(/={3,}.*\\d+ passed/.test(t)&&!/failed/.test(t)) return 'sum-ok';
  if(/={3,}.*\\d+ failed/.test(t)) return 'sum-err';
  if(/\\d+ passed/.test(t)&&!/failed/.test(t)) return 'sum-ok';
  if(/\\d+ failed/.test(t)) return 'sum-err';
  if(/warnings? summary/i.test(t)) return 'warn';
  if(/^[─│┌┐└┘├┤┬┴┼= -]+$/.test(t.trim())) return 'dim';
  return '';
}
function setIco(id,state){
  var ico=document.getElementById('ico-'+id); if(!ico)return;
  ico.className='si-ico '+state;
  if(state==='running') ico.innerHTML='<span class="spin">◌</span>';
  else if(state==='passed') ico.textContent='✓';
  else if(state==='failed') ico.textContent='✗';
  else ico.textContent='·';
}
function setActive(id){
  document.querySelectorAll('.si').forEach(el=>el.classList.remove('active'));
  var el=document.getElementById('si-'+id); if(el) el.classList.add('active');
}
function setTop(state,title,txt){
  document.getElementById('top-title').textContent=title;
  var s=document.getElementById('top-status');
  s.className='top-status'+(state?' '+state:''); s.textContent=txt;
}
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
</script>
</body>
</html>"""

# ─── Generar env files desde variables de entorno (Railway/producción) ────────
def _generate_env_files():
    """Si existen las env vars, genera los archivos .postman_environment.json."""
    print(f"  [env] BP_DIR = {BP_DIR}  (existe: {BP_DIR.exists()})")
    ck  = os.environ.get("SN_CONSUMER_KEY")
    cs  = os.environ.get("SN_CONSUMER_SECRET")
    url = os.environ.get("APIM_URL", "https://epreapi.onnetfibra.cl")
    print(f"  [env] SN_CONSUMER_KEY={'SET' if ck else 'NO ENCONTRADA'}")
    print(f"  [env] SN_CONSUMER_SECRET={'SET' if cs else 'NO ENCONTRADA'}")
    if not (ck and cs):
        print("  [env] ADVERTENCIA: sin credenciales APIM → los archivos .postman_environment.json deben existir localmente")
        return

    def _write(path, name, idvno, access_id, serial, speed, addr_id, addr_mcd, ck_vno=None, cs_vno=None):
        _ck = ck_vno or ck
        _cs = cs_vno or cs
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        data = {
            "id": f"env-vno{idvno}-generated",
            "name": name,
            "values": [
                {"key": "consumerKey",    "value": _ck,      "type": "default", "enabled": True},
                {"key": "consumerSecret", "value": _cs,      "type": "default", "enabled": True},
                {"key": "Token",          "value": "",       "type": "default", "enabled": True},
                {"key": "authorization",  "value": "",       "type": "default", "enabled": True},
                {"key": "apimURL",        "value": url,      "type": "default", "enabled": True},
                {"key": "idvno",          "value": idvno,    "type": "default", "enabled": True},
                {"key": "accessId",       "value": access_id,"type": "default", "enabled": True},
                {"key": "serial",         "value": serial,   "type": "default", "enabled": True},
                {"key": "speedPlan",      "value": speed,    "type": "default", "enabled": True},
                {"key": "addressId",      "value": addr_id,  "type": "default", "enabled": True},
                {"key": "addressMcd",     "value": addr_mcd, "type": "default", "enabled": True},
            ],
            "_postman_variable_scope": "environment",
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  [env] generado: {Path(path).name}")

    try:
        _write(
            path     = str(BP_DIR / "VnoB1_vnoid03 PRE.postman_environment.json"),
            name     = "VnoB1_vnoid03 PRE",
            idvno    = "03",
            access_id= os.environ.get("VNO03_ACCESS_ID",  "03-TESTPREPROD-DIR02873675-8"),
            serial   = os.environ.get("VNO03_SERIAL",     "SCOM13032001"),
            speed    = os.environ.get("VNO03_SPEED_PLAN", "940/940"),
            addr_id  = os.environ.get("VNO03_ADDRESS_ID", "DIR02873638"),
            addr_mcd = os.environ.get("VNO03_ADDRESS_MCD","OSP"),
            ck_vno   = os.environ.get("VNO03_CONSUMER_KEY"),
            cs_vno   = os.environ.get("VNO03_CONSUMER_SECRET"),
        )
    except Exception as e:
        print(f"  [env] ERROR generando VNO-03: {e}")
    try:
        _write(
            path     = str(BP_DIR / "VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json"),
            name     = "VnoB1_vnoid02 PRE ClaroVTR",
            idvno    = "02",
            access_id= os.environ.get("VNO02_ACCESS_ID",  "02-TESTPREPROD-DIR02803674-2"),
            serial   = os.environ.get("VNO02_SERIAL",     "SCOM13022002"),
            speed    = os.environ.get("VNO02_SPEED_PLAN", "600/600"),
            addr_id  = os.environ.get("VNO02_ADDRESS_ID", "DIR02803638"),
            addr_mcd = os.environ.get("VNO02_ADDRESS_MCD","OSP"),
            ck_vno   = os.environ.get("VNO02_CONSUMER_KEY"),
            cs_vno   = os.environ.get("VNO02_CONSUMER_SECRET"),
        )
    except Exception as e:
        print(f"  [env] ERROR generando VNO-02: {e}")
    try:
        _write(
            path     = str(BP_DIR / "VnoB1_vnoid05 PRE.postman_environment.json"),
            name     = "VnoB1_vnoid05 PRE",
            idvno    = "05",
            access_id= os.environ.get("VNO05_ACCESS_ID",  "05-TESTPREPROD-"),
            serial   = os.environ.get("VNO05_SERIAL",     ""),
            speed    = os.environ.get("VNO05_SPEED_PLAN", ""),
            addr_id  = os.environ.get("VNO05_ADDRESS_ID", ""),
            addr_mcd = os.environ.get("VNO05_ADDRESS_MCD","OSP"),
            ck_vno   = os.environ.get("VNO05_CONSUMER_KEY"),
            cs_vno   = os.environ.get("VNO05_CONSUMER_SECRET"),
        )
    except Exception as e:
        print(f"  [env] ERROR generando VNO-05: {e}")
    try:
        _write(
            path     = str(BP_DIR / "VnoB1_vnoid00 PRE.postman_environment.json"),
            name     = "VnoB1_vnoid00 PRE",
            idvno    = "00",
            access_id= os.environ.get("VNO00_ACCESS_ID",  "00-TESTPREPROD-"),
            serial   = os.environ.get("VNO00_SERIAL",     ""),
            speed    = os.environ.get("VNO00_SPEED_PLAN", ""),
            addr_id  = os.environ.get("VNO00_ADDRESS_ID", ""),
            addr_mcd = os.environ.get("VNO00_ADDRESS_MCD","OSP"),
            ck_vno   = os.environ.get("VNO00_CONSUMER_KEY"),
            cs_vno   = os.environ.get("VNO00_CONSUMER_SECRET"),
        )
    except Exception as e:
        print(f"  [env] ERROR generando VNO-00: {e}")

    # Environment DEV (Endpoints Kommand Dev + T7)
    dev_url = os.environ.get("DEV_BASE_URL", "https://onf-komands.cl:9016")
    dev_cid = os.environ.get("DEV_CLIENT_ID")
    dev_csc = os.environ.get("DEV_CLIENT_SECRET")
    if dev_cid and dev_csc:
        dev_data = {
            "id": "env-dev-generated",
            "name": "KOMANDs DEV",
            "values": [
                {"key": "base_url",     "value": dev_url, "type": "default", "enabled": True},
                {"key": "client_id",    "value": dev_cid, "type": "default", "enabled": True},
                {"key": "client_secret","value": dev_csc, "type": "default", "enabled": True},
                {"key": "scope",        "value": os.environ.get("DEV_SCOPE","komands:provision komands:query"), "type": "default", "enabled": True},
                {"key": "callback_url", "value": os.environ.get("DEV_CALLBACK_URL",""), "type": "default", "enabled": True},
                {"key": "u_id",         "value": os.environ.get("DEV_U_ID","NCOR_OLT_3_1_1_3"), "type": "default", "enabled": True},
            ],
            "_postman_variable_scope": "environment",
        }
        dev_path = COLL_DIR / "newman-environment-dev.json"
        dev_path.write_text(json.dumps(dev_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  [env] generado: {dev_path.name}")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        print("Instalar: pip install fastapi \"uvicorn[standard]\"")
        sys.exit(1)

    _load_persisted_config()
    _generate_env_files()

    port    = int(os.environ.get("PORT", 8001))
    is_prod = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER"))
    host    = "0.0.0.0" if is_prod else "127.0.0.1"

    print("=" * 50)
    print("  KOMANDs QA Test Runner")
    print(f"  URL: http://{'0.0.0.0' if is_prod else 'localhost'}:{port}")
    print("  Ctrl+C para detener")
    print("=" * 50)

    if not is_prod:
        def _open():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")
