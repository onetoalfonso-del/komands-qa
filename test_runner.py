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
QA_ACTIVACION_REQUEST_MAP = {
    "00": "Activation TCH",
    "02": "Activation KAO",
    "03": "Activation Entel",
    "05": "Activation DTV",
}
QA_ACTIV_SERIAL_BASE = {
    "03": "ZTEG1104",
    "02": "ZTEGD719",
    "05": "HTWC000A",
    # "00" TCH no usa serial
}
QA_RETRIEVE_REQUEST_MAP = {
    "00": "RetrieveAcces (TCH)",
    "02": "RetrieveAcces KAO",
    "03": "RetrieveAcces KAO",
    "05": "RetrieveAcces KAO",
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
     "label":"Activación",      "desc":"registrationActivation · activación ONT FTTH",
     "env_type":"qa_activacion","folder":"04-Activacion",
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
    # ── Suite Factibilidad — casos de prueba TC-01..TC-04 ──────────────────────
    {"id":"qa-fact-suite",  "group":"qa-child","parent":"qa-fact",
     "label":"▶ Ejecutar (4 VNOs · paralelo)",
     "desc":"TC-01 Entel · TC-02 KAO · TC-03 DTV · TC-04 TCH",
     "env_type":"qa_fact_suite",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"factibilidad"/"index.html"),"requires":None},
    {"id":"qa-fact-tc01","group":"hidden","label":"TC-01 Factibilidad Entel",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"factibilidad"/"TC-01.html")},
    {"id":"qa-fact-tc02","group":"hidden","label":"TC-02 Factibilidad KAO",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"factibilidad"/"TC-02.html")},
    {"id":"qa-fact-tc03","group":"hidden","label":"TC-03 Factibilidad DTV",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"factibilidad"/"TC-03.html")},
    {"id":"qa-fact-tc04","group":"hidden","label":"TC-04 Factibilidad TCH",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"factibilidad"/"TC-04.html")},
    # ── QA Asignación — suite paralela ────────────────────────────────────────
    {"id":"qa-asig",       "group":"qa-child","parent":"qa-fulfillment",
     "label":"Suite Asignación","desc":"TC-01..TC-04 · paralelo",
     "cmd":None,"cwd":None,"report":None,"requires":None},
    {"id":"qa-asig-suite", "group":"qa-child","parent":"qa-asig",
     "label":"▶ Ejecutar (4 VNOs · paralelo)",
     "desc":"TC-01 Entel · TC-02 KAO · TC-03 DTV · TC-04 TCH",
     "env_type":"qa_asig_suite",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"asignacion"/"index.html"),"requires":None},
    {"id":"qa-asig-tc05","group":"hidden","label":"TC-05 Asignación Entel",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"asignacion"/"TC-05.html")},
    {"id":"qa-asig-tc06","group":"hidden","label":"TC-06 Asignación KAO",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"asignacion"/"TC-06.html")},
    {"id":"qa-asig-tc07","group":"hidden","label":"TC-07 Asignación DTV",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"asignacion"/"TC-07.html")},
    {"id":"qa-asig-tc08","group":"hidden","label":"TC-08 Asignación TCH",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"asignacion"/"TC-08.html")},
    # ── QA Intervención Asegurada — suites paralelas ──────────────────────────
    {"id":"qa-ia-par",        "group":"qa-child","parent":"qa-fulfillment",
     "label":"Suite Interv. Asegurada","desc":"Inicio · Fin · paralelo",
     "cmd":None,"cwd":None,"report":None,"requires":None},
    {"id":"qa-ia-inicio-suite","group":"qa-child","parent":"qa-ia-par",
     "label":"▶ Inicio (4 VNOs · paralelo)",
     "desc":"TC-09..TC-12 · 01-Inicio Intervención",
     "env_type":"qa_ia_inicio_suite",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"ia"/"inicio_index.html"),"requires":None},
    {"id":"qa-ia-fin-suite",  "group":"qa-child","parent":"qa-ia-par",
     "label":"▶ Fin (4 VNOs · paralelo)",
     "desc":"TC-13..TC-16 · 03-Finalización Intervención",
     "env_type":"qa_ia_fin_suite",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"ia"/"fin_index.html"),"requires":None},
    {"id":"qa-ia-tc09","group":"hidden","label":"TC-09 IA Inicio Entel",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"ia"/"TC-09.html")},
    {"id":"qa-ia-tc10","group":"hidden","label":"TC-10 IA Inicio KAO",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"ia"/"TC-10.html")},
    {"id":"qa-ia-tc11","group":"hidden","label":"TC-11 IA Inicio DTV",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"ia"/"TC-11.html")},
    {"id":"qa-ia-tc12","group":"hidden","label":"TC-12 IA Inicio TCH",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"ia"/"TC-12.html")},
    {"id":"qa-ia-tc13","group":"hidden","label":"TC-13 IA Fin Entel",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"ia"/"TC-13.html")},
    {"id":"qa-ia-tc14","group":"hidden","label":"TC-14 IA Fin KAO",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"ia"/"TC-14.html")},
    {"id":"qa-ia-tc15","group":"hidden","label":"TC-15 IA Fin DTV",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"ia"/"TC-15.html")},
    {"id":"qa-ia-tc16","group":"hidden","label":"TC-16 IA Fin TCH",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"ia"/"TC-16.html")},
    # ── QA Activación — suite paralela ─────────────────────────────────────────
    {"id":"qa-activ-par",  "group":"qa-child","parent":"qa-fulfillment",
     "label":"Suite Activación","desc":"TC-17..TC-20 · 3 pasos por VNO · paralelo",
     "cmd":None,"cwd":None,"report":None,"requires":None},
    {"id":"qa-activ-suite","group":"qa-child","parent":"qa-activ-par",
     "label":"▶ Activación (4 VNOs · paralelo)",
     "desc":"TC-17..TC-20 · Activation + Idempotencia + Retrieve",
     "env_type":"qa_activ_suite",
     "cmd":None,"cwd":str(QA_DIR),"report":str(QA_DIR/"activacion"/"index.html"),"requires":None},
    {"id":"qa-activ-tc17","group":"hidden","label":"TC-17 Activación Entel",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"activacion"/"TC-17.html")},
    {"id":"qa-activ-tc18","group":"hidden","label":"TC-18 Activación KAO",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"activacion"/"TC-18.html")},
    {"id":"qa-activ-tc19","group":"hidden","label":"TC-19 Activación DTV",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"activacion"/"TC-19.html")},
    {"id":"qa-activ-tc20","group":"hidden","label":"TC-20 Activación TCH",
     "cmd":None,"cwd":None,"requires":None,"report":str(QA_DIR/"activacion"/"TC-20.html")},
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
    _tc_runs = None  # set by qa_fact_suite handler; triggers parallel SSE path

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

    elif suite.get("env_type") == "qa_activacion":
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp
        vno_code      = overrides.pop("vno", "02")
        access_id_vno = overrides.pop("access_id_vno", "")
        speed_plan    = overrides.pop("speed_plan", "600/600")
        serial_number = overrides.pop("serial_number", "")
        service_ba    = overrides.pop("service_ba", "true") == "true"
        service_voip  = overrides.pop("service_voip", "true") == "true"
        service_iptv  = overrides.pop("service_iptv", "true") == "true"
        env_file      = QA_VNO_ENV_MAP.get(vno_code, QA_VNO_ENV_MAP["02"])
        req_name      = QA_ACTIVACION_REQUEST_MAP.get(vno_code, "Activation KAO")
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
        body_dict = {
            "u_id_vno": vno_code,
            "u_access_id_vno": access_id_vno,
            "u_operation_type": "A",
            "u_speed_plan": speed_plan,
            "u_service_ba": service_ba,
            "u_service_voip": service_voip,
            "u_service_iptv": service_iptv,
        }
        if serial_number and vno_code != "00":
            body_dict["u_serial_number"] = serial_number
        new_body = _j.dumps(body_dict, indent=4, ensure_ascii=False)
        for sec in col_tmp.get("item", []):
            if "Activacion" in sec.get("name", "") or "04-Activ" in sec.get("name", ""):
                for req in sec.get("item", []):
                    if req.get("name", "") == req_name:
                        b = req.get("request", {}).get("body", {})
                        if b.get("mode") == "raw":
                            b["raw"] = new_body
        tmp_col = str(QA_DIR / f"_tmp_activ_{vno_code}.json")
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
                 "--folder", req_name,
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

    elif suite.get("env_type") == "qa_fact_suite":
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp
        _fact_dir = QA_DIR / "factibilidad"
        _fact_dir.mkdir(parents=True, exist_ok=True)
        _ADDR_ID = "DIR02803636"
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
        _TC_DEFS_ALL = [
            {"tc": "TC-01", "vno": "03", "vno_label": "Entel",  "sid": "qa-fact-tc01"},
            {"tc": "TC-02", "vno": "02", "vno_label": "KAO",    "sid": "qa-fact-tc02"},
            {"tc": "TC-03", "vno": "05", "vno_label": "DTV",    "sid": "qa-fact-tc03"},
            {"tc": "TC-04", "vno": "00", "vno_label": "TCH",    "sid": "qa-fact-tc04"},
        ]
        _tcs_param = overrides.get("tcs", "")
        _tcs_filter = set(_tcs_param.split(",")) if _tcs_param else {"TC-01","TC-02","TC-03","TC-04"}
        _TC_DEFS = [d for d in _TC_DEFS_ALL if d["tc"] in _tcs_filter]
        if not _TC_DEFS:
            _TC_DEFS = _TC_DEFS_ALL
        _tc_runs = []
        for _tcd in _TC_DEFS:
            _vno       = _tcd["vno"]
            _env_file  = QA_VNO_ENV_MAP.get(_vno, QA_VNO_ENV_MAP["02"])
            _folder    = QA_FACTIBILIDAD_FOLDER_MAP.get(_vno, "feasibility-KAO")
            _rp_out    = str(_fact_dir / f"{_tcd['tc']}.html")
            _json_out  = str(_fact_dir / f"{_tcd['tc']}.json")
            _env_data  = _j.load(open(QA_DIR / _env_file, encoding="utf-8"))
            _ev        = {v["key"]: v["value"] for v in _env_data["values"]}
            _apim_url  = _ev.get("apimURL", "")
            _auth_b64  = _b64.b64encode(f"{_ev.get('consumerKey','')}:{_ev.get('consumerSecret','')}".encode()).decode()
            _token = ""
            try:
                _body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
                _tok_req = _ur.Request(f"{_apim_url}/token", data=_body_b,
                    headers={"Authorization": f"Basic {_auth_b64}",
                             "Content-Type": "application/x-www-form-urlencoded"})
                _ctx = _sl.create_default_context()
                _ctx.check_hostname = False; _ctx.verify_mode = _sl.CERT_NONE
                with _ur.urlopen(_tok_req, context=_ctx, timeout=15) as _r:
                    _token = _j.loads(_r.read()).get("access_token", "")
            except Exception as _te:
                print(f"[GetToken {_tcd['tc']}] error: {_te}", flush=True)
            _col_src  = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
            _col_tmp  = _cp.deepcopy(_col_src)
            _new_body = _j.dumps({
                "u_id_vno": _vno,
                "u_operation_type": "Direccion Exacta",
                "u_address_id": _ADDR_ID,
                "u_address_mcd": "OSP",
                "u_service_type": "FTTH",
            }, indent=4, ensure_ascii=False)
            for _sec in _col_tmp.get("item", []):
                if "Factibilidad" in _sec.get("name", ""):
                    for _req in _sec.get("item", []):
                        if _req.get("name", "") == _folder:
                            _b = _req.get("request", {}).get("body", {})
                            if _b.get("mode") == "raw":
                                _b["raw"] = _new_body
            _tmp_col = str(QA_DIR / f"_tmp_fact_suite_{_vno}.json")
            _j.dump(_col_tmp, open(_tmp_col, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _tc_runs.append({
                "tc":      _tcd["tc"],
                "vno":     _vno,
                "vno_lbl": _tcd["vno_label"],
                "sid":     _tcd["sid"],
                "label":   f"{_tcd['tc']} · {_tcd['vno_label']} (VNO {_vno})",
                "cmd":     [NEWMAN, "run", _tmp_col,
                            "-e", _env_file,
                            "--folder", _folder,
                            "--env-var", f"Token={_token}",
                            "--env-var", f"idvno={_vno}",
                            "--insecure",
                            "--reporters", "cli,json,htmlextra",
                            "--reporter-json-export", _json_out,
                            "--reporter-htmlextra-export", _rp_out,
                            "--reporter-htmlextra-title", f"Reporte QA – {_tcd['tc']} Factibilidad · {_tcd['vno_label']} – OnnetFibra",
                            "--reporter-htmlextra-logo", _logo_uri],
                "cwd":     str(QA_DIR),
                "rp_out":  _rp_out,
                "json_out": _json_out,
            })

    elif suite.get("env_type") == "qa_asig_suite":
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp
        _asig_dir = QA_DIR / "asignacion"
        _asig_dir.mkdir(parents=True, exist_ok=True)
        _logo_svg_a = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="44">'
            b'<rect width="220" height="44" rx="4" fill="#0D1B3E"/>'
            b'<text x="12" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="700" fill="#00C8FF">ONNET</text>'
            b'<text x="105" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="400" fill="#ffffff">FIBRA</text>'
            b'</svg>'
        )
        _logo_uri_a = "data:image/svg+xml;base64," + _b64.b64encode(_logo_svg_a).decode()
        _access_ids_raw = overrides.get("access_ids", "")
        try:
            _access_ids_map = json.loads(_access_ids_raw) if _access_ids_raw else {}
        except Exception:
            _access_ids_map = {}
        _address_id = overrides.get("address_id", "")
        _speed_plan = overrides.get("speed_plan", "600/600")
        _service_ba   = overrides.get("service_ba",   "true")
        _service_voip = overrides.get("service_voip", "true")
        _service_iptv = overrides.get("service_iptv", "true")
        _TC_DEFS_ALL_A = [
            {"tc": "TC-05", "vno": "03", "vno_label": "Entel", "sid": "qa-asig-tc05"},
            {"tc": "TC-06", "vno": "02", "vno_label": "KAO",   "sid": "qa-asig-tc06"},
            {"tc": "TC-07", "vno": "05", "vno_label": "DTV",   "sid": "qa-asig-tc07"},
            {"tc": "TC-08", "vno": "00", "vno_label": "TCH",   "sid": "qa-asig-tc08"},
        ]
        _tcs_param_a  = overrides.get("tcs", "")
        _tcs_filter_a = set(_tcs_param_a.split(",")) if _tcs_param_a else {"TC-01","TC-02","TC-03","TC-04"}
        _TC_DEFS_A = [d for d in _TC_DEFS_ALL_A if d["tc"] in _tcs_filter_a]
        if not _TC_DEFS_A:
            _TC_DEFS_A = _TC_DEFS_ALL_A
        _tc_runs = []
        for _tcd in _TC_DEFS_A:
            _vno      = _tcd["vno"]
            _env_file = QA_VNO_ENV_MAP.get(_vno, QA_VNO_ENV_MAP["02"])
            _folder   = QA_ASSIGNMENT_FOLDER_MAP.get(_vno, "assigment- KAO")
            _rp_out   = str(_asig_dir / f"{_tcd['tc']}.html")
            _json_out = str(_asig_dir / f"{_tcd['tc']}.json")
            _env_data = _j.load(open(QA_DIR / _env_file, encoding="utf-8"))
            _ev       = {v["key"]: v["value"] for v in _env_data["values"]}
            _apim_url = _ev.get("apimURL", "")
            _auth_b64 = _b64.b64encode(f"{_ev.get('consumerKey','')}:{_ev.get('consumerSecret','')}".encode()).decode()
            _token = ""
            try:
                _body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
                _tok_req = _ur.Request(f"{_apim_url}/token", data=_body_b,
                    headers={"Authorization": f"Basic {_auth_b64}",
                             "Content-Type": "application/x-www-form-urlencoded"})
                _ctx = _sl.create_default_context()
                _ctx.check_hostname = False; _ctx.verify_mode = _sl.CERT_NONE
                with _ur.urlopen(_tok_req, context=_ctx, timeout=15) as _r:
                    _token = _j.loads(_r.read()).get("access_token", "")
            except Exception as _te:
                print(f"[GetToken {_tcd['tc']}] error: {_te}", flush=True)
            _col_src  = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
            _col_tmp  = _cp.deepcopy(_col_src)
            _new_body = _j.dumps({
                "u_access_id_vno": _access_ids_map.get(_tcd["tc"], ""),
                "u_id_vno": _vno,
                "u_operation_type": "Alta",
                "u_scenario": "Alta de acceso",
                "u_speed_plan": _speed_plan,
                "u_address_id": _address_id,
                "u_address_mcd": "OSP",
                "u_service_ba":   _service_ba,
                "u_service_voip": _service_voip,
                "u_service_iptv": _service_iptv,
                "u_service_type": "FTTH",
            }, indent=4, ensure_ascii=False)
            for _sec in _col_tmp.get("item", []):
                if "Assignment" in _sec.get("name", ""):
                    for _req in _sec.get("item", []):
                        if _req.get("name", "") == _folder:
                            _b = _req.get("request", {}).get("body", {})
                            if _b.get("mode") == "raw":
                                _b["raw"] = _new_body
            _tmp_col = str(QA_DIR / f"_tmp_asig_suite_{_vno}.json")
            _j.dump(_col_tmp, open(_tmp_col, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _tc_runs.append({
                "tc":      _tcd["tc"],
                "vno":     _vno,
                "vno_lbl": _tcd["vno_label"],
                "sid":     _tcd["sid"],
                "label":   f"{_tcd['tc']} · {_tcd['vno_label']} (VNO {_vno})",
                "cmd":     [NEWMAN, "run", _tmp_col,
                            "-e", _env_file,
                            "--folder", _folder,
                            "--env-var", f"Token={_token}",
                            "--env-var", f"idvno={_vno}",
                            "--insecure",
                            "--reporters", "cli,json,htmlextra",
                            "--reporter-json-export", _json_out,
                            "--reporter-htmlextra-export", _rp_out,
                            "--reporter-htmlextra-title", f"Reporte QA – {_tcd['tc']} Asignación · {_tcd['vno_label']} – OnnetFibra",
                            "--reporter-htmlextra-logo", _logo_uri_a],
                "cwd":     str(QA_DIR),
                "rp_out":  _rp_out,
                "json_out": _json_out,
            })

    elif suite.get("env_type") in ("qa_ia_inicio_suite", "qa_ia_fin_suite"):
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp
        _is_inicio   = suite.get("env_type") == "qa_ia_inicio_suite"
        _ia_dir      = QA_DIR / "ia"
        _ia_dir.mkdir(parents=True, exist_ok=True)
        _logo_svg_ia = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="44">'
            b'<rect width="220" height="44" rx="4" fill="#0D1B3E"/>'
            b'<text x="12" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="700" fill="#00C8FF">ONNET</text>'
            b'<text x="105" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="400" fill="#ffffff">FIBRA</text>'
            b'</svg>'
        )
        _logo_uri_ia  = "data:image/svg+xml;base64," + _b64.b64encode(_logo_svg_ia).decode()
        _access_ids_raw_ia = overrides.get("access_ids", "")
        try:
            _access_ids_map_ia = json.loads(_access_ids_raw_ia) if _access_ids_raw_ia else {}
        except Exception:
            _access_ids_map_ia = {}
        _scenario    = overrides.get("scenario",     "Instalación")
        _service_type = overrides.get("service_type", "FTTH")
        _TC_DEFS_IA = [
            {"tc": "TC-09" if _is_inicio else "TC-13", "vno": "03", "vno_label": "Entel",
             "sid": "qa-ia-tc09" if _is_inicio else "qa-ia-tc13"},
            {"tc": "TC-10" if _is_inicio else "TC-14", "vno": "02", "vno_label": "KAO",
             "sid": "qa-ia-tc10" if _is_inicio else "qa-ia-tc14"},
            {"tc": "TC-11" if _is_inicio else "TC-15", "vno": "05", "vno_label": "DTV",
             "sid": "qa-ia-tc11" if _is_inicio else "qa-ia-tc15"},
            {"tc": "TC-12" if _is_inicio else "TC-16", "vno": "00", "vno_label": "TCH",
             "sid": "qa-ia-tc12" if _is_inicio else "qa-ia-tc16"},
        ]
        _tcs_param_ia  = overrides.get("tcs", "")
        _tcs_filter_ia = set(_tcs_param_ia.split(",")) if _tcs_param_ia else {d["tc"] for d in _TC_DEFS_IA}
        _TC_DEFS_IA = [d for d in _TC_DEFS_IA if d["tc"] in _tcs_filter_ia] or _TC_DEFS_IA
        _tc_runs = []
        for _tcd in _TC_DEFS_IA:
            _vno          = _tcd["vno"]
            _env_file     = QA_VNO_ENV_MAP.get(_vno, QA_VNO_ENV_MAP["02"])
            _vno_subfolder= QA_IA_VNO_SUBFOLDER.get(_vno, "KAO")
            _rp_out       = str(_ia_dir / f"{_tcd['tc']}.html")
            _json_out     = str(_ia_dir / f"{_tcd['tc']}.json")
            _env_data     = _j.load(open(QA_DIR / _env_file, encoding="utf-8"))
            _ev           = {v["key"]: v["value"] for v in _env_data["values"]}
            _apim_url     = _ev.get("apimURL", "")
            _auth_b64     = _b64.b64encode(f"{_ev.get('consumerKey','')}:{_ev.get('consumerSecret','')}".encode()).decode()
            _token = ""
            try:
                _body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
                _tok_req = _ur.Request(f"{_apim_url}/token", data=_body_b,
                    headers={"Authorization": f"Basic {_auth_b64}",
                             "Content-Type": "application/x-www-form-urlencoded"})
                _ctx = _sl.create_default_context()
                _ctx.check_hostname = False; _ctx.verify_mode = _sl.CERT_NONE
                with _ur.urlopen(_tok_req, context=_ctx, timeout=15) as _r:
                    _token = _j.loads(_r.read()).get("access_token", "")
            except Exception as _te:
                print(f"[GetToken {_tcd['tc']}] error: {_te}", flush=True)
            _col_src  = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
            _col_tmp  = _cp.deepcopy(_col_src)
            _new_body = _j.dumps({
                "u_id_vno":        _vno,
                "u_access_id_vno": _access_ids_map_ia.get(_tcd["tc"], ""),
                "u_scenario":      _scenario,
                "u_service_type":  _service_type,
            }, indent=4, ensure_ascii=False)
            for _sec in _col_tmp.get("item", []):
                if "Interven" in _sec.get("name", ""):
                    _sec["item"] = [sf for sf in _sec.get("item", []) if sf.get("name", "") == _vno_subfolder]
                    for _sf in _sec.get("item", []):
                        for _req in _sf.get("item", []):
                            _nm = _req.get("name", "")
                            if _is_inicio:
                                _match = _nm in ("01-Inicio Intervención", "01-Inicio Intervencion")
                            else:
                                _match = "Finaliz" in _nm and "Masiva" not in _nm
                            if _match:
                                _b = _req.get("request", {}).get("body", {})
                                if _b.get("mode") == "raw":
                                    _b["raw"] = _new_body
            _pfx = "inicio" if _is_inicio else "fin"
            _tmp_col = str(QA_DIR / f"_tmp_ia_{_pfx}_{_vno}.json")
            _j.dump(_col_tmp, open(_tmp_col, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _nf = "01-Inicio Intervención" if _is_inicio else "03-Finalización Intervención"
            _op_lbl = "IA Inicio" if _is_inicio else "IA Fin"
            _tc_runs.append({
                "tc":      _tcd["tc"],
                "vno":     _vno,
                "vno_lbl": _tcd["vno_label"],
                "sid":     _tcd["sid"],
                "label":   f"{_tcd['tc']} · {_tcd['vno_label']} (VNO {_vno})",
                "cmd":     [NEWMAN, "run", _tmp_col,
                            "-e", _env_file,
                            "--folder", _nf,
                            "--env-var", f"Token={_token}",
                            "--env-var", f"idvno={_vno}",
                            "--insecure",
                            "--reporters", "cli,json,htmlextra",
                            "--reporter-json-export", _json_out,
                            "--reporter-htmlextra-export", _rp_out,
                            "--reporter-htmlextra-title", f"Reporte QA – {_tcd['tc']} {_op_lbl} · {_tcd['vno_label']} – OnnetFibra",
                            "--reporter-htmlextra-logo", _logo_uri_ia],
                "cwd":     str(QA_DIR),
                "rp_out":  _rp_out,
                "json_out": _json_out,
            })

    # ── Suite Activación — cadena completa 6 pasos por VNO en paralelo ─────────
    _activ_runs = None
    if suite.get("env_type") == "qa_activ_suite":
        import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up, base64 as _b64, copy as _cp

        def _find_req_in_col(col, req_name):
            for it in col.get("item", []):
                if it.get("name") == req_name and "request" in it:
                    return it
                if "item" in it:
                    found = _find_req_in_col(it, req_name)
                    if found:
                        return found
            return None

        _logo_svg_activ = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="44">'
            b'<rect width="220" height="44" rx="4" fill="#0D1B3E"/>'
            b'<text x="12" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="700" fill="#00C8FF">ONNET</text>'
            b'<text x="105" y="30" font-family="Arial,Helvetica,sans-serif"'
            b' font-size="20" font-weight="400" fill="#ffffff">FIBRA</text>'
            b'</svg>'
        )
        _logo_uri_activ = "data:image/svg+xml;base64," + _b64.b64encode(_logo_svg_activ).decode()
        _access_ids_raw_activ = overrides.get("access_ids", "")
        try:
            _access_ids_map_activ = _j.loads(_access_ids_raw_activ) if _access_ids_raw_activ else {}
        except Exception:
            _access_ids_map_activ = {}
        _speed_plan   = overrides.get("speed_plan", "600/600")
        _serial_suffix = overrides.get("serial_suffix", "0000")
        _svc_ba   = overrides.get("service_ba",   "true").lower() != "false"
        _svc_voip = overrides.get("service_voip", "true").lower() != "false"
        _svc_iptv = overrides.get("service_iptv", "true").lower() != "false"
        _TC_DEFS_ACTIV = [
            {"tc":"TC-17","vno":"03","vno_label":"Entel","sid":"qa-activ-tc17"},
            {"tc":"TC-18","vno":"02","vno_label":"KAO",  "sid":"qa-activ-tc18"},
            {"tc":"TC-19","vno":"05","vno_label":"DTV",  "sid":"qa-activ-tc19"},
            {"tc":"TC-20","vno":"00","vno_label":"TCH",  "sid":"qa-activ-tc20"},
        ]
        _tcs_param_activ  = overrides.get("tcs", "")
        _tcs_filter_activ = set(_tcs_param_activ.split(",")) if _tcs_param_activ else {d["tc"] for d in _TC_DEFS_ACTIV}
        _TC_DEFS_ACTIV    = [d for d in _TC_DEFS_ACTIV if d["tc"] in _tcs_filter_activ] or _TC_DEFS_ACTIV
        _activ_dir = QA_DIR / "activacion"
        _activ_dir.mkdir(parents=True, exist_ok=True)
        _col_ff  = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
        _col_con = _j.load(open(QA_DIR / "03-Consultas.postman_collection.json", encoding="utf-8"))
        _ADDR_ID_ACTIV = "DIR02803636"
        _activ_runs = []
        for _tcd in _TC_DEFS_ACTIV:
            _vno          = _tcd["vno"]
            _env_file     = QA_VNO_ENV_MAP.get(_vno, QA_VNO_ENV_MAP["02"])
            _access_id    = _access_ids_map_activ.get(_tcd["tc"], "")
            _fact_folder  = QA_FACTIBILIDAD_FOLDER_MAP.get(_vno, "feasibility-KAO")
            _asig_folder  = QA_ASSIGNMENT_FOLDER_MAP.get(_vno, "assigment- KAO")
            _ia_subfolder = QA_IA_VNO_SUBFOLDER.get(_vno, "KAO")
            _activ_req_nm = QA_ACTIVACION_REQUEST_MAP.get(_vno, "Activation KAO")
            _ret_req_nm   = QA_RETRIEVE_REQUEST_MAP.get(_vno, "RetrieveAcces KAO")
            _env_data     = _j.load(open(QA_DIR / _env_file, encoding="utf-8"))
            _ev           = {v["key"]: v["value"] for v in _env_data["values"]}
            _apim_url     = _ev.get("apimURL", "")
            _auth_b64     = _b64.b64encode(f"{_ev.get('consumerKey','')}:{_ev.get('consumerSecret','')}".encode()).decode()
            _token = ""
            try:
                _body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
                _tok_req = _ur.Request(f"{_apim_url}/token", data=_body_b,
                    headers={"Authorization": f"Basic {_auth_b64}",
                             "Content-Type": "application/x-www-form-urlencoded"})
                _ctx = _sl.create_default_context()
                _ctx.check_hostname = False; _ctx.verify_mode = _sl.CERT_NONE
                with _ur.urlopen(_tok_req, context=_ctx, timeout=15) as _r:
                    _token = _j.loads(_r.read()).get("access_token", "")
            except Exception as _te:
                print(f"[GetToken {_tcd['tc']}] error: {_te}", flush=True)

            _base_cmd = [NEWMAN, "run", "",
                         "-e", _env_file,
                         "--env-var", f"Token={_token}",
                         "--env-var", f"idvno={_vno}",
                         "--insecure",
                         "--reporters", "cli,json,htmlextra",
                         "--reporter-htmlextra-logo", _logo_uri_activ]

            # ── Paso 1: Factibilidad ────────────────────────────────────────────
            _col_fact = _cp.deepcopy(_col_ff)
            _fact_body = _j.dumps({"u_id_vno": _vno, "u_operation_type": "Direccion Exacta",
                                   "u_address_id": _ADDR_ID_ACTIV, "u_address_mcd": "OSP",
                                   "u_service_type": "FTTH"}, indent=4, ensure_ascii=False)
            for _sec in _col_fact.get("item", []):
                if "Factibilidad" in _sec.get("name", ""):
                    for _req in _sec.get("item", []):
                        if _req.get("name", "") == _fact_folder:
                            _b = _req.get("request", {}).get("body", {})
                            if _b.get("mode") == "raw": _b["raw"] = _fact_body
            _tmp_fact = str(QA_DIR / f"_tmp_activ_fact_{_vno}.json")
            _j.dump(_col_fact, open(_tmp_fact, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _rp_fact = str(_activ_dir / f"{_tcd['tc']}_fact.html")
            _js_fact = str(_activ_dir / f"{_tcd['tc']}_fact.json")
            _cmd_fact = list(_base_cmd); _cmd_fact[2] = _tmp_fact
            _cmd_fact += ["--folder", _fact_folder,
                          "--reporter-json-export", _js_fact,
                          "--reporter-htmlextra-export", _rp_fact,
                          "--reporter-htmlextra-title", f"Reporte QA – {_tcd['tc']} Factibilidad · {_tcd['vno_label']}"]

            # ── Paso 2: Asignación ──────────────────────────────────────────────
            _col_asig = _cp.deepcopy(_col_ff)
            _asig_body = _j.dumps({
                "u_access_id_vno": _access_id, "u_id_vno": _vno,
                "u_operation_type": "Alta", "u_scenario": "Alta de acceso",
                "u_speed_plan": _speed_plan, "u_address_id": _ADDR_ID_ACTIV,
                "u_address_mcd": "OSP",
                "u_service_ba": _svc_ba, "u_service_voip": _svc_voip,
                "u_service_iptv": _svc_iptv, "u_service_type": "FTTH",
            }, indent=4, ensure_ascii=False)
            for _sec in _col_asig.get("item", []):
                if "Assignment" in _sec.get("name", ""):
                    for _req in _sec.get("item", []):
                        if _req.get("name", "") == _asig_folder:
                            _b = _req.get("request", {}).get("body", {})
                            if _b.get("mode") == "raw": _b["raw"] = _asig_body
            _tmp_asig = str(QA_DIR / f"_tmp_activ_asig_{_vno}.json")
            _j.dump(_col_asig, open(_tmp_asig, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _rp_asig = str(_activ_dir / f"{_tcd['tc']}_asig.html")
            _js_asig = str(_activ_dir / f"{_tcd['tc']}_asig.json")
            _cmd_asig = list(_base_cmd); _cmd_asig[2] = _tmp_asig
            _cmd_asig += ["--folder", _asig_folder,
                          "--reporter-json-export", _js_asig,
                          "--reporter-htmlextra-export", _rp_asig,
                          "--reporter-htmlextra-title", f"Reporte QA – {_tcd['tc']} Asignación · {_tcd['vno_label']}"]

            # ── Paso 3: IA Inicio ───────────────────────────────────────────────
            _col_ia = _cp.deepcopy(_col_ff)
            _ia_body = _j.dumps({"u_id_vno": _vno, "u_access_id_vno": _access_id,
                                  "u_scenario": "Instalación", "u_service_type": "FTTH"},
                                 indent=4, ensure_ascii=False)
            for _sec in _col_ia.get("item", []):
                if "Interven" in _sec.get("name", ""):
                    _sec["item"] = [sf for sf in _sec.get("item", []) if sf.get("name", "") == _ia_subfolder]
                    for _sf in _sec.get("item", []):
                        for _req in _sf.get("item", []):
                            if _req.get("name", "") in ("01-Inicio Intervención", "01-Inicio Intervencion"):
                                _b = _req.get("request", {}).get("body", {})
                                if _b.get("mode") == "raw": _b["raw"] = _ia_body
            _tmp_ia = str(QA_DIR / f"_tmp_activ_ia_{_vno}.json")
            _j.dump(_col_ia, open(_tmp_ia, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _rp_ia = str(_activ_dir / f"{_tcd['tc']}_ia.html")
            _js_ia = str(_activ_dir / f"{_tcd['tc']}_ia.json")
            _cmd_ia = list(_base_cmd); _cmd_ia[2] = _tmp_ia
            _cmd_ia += ["--folder", "01-Inicio Intervención",
                        "--reporter-json-export", _js_ia,
                        "--reporter-htmlextra-export", _rp_ia,
                        "--reporter-htmlextra-title", f"Reporte QA – {_tcd['tc']} IA Inicio · {_tcd['vno_label']}"]

            # ── Pasos 4+5: Activación × 2 en mismo Newman run ──────────────────
            _activ_body_j = _j.dumps({
                "u_id_vno": _vno, "u_access_id_vno": _access_id,
                "u_operation_type": "A", "u_speed_plan": _speed_plan,
                "u_service_ba": _svc_ba, "u_service_voip": _svc_voip,
                "u_service_iptv": _svc_iptv,
                **( {"u_serial_number": QA_ACTIV_SERIAL_BASE[_vno] + _serial_suffix}
                    if _vno in QA_ACTIV_SERIAL_BASE else {} )
            }, indent=4, ensure_ascii=False)
            _act_req = _find_req_in_col(_cp.deepcopy(_col_ff), _activ_req_nm)
            if _act_req:
                _b = _act_req.get("request", {}).get("body", {})
                if _b.get("mode") == "raw": _b["raw"] = _activ_body_j
            _act_req2 = _cp.deepcopy(_act_req) if _act_req else None
            if _act_req2: _act_req2["name"] = _act_req2.get("name","") + " (idempotencia)"
            _tmp_act = str(QA_DIR / f"_tmp_activ_act_{_vno}.json")
            _act_items = [i for i in [_act_req, _act_req2] if i]
            _j.dump({"info": _col_ff.get("info", {}), "item": _act_items},
                    open(_tmp_act, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _rp_act  = str(_activ_dir / f"{_tcd['tc']}.html")
            _js_act  = str(_activ_dir / f"{_tcd['tc']}.json")
            _cmd_act = list(_base_cmd); _cmd_act[2] = _tmp_act
            _cmd_act += ["--reporter-json-export", _js_act,
                         "--reporter-htmlextra-export", _rp_act,
                         "--reporter-htmlextra-title", f"Reporte QA – {_tcd['tc']} Activación × 2 · {_tcd['vno_label']}"]

            # ── Paso 6: Retrieve Access ─────────────────────────────────────────
            _ret_req = _find_req_in_col(_cp.deepcopy(_col_con), _ret_req_nm)
            _ret_body_j = _j.dumps({"u_id_vno": _vno, "u_access_id_vno": _access_id,
                                     "u_flag_scope": "0"}, indent=4, ensure_ascii=False)
            if _ret_req:
                _b = _ret_req.get("request", {}).get("body", {})
                if _b.get("mode") == "raw": _b["raw"] = _ret_body_j
            _tmp_ret = str(QA_DIR / f"_tmp_activ_ret_{_vno}.json")
            _j.dump({"info": _col_con.get("info", {}), "item": [_ret_req] if _ret_req else []},
                    open(_tmp_ret, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _rp_ret  = str(_activ_dir / f"{_tcd['tc']}_ret.html")
            _js_ret  = str(_activ_dir / f"{_tcd['tc']}_ret.json")
            _cmd_ret = list(_base_cmd); _cmd_ret[2] = _tmp_ret
            _cmd_ret += ["--reporter-json-export", _js_ret,
                         "--reporter-htmlextra-export", _rp_ret,
                         "--reporter-htmlextra-title", f"Reporte QA – {_tcd['tc']} Retrieve Access · {_tcd['vno_label']}"]

            _activ_runs.append({
                "tc":      _tcd["tc"], "vno": _vno, "vno_lbl": _tcd["vno_label"],
                "sid":     _tcd["sid"],
                "label":   f"{_tcd['tc']} · {_tcd['vno_label']} (VNO {_vno})",
                "steps": [
                    ("1/6 Factibilidad",     _cmd_fact, _js_fact),
                    ("2/6 Asignación",       _cmd_asig, _js_asig),
                    ("3/6 IA Inicio",        _cmd_ia,   _js_ia),
                    ("4+5/6 Activación × 2", _cmd_act,  _js_act),
                    ("6/6 Retrieve Access",  _cmd_ret,  _js_ret),
                ],
                "cwd":    str(QA_DIR),
                "rp_out": _rp_act,
            })

    if _activ_runs is not None:
        async def sse_activ():
            yield f"data: {json.dumps({'e':'start','id':suite_id,'label':suite['label']})}\n\n"
            yield f"data: {json.dumps({'e':'line','t':'━'*55})}\n\n"
            yield f"data: {json.dumps({'e':'line','t':f'Suite Activación — {len(_activ_runs)} TCs · cadena completa 6 pasos'})}\n\n"
            yield f"data: {json.dumps({'e':'line','t':'━'*55})}\n\n"
            _env_activ = {**os.environ,
                          "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
                          "PYTHONUNBUFFERED": "1",
                          "NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}
            _out_q_activ = asyncio.Queue()
            _results_activ = []

            async def _run_activ(tr):
                await _out_q_activ.put(("L", tr["tc"], f"▶ {tr['label']} iniciando…"))
                _last_json = None
                _overall   = 1
                for _step_lbl, _step_cmd, _step_json in tr["steps"]:
                    await _out_q_activ.put(("L", tr["tc"], f"── Paso {_step_lbl} ──"))
                    _step_code = 1
                    async for _k, _v in _iter_proc(_step_cmd, tr["cwd"], _env_activ):
                        if _k == "L":
                            await _out_q_activ.put(("L", tr["tc"], _v))
                        elif _k == "D":
                            _step_code = _v
                    if _step_json:
                        _last_json = _step_json
                    # Paso 4+5 puede tener código ≠ 0 por el error 21 esperado — no es fallo del TC
                    if "4+5" not in _step_lbl and _step_code != 0:
                        await _out_q_activ.put(("L", tr["tc"], f"✗ {_step_lbl} falló (código {_step_code}) — deteniendo"))
                        await _out_q_activ.put(("D", tr, 1, _last_json))
                        return
                    if "4+5" in _step_lbl:
                        _overall = 0   # si llegamos hasta aquí Activación OK
                await _out_q_activ.put(("D", tr, _overall, _last_json))

            _tasks_activ = [asyncio.create_task(_run_activ(tr)) for tr in _activ_runs]
            _remaining_activ = len(_activ_runs)
            while _remaining_activ > 0:
                _item = await _out_q_activ.get()
                if _item[0] == "L":
                    yield f"data: {json.dumps({'e':'line','tc':_item[1],'t':_item[2]})}\n\n"
                elif _item[0] == "D":
                    _remaining_activ -= 1
                    _tr2, _code, _last_json = _item[1], _item[2], _item[3]
                    _has_rp = bool(Path(_tr2["rp_out"]).exists())
                    _sym = "✓" if _code == 0 else "✗"
                    _results_activ.append({"tc": _tr2["tc"], "vno_lbl": _tr2["vno_lbl"],
                                           "sid": _tr2["sid"], "code": _code, "has_rp": _has_rp})
                    _tc_msg = f"{_sym} {_tr2['label']} — código {_code}"
                    yield f"data: {json.dumps({'e':'line','tc':_tr2['tc'],'t':_tc_msg})}\n\n"
                    yield f"data: {json.dumps({'e':'tc_done','tc':_tr2['tc'],'code':_code,'has_report':_has_rp,'sid':_tr2['sid']})}\n\n"
                    try:
                        _jp = Path(_last_json) if _last_json else None
                        if _jp and _jp.exists():
                            _jdata = _j.loads(_jp.read_text(encoding="utf-8"))
                            _rsps = []
                            for _ex in _jdata.get("run", {}).get("executions", []):
                                _resp  = _ex.get("response") or {}
                                _stream = _resp.get("stream") or {}
                                if isinstance(_stream, dict) and _stream.get("type") == "Buffer":
                                    try: _rbody = bytes(_stream["data"]).decode("utf-8", errors="replace")
                                    except Exception: _rbody = ""
                                else:
                                    _rbody = _resp.get("body", "") or ""
                                _req2  = _ex.get("request") or {}
                                _url2  = _req2.get("url") or {}
                                _url_r = _url2.get("raw", "") if isinstance(_url2, dict) else str(_url2)
                                _rsps.append({
                                    "name":    _ex.get("item", {}).get("name", ""),
                                    "method":  _req2.get("method", "GET"),
                                    "url":     _url_r[:200],
                                    "code":    _resp.get("code", 0),
                                    "status":  _resp.get("status", ""),
                                    "time_ms": _resp.get("responseTime", 0),
                                    "body":    _rbody[:6144],
                                })
                            if _rsps:
                                yield f"data: {_j.dumps({'e':'tc_response','tc':_tr2['tc'],'responses':_rsps})}\n\n"
                    except Exception:
                        pass
            yield f"data: {json.dumps({'e':'line','t':'━'*55})}\n\n"
            _n_ok_activ   = sum(1 for r in _results_activ if r["code"] == 0)
            _n_fail_activ = len(_results_activ) - _n_ok_activ
            yield f"data: {json.dumps({'e':'line','t':f'Resultado: {_n_ok_activ}/{len(_results_activ)} TCs OK'})}\n\n"
            _rows_activ = ""
            for _r in sorted(_results_activ, key=lambda x: x["tc"]):
                _color = "#3DD68C" if _r["code"] == 0 else "#FF6B6B"
                _st    = "✓ OK" if _r["code"] == 0 else "✗ FAIL"
                _lnk   = (f'<a href="/api/report/{_r["sid"]}" target="_blank" style="color:#00C8D4">Ver reporte</a>'
                          if _r["has_rp"] else "—")
                _rows_activ += (f'<tr><td>{_r["tc"]}</td><td>{_r["vno_lbl"]}</td>'
                                f'<td style="color:{_color};font-weight:700">{_st}</td><td>{_lnk}</td></tr>')
            _idx_activ = (
                '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
                '<title>QA Activación</title>'
                '<style>body{font-family:Arial,sans-serif;background:#0D1B3E;color:#DCE2F6;padding:32px}'
                'h1{color:#00C8FF;margin-bottom:8px}p{color:#6272A4;margin-bottom:20px}'
                'table{border-collapse:collapse;width:100%}th,td{border:1px solid #262558;padding:9px 14px;text-align:left}'
                'th{background:#1A1A3E;color:#6272A4;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}'
                '</style></head><body>'
                '<h1>QA Activación</h1>'
                f'<p>{_n_ok_activ}/{len(_results_activ)} TCs OK</p>'
                '<table><tr><th>TC</th><th>VNO</th><th>Estado</th><th>Reporte</th></tr>'
                f'{_rows_activ}</table></body></html>'
            )
            (_activ_dir / "index.html").write_text(_idx_activ, encoding="utf-8")
            _has_idx_activ = (_activ_dir / "index.html").exists()
            yield f"data: {json.dumps({'e':'done','code':0 if _n_fail_activ==0 else 1,'passed':_n_ok_activ,'failed':_n_fail_activ,'requests':len(_results_activ),'has_report':_has_idx_activ,'report_id':suite_id})}\n\n"
            await asyncio.sleep(0.15)

        return StreamingResponse(sse_activ(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform",
                     "X-Accel-Buffering": "no",
                     "Connection": "keep-alive"})

    if _tc_runs is not None:
        async def sse_parallel():
            yield f"data: {json.dumps({'e':'start','id':suite_id,'label':suite['label']})}\n\n"
            yield f"data: {json.dumps({'e':'line','t':'━'*55})}\n\n"
            _suite_lbl = suite.get("label","Suite")
            yield f"data: {json.dumps({'e':'line','t':f'{_suite_lbl} — {len(_tc_runs)} TCs en paralelo'})}\n\n"
            yield f"data: {json.dumps({'e':'line','t':'━'*55})}\n\n"

            _env = {**os.environ,
                    "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
                    "PYTHONUNBUFFERED": "1",
                    "NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}
            _out_q = asyncio.Queue()
            _results = []

            async def _run_tc(tr):
                await _out_q.put(("L", tr["tc"], "▶ " + tr["label"] + " iniciando…"))
                async for _k, _v in _iter_proc(tr["cmd"], tr["cwd"], _env):
                    if _k == "L":
                        await _out_q.put(("L", tr["tc"], _v))
                    elif _k == "D":
                        await _out_q.put(("D", tr, _v))
                        return
                    elif _k == "E":
                        await _out_q.put(("L", tr["tc"], "ERROR: " + _v))
                        await _out_q.put(("D", tr, -1))
                        return

            for _tr in _tc_runs:
                asyncio.create_task(_run_tc(_tr))

            _remaining = len(_tc_runs)
            while _remaining > 0:
                _item = await _out_q.get()
                if _item[0] == "L":
                    yield f"data: {json.dumps({'e':'line','tc':_item[1],'t':_item[2]})}\n\n"
                elif _item[0] == "D":
                    _tr2, _code = _item[1], _item[2]
                    _remaining -= 1
                    _has_rp = bool(Path(_tr2["rp_out"]).exists())
                    _sym = "✓" if _code == 0 else "✗"
                    _results.append({"tc": _tr2["tc"], "vno_lbl": _tr2["vno_lbl"],
                                     "sid": _tr2["sid"], "code": _code, "has_rp": _has_rp})
                    _tc_msg = _sym + " " + _tr2["label"] + " — código " + str(_code)
                    yield f"data: {json.dumps({'e':'line','tc':_tr2['tc'],'t':_tc_msg})}\n\n"
                    yield f"data: {json.dumps({'e':'tc_done','tc':_tr2['tc'],'code':_code,'has_report':_has_rp,'sid':_tr2['sid']})}\n\n"
                    # Emitir respuestas HTTP del TC
                    try:
                        _jpath = Path(_tr2["json_out"])
                        if _jpath.exists():
                            _jdata = _j.loads(_jpath.read_text(encoding="utf-8"))
                            _rsps = []
                            for _ex in _jdata.get("run", {}).get("executions", []):
                                _resp = _ex.get("response") or {}
                                _stream = _resp.get("stream") or {}
                                if isinstance(_stream, dict) and _stream.get("type") == "Buffer":
                                    try:
                                        _rbody = bytes(_stream["data"]).decode("utf-8", errors="replace")
                                    except Exception:
                                        _rbody = ""
                                else:
                                    _rbody = _resp.get("body", "") or ""
                                _req = _ex.get("request") or {}
                                _url_obj = _req.get("url") or {}
                                _url_raw = _url_obj.get("raw", "") if isinstance(_url_obj, dict) else str(_url_obj)
                                _rsps.append({
                                    "name":    _ex.get("item", {}).get("name", ""),
                                    "method":  _req.get("method", "GET"),
                                    "url":     _url_raw[:200],
                                    "code":    _resp.get("code", 0),
                                    "status":  _resp.get("status", ""),
                                    "time_ms": _resp.get("responseTime", 0),
                                    "body":    _rbody[:6144],
                                })
                            if _rsps:
                                yield f"data: {_j.dumps({'e':'tc_response','tc':_tr2['tc'],'responses':_rsps})}\n\n"
                    except Exception:
                        pass

            yield f"data: {json.dumps({'e':'line','t':'━'*55})}\n\n"
            _n_ok   = sum(1 for r in _results if r["code"] == 0)
            _n_fail = len(_results) - _n_ok
            yield f"data: {json.dumps({'e':'line','t':f'Resultado: {_n_ok}/{len(_results)} TCs OK'})}\n\n"

            _rows = ""
            for _r in sorted(_results, key=lambda x: x["tc"]):
                _color = "#3DD68C" if _r["code"] == 0 else "#FF6B6B"
                _st    = "✓ OK" if _r["code"] == 0 else "✗ FAIL"
                _lnk   = (f'<a href="/api/report/{_r["sid"]}" target="_blank" style="color:#00C8D4">Ver reporte</a>'
                          if _r["has_rp"] else "—")
                _rows += (f'<tr><td>{_r["tc"]}</td><td>{_r["vno_lbl"]}</td>'
                          f'<td style="color:{_color};font-weight:700">{_st}</td><td>{_lnk}</td></tr>')

            _idx_html = (
                '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
                '<title>QA Factibilidad</title>'
                '<style>body{font-family:Arial,sans-serif;background:#0D1B3E;color:#DCE2F6;padding:32px}'
                'h1{color:#00C8FF;margin-bottom:8px}p{color:#6272A4;margin-bottom:20px}'
                'table{border-collapse:collapse;width:100%}th,td{border:1px solid #262558;padding:9px 14px;text-align:left}'
                'th{background:#1A1A3E;color:#6272A4;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}'
                '</style></head><body>'
                '<h1>QA Factibilidad</h1>'
                f'<p>Dirección: DIR02803636 &nbsp;·&nbsp; {_n_ok}/{len(_results)} TCs OK</p>'
                '<table><tr><th>TC</th><th>VNO</th><th>Estado</th><th>Reporte</th></tr>'
                f'{_rows}</table></body></html>'
            )
            (QA_DIR / "factibilidad" / "index.html").write_text(_idx_html, encoding="utf-8")
            _has_idx = (QA_DIR / "factibilidad" / "index.html").exists()
            yield f"data: {json.dumps({'e':'done','code':0 if _n_fail==0 else 1,'passed':_n_ok,'failed':_n_fail,'requests':len(_results),'has_report':_has_idx,'report_id':suite_id})}\n\n"
            await asyncio.sleep(0.15)

        return StreamingResponse(sse_parallel(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform",
                     "X-Accel-Buffering": "no",
                     "Connection": "keep-alive"})

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
/* ── Fact view: 4 consolas paralelas ───────────────────────────────────────── */
#fact-sel-bar{display:flex;align-items:center;gap:6px;padding:6px 10px 4px;flex-shrink:0;flex-wrap:wrap;border-bottom:1px solid var(--brd)}
#fact-sel-bar .fsb-lbl{font-size:.62rem;color:var(--txt3);font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-right:2px}
.tc-sel-btn{font-size:.65rem;font-weight:700;padding:3px 10px;border-radius:12px;border:1px solid var(--brd);background:transparent;color:var(--txt3);cursor:pointer;transition:background .15s,color .15s,border-color .15s;white-space:nowrap}
.tc-sel-btn.on{border-color:var(--acc);background:rgba(0,200,255,.12);color:var(--acc)}
.fsb-sep{width:1px;height:16px;background:var(--brd);margin:0 2px}
.fsb-all{font-size:.61rem;padding:2px 7px;border-radius:10px;border:1px solid var(--brd);background:transparent;color:var(--txt3);cursor:pointer}
.fsb-all:hover{color:var(--txt);border-color:var(--txt2)}
#fact-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;flex:1;overflow:hidden;padding:8px 10px;min-height:0}
#asig-form-bar{display:flex;align-items:center;gap:8px;padding:6px 10px 5px;flex-shrink:0;flex-wrap:wrap;border-bottom:1px solid var(--brd);background:var(--card)}
#asig-form-bar .afb-lbl{font-size:.6rem;color:var(--txt3);font-weight:700;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
#asig-form-bar input,#asig-form-bar select{font-size:.68rem;padding:3px 7px;border-radius:4px;border:1px solid var(--brd);background:var(--input,var(--card));color:var(--txt);outline:none}
#asig-form-bar input:focus,#asig-form-bar select:focus{border-color:var(--acc)}
#asig-form-bar input.wide{width:170px}#asig-form-bar input.med{width:110px}
#asig-access-preview{display:flex;gap:10px;flex-wrap:wrap;padding:3px 10px 5px;background:var(--card);border-bottom:1px solid var(--brd);flex-shrink:0}
.aap-item{font-size:.62rem;font-family:var(--mono);display:flex;align-items:center;gap:4px}
.aap-vno{color:var(--txt3);font-size:.58rem}.aap-id{color:var(--acc)}.aap-empty{color:var(--txt3);font-style:italic}
#asig-sel-bar,#ia-sel-bar,#activ-sel-bar{display:flex;align-items:center;gap:6px;padding:5px 10px 4px;flex-shrink:0;flex-wrap:wrap;border-bottom:1px solid var(--brd)}
#asig-sel-bar .fsb-lbl,#ia-sel-bar .fsb-lbl,#activ-sel-bar .fsb-lbl{font-size:.62rem;color:var(--txt3);font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-right:2px}
#asig-grid,#ia-grid,#activ-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;flex:1;overflow:hidden;padding:8px 10px;min-height:0}
#ia-form-bar,#activ-form-bar{display:flex;align-items:center;gap:8px;padding:6px 10px 5px;flex-shrink:0;flex-wrap:wrap;border-bottom:1px solid var(--brd);background:var(--card)}
#ia-access-preview,#activ-access-preview{display:flex;gap:10px;flex-wrap:wrap;padding:3px 10px 5px;background:var(--card);border-bottom:1px solid var(--brd);flex-shrink:0}
#activ-form-bar input,#activ-form-bar select{font-size:.68rem;padding:3px 7px;border-radius:4px;border:1px solid var(--brd);background:var(--input,var(--card));color:var(--txt);outline:none}
#activ-form-bar input:focus{border-color:var(--acc)}
#activ-form-bar input.wide{width:170px}
.aap-serial{color:var(--txt3);font-size:.58rem;margin-left:2px}
.activ-svc{font-size:.65rem;color:var(--txt);display:flex;align-items:center;gap:3px;cursor:pointer}
#ia-form-bar .afb-lbl{font-size:.6rem;color:var(--txt3);font-weight:700;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
#ia-form-bar input,#ia-form-bar select{font-size:.68rem;padding:3px 7px;border-radius:4px;border:1px solid var(--brd);background:var(--input,var(--card));color:var(--txt);outline:none}
#ia-form-bar input:focus,#ia-form-bar select:focus{border-color:var(--acc)}
#ia-form-bar input.wide{width:170px}
#ia-access-preview{display:flex;gap:10px;flex-wrap:wrap;padding:3px 10px 5px;background:var(--card);border-bottom:1px solid var(--brd);flex-shrink:0}
#activ-form-bar label.activ-svc input{width:auto;padding:0;border:none;background:none}
.ia-mode-badge{font-size:.62rem;font-weight:700;padding:2px 8px;border-radius:10px;margin-left:4px}
.ia-mode-badge.inicio{background:rgba(255,159,139,.18);color:#FF9F8B}
.ia-mode-badge.fin{background:rgba(183,147,255,.18);color:#B793FF}
.fact-panel{display:flex;flex-direction:column;background:var(--term);border:1px solid var(--brd);border-radius:6px;overflow:hidden;min-height:0}
.fp-hdr{display:flex;align-items:center;gap:6px;padding:5px 10px;background:var(--card);border-bottom:1px solid var(--brd);flex-shrink:0}
.fp-dot{width:10px;height:10px;border-radius:50%;background:var(--txt3);flex-shrink:0;transition:background .25s}
.fp-dot.running{background:var(--warn);animation:fpulse .9s ease-in-out infinite}
.fp-dot.passed{background:var(--ok)}
.fp-dot.failed{background:var(--err)}
@keyframes fpulse{0%,100%{opacity:1}50%{opacity:.3}}
.fp-name{font-size:.71rem;font-weight:700;color:var(--txt);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fp-badge{font-size:.63rem;font-weight:700;padding:1px 6px;border-radius:10px;flex-shrink:0}
.fp-badge.idle{background:var(--brd);color:var(--txt3)}
.fp-badge.running{background:rgba(255,179,71,.18);color:var(--warn)}
.fp-badge.passed{background:var(--okd);color:var(--ok)}
.fp-badge.failed{background:var(--errd);color:var(--err)}
.fp-rpt{font-size:.63rem;color:var(--acc);text-decoration:none;padding:2px 6px;border:1px solid var(--acc);border-radius:4px;white-space:nowrap;flex-shrink:0;opacity:0;pointer-events:none;transition:opacity .2s}
.fp-rpt.show{opacity:1;pointer-events:auto}
.fact-term{flex:1 1 0;overflow-y:auto;overflow-x:hidden;padding:7px 10px;font-family:var(--mono);font-size:.68rem;line-height:1.5;min-height:40px}
.fp-resp-bar{display:flex;align-items:center;gap:6px;padding:3px 8px;background:var(--card);border-top:1px solid var(--brd);flex-shrink:0;font-size:.6rem}
.fp-resp-bar .fr-label{color:var(--txt3);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.fp-resp-bar .fr-scode{font-weight:700;padding:1px 5px;border-radius:3px;flex-shrink:0}
.fp-resp-bar .fr-scode.ok{background:var(--okd);color:var(--ok)}.fp-resp-bar .fr-scode.err{background:var(--errd);color:var(--err)}.fp-resp-bar .fr-scode.warn{background:rgba(255,179,71,.15);color:var(--warn)}
.fp-resp-bar .fr-stime{color:var(--txt3)}.fp-resp-bar .fr-sname{color:var(--txt2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fp-resp{flex:0 0 130px;overflow-y:auto;overflow-x:hidden;padding:6px 8px;background:var(--term);font-family:var(--mono);font-size:.64rem;line-height:1.5}
.fp-resp .fr-empty{color:var(--txt3);font-size:.68rem;font-family:var(--sans)}
.fp-resp pre{margin:0;white-space:pre-wrap;word-break:break-all;color:var(--txt)}
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
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAlgAAACWCAYAAAACG/YxAAAACXBIWXMAACxKAAAsSgF3enRNAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAHc1JREFUeJzt3XmYXFWd//H393bXvd3ZqiqJCwgDIoMLIiAzP4Xxx6gw4AiICPgbR1F+yOagoiwGAQm4ICCgwoAEcEHUYYjCKLiBGw/CgIiDqKg4IirKICF1KwvdVdVV3/mjqpNO0tXpqjpV1Z18Xs/D86SWPuebptP96XvP+R5zd0REREQknKjfBYiIiIhsaRSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAhvs18Tz1/DMsTF2rcJzI2ORz4KwZ86IG0+483Alx0MOpa7NtZrFmRo7bOZtXsnyU4dqt+oIbWgVO9ecbLPXK1kedKi0M3ZS4CUekZnqPYNVnnh6IY+1M36/TPX3GnBWjOT4/VQfHxfZqzuVzVw2xtrSIn618fNzV7BNJcO2/aipn8pZ7m/l/TP1ayaCdDTLbzf3vonfPwdrPPl0nj9MZ/zhlB2qxmKASsTvfT4rOqu4N6b58yKYyCiWSvyPP4M1vZqzmXlreVZ5jO3GH8+k7/Hm7j2bLC6yF85bzDgQ54U9m7g7RhzuxrmpMsANvoCVIQePixxvzrJpvPWnbry91W+g/ZKkfA04pNnrg2M8Z+1i/tzm2H+Czf7wrOBcWs6ztJsBOaSp/l7mXD2a54TNfHzv/pHPHD8p5TYNCUnKucDS3pfTX6Uc1sr7Z/DXzK2lXPPvH+Mmfv8055rRPMdPZ/ChAsvc6u81WOGwqrNyN6vq8JgZd1PjhlKen7czSAs/L0KqAb8Ebo6Mz4xk+V2P5wcgTvm+wSsnPPVwOceuDmP9qGeinlzBSlIOBc40+D8AM/afbmuGDfbD2C+ucelQkc+ac+FIjkd7XMfu5tyTFLhkNoWGPspgLIlTDoojji0v4N5+FyQiM4/DYur/dZXBX+O8CuOspMg3qXJaaSEPdXveACJgV2DXmrNkqMDnSgOcEfpiw1SGi+y3UbgC2CUu8E/k+UKv6mimqwEreYoX+ABXGryqm/PMAIk7Jzq8LUm5oJzjAodyD+cfbISGwzNwbCXHHT2ce7Z6sdW4e6jAtaUxTp0Jl7pFZqif9LuAcQ7/3e8ausr5RyJePZRy+miOy9sZonHlbcplAx1z5mFsB8xtPJNx47i4xmviVRxeXsB9XZ1/vAznnElfMJYa3NDvq1hdC1hxyjE2wOUGc7o1xww0DJwXpxwybPy/kSyP9Hj+nSP4/lCBa0pVTvPFrO7x/LNN5MbxcYYDhoqcMJrltn4XJDLTTHardavgnBVF3NDVKSIGqbFDzXmNwbHAAiBxuCwpsm0py/tbH5SbSptZNhCCgWVSdgeOMjiR+s/67a3G94aLHDaS5TvdnH9oFQc67Nt46A5XGpzUeLxzJuUocny2mzVsTvCAZWBxylLbCtc5TPA3Nee+zEoOqSzk7h7PbW4cHw8qNLRgR3e+naQsLw/wL7NlYauIdI9HrOjRL8kPA7fbas6Pq3yW8TWqzhlxykPlHNf3oIaWOTg5HgAeGE65rAqfa9yum1dzbo5X8epuXsly59wJxdxYyXNyXOTV4+u7Dc4x+GKP7yZtIHjAyqRczvoUOR1V4AngL8zs3XCLgG2AZJrvXxhFfDtexf59WuczMTS8w+fzVB9qmG2OzFTZN055XznH5/tdjIhsPXw+Txm8PklZ5vWrWURwqaXc4jnSftc3lZEcvzc4IE75InAkMM9qfNlWsWc31mQNFTgI4+WNh1VqnOtQTeBc4N8bz++YKfJWslwbev7pChqwkgJnmW0+XBnchfFVH+OW8iIe9vpuhFlhzkq2HzMOMjgMY3+mbi8xL6px69Aq9hldwG96VeNGjsxU2Tcp8q5SluV9qmHWMHgWcF2S8saBGu94eiF/7HdNIrJ1cKhZjhPiIi/GebnD4hhOBT7Q79o2x6FiKW+Nc+wC7A78VVzjYuCY4HPZ+rVX5nxmtNGSpZxleZyyBHhp47UPGHy+X1exggWs4ZRXYpw35ZuMeyLn/SM5fhBq3l5r/MC9CrgqWcmLiDiXemKflMNianzFHuNlvh0jvapzIoNn4dyYpNw6UOXEpxfxp37UMcscVI342VDK0lKOy2fTLwGtMFiBc3O/6wit2SJfc+4HrulJDcZeNL7RN6mlJ3XI7OJQG6rxQTe+AYBxrMF5/V6wPR2+I6PxKo63GvcABrwtWcklpYX8ItQcja4E4x0JRiPnQ+vmBx+qcZZHfLPx1F9lChxDnqtCzd+KIAHLVjA/HuQLwECTt4wZnDKabW9XxEzV2Er7xjjlaKuHrma3D3eL53MOtLFgMayDqwP8PC6ypJLlGt9SGmZ0T9bhE0nKEUmV4yZrXDnbOfyhNM0eQVuC0Ty3ALf0Yq5Gz62mAWu6vZlk61Mq8v04yyjGEM6zM6vYi1nSUqa8gB/FKd816nd4POIY6lfhOmZgMevXXrlx5dP5De8yjC7kW43eWK8CMOMD9hjX9eMCR5Du6fEA5wDPafJyMTIObHfL6WxQzvG5mrMfTHGv2TllaDXPDzap8+02PzJnzrK4wLeGU3YMVs/MV8S4p50PdHgFEf+VFDjD+nj6gYhsHXxHRrEJdxqcPfpYTuuML6/7o/HaUMPGRd4A6z4Xa5JBLpz0jRFnsP4CwrbJXN4eqoZWdByw5q/hmTRfd1U15y0jWb7X6TwhxCt5eZJyXZLySJJSSlK8hf9WxCnfi4ucYJNcqarkuavmvJ7m93pjr3J2qL/LYJVjzDkI2lwjZBxQg18kRZZY8yuPW5K15Sz7uHECtNHzyhjC+Giccn+8ir8NX56IyAaeHv+D1VjUz0JaZjyw7s/OLvYk8zofEsM3WIt28ep5/GWy95YX8CPg6+tKMM60xxjutIZWdRywymO8EyYv3OC00Ty3djpHpwwsKfJRi7gbeCvwXCBucZhFBq8y56o45aG43v9jA5U8dxqcNsUY/zRnJdu3OG9To3m+UXZ2c7iM9tYIzcG5IC5yZ7KSF4Wqa6Zy8HKWqyPYzeH2Nod5idW4O075pD2xrsmeiEhYxjPW/7HrR/YENeA8OeFhlMQ8q9Mx4yJvpL54HoMV5Rofn/IDnDNZ/3Nxm2Re93uDbayjgGX1RWxvafLyT0s5Lutk/BAMojjlepwz6g+D2MngrqECB238QinHFdD0XMDBqjX9fLXF8xTLOU6uOa/E+XV7g7A3EQ8kBS6w1oPnrDOS49FyjgMw3ghtta8YNHh3nPDgcJH9Q9cnIlu34ZQdcZ49/tgs3CLxnvANWy55rbNfRg0inLMmPHW+L5w6dJby/Axb17IBN5bY471tfN5RwMrUb5U8d7LXzHjfTNh5FRc5DXhzF4ae68aNyVMbHlrtUDObYjG7cUQXaqGS587yWvbEuZD2+omNn9H343hVY4fGFq6UZXkmw66wfr1Ai3aqObclKZ+31bPsEr6IzFg122ADxOrRkdmxwH1cFRZOfDxAZ3284gJvAnZrPPxTac30dgVGcBbjy3acZydz+JdO6mhVZ1ewqry6yUv/PRM6iCcFXozz4S5OMYcBPrjxk6NZbqfenXcye3Trh7Fvx0gpzxkOf0P754ftZjXu2lpuga2ZyxOlHEea8zpoq32FAUfFNX6eFLsTnkVk6xGn7IHznvHH5vybb7N+PdZsYL7BkpO1I/n2WwMZDBCtX7/sxtLp7ggcyfI78wnH5ThLbAXz262lVZ3tiLImi32d/+ho3EDcOM4g0+VpDrEVzN/k3D/na9ik67GipMZLaX8N0GaVczxg8PK4yCk45zH97vPjxm+BHTxc5PiRLN/tRp3T0eg1Vt9W7xwKvBjjI+Z8ZzTgeVujeW6xlDsT50I3jqPV28n1y/nLZ2Gvsd2SlD/3u4jgnAdLeV7T7zJEWpE8xQtsgFsYX9fsjJrx0f5W1YaIg8f38Dnc6x2c0pJJeQvwgsbDhytZrmvl4weqnDc2yFHAHIfF8QAnARe0W08rOt1yvstkT1rU/6tXBoMJvKkHjZ6SOMOBbHSbySJud2+y4L3GLnQxYEG9qy5ZLkxWcisDXIuvO1agFTvVnNuTlC+UI97TjSMPNqe0kIeSIk/g7G3wLjdeCuxExFdCz9U4juKETMqXonozyr9uY5jZ1mssQ/0IqC2L8Xi/SxCZLoOBTJGjbYCLgdy6FyKWjmR5tG+FtaHR/ufwdU8YN7Y7lsFADGdOeOLsVhuurl3M40mBKzBOb4xxmq3kys2t4Qqh04C17aTPRpN3Ue6lzCr2dNbvwugmd/Zlo4DlY/yhWfMDj5p83rqgtJBfGPxdpsix5lwCLW+XHb8Ftn+SclIp17uu31Ygm4nY2ZzbgL3dOIb61+yfa7AyeYoXlhbxy9DzVnLcYY+zRzzEOY2rkK22sciZsyxJefPQAMeNzm96u1hkxms0TJ0ZnF+X8vxbL6Yy58CkSL6rk9RYTMRzMs6rG8d0TXRzOcvFXZ0/sEYj0H9l/Z2jQqXGDe2OlylyNOsv5Py0nG3vF+tyxEdj51ggDyyKI94NXV0+BHQesCb9YV0a5c+9u8s5Oavy/GB7Bjc3F7xs4+fKzp+abcdz7+1nx6FGlquHi9xedZYZ/EMbw2wD3JSkLC8PcpLP22AbblcksK87X5vw1PjX67bm3McA91NfbxZcY83DGZmVfDWKuBZab2PhsC9VHkiKnFfOcnEnl8lF+mhpvwtYx7gVehOwgDfgvKGrMxjgk6xHMG4oZzl6JmwUa0WcshQ22F1/qecptjOWQSb29VevrMYZ7X4+PEshSbkU1h2rc6oVucKzFNoZb7qCdHLfhPUq2kwhotKzuZzsJPP3/3OwkZEsv+uwPQHAkfEYv46L3T/mwyLWAo+w6eLzp5s8H1xlIf9ZzrEHxhm0d2DoMM4FccqP4yJ7ha5PRLYsBk+6c5FDqd+1TJc9ylCccjkTw7hxTznXpNP6NGSKHAPsVB+KH44u5Fud1Fgu8XGHJxoPc7FzcifjTUenV7DWsNF2TIAkYVtosydTILUqf4y6Ex83Zfxm46dib3p0EGb9bRpXyrJ83pPcWclwObS18y1vzrKkyKEDVU5sHIAdXOMEgOfFKf/f4DMOf7H619tIeYTderWzZt16tgLfwPg0tNXJfQ9z7kkKXFIucq7vyGjoOkW65Lx+F7BOu73+ZrY1wBCNn8cOzzC4Ny5yUjk7sw8Et8cYjudyeJzjA2y4JvvRwQqHl2jvQodBHNd7VwJQpfNTUPxZrB1KOd/hk42n3muruKyba4s7DVh/ZpKARY2/os8Ba2yQX8U1xujB2XE2ybmANsj23mR5s9X6vwB3zTP4H+DIoQKHuPEpmp8l2Zzz2mrEz4dSzinluLxbl7MNXgdgxrU4uwBHZIZ4G/CpbszXTCnPzwz2SVJOcvgItNzGYhBjSZzj8OGU40dyfL8bdYqEVMrNoDVYveScFUXtrx+ajtEqK3whq2wlCzIRh1n9IOMdgYw5V8cFBsr56fV8GucR/3eowLJu1DthjvnmbB/PY082/T74iEUcuHZx+7uTkwLHu607K/fWSo472h1rolKOq+KUk6lfGVsQO6cQILw102n4+DXw4o2f9BoH0OVdcpvjC1iZpHwTOKTLU1VKmfXdYsfVnAOa3SO0aOb8FtZxewJY4PCJJOWIpMpxpUX8KmR9BoNx/R/DIxbx+VqNuVGNlRZ1frZVOxzGyPHJ4SK3VJ1rjKa94Kaycw2+O1TgmpJzei92s0yhAqzo4/zd4d1fIyhbNo9YMZLlkZ7MVf8ecJ2t5OZ4gH/H6y1GzLgsKXB3Kc+D0x+MF7pt2AA7uCbbox2+F2f45zVz192Ka5k9ylCcY0njYc3Z4PzBjjiUY/iQ0eiN5Zw8fw2XNTvTsFOd9sG6D5+wHXP984dBY0tkH7lxnjkHE+6InE0ZX55swbfBYU0+ojra/CidvhhvTzC0ipu8xjJgh5bHgFcwwE+SlIvKOT7ibV4anmTcMXKbnPvY8zOlNjaS5RGD/TNFjjPnY8CCFocwN46PjUN6vTtzIz8r5bQ2TGQm8IWsMjg0LnIzzmuBjBmXA3/f79qmYvAkznnlPFeVO9zMk+Q40WG7xsA3lLMTDo4OoJLj+jjldOobl+aVK5wC629HhtTRKiU3vtfkpecNFdvaqRZUOcv9wOe7OMUfysY7N35yqMgBNBbnTeKBbu9caNfoAr5dHuFFHRy3MwwsjVPu2xoWdI8fHj04xgug7YA0vjvzxvlreGbA8kRkFnIolyPeBvXddw77Dqe8sr9VbaII69cuOdw5mueKTndK26MM+fqLMxWz8DtYGzWuvypmvHPe2s4Po55MR1ewKgv4cZzyCJOECXc+ZvDSfm8zLa/hHfF8nonzj4GHXukRR2y8QM4gin2KLrHG8sB1BDWhPcHXonqD0nYuNe++bkF3nqWzaTdMO9Yu5nHgDUmRI825os3+a0eWx9g/LnLGLGlQKiJd4vNZMVTkS+68A6AGRwM/mM7HmnN1yFMumkme4gUM8AvqF2peH6IvYZLjJG/01zQoeo3zk45OMWzKqAetAWBuucLp0KQxeAc6ClgOnsD1TN4nZfck5SRyXN7JHJ3y7RgxOCSTcqHBKYS5XfgIVQ4u5zb9YkpS3uWwZ5OPGxuo8sUA83ddZSF3G+zeOG7ng0Cztl7NDDYOjz48A8eGWqQ4k5WyLLci30lqXODWVhuLvDnL4iKHDTsnjuT637BXRPrD4Q6oByzaW+vZVaVF/CpJ+Tr1dc6RRbyHDpZv2BPMzSS8b/wHtMNi4MgApW5+buekOU/x8dBHnHXcyKA8wOXUt5luwuGS4SL7dTpHpxyq5RynecTewHXUeyi1elVlpcFdBqeUR9htsqSeSdnX4aIpxvjS0wt5rMV5+8ahUspyIc7fAve1OczOEXx/qMCyXh6y2S+epTCa5wRzDoI221c4r6nBQ0mRJdZ6F3kR2QLUahvswtveHmdO34ppolZffwqAG2+bu6L9Y7fimHcZfVomYQyNDYRfN95xCwOfz1ONc36WTPJypubcmCnwukqeuzqdq1PlBdwL3NvxQLlNn8oUeEVk3EzzKz0li7rfmr8bSnkeNNgnLnAasBRjqMUh6gu6BzkApzTzWrCGN5rnG1ZgtwQuanN35hycC+Iih9J6OwgR2dLMYw70pvffdFXy3Jmk3A3sAyRjGd4JnNXqOLaC+ckgp65bF+F8jKjtX+qnr8bOGOcDmHPCnKf4WMirWEF6RJXH+HCc4Z+B7Sd5eWFkfDdOeUc519gauYWJi7w9Mq5kqttoxiWjCzZtSDpbOIyR54KhIstrztVttifYcWsIV+MaR0SckClwfQTXYjy/9UHYO3xlIjLTRRv+PK0wf2ZujgIuBm4CwDnJClzU6vE48SAnN24JAjxaznO2t3dyRsuSIofg7N24ivV+2HTjWruCBCx/BmsyKUdF8F0mv6WRGHwmTnkzcHo5x3+FmLffkpXsSsSFtuHZS5N5sLyaD09yoM6sM5rltx22J9jqVPL80B5jz3guS9s8PLqbskOFrveK67kqpJU8d/a7DpG2GftPePTATD3LtJzjP+Iiv2xsiMomxtuBS6f78VYgGxvvHX/scE6vwhVABOfUGn07DY4bTrl4JMejIcYO1uW8kuOOpMDZGB9t9h6D/YAfJwW+43DzIHzj6Tx/CFVDLwyn7FB1XotxmEXsx2bWsRk8ifEG346RHpXYdV4/ffHquSu4dWyQK4DX97umma7x//+MOOUGg08DL+13TQ3Pc9vgQO0tQgQ/gS2/VYhsmYZTdsB5E+tXfH+1rwVNwcFjuNSoH+vj8F6Df51uSGqEq/ETYR6u5Hp2mDcAI1m+E6f8wOCVQOz1I3pODDF20GNkSnkuiFO2NXjXFG+LMA4wOKAKJCkl4HHaP3y4VxZR71mU2PRvc62pRRxcXsBvu1ZVHzWOQjisw/YEW5VyjgcMXhYXORXnPCDpd00iMnMYJAl8ccJa15HBKp/pa1GbUclyfZxyHvUWC9tlUt5Ejus293GWkovh3euf4GyHsS6WOil3zjbjhwBuHDNc5KIQXfyDn9NXyXFynLKSyVs3TCahfvbSjqFr6bOnajUOqeT4Ub8L6bZSluXz13BHeYyLgaP6Xc9M5zBGlguHVnETNa7xGd6lWUR6wyCJU250+LsJT3680WtvxnIoJc7l43ewzFhicP3m+mDGcCqQbzz8WTnLV7pd62Qqee5KCnwb40Ag486ZwLGdjttxm4aNOXgpx7kObwXWhh5/VnDujWCvykL+s9+l9MrqefyllOOtjaOJ2mtPsJUZXcBvSjle5cYJNGl1IiJbPnuSeUmRI+KU+2kcbt/wYLnAh/pVVyvKzpU0us/jvDApTN3c21aziAlXrwzO7mdjco84i0aDZ4ejh1azS6djBr+CNa6c4/qh1dxbq3KFscFivS3Z0zjnl/N8rJeL9GaS0TxftwK7ZYwPWn03RvAQvyUZX882nHJbzVmGcUC/axIRMOfMJG2rYXCrFscZtsXJbPT8YxEc6jsy2oMaOuYLWZUUuKaxkQeM04GvN3t/XOM01m+S+nEpxy3dr7K5cpb7k5SvAYcCA17lTOod9NvWtYAFMDqfh4F/GCpwsEechfPybs7XN86oG58erHHh0wt19aaxRffkTIEvR3BNW+0JtjKNXSsHJkWOxPkU9TV/ItI/O9DGwfdBOPcOwBtn2yawgRqfqA7wbiB2+PvMSvae7E6OrWZx7Jy07rFx1ow4Hsw5G6t3pgfekjzFBaVF/Krd4XpydWE0z62lLHs77OlwCfCLXszbZWtxbnPjxHLEtuUc71S42lAlz53ltezZweHRW51SluWZDLsCX+53LSLSc39044Rynn1mW7gCaDTp/NL44yji1MneF4+xBOonexjcNZrltt5UOLVSnp/j6773DjDA2Z2MZ+79CY22msWDVXY12CmChQ7z8ZY7hPdS0WC1RzzhzsOVHL/s5m1AW83iTK35b0+VLA86VLo1f2jDRZ5bXb8Vt6lO/l5JgZd4tMlldgCsRqWU58F2xu2XZCW7+sDU/yYGnBWbO7MwLm597QpsjLWd/OYZwtwVbFPJ1A+unUw5y/29rKcVScq5438u5db/ebaY+P1zsMaT0w0rwyk71OobtF7S1QIncla48cvIub2U57Z2dtFN/PtO53tCN9kqFmac5wLg1Cbreznxe1s8yGNr5vJEj8tsaqP6q+UcD7Q9Vr8CloiIiMiWSguQRURERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQnsfwGGC9wjxnoqDgAAAABJRU5ErkJggg==" alt="OnnetFibra QA" style="height:32px;max-width:200px;object-fit:contain">
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
    <!-- Vista Factibilidad — 4 consolas paralelas -->
    <div id="fact-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="fact-sel-bar"></div>
      <div id="fact-grid"></div>
    </div>
    <!-- Vista Intervención Asegurada — 4 consolas paralelas -->
    <div id="ia-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="ia-form-bar"></div>
      <div id="ia-access-preview"></div>
      <div id="ia-sel-bar"></div>
      <div id="ia-grid"></div>
    </div>
    <!-- Vista Activación — 4 consolas paralelas -->
    <div id="activ-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="activ-form-bar"></div>
      <div id="activ-access-preview"></div>
      <div id="activ-sel-bar"></div>
      <div id="activ-grid"></div>
    </div>
    <!-- Vista Asignación — 4 consolas paralelas -->
    <div id="asig-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="asig-form-bar"></div>
      <div id="asig-access-preview"></div>
      <div id="asig-sel-bar"></div>
      <div id="asig-grid"></div>
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
<script>window.onerror=function(msg,src,line,col){var el=document.getElementById('sb-list');if(el)el.innerHTML='<div style="padding:8px;color:#e06c75;font-size:.65rem">JS ERR L'+line+': '+msg+'</div>';return false;};</script>
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
var _accordionOpen={'qa-fulfillment':true};
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
      document.getElementById('sb-list').innerHTML='<div style="padding:8px;color:#e06c75;font-size:.7rem">API devolvió vacío</div>';
      return;
    }
    try{ renderSB(); }
    catch(e){ document.getElementById('sb-list').innerHTML='<div style="padding:8px;color:#e06c75;font-size:.7rem">renderSB error: '+e.message+'</div>'; }
  }).catch(function(err){
    var msg='Error API /suites (intento '+attempt+'): '+err.message;
    document.getElementById('sb-list').innerHTML='<div style="padding:8px;color:#e06c75;font-size:.7rem;white-space:pre-wrap">'+msg+'</div>';
    if(attempt<4){setTimeout(function(){loadSuites(attempt+1);}, 1500);}
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
      if(s.id==='qa-endpoints'||s.id==='qa-fulfillment'){
        var isOpen=!!_accordionOpen[s.id];
        var _accTitle=s.id==='qa-endpoints'?'Expandir endpoints':'Expandir suites de prueba';
        row.innerHTML='<div class="si-ico" id="ico-'+s.id+'">&#183;</div>'
          +'<div class="si-txt" style="flex:1">'
          +'<div class="si-name">'+esc(s.label)+'</div>'
          +'<div class="si-desc">'+esc(s.desc)+'</div></div>'
          +'<button class="acc-toggle" title="'+_accTitle+'">'
          +(isOpen?'&#9660;':'&#9654;')+'</button>';
        row.querySelector('.si-txt').onclick=(function(sid){return function(){selectSuite(sid);};})(s.id);
        row.querySelector('.acc-toggle').onclick=(function(pid){return function(e){e.stopPropagation();toggleAccordion(pid);};})(s.id);
        el.appendChild(row);
        if(isOpen){
          var _sections=s.id==='qa-endpoints'
            ?[{lbl:'FulFillment',par:'qa-fulfillment'},{lbl:'Consultas',par:'qa-consultas'}]
            :s.id==='qa-fulfillment'
            ?[{lbl:'Factibilidad',par:'qa-fact'},{lbl:'Asignación',par:'qa-asig'},{lbl:'Interv. Asegurada',par:'qa-ia-par'},{lbl:'Activación',par:'qa-activ-par'}]
            :[{lbl:'Factibilidad',par:'qa-fact'}];
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
  if(id==='qa-ep-activacion'){
    _isQAChild=true;
    switchView('ep-form');
    renderEPFVNOBar();
    renderActivacionForm();
    setTop('','Activación','registrationActivation · configura y ejecuta');
    var _eb0d=document.getElementById('exec-btn'); if(_eb0d) _eb0d.disabled=true;
    return;
  }
  if(id==='qa-fact-suite'){
    _isQAChild=false;
    switchView('fact');
    renderFactSelBar();
    renderFactView();
    setTop('','Suite: Factibilidad','TC-01..TC-04 · DIR02803636 · presiona Ejecutar');
    _syncExecBtn();
    return;
  }
  if(id==='qa-asig-suite'){
    _isQAChild=false;
    switchView('asig');
    renderAsigFormBar();
    renderAsigSelBar();
    renderAsigView();
    setTop('','Suite: Asignación','TC-05..TC-08 · presiona Ejecutar');
    _syncAsigExecBtn();
    return;
  }
  if(id==='qa-ia-inicio-suite'||id==='qa-ia-fin-suite'){
    _isQAChild=false;
    _iaMode=id==='qa-ia-inicio-suite'?'inicio':'fin';
    switchView('ia');
    renderIAFormBar();
    renderIASelBar();
    renderIAView();
    var _iaTcs=_iaMode==='inicio'?'TC-09..TC-12':'TC-13..TC-16';
    var _iaLbl=_iaMode==='inicio'?'IA Inicio':'IA Fin';
    setTop('','Suite: '+_iaLbl,_iaTcs+' · presiona Ejecutar');
    _syncIAExecBtn();
    return;
  }
  if(id==='qa-activ-suite'){
    _isQAChild=false;
    switchView('activ');
    renderActivFormBar();
    renderActivSelBar();
    renderActivView();
    setTop('','Suite: Activación','TC-17..TC-20 · presiona Ejecutar');
    _syncActivExecBtn();
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
  if(selectedId==='qa-fact-suite'){
    var _sf=suites.find(function(x){return x.id==='qa-fact-suite';});
    if(_sf) _doRunFact(_sf);
    return;
  }
  if(selectedId==='qa-asig-suite'){
    var _sa=suites.find(function(x){return x.id==='qa-asig-suite';});
    if(_sa) _doRunAsig(_sa);
    return;
  }
  if(selectedId==='qa-ia-inicio-suite'||selectedId==='qa-ia-fin-suite'){
    var _si=suites.find(function(x){return x.id===selectedId;});
    if(_si) _doRunIA(_si);
    return;
  }
  if(selectedId==='qa-activ-suite'){
    var _sac=suites.find(function(x){return x.id==='qa-activ-suite';});
    if(_sac) _doRunActiv(_sac);
    return;
  }
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
  if(id==='qa-fact-suite'){
    _isQAChild=false;
    switchView('fact'); renderFactView();
    setTop('','Suite: Factibilidad','TC-01..TC-04 · DIR02803636');
    _doRunFact(s);
    return;
  }
  _isQAChild = !!(s.env_type==='qa_vno');
  switchView('std');
  var _vbar=document.getElementById('vno-bar');
  if(_isQAChild){ renderVNOBar(); } else { _vbar.style.display='none'; }
  var _rp2=document.getElementById('resp-panel'); if(_rp2) _rp2.style.display='none';
  var _runParams=_isQAChild?{vno:_globalVNO}:{};
  _doRun('/api/run/'+id, _runParams, s);
}

function switchView(mode){
  var _vs=["std-view","sn-view","ep-view","ep-form-view","fact-view","asig-view","ia-view","activ-view"];
  _vs.forEach(function(vid){var el=document.getElementById(vid);if(el)el.style.display="none";});
  var target={"sn":"sn-view","ep":"ep-view","ep-form":"ep-form-view","fact":"fact-view","asig":"asig-view","ia":"ia-view","activ":"activ-view"}[mode]||"std-view";
  var el=document.getElementById(target);
  if(el){el.style.display="flex";el.style.flexDirection="column";}
}

// ── Factibilidad: vista multi-consola ────────────────────────────────────────
var _FACT_TC_META = [
  {tc:'TC-01', label:'TC-01 · Entel', vno:'VNO 03', sid:'qa-fact-tc01', color:'#A8FF78'},
  {tc:'TC-02', label:'TC-02 · KAO',   vno:'VNO 02', sid:'qa-fact-tc02', color:'#00C8D4'},
  {tc:'TC-03', label:'TC-03 · DTV',   vno:'VNO 05', sid:'qa-fact-tc03', color:'#FFB347'},
  {tc:'TC-04', label:'TC-04 · TCH',   vno:'VNO 00', sid:'qa-fact-tc04', color:'#6E8EFF'},
];

var _factSel={'TC-01':true,'TC-02':true,'TC-03':true,'TC-04':true};

function renderFactSelBar(){
  var bar=document.getElementById('fact-sel-bar'); if(!bar) return;
  var h='<span class="fsb-lbl">VNOs a ejecutar:</span>';
  _FACT_TC_META.forEach(function(m){
    var on=_factSel[m.tc]?'on':'';
    h+='<button class="tc-sel-btn '+on+'" id="tcsb-'+m.tc+'">'+esc(m.label)+'</button>';
  });
  h+='<span class="fsb-sep"></span>'
    +'<button class="fsb-all" id="fsb-all">Todos</button>'
    +'<button class="fsb-all" id="fsb-none">Ninguno</button>';
  bar.innerHTML=h;
  _FACT_TC_META.forEach(function(m){
    document.getElementById('tcsb-'+m.tc).onclick=(function(tc){
      return function(){ toggleFactTC(tc); };
    })(m.tc);
  });
  document.getElementById('fsb-all').onclick=function(){ selectAllFact(true); };
  document.getElementById('fsb-none').onclick=function(){ selectAllFact(false); };
}

function toggleFactTC(tc){
  _factSel[tc]=!_factSel[tc];
  var btn=document.getElementById('tcsb-'+tc);
  if(btn) btn.className='tc-sel-btn'+(_factSel[tc]?' on':'');
  renderFactView();
  _syncExecBtn();
}

function selectAllFact(val){
  _FACT_TC_META.forEach(function(m){ _factSel[m.tc]=val; });
  renderFactSelBar();
  renderFactView();
  _syncExecBtn();
}

function _syncExecBtn(){
  var anyOn=_FACT_TC_META.some(function(m){ return _factSel[m.tc]; });
  var eb=document.getElementById('exec-btn');
  if(eb) eb.disabled=running||!anyOn;
}

function renderFactView(){
  var grid=document.getElementById('fact-grid'); if(!grid) return;
  grid.innerHTML='';
  var _sel=_FACT_TC_META.filter(function(m){ return _factSel[m.tc]; });
  grid.style.gridTemplateColumns=_sel.length===1?'1fr':'1fr 1fr';
  _sel.forEach(function(m){
    var p=document.createElement('div'); p.className='fact-panel'; p.id='fp-'+m.tc;
    var _tc=m.tc;
    p.innerHTML=
      '<div class="fp-hdr">'
      +'<span class="fp-dot idle" id="fpd-'+_tc+'"></span>'
      +'<span class="fp-name" style="color:'+m.color+'">'+esc(m.label)+'</span>'
      +'<span style="font-size:.65rem;color:var(--txt3)">'+esc(m.vno)+'</span>'
      +'<span class="fp-badge idle" id="fpb-'+_tc+'">espera</span>'
      +'<a class="fp-rpt" id="fpr-'+_tc+'" href="#" target="_blank">&#128196; Ver</a>'
      +'</div>'
      +'<div class="fact-term" id="ft-'+_tc+'"></div>'
      +'<div class="fp-resp-bar" id="frb-'+_tc+'">'
      +'<span class="fr-label">Response</span>'
      +'<span id="frs-'+_tc+'"></span>'
      +'</div>'
      +'<div class="fp-resp" id="fr-'+_tc+'"><span class="fr-empty">—</span></div>';
    grid.appendChild(p);
  });
}

function _factSetResponse(tc, responses){
  var el=document.getElementById('fr-'+tc);
  var bar=document.getElementById('frs-'+tc);
  if(!el||!responses||!responses.length) return;
  var r=responses[responses.length-1];
  var cls=r.code>=200&&r.code<300?'ok':r.code>=400?'err':'warn';
  if(bar){
    bar.innerHTML='<span class="fr-scode '+cls+'">'+r.code+' '+esc(r.status||'')+'</span>'
      +'<span class="fr-stime">'+r.time_ms+'ms</span>'
      +'<span class="fr-sname">'+esc(r.name||'')+'</span>';
  }
  var bodyTxt=r.body||'';
  if(bodyTxt){
    try{ bodyTxt=JSON.stringify(JSON.parse(bodyTxt),null,2); }catch(e){}
  }
  el.innerHTML=bodyTxt?'<pre>'+esc(bodyTxt)+'</pre>':'<span class="fr-empty">Sin body</span>';
}

function _factApp(tc, text, cls){
  var el=document.getElementById('ft-'+tc); if(!el) return;
  var sp=document.createElement('span');
  sp.className='tl'+(cls?' '+cls:'');
  sp.textContent=text+'\\n';
  el.appendChild(sp);
  el.scrollTop=el.scrollHeight;
}

function _factSetState(tc, state){
  var dot=document.getElementById('fpd-'+tc);
  var badge=document.getElementById('fpb-'+tc);
  var states={idle:'espera',running:'ejecutando',passed:'OK ✓',failed:'FAIL ✗'};
  if(dot){ dot.className='fp-dot '+state; }
  if(badge){ badge.className='fp-badge '+state; badge.textContent=states[state]||state; }
}

function _doRunFact(s){
  if(running) return;
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando 4 VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  document.getElementById('run-all').disabled=true;
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  // Reset panels
  _FACT_TC_META.forEach(function(m){
    var ft=document.getElementById('ft-'+m.tc); if(ft) ft.innerHTML='';
    var fr=document.getElementById('fr-'+m.tc); if(fr) fr.innerHTML='<span class="fr-empty">—</span>';
    var frs=document.getElementById('frs-'+m.tc); if(frs) frs.innerHTML='';
    var fpr=document.getElementById('fpr-'+m.tc); if(fpr) fpr.classList.remove('show');
    _factSetState(m.tc,'idle');
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _selTcs=_FACT_TC_META.filter(function(m){return _factSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var es=new EventSource('/api/run/qa-fact-suite?tcs='+encodeURIComponent(_selTcs));
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){
        _factApp(d.tc, d.t, col(d.t));
        _factSetState(d.tc,'running');
      }
      suiteLogs[s.id].push({text:d.t,cls:col(d.t)});
    } else if(d.e==='tc_done'){
      var ok=d.code===0;
      _factSetState(d.tc, ok?'passed':'failed');
      if(d.has_report){
        var fpr=document.getElementById('fpr-'+d.tc);
        if(fpr){fpr.href='/api/report/'+d.sid;fpr.classList.add('show');}
      }
    } else if(d.e==='tc_response'){
      _factSetResponse(d.tc, d.responses);
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error'){onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);}
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){
      currentEs=null; es.close();
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
    }
  };
}

// ── Asignación: vista multi-consola ─────────────────────────────────────────
var _ASIG_TC_META = [
  {tc:'TC-05', label:'TC-05 · Entel', vno:'VNO 03', sid:'qa-asig-tc05', color:'#98F5A4'},
  {tc:'TC-06', label:'TC-06 · KAO',   vno:'VNO 02', sid:'qa-asig-tc06', color:'#7EC8E3'},
  {tc:'TC-07', label:'TC-07 · DTV',   vno:'VNO 05', sid:'qa-asig-tc07', color:'#FFD580'},
  {tc:'TC-08', label:'TC-08 · TCH',   vno:'VNO 00', sid:'qa-asig-tc08', color:'#B39DFF'},
];
var _asigSel={'TC-05':true,'TC-06':true,'TC-07':true,'TC-08':true};

var _VNO_CODES={'TC-05':'03','TC-06':'02','TC-07':'05','TC-08':'00'};
var _VNO_KNOWN=['00','02','03','05'];

function _resolveAccessId(raw, vnoCode){
  if(!raw) return '';
  var m=raw.match(/^(\d{2})-(.+)$/);
  if(m && _VNO_KNOWN.indexOf(m[1])!==-1){
    return vnoCode+'-'+m[2];
  }
  return raw;
}

function _updateAsigAccessPreview(){
  var el=document.getElementById('asig-access-preview'); if(!el) return;
  var raw=(document.getElementById('asig-access')||{}).value||'';
  if(!raw.trim()){
    el.innerHTML='<span class="aap-empty">Ingresa un Access ID para ver la preview por VNO</span>';
    return;
  }
  var h='';
  _ASIG_TC_META.forEach(function(m){
    var resolved=_resolveAccessId(raw.trim(), _VNO_CODES[m.tc]);
    h+='<span class="aap-item">'
      +'<span class="aap-vno">'+esc(m.label)+':</span>'
      +'<span class="aap-id">'+esc(resolved)+'</span>'
      +'</span>';
  });
  el.innerHTML=h;
}

function renderAsigFormBar(){
  var bar=document.getElementById('asig-form-bar'); if(!bar) return;
  bar.innerHTML=
    '<span class="afb-lbl">Access ID:</span>'
    +'<input class="wide" id="asig-access" placeholder="ej: 02-XXXXX-01" />'
    +'<span class="afb-lbl">Address ID:</span>'
    +'<input class="med" id="asig-addr" placeholder="DIR..." />'
    +'<span class="afb-lbl">Plan:</span>'
    +'<select id="asig-speed">'
    +'<option value="100/100">100/100</option>'
    +'<option value="300/300">300/300</option>'
    +'<option value="400/400">400/400</option>'
    +'<option value="600/600" selected>600/600</option>'
    +'<option value="800/800">800/800</option>'
    +'<option value="1000/1000">1000/1000</option>'
    +'</select>'
    +'<span class="afb-lbl">BA:</span>'
    +'<select id="asig-ba"><option value="true" selected>Si</option><option value="false">No</option></select>'
    +'<span class="afb-lbl">VoIP:</span>'
    +'<select id="asig-voip"><option value="true" selected>Si</option><option value="false">No</option></select>'
    +'<span class="afb-lbl">IPTV:</span>'
    +'<select id="asig-iptv"><option value="true" selected>Si</option><option value="false">No</option></select>';
  var inp=document.getElementById('asig-access');
  if(inp) inp.oninput=_updateAsigAccessPreview;
  _updateAsigAccessPreview();
}

function renderAsigSelBar(){
  var bar=document.getElementById('asig-sel-bar'); if(!bar) return;
  var h='<span class="fsb-lbl">VNOs a ejecutar:</span>';
  _ASIG_TC_META.forEach(function(m){
    var on=_asigSel[m.tc]?'on':'';
    h+='<button class="tc-sel-btn '+on+'" id="asb-'+m.tc+'">'+esc(m.label)+'</button>';
  });
  h+='<span class="fsb-sep"></span>'
    +'<button class="fsb-all" id="asb-all">Todos</button>'
    +'<button class="fsb-all" id="asb-none">Ninguno</button>';
  bar.innerHTML=h;
  _ASIG_TC_META.forEach(function(m){
    document.getElementById('asb-'+m.tc).onclick=(function(tc){
      return function(){ _toggleAsigTC(tc); };
    })(m.tc);
  });
  document.getElementById('asb-all').onclick=function(){ _selectAllAsig(true); };
  document.getElementById('asb-none').onclick=function(){ _selectAllAsig(false); };
}

function _toggleAsigTC(tc){
  _asigSel[tc]=!_asigSel[tc];
  var btn=document.getElementById('asb-'+tc);
  if(btn) btn.className='tc-sel-btn'+(_asigSel[tc]?' on':'');
  renderAsigView();
  _syncAsigExecBtn();
}

function _selectAllAsig(val){
  _ASIG_TC_META.forEach(function(m){ _asigSel[m.tc]=val; });
  renderAsigSelBar();
  renderAsigView();
  _syncAsigExecBtn();
}

function _syncAsigExecBtn(){
  var anyOn=_ASIG_TC_META.some(function(m){ return _asigSel[m.tc]; });
  var eb=document.getElementById('exec-btn');
  if(eb) eb.disabled=running||!anyOn;
}

function renderAsigView(){
  var grid=document.getElementById('asig-grid'); if(!grid) return;
  grid.innerHTML='';
  var _sel=_ASIG_TC_META.filter(function(m){ return _asigSel[m.tc]; });
  grid.style.gridTemplateColumns=_sel.length===1?'1fr':'1fr 1fr';
  _sel.forEach(function(m){
    var p=document.createElement('div'); p.className='fact-panel'; p.id='ap-'+m.tc;
    var _tc=m.tc;
    p.innerHTML=
      '<div class="fp-hdr">'
      +'<span class="fp-dot idle" id="apd-'+_tc+'"></span>'
      +'<span class="fp-name" style="color:'+m.color+'">'+esc(m.label)+'</span>'
      +'<span style="font-size:.65rem;color:var(--txt3)">'+esc(m.vno)+'</span>'
      +'<span class="fp-badge idle" id="apb-'+_tc+'">espera</span>'
      +'<a class="fp-rpt" id="apr-'+_tc+'" href="#" target="_blank">&#128196; Ver</a>'
      +'</div>'
      +'<div class="fact-term" id="at-'+_tc+'"></div>'
      +'<div class="fp-resp-bar" id="afrb-'+_tc+'">'
      +'<span class="fr-label">Response</span>'
      +'<span id="afrs-'+_tc+'"></span>'
      +'</div>'
      +'<div class="fp-resp" id="afr-'+_tc+'"><span class="fr-empty">—</span></div>';
    grid.appendChild(p);
  });
}

function _asigApp(tc, text, cls){
  var el=document.getElementById('at-'+tc); if(!el) return;
  var sp=document.createElement('span');
  sp.className='tl'+(cls?' '+cls:'');
  sp.textContent=text+'\\n';
  el.appendChild(sp);
  el.scrollTop=el.scrollHeight;
}

function _asigSetState(tc, state){
  var dot=document.getElementById('apd-'+tc);
  var badge=document.getElementById('apb-'+tc);
  var states={idle:'espera',running:'ejecutando',passed:'OK ✓',failed:'FAIL ✗'};
  if(dot){ dot.className='fp-dot '+state; }
  if(badge){ badge.className='fp-badge '+state; badge.textContent=states[state]||state; }
}

function _asigSetResponse(tc, responses){
  var el=document.getElementById('afr-'+tc);
  var bar=document.getElementById('afrs-'+tc);
  if(!el||!responses||!responses.length) return;
  var r=responses[responses.length-1];
  var cls=r.code>=200&&r.code<300?'ok':r.code>=400?'err':'warn';
  if(bar){
    bar.innerHTML='<span class="fr-scode '+cls+'">'+r.code+' '+esc(r.status||'')+'</span>'
      +'<span class="fr-stime">'+r.time_ms+'ms</span>'
      +'<span class="fr-sname">'+esc(r.name||'')+'</span>';
  }
  var bodyTxt=r.body||'';
  if(bodyTxt){
    try{ bodyTxt=JSON.stringify(JSON.parse(bodyTxt),null,2); }catch(e){}
  }
  el.innerHTML=bodyTxt?'<pre>'+esc(bodyTxt)+'</pre>':'<span class="fr-empty">Sin body</span>';
}

function _doRunAsig(s){
  if(running) return;
  var accessId=document.getElementById('asig-access');
  var addrId=document.getElementById('asig-addr');
  var speed=document.getElementById('asig-speed');
  var ba=document.getElementById('asig-ba');
  var voip=document.getElementById('asig-voip');
  var iptv=document.getElementById('asig-iptv');
  if(!accessId||!accessId.value.trim()){
    accessId&&(accessId.style.borderColor='var(--err)');
    return;
  }
  if(accessId) accessId.style.borderColor='';
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  document.getElementById('run-all').disabled=true;
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _ASIG_TC_META.forEach(function(m){
    var at=document.getElementById('at-'+m.tc); if(at) at.innerHTML='';
    var afr=document.getElementById('afr-'+m.tc); if(afr) afr.innerHTML='<span class="fr-empty">—</span>';
    var afrs=document.getElementById('afrs-'+m.tc); if(afrs) afrs.innerHTML='';
    var apr=document.getElementById('apr-'+m.tc); if(apr) apr.classList.remove('show');
    _asigSetState(m.tc,'idle');
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _rawAccess=accessId?accessId.value.trim():'';
  var _selTcs=_ASIG_TC_META.filter(function(m){return _asigSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var _accessMap={};
  _ASIG_TC_META.forEach(function(m){ _accessMap[m.tc]=_resolveAccessId(_rawAccess,_VNO_CODES[m.tc]); });
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&access_ids='+encodeURIComponent(JSON.stringify(_accessMap))
    +'&address_id='+encodeURIComponent(addrId?addrId.value.trim():'')
    +'&speed_plan='+encodeURIComponent(speed?speed.value:'600/600')
    +'&service_ba='+encodeURIComponent(ba?ba.value:'true')
    +'&service_voip='+encodeURIComponent(voip?voip.value:'true')
    +'&service_iptv='+encodeURIComponent(iptv?iptv.value:'true');
  var es=new EventSource('/api/run/qa-asig-suite?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _asigApp(d.tc,d.t,col(d.t)); _asigSetState(d.tc,'running'); }
      suiteLogs[s.id].push({text:d.t,cls:col(d.t)});
    } else if(d.e==='tc_done'){
      var ok=d.code===0;
      _asigSetState(d.tc,ok?'passed':'failed');
      if(d.has_report){
        var apr=document.getElementById('apr-'+d.tc);
        if(apr){apr.href='/api/report/'+d.sid;apr.classList.add('show');}
      }
    } else if(d.e==='tc_response'){
      _asigSetResponse(d.tc,d.responses);
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error'){onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);}
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){
      currentEs=null; es.close();
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
    }
  };
}

// ── Intervención Asegurada: vista multi-consola ──────────────────────────────
var _iaMode = 'inicio';
var _IA_INICIO_META = [
  {tc:'TC-09', label:'TC-09 · Entel', vno:'VNO 03', sid:'qa-ia-tc09', color:'#FF9F8B'},
  {tc:'TC-10', label:'TC-10 · KAO',   vno:'VNO 02', sid:'qa-ia-tc10', color:'#85E89D'},
  {tc:'TC-11', label:'TC-11 · DTV',   vno:'VNO 05', sid:'qa-ia-tc11', color:'#FFD580'},
  {tc:'TC-12', label:'TC-12 · TCH',   vno:'VNO 00', sid:'qa-ia-tc12', color:'#79C8FF'},
];
var _IA_FIN_META = [
  {tc:'TC-13', label:'TC-13 · Entel', vno:'VNO 03', sid:'qa-ia-tc13', color:'#C7CEEA'},
  {tc:'TC-14', label:'TC-14 · KAO',   vno:'VNO 02', sid:'qa-ia-tc14', color:'#B5EAD7'},
  {tc:'TC-15', label:'TC-15 · DTV',   vno:'VNO 05', sid:'qa-ia-tc15', color:'#FFDAC1'},
  {tc:'TC-16', label:'TC-16 · TCH',   vno:'VNO 00', sid:'qa-ia-tc16', color:'#B39DFF'},
];
var _iaSel={};
(function(){ _IA_INICIO_META.concat(_IA_FIN_META).forEach(function(m){ _iaSel[m.tc]=true; }); })();
var _IA_VNO_CODES={'TC-09':'03','TC-10':'02','TC-11':'05','TC-12':'00',
                   'TC-13':'03','TC-14':'02','TC-15':'05','TC-16':'00'};

function _iaMeta(){ return _iaMode==='inicio'?_IA_INICIO_META:_IA_FIN_META; }
function _iaSuiteId(){ return _iaMode==='inicio'?'qa-ia-inicio-suite':'qa-ia-fin-suite'; }

function renderIAFormBar(){
  var bar=document.getElementById('ia-form-bar'); if(!bar) return;
  var modeLabel=_iaMode==='inicio'
    ?'<span class="ia-mode-badge inicio">Inicio</span>'
    :'<span class="ia-mode-badge fin">Fin</span>';
  bar.innerHTML=
    '<span class="afb-lbl">Modo:</span>'+modeLabel
    +'<span class="afb-lbl" style="margin-left:8px">Access ID:</span>'
    +'<input class="wide" id="ia-access" placeholder="ej: 02-XXXXX-01" />'
    +'<span class="afb-lbl">Escenario:</span>'
    +'<select id="ia-scenario">'
    +'<option value="Instalación" selected>Instalación</option>'
    +'<option value="Reparación">Reparación</option>'
    +'</select>'
    +'<span class="afb-lbl">Servicio:</span>'
    +'<select id="ia-svctype">'
    +'<option value="FTTH" selected>FTTH</option>'
    +'<option value="SSAA">SSAA</option>'
    +'</select>';
  var inp=document.getElementById('ia-access');
  if(inp) inp.oninput=_updateIAAccessPreview;
  _updateIAAccessPreview();
}

function _updateIAAccessPreview(){
  var el=document.getElementById('ia-access-preview'); if(!el) return;
  var raw=(document.getElementById('ia-access')||{}).value||'';
  if(!raw.trim()){
    el.innerHTML='<span class="aap-empty">Ingresa un Access ID para ver la preview por VNO</span>';
    return;
  }
  var h='';
  _iaMeta().forEach(function(m){
    var resolved=_resolveAccessId(raw.trim(),_IA_VNO_CODES[m.tc]);
    h+='<span class="aap-item"><span class="aap-vno">'+esc(m.label)+':</span>'
      +'<span class="aap-id">'+esc(resolved)+'</span></span>';
  });
  el.innerHTML=h;
}

function renderIASelBar(){
  var bar=document.getElementById('ia-sel-bar'); if(!bar) return;
  var h='<span class="fsb-lbl">VNOs a ejecutar:</span>';
  _iaMeta().forEach(function(m){
    var on=_iaSel[m.tc]?'on':'';
    h+='<button class="tc-sel-btn '+on+'" id="iasb-'+m.tc+'">'+esc(m.label)+'</button>';
  });
  h+='<span class="fsb-sep"></span>'
    +'<button class="fsb-all" id="iasb-all">Todos</button>'
    +'<button class="fsb-all" id="iasb-none">Ninguno</button>';
  bar.innerHTML=h;
  _iaMeta().forEach(function(m){
    document.getElementById('iasb-'+m.tc).onclick=(function(tc){
      return function(){ _iaSel[tc]=!_iaSel[tc];
        var btn=document.getElementById('iasb-'+tc);
        if(btn) btn.className='tc-sel-btn'+(_iaSel[tc]?' on':'');
        renderIAView(); _syncIAExecBtn(); };
    })(m.tc);
  });
  document.getElementById('iasb-all').onclick=function(){
    _iaMeta().forEach(function(m){ _iaSel[m.tc]=true; }); renderIASelBar(); renderIAView(); _syncIAExecBtn(); };
  document.getElementById('iasb-none').onclick=function(){
    _iaMeta().forEach(function(m){ _iaSel[m.tc]=false; }); renderIASelBar(); renderIAView(); _syncIAExecBtn(); };
}

function _syncIAExecBtn(){
  var anyOn=_iaMeta().some(function(m){ return _iaSel[m.tc]; });
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=running||!anyOn;
}

function renderIAView(){
  var grid=document.getElementById('ia-grid'); if(!grid) return;
  grid.innerHTML='';
  var _sel=_iaMeta().filter(function(m){ return _iaSel[m.tc]; });
  grid.style.gridTemplateColumns=_sel.length===1?'1fr':'1fr 1fr';
  _sel.forEach(function(m){
    var p=document.createElement('div'); p.className='fact-panel'; p.id='ip-'+m.tc;
    var _tc=m.tc;
    p.innerHTML=
      '<div class="fp-hdr">'
      +'<span class="fp-dot idle" id="ipd-'+_tc+'"></span>'
      +'<span class="fp-name" style="color:'+m.color+'">'+esc(m.label)+'</span>'
      +'<span style="font-size:.65rem;color:var(--txt3)">'+esc(m.vno)+'</span>'
      +'<span class="fp-badge idle" id="ipb-'+_tc+'">espera</span>'
      +'<a class="fp-rpt" id="ipr-'+_tc+'" href="#" target="_blank">&#128196; Ver</a>'
      +'</div>'
      +'<div class="fact-term" id="it-'+_tc+'"></div>'
      +'<div class="fp-resp-bar" id="ifrb-'+_tc+'">'
      +'<span class="fr-label">Response</span>'
      +'<span id="ifrs-'+_tc+'"></span>'
      +'</div>'
      +'<div class="fp-resp" id="ifr-'+_tc+'"><span class="fr-empty">—</span></div>';
    grid.appendChild(p);
  });
}

function _iaApp(tc,text,cls){
  var el=document.getElementById('it-'+tc); if(!el) return;
  var sp=document.createElement('span');
  sp.className='tl'+(cls?' '+cls:'');
  sp.textContent=text+'\\n';
  el.appendChild(sp); el.scrollTop=el.scrollHeight;
}

function _iaSetState(tc,state){
  var dot=document.getElementById('ipd-'+tc);
  var badge=document.getElementById('ipb-'+tc);
  var states={idle:'espera',running:'ejecutando',passed:'OK ✓',failed:'FAIL ✗'};
  if(dot){ dot.className='fp-dot '+state; }
  if(badge){ badge.className='fp-badge '+state; badge.textContent=states[state]||state; }
}

function _iaSetResponse(tc,responses){
  var el=document.getElementById('ifr-'+tc);
  var bar=document.getElementById('ifrs-'+tc);
  if(!el||!responses||!responses.length) return;
  var r=responses[responses.length-1];
  var cls=r.code>=200&&r.code<300?'ok':r.code>=400?'err':'warn';
  if(bar){
    bar.innerHTML='<span class="fr-scode '+cls+'">'+r.code+' '+esc(r.status||'')+'</span>'
      +'<span class="fr-stime">'+r.time_ms+'ms</span>'
      +'<span class="fr-sname">'+esc(r.name||'')+'</span>';
  }
  var bodyTxt=r.body||'';
  if(bodyTxt){ try{ bodyTxt=JSON.stringify(JSON.parse(bodyTxt),null,2); }catch(e){} }
  el.innerHTML=bodyTxt?'<pre>'+esc(bodyTxt)+'</pre>':'<span class="fr-empty">Sin body</span>';
}

function _doRunIA(s){
  if(running) return;
  var accessEl=document.getElementById('ia-access');
  if(!accessEl||!accessEl.value.trim()){ if(accessEl) accessEl.style.borderColor='var(--err)'; return; }
  accessEl.style.borderColor='';
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  document.getElementById('run-all').disabled=true;
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _iaMeta().forEach(function(m){
    var it=document.getElementById('it-'+m.tc); if(it) it.innerHTML='';
    var ifr=document.getElementById('ifr-'+m.tc); if(ifr) ifr.innerHTML='<span class="fr-empty">—</span>';
    var ifrs=document.getElementById('ifrs-'+m.tc); if(ifrs) ifrs.innerHTML='';
    var ipr=document.getElementById('ipr-'+m.tc); if(ipr) ipr.classList.remove('show');
    _iaSetState(m.tc,'idle');
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _rawAccess=accessEl.value.trim();
  var _selTcs=_iaMeta().filter(function(m){return _iaSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var _accessMap={};
  _iaMeta().forEach(function(m){ _accessMap[m.tc]=_resolveAccessId(_rawAccess,_IA_VNO_CODES[m.tc]); });
  var _sc=(document.getElementById('ia-scenario')||{}).value||'Instalación';
  var _sv=(document.getElementById('ia-svctype')||{}).value||'FTTH';
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&access_ids='+encodeURIComponent(JSON.stringify(_accessMap))
    +'&scenario='+encodeURIComponent(_sc)
    +'&service_type='+encodeURIComponent(_sv);
  var es=new EventSource('/api/run/'+_iaSuiteId()+'?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _iaApp(d.tc,d.t,col(d.t)); _iaSetState(d.tc,'running'); }
      suiteLogs[s.id].push({text:d.t,cls:col(d.t)});
    } else if(d.e==='tc_done'){
      _iaSetState(d.tc,d.code===0?'passed':'failed');
      if(d.has_report){
        var ipr=document.getElementById('ipr-'+d.tc);
        if(ipr){ipr.href='/api/report/'+d.sid;ipr.classList.add('show');}
      }
    } else if(d.e==='tc_response'){
      _iaSetResponse(d.tc,d.responses);
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error') onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){ currentEs=null; es.close();
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s); }
  };
}

// ── Suite Activación: vista multi-consola ────────────────────────────────────
var _ACTIV_META = [
  {tc:'TC-17', label:'TC-17 · Entel', vno:'VNO 03', sid:'qa-activ-tc17', color:'#FF9F8B'},
  {tc:'TC-18', label:'TC-18 · KAO',   vno:'VNO 02', sid:'qa-activ-tc18', color:'#85E89D'},
  {tc:'TC-19', label:'TC-19 · DTV',   vno:'VNO 05', sid:'qa-activ-tc19', color:'#FFD580'},
  {tc:'TC-20', label:'TC-20 · TCH',   vno:'VNO 00', sid:'qa-activ-tc20', color:'#79C8FF'},
];
var _activSel={};
(function(){ _ACTIV_META.forEach(function(m){ _activSel[m.tc]=true; }); })();
var _ACTIV_VNO_CODES={'TC-17':'03','TC-18':'02','TC-19':'05','TC-20':'00'};
var _ACTIV_SERIAL_BASE={'TC-17':'ZTEG1104','TC-18':'ZTEGD719','TC-19':'HTWC000A'};

function renderActivFormBar(){
  var bar=document.getElementById('activ-form-bar'); if(!bar) return;
  bar.innerHTML=
    '<span class="afb-lbl">Access ID:</span>'
    +'<input class="wide" id="activ-access" placeholder="ej: 03-AOQACAP-03" />'
    +'<span class="afb-lbl">Speed Plan:</span>'
    +'<input id="activ-speed" style="width:90px" placeholder="600/600" value="600/600" />'
    +'<span class="afb-lbl">Servicios:</span>'
    +'<label class="activ-svc"><input type="checkbox" id="activ-sba" checked> BA</label>'
    +'<label class="activ-svc"><input type="checkbox" id="activ-svoip" checked> VoIP</label>'
    +'<label class="activ-svc"><input type="checkbox" id="activ-siptv" checked> IPTV</label>'
    +'<span class="afb-lbl" style="margin-left:8px">Serial (últ. 4):</span>'
    +'<input id="activ-serial" style="width:60px" maxlength="4" placeholder="0000" />';
  var inp=document.getElementById('activ-access');
  if(inp) inp.oninput=_updateActivAccessPreview;
  var sinp=document.getElementById('activ-serial');
  if(sinp) sinp.oninput=_updateActivAccessPreview;
  _updateActivAccessPreview();
}

function _updateActivAccessPreview(){
  var el=document.getElementById('activ-access-preview'); if(!el) return;
  var raw=(document.getElementById('activ-access')||{}).value||'';
  var suffix=(document.getElementById('activ-serial')||{}).value||'';
  var h='';
  _ACTIV_META.forEach(function(m){
    var resolved=_resolveAccessId(raw.trim(),_ACTIV_VNO_CODES[m.tc]);
    var serial=_ACTIV_SERIAL_BASE[m.tc]?(esc(_ACTIV_SERIAL_BASE[m.tc])+esc(suffix)):'(sin serial)';
    h+='<span class="aap-item"><span class="aap-vno">'+esc(m.label)+':</span>'
      +'<span class="aap-id">'+esc(resolved)+'</span>'
      +'<span class="aap-serial">&#128273; '+serial+'</span></span>';
  });
  el.innerHTML=h||'<span class="aap-empty">Ingresa un Access ID para ver la preview por VNO</span>';
}

function renderActivSelBar(){
  var bar=document.getElementById('activ-sel-bar'); if(!bar) return;
  var h='<span class="fsb-lbl">VNOs a ejecutar:</span>';
  _ACTIV_META.forEach(function(m){
    var on=_activSel[m.tc]?'on':'';
    h+='<button class="tc-sel-btn '+on+'" id="actsb-'+m.tc+'">'+esc(m.label)+'</button>';
  });
  h+='<span class="fsb-sep"></span>'
    +'<button class="fsb-all" id="actsb-all">Todos</button>'
    +'<button class="fsb-all" id="actsb-none">Ninguno</button>';
  bar.innerHTML=h;
  _ACTIV_META.forEach(function(m){
    document.getElementById('actsb-'+m.tc).onclick=(function(tc){
      return function(){ _activSel[tc]=!_activSel[tc];
        var btn=document.getElementById('actsb-'+tc);
        if(btn) btn.className='tc-sel-btn'+(_activSel[tc]?' on':'');
        renderActivView(); _syncActivExecBtn(); };
    })(m.tc);
  });
  document.getElementById('actsb-all').onclick=function(){
    _ACTIV_META.forEach(function(m){ _activSel[m.tc]=true; }); renderActivSelBar(); renderActivView(); _syncActivExecBtn(); };
  document.getElementById('actsb-none').onclick=function(){
    _ACTIV_META.forEach(function(m){ _activSel[m.tc]=false; }); renderActivSelBar(); renderActivView(); _syncActivExecBtn(); };
}

function _syncActivExecBtn(){
  var anyOn=_ACTIV_META.some(function(m){ return _activSel[m.tc]; });
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=running||!anyOn;
}

function renderActivView(){
  var grid=document.getElementById('activ-grid'); if(!grid) return;
  grid.innerHTML='';
  var _sel=_ACTIV_META.filter(function(m){ return _activSel[m.tc]; });
  grid.style.gridTemplateColumns=_sel.length===1?'1fr':'1fr 1fr';
  _sel.forEach(function(m){
    var p=document.createElement('div'); p.className='fact-panel'; p.id='acp-'+m.tc;
    var _tc=m.tc;
    p.innerHTML=
      '<div class="fp-hdr">'
      +'<span class="fp-dot idle" id="acpd-'+_tc+'"></span>'
      +'<span class="fp-name" style="color:'+m.color+'">'+esc(m.label)+'</span>'
      +'<span style="font-size:.65rem;color:var(--txt3)">'+esc(m.vno)+'</span>'
      +'<span class="fp-badge idle" id="acpb-'+_tc+'">espera</span>'
      +'<a class="fp-rpt" id="acpr-'+_tc+'" href="#" target="_blank">&#128196; Ver</a>'
      +'</div>'
      +'<div class="fact-term" id="act-'+_tc+'"></div>'
      +'<div class="fp-resp-bar" id="acfrb-'+_tc+'">'
      +'<span class="fr-label">Response</span>'
      +'<span id="acfrs-'+_tc+'"></span>'
      +'</div>'
      +'<div class="fp-resp" id="acfr-'+_tc+'"><span class="fr-empty">—</span></div>';
    grid.appendChild(p);
  });
}

function _activApp(tc,text,cls){
  var el=document.getElementById('act-'+tc); if(!el) return;
  var sp=document.createElement('span');
  sp.className='tl'+(cls?' '+cls:'');
  sp.textContent=text+'\\n';
  el.appendChild(sp); el.scrollTop=el.scrollHeight;
}

function _activSetState(tc,state){
  var dot=document.getElementById('acpd-'+tc);
  var badge=document.getElementById('acpb-'+tc);
  var states={idle:'espera',running:'ejecutando',passed:'OK ✓',failed:'FAIL ✗'};
  if(dot){ dot.className='fp-dot '+state; }
  if(badge){ badge.className='fp-badge '+state; badge.textContent=states[state]||state; }
}

function _activSetResponse(tc,responses){
  var el=document.getElementById('acfr-'+tc);
  var bar=document.getElementById('acfrs-'+tc);
  if(!el||!responses||!responses.length) return;
  var r=responses[responses.length-1];
  var cls=r.code>=200&&r.code<300?'ok':r.code>=400?'err':'warn';
  if(bar){
    bar.innerHTML='<span class="fr-scode '+cls+'">'+r.code+' '+esc(r.status||'')+'</span>'
      +'<span class="fr-stime">'+r.time_ms+'ms</span>'
      +'<span class="fr-sname">'+esc(r.name||'')+'</span>';
  }
  var bodyTxt=r.body||'';
  if(bodyTxt){ try{ bodyTxt=JSON.stringify(JSON.parse(bodyTxt),null,2); }catch(e){} }
  el.innerHTML=bodyTxt?'<pre>'+esc(bodyTxt)+'</pre>':'<span class="fr-empty">Sin body</span>';
}

function _doRunActiv(s){
  if(running) return;
  var accessEl=document.getElementById('activ-access');
  if(!accessEl||!accessEl.value.trim()){ if(accessEl) accessEl.style.borderColor='var(--err)'; return; }
  accessEl.style.borderColor='';
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  document.getElementById('run-all').disabled=true;
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _ACTIV_META.forEach(function(m){
    var at=document.getElementById('act-'+m.tc); if(at) at.innerHTML='';
    var afr=document.getElementById('acfr-'+m.tc); if(afr) afr.innerHTML='<span class="fr-empty">—</span>';
    var afrs=document.getElementById('acfrs-'+m.tc); if(afrs) afrs.innerHTML='';
    var acpr=document.getElementById('acpr-'+m.tc); if(acpr) acpr.classList.remove('show');
    _activSetState(m.tc,'idle');
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _rawAccess=accessEl.value.trim();
  var _selTcs=_ACTIV_META.filter(function(m){return _activSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var _accessMap={};
  _ACTIV_META.forEach(function(m){ _accessMap[m.tc]=_resolveAccessId(_rawAccess,_ACTIV_VNO_CODES[m.tc]); });
  var _speed=(document.getElementById('activ-speed')||{}).value||'600/600';
  var _serial=(document.getElementById('activ-serial')||{}).value||'0000';
  var _sba=(document.getElementById('activ-sba')||{}).checked!==false;
  var _svoip=(document.getElementById('activ-svoip')||{}).checked!==false;
  var _siptv=(document.getElementById('activ-siptv')||{}).checked!==false;
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&access_ids='+encodeURIComponent(JSON.stringify(_accessMap))
    +'&speed_plan='+encodeURIComponent(_speed)
    +'&serial_suffix='+encodeURIComponent(_serial)
    +'&service_ba='+(_sba?'true':'false')
    +'&service_voip='+(_svoip?'true':'false')
    +'&service_iptv='+(_siptv?'true':'false');
  var es=new EventSource('/api/run/qa-activ-suite?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _activApp(d.tc,d.t,col(d.t)); _activSetState(d.tc,'running'); }
      suiteLogs[s.id].push({text:d.t,cls:col(d.t)});
    } else if(d.e==='tc_done'){
      _activSetState(d.tc,d.code===0?'passed':'failed');
      if(d.has_report){
        var acpr=document.getElementById('acpr-'+d.tc);
        if(acpr){acpr.href='/api/report/'+d.sid;acpr.classList.add('show');}
      }
    } else if(d.e==='tc_response'){
      _activSetResponse(d.tc,d.responses);
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error') onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){ currentEs=null; es.close();
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s); }
  };
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
      else if(selectedId==='qa-ep-activacion') renderActivacionForm();
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
var QA_ACTIVACION_PLACEHOLDER={
  '00':'00TESTQASMERROR030-0506-12',
  '02':'ej. 02-OrderCharacteristics-30',
  '03':'ej. 03-SMQAPREACT2111-01',
  '05':'ej. 05-QAONETO-01',
};
function renderActivacionForm(){
  var container=document.getElementById("epf-container");
  if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO;
  var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="Activación";
  var sf=document.createElement("div"); sf.className="epf-folder";
  sf.innerHTML='Endpoint: <span>fullFillment-activation/v1/registrationActivation</span>';
  card.appendChild(tt); card.appendChild(sf);
  // u_id_vno (auto)
  var f1=document.createElement("div"); f1.className="epf-field";
  var l1=document.createElement("label"); l1.className="epf-label"; l1.textContent="u_id_vno (auto)";
  var v1=document.createElement("div"); v1.className="epf-readonly";
  v1.style.color=clr; v1.textContent=vno+" — "+(_QA_VNO_LABELS[vno]||vno);
  f1.appendChild(l1); f1.appendChild(v1); card.appendChild(f1);
  // u_access_id_vno (text — placeholder cambia por VNO)
  var f2=document.createElement("div"); f2.className="epf-field";
  var l2=document.createElement("label"); l2.className="epf-label"; l2.textContent="u_access_id_vno";
  var i2=document.createElement("input"); i2.type="text"; i2.className="epf-input"; i2.id="epf-activ-access";
  i2.placeholder=QA_ACTIVACION_PLACEHOLDER[vno]||"";
  f2.appendChild(l2); f2.appendChild(i2); card.appendChild(f2);
  // u_speed_plan (select)
  var f3=document.createElement("div"); f3.className="epf-field";
  var l3=document.createElement("label"); l3.className="epf-label"; l3.textContent="u_speed_plan";
  var s3=document.createElement("select"); s3.className="epf-select"; s3.id="epf-activ-speed";
  QA_SPEED_PLANS.forEach(function(sp){
    var o=document.createElement("option"); o.value=sp; o.textContent=sp;
    if(sp==="600/600") o.selected=true;
    s3.appendChild(o);
  });
  f3.appendChild(l3); f3.appendChild(s3); card.appendChild(f3);
  // u_serial_number (text — solo VNOs distintos de 00)
  if(vno!=='00'){
    var f4=document.createElement("div"); f4.className="epf-field";
    var l4=document.createElement("label"); l4.className="epf-label"; l4.textContent="u_serial_number";
    var i4=document.createElement("input"); i4.type="text"; i4.className="epf-input"; i4.id="epf-activ-serial";
    i4.placeholder="ej. ZTEGD719D911";
    f4.appendChild(l4); f4.appendChild(i4); card.appendChild(f4);
  }
  // u_service_ba / voip / iptv (select true/false)
  [['u_service_ba','epf-activ-ba'],['u_service_voip','epf-activ-voip'],['u_service_iptv','epf-activ-iptv']].forEach(function(pair){
    var fx=document.createElement("div"); fx.className="epf-field";
    var lx=document.createElement("label"); lx.className="epf-label"; lx.textContent=pair[0];
    var sx=document.createElement("select"); sx.className="epf-select"; sx.id=pair[1];
    ['true','false'].forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;if(v==="true")o.selected=true;sx.appendChild(o);});
    fx.appendChild(lx); fx.appendChild(sx); card.appendChild(fx);
  });
  // u_operation_type (fixed)
  var fop=document.createElement("div"); fop.className="epf-field";
  var lop=document.createElement("label"); lop.className="epf-label"; lop.textContent="u_operation_type (fijo)";
  var vop=document.createElement("div"); vop.className="epf-readonly";
  vop.style.color="var(--txt3)"; vop.style.borderStyle="dashed"; vop.textContent="A";
  fop.appendChild(lop); fop.appendChild(vop); card.appendChild(fop);
  var eb=document.createElement("button"); eb.className="epf-exec"; eb.textContent="▶ Ejecutar";
  eb.disabled=running;
  eb.onclick=function(){
    var accessEl=document.getElementById("epf-activ-access");
    var speedEl=document.getElementById("epf-activ-speed");
    var serialEl=document.getElementById("epf-activ-serial");
    var baEl=document.getElementById("epf-activ-ba");
    var voipEl=document.getElementById("epf-activ-voip");
    var iptvEl=document.getElementById("epf-activ-iptv");
    if(!accessEl||!speedEl) return;
    runActivacion({
      vno:_globalVNO,
      access_id_vno:accessEl.value,
      speed_plan:speedEl.value,
      serial_number:serialEl?serialEl.value:"",
      service_ba:baEl.value,
      service_voip:voipEl.value,
      service_iptv:iptvEl.value,
    });
  };
  card.appendChild(eb);
  container.appendChild(card);
}
function runActivacion(params){
  if(running) return;
  var sid="qa-ep-activacion";
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
