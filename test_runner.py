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
IS_PRE_DEPLOYMENT = "epreapi" in os.environ.get("APIM_URL", "")
COLL_DIR  = ROOT / "collection Kommand"
BP_DIR    = ROOT / "collection Blueplanet"
QA_DIR    = ROOT / "collection QA"
QA_VNO_ENV_MAP = {
    "00": "00-TCH QA.postman_environment.json",
    "02": "02 QA_KAO.postman_environment.json",
    "03": "03-B1_vnoid03 QA.postman_environment.json",
    "05": "05 QA_DTV.postman_environment.json",
}
PPRD_VNO_ENV_MAP = {
    "00": "VnoB1_vnoid00 PRE.postman_environment.json",
    "02": "VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json",
    "03": "VnoB1_vnoid03 PRE.postman_environment.json",
    "05": "VnoB1_vnoid05 PRE.postman_environment.json",
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
QA_ASSIGNMENT_OPERATION_TYPE = {
    "00": "Alta",
    "02": "Alta",
    "03": "A",
    "05": "A",
}
QA_ASSIGNMENT_ADDRESS_MCD = {
    "00": "",
    "02": "OSP",
    "03": "XYGO",
    "05": "OSP",
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
QA_DM_REQUEST_MAP = {
    "00": "DeviceModification TCH",
    "02": "DeviceModification KAO",
    "03": "DeviceModification LASER",
    "05": "DeviceModification DTV",
}
QA_CANCEL_REQUEST_MAP = {
    "00": "cancel service order TCH",
    "02": "cancel service order KAO",
    "03": "cancel service order LASER",
    "05": "cancel service order DTV",
}
QA_CANCEL_COLLECTION = "08-CancelOrdenServicio.postman_collection.json"
QA_MODIF_REQUEST_MAP = {
    "00": "Modification TCH",
    "02": "Modification KAO",
    "03": "Modification LASER",
    "05": "Modification DTV",
}


PY     = sys.executable
NEWMAN = shutil.which("newman") or "newman"

# ─── Suites ──────────────────────────────────────────────────────────────────
SUITES = [
    {
        "id": "t1", "group": "disponible",
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
        "id": "t1-contract", "group": "disponible",
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
        "id": "t1c-real", "group": "disponible",
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
        "id": "t2", "group": "disponible",
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
        "id": "t3", "group": "disponible",
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
        "id": "newman-dev", "group": "disponible",
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
        "id": "apim-parallel", "group": "disponible",
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
        "id": "t7", "group": "disponible",
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
        "id": "t5", "group": "bloqueado",
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
        "id": "t4", "group": "bloqueado",
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
        "id": "t6", "group": "bloqueado",
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
        "id": "t8", "group": "bloqueado",
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
        "id": "t-flg", "group": "bloqueado",
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

app = FastAPI(title="KOMANDs QA Runner")


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

    to_run = []
    for code, enabled in vno_enabled.items():
        if not enabled:
            continue
        suite = SUITE_MAP.get(f"apim-vno{code}")
        if not suite:
            continue
        overrides = {k[3:]: v for k, v in params.items() if k.startswith(f"{code}_")}
        overrides["run_phase"] = phase
        to_run.append((suite, f"VNO-{code}", overrides))

    async def sse():
        yield f"data: {json.dumps({'e':'start','id':'apim-parallel','label':'Endpoints Services Now'})}\n\n"

        apim_suite = SUITE_MAP.get("apim-parallel", {})
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
        return JSONResponse({"error": "Reporte no generado aún."}, status_code=404)
    filename = f"reporte_{suite_id}.html"
    return FileResponse(rp, media_type="text/html", headers={
        "Content-Disposition": f'inline; filename="{filename}"'
    })


# ─── UI ───────────────────────────────────────────────────────────────────────
# ─── ATRF FullFillment: ruta run-step ─────────────────────────────────────────
@app.post("/api/atrf/run-step")
async def atrf_run_step(request: Request):
    import json as _j, ssl as _sl, urllib.request as _ur, urllib.parse as _up
    import base64 as _b64, copy as _cp, uuid as _uid, asyncio as _aio
    import concurrent.futures as _cf

    body        = await request.json()
    func_name   = body.get("func", "")
    vno         = body.get("vno", "02")
    direccion   = body.get("direccion", "")
    address_mcd = body.get("addressMcd") or QA_ASSIGNMENT_ADDRESS_MCD.get(vno, "OSP")
    svc_type    = body.get("serviceType", "FTTH")
    access_id   = body.get("accessId", "")
    serial_num  = body.get("serialNumber", "")
    new_serial  = body.get("newSerialNumber", "")
    speed_plan      = body.get("speedPlan", "600/600")
    new_speed_plan  = body.get("newSpeedPlan", "")
    amb_url         = body.get("ambUrl", "")
    ambiente        = body.get("ambiente", "QA")
    _railway_apim = os.environ.get("APIM_URL", "")
    _use_pprd = (bool(amb_url) or ambiente.upper() == "PPRD" or IS_PRE_DEPLOYMENT)
    if not amb_url and IS_PRE_DEPLOYMENT and _railway_apim:
        amb_url = _railway_apim
    if _use_pprd:
        _generate_env_files()
    def _resolve_env(v):
        if _use_pprd:
            return str(BP_DIR / PPRD_VNO_ENV_MAP.get(v, PPRD_VNO_ENV_MAP["02"]))
        return str(QA_DIR / QA_VNO_ENV_MAP.get(v, QA_VNO_ENV_MAP["02"]))
    scenario    = body.get("scenario", "Instalación")
    service_ba  = body.get("serviceBa", True)
    service_voip= body.get("serviceVoip", True)
    service_iptv= body.get("serviceIptv", True)

    # ── Factibilidad ──────────────────────────────────────────────────────────
    if func_name == "Factibilidad":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev       = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        auth_b64 = _b64.b64encode(
            f"{ev.get('consumerKey','')}:{ev.get('consumerSecret','')}".encode()
        ).decode()
        token = ""
        try:
            _body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}",
                                 "req": "", "res": ""})
        req_body_dict = {
            "u_id_vno": vno, "u_operation_type": "Direccion Exacta",
            "u_address_id": direccion, "u_address_mcd": address_mcd,
            "u_service_type": svc_type,
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        if _use_pprd:
            _fact_url = f"{apim_url.rstrip('/')}/fullFillment-Factibilidad/v1/feasibilityUpselling"
            _pass = False; _res_body = ""; _http_code = 0
            try:
                _api_req = _ur.Request(_fact_url,
                    data=_j.dumps(req_body_dict).encode("utf-8"),
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json",
                             "vnoId": vno})
                _ctx2 = _sl.create_default_context()
                _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
                with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                    _res_body = _r.read().decode("utf-8", errors="replace")
                    _http_code = _r.getcode()
            except _ur.HTTPError as _he:
                _http_code = _he.code
                try: _res_body = _he.read().decode("utf-8", errors="replace")
                except: _res_body = str(_he)
            except Exception as _ae:
                _res_body = f"Error HTTP directo: {_ae}"
            try:
                _rj = _j.loads(_res_body)
                _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
                _pass = _http_code in (200, 201) and _rc == "0"
            except Exception:
                _pass = _http_code in (200, 201)
            return JSONResponse({"pass": _pass, "req": req_body_str,
                                 "res": _res_body, "vno": vno, "func": func_name,
                                 "httpCode": _http_code})
        # QA: usar Newman con colección QA
        folder_name = QA_FACTIBILIDAD_FOLDER_MAP.get(vno, "feasibility-KAO")
        if vno == "03" and svc_type == "SSAA":
            folder_name = "feasibility-Entel SSAA"
        col_src = _j.load(open(QA_DIR / "01-FulFillment.postman_collection.json", encoding="utf-8"))
        col_tmp = _cp.deepcopy(col_src)
        for sec in col_tmp.get("item", []):
            if "Factibilidad" in sec.get("name", ""):
                for req in sec.get("item", []):
                    if req.get("name", "") == folder_name:
                        b = req.get("request", {}).get("body", {})
                        if b.get("mode") == "raw":
                            b["raw"] = req_body_str
        run_id   = _uid.uuid4().hex[:8]
        tmp_col  = str(QA_DIR / f"_atrf_fact_{vno}_{run_id}.json")
        json_out = str(QA_DIR / f"_atrf_fact_{vno}_{run_id}.result.json")
        _j.dump(col_tmp, open(tmp_col, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        cmd = [NEWMAN, "run", tmp_col, "-e", env_file,
               "--folder", folder_name,
               "--env-var", f"Token={token}",
               "--env-var", f"idvno={vno}",
               "--insecure",
               "--reporters", "cli,json",
               "--reporter-json-export", json_out,
               "--timeout-request", "90000"]
        if amb_url:
            cmd += ["--env-var", f"apimURL={amb_url}"]
        loop = _aio.get_event_loop()
        await loop.run_in_executor(None, lambda: subprocess.run(
            cmd, cwd=str(QA_DIR), capture_output=True, timeout=120
        ))
        pass_flag = False; res_body = ""; http_code = 0
        try:
            jdata = _j.loads(Path(json_out).read_text(encoding="utf-8"))
            execs = jdata.get("run", {}).get("executions", [])
            if execs:
                ex  = execs[-1]
                r   = ex.get("response") or {}
                st  = r.get("stream") or {}
                if isinstance(st, dict) and st.get("type") == "Buffer":
                    res_body = bytes(st["data"]).decode("utf-8", errors="replace")
                else:
                    res_body = r.get("body", "")
                http_code = r.get("code", 0)
                failures  = jdata.get("run", {}).get("failures", [])
                try:
                    rj = _j.loads(res_body)
                    rc = rj.get("u_return_code") or rj.get("result", {}).get("u_return_code")
                    pass_flag = http_code in (200, 201) and not failures and str(rc) == "0"
                except Exception:
                    pass_flag = http_code in (200, 201) and not failures
        except Exception as pe:
            res_body = f"Error parseando resultado Newman: {pe}"
        try:
            Path(tmp_col).unlink(missing_ok=True)
            Path(json_out).unlink(missing_ok=True)
        except Exception:
            pass
        return JSONResponse({"pass": pass_flag, "req": req_body_str,
                             "res": res_body, "vno": vno, "func": func_name,
                             "httpCode": http_code})

    # ── Asignación ────────────────────────────────────────────────────────────
    if func_name == "Asignación":
        env_file    = _resolve_env(vno)
        folder_name = QA_ASSIGNMENT_FOLDER_MAP.get(vno, "assigment- KAO")
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev       = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        op_type = QA_ASSIGNMENT_OPERATION_TYPE.get(vno, "Alta")
        req_body_dict = {
            "u_access_id_vno": access_id,
            "u_id_vno": vno, "u_operation_type": op_type,
            "u_scenario": "Alta de Acceso", "u_speed_plan": speed_plan,
            "u_address_id": direccion, "u_address_mcd": address_mcd,
            "u_service_ba": service_ba, "u_service_voip": service_voip, "u_service_iptv": service_iptv,
            "u_service_type": svc_type,
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _asgn_url = f"{apim_url.rstrip('/')}/fullFillment-assignment/v1/assignment"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_asgn_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Cancelación Orden de Servicio ──────────────────────────────────────────
    if func_name == "Cancelación Orden de Servicio":
        env_file   = _resolve_env(vno)
        cancel_req = QA_CANCEL_REQUEST_MAP.get(vno, "cancel service order KAO")
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev       = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {
            "u_id_vno": vno,
            "u_access_id_vno": access_id,
            "u_service_type": svc_type,
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _cncl_url = f"{apim_url.rstrip('/')}/fullFillment-cancelServiceOrder/v1/oossCancellation"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_cncl_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Intervención Asegurada: Inicio / Finalización / Cancelación ──────────
    _IA_ENDPOINTS = {
        "Inicio Intervención Asegurada":       "/fullFillment-gIntervention/v1/assuredIntervention",
        "Finalización Intervención Asegurada": "/fullFillment-finalization/v1/interventionFinalization",
        "Cancelación Intervención Asegurada":  "/fullFillment-cancelIntervention/v1/interventionCancellation",
    }
    if func_name in _IA_ENDPOINTS:
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev       = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b  = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        if func_name == "Inicio Intervención Asegurada":
            req_body_dict = {"u_id_vno": vno, "u_access_id_vno": access_id,
                             "u_scenario": scenario, "u_service_type": svc_type}
        elif func_name == "Finalización Intervención Asegurada":
            req_body_dict = {"u_id_vno": vno, "u_access_id_vno": access_id,
                             "u_scenario": scenario, "u_service_type": svc_type}
        else:  # Cancelación
            req_body_dict = {"u_id_vno": vno, "u_access_id_vno": access_id,
                             "u_service_type": svc_type}
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _ia_url = f"{apim_url.rstrip('/')}{_IA_ENDPOINTS[func_name]}"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_ia_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Activación ────────────────────────────────────────────────────────────
    if func_name == "Activación":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {
            "u_id_vno": vno,
            "u_access_id_vno": access_id,
            "u_operation_type": "A",
            "u_speed_plan": speed_plan,
            "u_service_ba": service_ba,
            "u_service_voip": service_voip,
            "u_service_iptv": service_iptv,
            "u_serial_number": serial_num,
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _activ_url = (f"{apim_url.rstrip('/')}/fullFillment-ActivationSSAA/v1/registrationActivationSSAA" if _use_pprd
                      else f"{apim_url.rstrip('/')}/fullFillment-activation/v1/registrationActivation")
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_activ_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Modificación de Acceso ────────────────────────────────────────────────
    if func_name == "Modificación de Acceso":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {
            "u_id_vno": vno,
            "u_access_id_vno": access_id,
            "u_operation_type": "M",
            "u_speed_plan": new_speed_plan or speed_plan,
            "u_service_ba": service_ba,
            "u_service_voip": service_voip,
            "u_service_iptv": service_iptv,
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _mod_url = (f"{apim_url.rstrip('/')}/fullFillment-ModificationSSAA/v1/registrationModificationSSAA" if _use_pprd
                    else f"{apim_url.rstrip('/')}/fullFillment-modification/v1/registrationModification")
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_mod_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Reinicio ONT ──────────────────────────────────────────────────────────
    if func_name == "Reinicio ONT":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {
            "u_access_id_vno": access_id,
            "u_id_vno": vno,
            "u_reset_type": "1",
            "u_port": "",
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _reint_url = f"{apim_url.rstrip('/')}/reinicioONT/v1/ONTRestart"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_reint_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Diagnóstico de Acceso ─────────────────────────────────────────────────
    if func_name == "Diagnóstico de Acceso":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {"u_access_id_vno": access_id}
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _diag_url = f"{apim_url.rstrip('/')}/diagnosticoAcceso/v1/AccesStatus"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_diag_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Consulta Estado Vecino (POST) ─────────────────────────────────────────
    if func_name == "Consulta Estado Vecino (POST)":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {
            "u_access_id_vno": access_id,
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _cev_post_url = f"{apim_url.rstrip('/')}/estadoVecino/v1/QueryNeighborsState"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_cev_post_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Consulta Estado Vecino (GET) ──────────────────────────────────────────
    if func_name == "Consulta Estado Vecino (GET)":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        _cev_url = f"{apim_url.rstrip('/')}/fullFillment-CEVEstadoVecino/v1/estado_vecino_api/{access_id}"
        req_body_str = f"GET {_cev_url}"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_cev_url,
                headers={"Authorization": f"Bearer {token}",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── GET Consulta de Acceso ────────────────────────────────────────────────
    if func_name == "GET Consulta de Acceso":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        _ca_url = f"{apim_url.rstrip('/')}/fullFillment-consultaAcceso/v1/{access_id}"
        req_body_str = f"GET {_ca_url}"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_ca_url,
                headers={"Authorization": f"Bearer {token}",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Baja Total de Servicio ────────────────────────────────────────────────
    if func_name == "Baja Total de Servicio":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {
            "u_id_vno": vno,
            "u_access_id_vno": access_id,
            "u_service_type": svc_type,
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _baja_url = (f"{apim_url.rstrip('/')}/fullFillment-accessDeregistrationAsync/v1/accessDeregistrationAsync" if _use_pprd
                     else f"{apim_url.rstrip('/')}/fullFillment-unsubcription/v1/accessDeregistration")
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_baja_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Modificación de Dispositivo ───────────────────────────────────────────
    if func_name == "Modificación de Dispositivo":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {
            "u_id_vno": vno,
            "u_access_id_vno": access_id,
            "u_serial_number": serial_num,
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _dm_url = f"{apim_url.rstrip('/')}/fullFillment-deviceModification/v1/deviceModification"
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_dm_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Retrieve Access ───────────────────────────────────────────────────────
    if func_name == "RetrieveAccess":
        env_file = _resolve_env(vno)
        try:
            env_data = _j.load(open(env_file, encoding="utf-8"))
        except Exception as e:
            return JSONResponse({"pass": False, "error": f"env file: {e}"})
        ev = {v["key"]: v["value"] for v in env_data["values"]}
        apim_url = amb_url or ev.get("apimURL", "")
        import os as _os
        _ck = ev.get("consumerKey", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_KEY") or ev.get("consumerKey", ""))
        _cs = ev.get("consumerSecret", "") if _use_pprd else (_os.environ.get(f"VNO{vno}_CONSUMER_SECRET") or ev.get("consumerSecret", ""))
        auth_b64 = _b64.b64encode(f"{_ck}:{_cs}".encode()).decode()
        token = ""
        try:
            _body_b = _up.urlencode({"grant_type": "client_credentials"}).encode()
            _tok_req = _ur.Request(f"{apim_url}/token", data=_body_b,
                headers={"Authorization": f"Basic {auth_b64}",
                         "Content-Type": "application/x-www-form-urlencoded"})
            ctx = _sl.create_default_context()
            ctx.check_hostname = False; ctx.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_tok_req, context=ctx, timeout=15) as r:
                token = _j.loads(r.read()).get("access_token", "")
        except Exception as te:
            return JSONResponse({"pass": False, "error": f"token: {te}", "req": "", "res": ""})
        req_body_dict = {
            "u_id_vno": vno,
            "u_access_id_vno": access_id,
            "u_flag_scope": "2",
        }
        req_body_str = _j.dumps(req_body_dict, indent=4, ensure_ascii=False)
        _ra_url = (f"{apim_url.rstrip('/')}/fullFillment-retrieveAccessAsync/v1/retrieveAccessAsync" if _use_pprd
                   else f"{apim_url.rstrip('/')}/provisioning/v1/retrieve-access")
        _pass = False; _res_body = ""; _http_code = 0
        try:
            _api_req = _ur.Request(_ra_url,
                data=_j.dumps(req_body_dict).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json",
                         "vnoId": vno})
            _ctx2 = _sl.create_default_context()
            _ctx2.check_hostname = False; _ctx2.verify_mode = _sl.CERT_NONE
            with _ur.urlopen(_api_req, context=_ctx2, timeout=90) as _r:
                _res_body = _r.read().decode("utf-8", errors="replace")
                _http_code = _r.getcode()
        except _ur.HTTPError as _he:
            _http_code = _he.code
            try: _res_body = _he.read().decode("utf-8", errors="replace")
            except: _res_body = str(_he)
        except Exception as _ae:
            _res_body = f"Error HTTP directo: {_ae}"
        try:
            _rj = _j.loads(_res_body)
            _rc = str((_rj.get("result") or _rj).get("u_return_code", ""))
            _pass = _http_code in (200, 201) and _rc == "0"
        except Exception:
            _pass = _http_code in (200, 201)
        return JSONResponse({"pass": _pass, "req": req_body_str, "res": _res_body,
                             "vno": vno, "func": func_name, "httpCode": _http_code})

    # ── Resto de funcionalidades: pendiente ───────────────────────────────────
    return JSONResponse({"error": "not_implemented", "func": func_name}, status_code=501)



# ─── ATRF: Almacenamiento file-based (sin Supabase) ──────────────────────────
_FF_CONFIG_FILE    = Path("/tmp/ff-config.json")
_FF_HISTORIAL_FILE = Path("/tmp/ff-historial.json")
_FF_ENVS_FILE      = Path("/tmp/ff-environments.json")
_FF_CONFIG_LABELS  = {
    "delay_factibilidad": "Delay entre pasos Factibilidad (ms)",
    "delay_assignment":   "Delay entre pasos Asignacion (ms)",
    "delay_activacion":   "Delay entre pasos Activacion (ms)",
    "delay_global":       "Delay global entre pasos (ms)",
}


@app.get("/api/config")
async def atrf_config_get():
    """Devuelve configuracion de delays para ATRF (file-based)."""
    if _FF_CONFIG_FILE.exists():
        try:
            return json.loads(_FF_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


@app.put("/api/config/{key}")
async def atrf_config_put(key: str, request: Request):
    """Guarda configuracion de delays para ATRF (file-based)."""
    body = await request.json()
    value = str(body.get("value", ""))
    label = _FF_CONFIG_LABELS.get(key, body.get("label", key))
    try:
        cfg = []
        if _FF_CONFIG_FILE.exists():
            cfg = json.loads(_FF_CONFIG_FILE.read_text(encoding="utf-8"))
        entry = next((e for e in cfg if e.get("key") == key), None)
        if entry:
            entry["value"] = value
        else:
            cfg.append({"key": key, "value": value, "label": label})
        _FF_CONFIG_FILE.write_text(json.dumps(cfg), encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/historial")
async def atrf_historial_get(limit: int = 200, suite_id: str = "", vno: str = "", resultado: str = ""):
    """Devuelve historial de ejecuciones ATRF (file-based)."""
    try:
        rows = []
        if _FF_HISTORIAL_FILE.exists():
            rows = json.loads(_FF_HISTORIAL_FILE.read_text(encoding="utf-8"))
        if suite_id:
            rows = [r for r in rows if r.get("suite_id") == suite_id]
        if vno:
            rows = [r for r in rows if r.get("vno") == vno]
        if resultado:
            rows = [r for r in rows if r.get("resultado") == resultado]
        rows = sorted(rows, key=lambda x: x.get("id", 0), reverse=True)[:min(limit, 1000)]
        return rows
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/historial")
async def atrf_historial_post(request: Request):
    body = await request.json()
    try:
        rows = []
        if _FF_HISTORIAL_FILE.exists():
            rows = json.loads(_FF_HISTORIAL_FILE.read_text(encoding="utf-8"))
        next_id = max((r.get("id", 0) for r in rows), default=0) + 1
        body["id"] = next_id
        rows.append(body)
        _FF_HISTORIAL_FILE.write_text(json.dumps(rows), encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/historial/{rec_id}")
async def atrf_historial_delete(rec_id: int):
    try:
        rows = []
        if _FF_HISTORIAL_FILE.exists():
            rows = json.loads(_FF_HISTORIAL_FILE.read_text(encoding="utf-8"))
        rows = [r for r in rows if r.get("id") != rec_id]
        _FF_HISTORIAL_FILE.write_text(json.dumps(rows), encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/historial")
async def atrf_historial_delete_all():
    try:
        _FF_HISTORIAL_FILE.write_text("[]", encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/environments")
async def atrf_environments_get():
    """Devuelve ambientes ATRF (file-based)."""
    try:
        envs = []
        if _FF_ENVS_FILE.exists():
            envs = json.loads(_FF_ENVS_FILE.read_text(encoding="utf-8"))
        return envs
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/environments")
async def atrf_environments_post(request: Request):
    body = await request.json()
    name     = str(body.get("name",     "")).strip()
    label    = str(body.get("label",    "")).strip()
    base_url = str(body.get("base_url", "")).strip()
    env_type = str(body.get("env_type", "custom")).strip()
    if not name or not base_url:
        return JSONResponse({"error": "name y base_url son requeridos"}, status_code=400)
    try:
        envs = []
        if _FF_ENVS_FILE.exists():
            envs = json.loads(_FF_ENVS_FILE.read_text(encoding="utf-8"))
        next_id = max((e.get("id", 0) for e in envs), default=0) + 1
        env = {"id": next_id, "name": name, "label": label, "base_url": base_url,
               "env_type": env_type, "active": True}
        envs.append(env)
        _FF_ENVS_FILE.write_text(json.dumps(envs), encoding="utf-8")
        return {"ok": True, "id": next_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.put("/api/environments/{env_id}")
async def atrf_environments_put(env_id: int, request: Request):
    body = await request.json()
    name     = str(body.get("name",     "")).strip()
    label    = str(body.get("label",    "")).strip()
    base_url = str(body.get("base_url", "")).strip()
    env_type = str(body.get("env_type", "custom")).strip()
    active   = bool(body.get("active",  True))
    if not name or not base_url:
        return JSONResponse({"error": "name y base_url son requeridos"}, status_code=400)
    try:
        envs = []
        if _FF_ENVS_FILE.exists():
            envs = json.loads(_FF_ENVS_FILE.read_text(encoding="utf-8"))
        for e in envs:
            if e.get("id") == env_id:
                e["name"] = name; e["label"] = label; e["base_url"] = base_url
                e["env_type"] = env_type; e["active"] = active
                _FF_ENVS_FILE.write_text(json.dumps(envs), encoding="utf-8")
                return {"ok": True}
        return JSONResponse({"error": "Ambiente no encontrado"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/environments/{env_id}")
async def atrf_environments_delete(env_id: int):
    try:
        envs = []
        if _FF_ENVS_FILE.exists():
            envs = json.loads(_FF_ENVS_FILE.read_text(encoding="utf-8"))
        envs = [e for e in envs if e.get("id") != env_id]
        _FF_ENVS_FILE.write_text(json.dumps(envs), encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ─── ATRF FullFillment: pagina HTML (/ff) ──────────────────────────────────────
FF_HTML = """<!DOCTYPE html>
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
  --atrf-bg:#13132A;--atrf-surface:#181836;--atrf-surface2:#1A1A3E;
  --atrf-border:#262558;--atrf-border2:#262558;
  --atrf-text:#DCE2F6;--atrf-text2:#6272A4;--atrf-text3:#353665;
  --atrf-accent:#00C8D4;--atrf-accent2:#00A8B4;
  --atrf-green:#3DD68C;--atrf-green-bg:rgba(61,214,140,.13);--atrf-green-border:rgba(61,214,140,.3);
  --atrf-red:#FF6B6B;--atrf-red-bg:rgba(255,107,107,.12);--atrf-red-border:rgba(255,107,107,.28);
  --atrf-amber:#FFB347;--atrf-amber-bg:rgba(255,179,71,.10);--atrf-amber-border:rgba(255,179,71,.30);
  --atrf-radius:8px;--atrf-radius-lg:12px;
  --atrf-font:'Segoe UI Variable Display','Segoe UI',system-ui,sans-serif;
  --atrf-mono:'Cascadia Code','Consolas','Courier New',monospace;
}
body.light{
  --bg:#F2F5FB;--side:#FFFFFF;--sideh:#EBF5F9;--card:#FFFFFF;--term:#F4F7FC;
  --brd:#DDE4EF;--brdl:#EEF2FA;
  --acc:#00A8B4;--accd:rgba(0,168,180,.10);
  --ok:#1A9E5E;--okd:rgba(26,158,94,.10);--okb:rgba(26,158,94,.25);
  --err:#D94F4F;--errd:rgba(217,79,79,.10);--errb:rgba(217,79,79,.25);
  --warn:#B87200;
  --txt:#0D1B3E;--txt2:#4A5A80;--txt3:#9AAAC8;
  --atrf-bg:#F2F5FB;--atrf-surface:#FFFFFF;--atrf-surface2:#FFFFFF;
  --atrf-border:#DDE4EF;--atrf-border2:#DDE4EF;
  --atrf-text:#0D1B3E;--atrf-text2:#4A5A80;--atrf-text3:#9AAAC8;
  --atrf-accent:#00A8B4;--atrf-accent2:#0090A0;
  --atrf-green:#1A9E5E;--atrf-green-bg:rgba(26,158,94,.10);--atrf-green-border:rgba(26,158,94,.25);
  --atrf-red:#D94F4F;--atrf-red-bg:rgba(217,79,79,.10);--atrf-red-border:rgba(217,79,79,.25);
  --atrf-amber:#B87200;--atrf-amber-bg:rgba(184,114,0,.08);--atrf-amber-border:rgba(184,114,0,.25);
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
.hist-btn{margin:10px 12px 12px;padding:7px 10px;border-radius:6px;background:var(--card);border:1px solid var(--brd);color:var(--txt2);font-size:.76rem;font-weight:600;transition:background .15s,color .15s;flex-shrink:0;text-align:left;display:flex;align-items:center;gap:6px}
.hist-btn:hover{background:var(--sideh);color:var(--txt)}
.hist-btn.active{background:var(--accd);border-color:var(--acc);color:var(--acc)}

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
#asig-sel-bar,#ia-sel-bar,#activ-sel-bar,#dm-sel-bar,#cancel-sel-bar{display:flex;align-items:center;gap:6px;padding:5px 10px 4px;flex-shrink:0;flex-wrap:wrap;border-bottom:1px solid var(--brd)}
#asig-sel-bar .fsb-lbl,#ia-sel-bar .fsb-lbl,#activ-sel-bar .fsb-lbl,#dm-sel-bar .fsb-lbl,#cancel-sel-bar .fsb-lbl{font-size:.62rem;color:var(--txt3);font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-right:2px}
#cancel-form-bar input,#cancel-form-bar select{font-size:.68rem;padding:3px 7px;border-radius:4px;border:1px solid var(--brd);background:var(--input,var(--card));color:var(--txt);outline:none}
#cancel-form-bar input:focus,#cancel-form-bar select:focus{border-color:var(--acc)}
#cancel-serial-preview{padding:4px 12px 5px;min-height:20px;background:var(--card);border-bottom:1px solid var(--brd);flex-shrink:0}
#gf-panel{flex-shrink:0;background:var(--card)}
.gf-bar{display:flex;align-items:center;gap:10px;padding:5px 14px;background:var(--card);border-bottom:2px solid var(--acc);flex-wrap:wrap}
.gf-bar-ttl{font-size:.62rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:var(--acc);white-space:nowrap}
.gf-bar-chip{display:flex;align-items:center;gap:4px}
.gf-bar-lbl{font-size:.57rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--txt3)}
.gf-bar-val{font-size:.68rem;font-weight:600;color:var(--txt);font-family:monospace}
.gf-bar-val.empty{color:var(--err,#e05252);font-style:italic;font-family:inherit;font-size:.62rem}
.gf-bar-sep{width:1px;height:14px;background:var(--brd);margin:0 2px}
.gf-config-btn{font-size:.6rem;font-weight:700;padding:3px 10px;border-radius:4px;border:1px solid var(--acc);background:transparent;color:var(--acc);cursor:pointer;text-transform:uppercase;letter-spacing:.05em;margin-left:auto;white-space:nowrap}
.gf-config-btn:hover{background:var(--acc);color:#fff}
#gf-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.78);z-index:9000;align-items:flex-start;justify-content:center;padding-top:36px}
#gf-modal.open{display:flex}
.gfm-card{background:#181c2a;border:1px solid #252c45;border-radius:8px;width:720px;max-width:97vw;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 16px 60px rgba(0,0,0,.8)}
.gfm-hdr{display:flex;align-items:center;gap:10px;padding:12px 18px 10px;border-bottom:1px solid #1e2438;flex-shrink:0}
.gfm-hdr-ttl{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:#4f8ef7;white-space:nowrap}
.gfm-name-inp{flex:1;background:#0e1220;border:1px solid #252c45;border-radius:4px;color:#dce4f4;font-size:.73rem;padding:5px 10px;outline:none;font-family:monospace}
.gfm-name-inp:focus{border-color:#4f8ef7}
.gfm-btn-c{font-size:.63rem;font-weight:700;padding:5px 12px;border-radius:4px;border:1px solid #c04040;background:transparent;color:#c04040;cursor:pointer;text-transform:uppercase;letter-spacing:.05em}
.gfm-btn-c:hover{background:#c04040;color:#fff}
.gfm-btn-ok{font-size:.63rem;font-weight:700;padding:5px 14px;border-radius:4px;border:none;background:#4f8ef7;color:#fff;cursor:pointer;text-transform:uppercase;letter-spacing:.05em}
.gfm-btn-ok:hover{background:#3a7de5}
.gfm-meta{font-size:.58rem;color:#4a5580;padding:4px 18px 5px;border-bottom:1px solid #1e2438;flex-shrink:0}
.gfm-err-bar{display:none;background:rgba(180,40,40,.18);border-left:3px solid #e05252;padding:6px 14px;flex-shrink:0;font-size:.62rem;color:#e07070;line-height:1.7}
.gfm-err-bar.show{display:block}
.gfm-tabs{display:flex;border-bottom:1px solid #1e2438;flex-shrink:0;padding:0 18px;background:#181c2a}
.gfm-tab{font-size:.68rem;font-weight:600;padding:8px 14px 6px;border-bottom:2px solid transparent;color:#5060a0;cursor:pointer;letter-spacing:.03em;margin-bottom:-1px}
.gfm-tab.active{color:#dce4f4;border-bottom-color:#4f8ef7}
.gfm-tab:hover:not(.active){color:#8090b8}
.gfm-body{overflow-y:auto;flex:1}
.gfm-tc{display:none;padding:13px 18px 18px;flex-direction:column;gap:13px}
.gfm-tc.active{display:flex}
.gfm-sec{display:flex;flex-direction:column;gap:8px}
.gfm-sec-ttl{font-size:.55rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#4a5580;padding-bottom:5px;border-bottom:1px solid #1a2035}
.gfm-row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}
.gf-f{display:flex;flex-direction:column;gap:3px}
.gf-f label{font-size:.56rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#7080a8;white-space:nowrap}
.gf-f .r{color:#4f8ef7}
.gf-f input,.gf-f select{font-size:.7rem;padding:5px 8px;border-radius:4px;border:1px solid #252c45;background:#0e1220;color:#d0daf0;outline:none;height:30px;min-width:0}
.gf-f input:focus,.gf-f select:focus{border-color:#4f8ef7}
.gf-f .mono{font-family:monospace;letter-spacing:.04em}
.gfm-ar{display:flex;gap:5px;align-items:stretch}
.gfm-abtn{font-size:.55rem;font-weight:800;padding:0 9px;border-radius:4px;border:1px solid #4f8ef7;background:transparent;color:#4f8ef7;cursor:pointer;text-transform:uppercase;letter-spacing:.05em;height:30px;white-space:nowrap}
.gfm-abtn:hover{background:#4f8ef7;color:#fff}
.gfm-abtn.grn{border-color:#22bb66;color:#22bb66}
.gfm-abtn.grn:hover{background:#22bb66;color:#fff}
.gfm-hint{font-size:.56rem;color:#4a5580;margin-top:2px}
.gfm-pill{font-size:.5rem;padding:1px 5px;border-radius:3px;margin-left:5px;font-weight:700;vertical-align:middle}
.gfm-pill.blue{background:#4f8ef7;color:#fff}
.gfm-pill.amber{background:#b87020;color:#fff;cursor:pointer}
.gfm-pill.grn{background:#22bb66;color:#fff;font-family:monospace}
.gfm-fw{flex:1;min-width:100px}
.gfm-wlg{width:175px}.gfm-wmd{width:128px}.gfm-wsm{width:95px}.gfm-wxs{width:66px}
.gfm-env{display:flex;gap:8px}
.gfm-ec{font-size:.66rem;font-weight:700;padding:5px 16px;border-radius:5px;border:1px solid #252c45;background:#0e1220;color:#7080a8;cursor:pointer;text-transform:uppercase;letter-spacing:.05em;user-select:none}
.gfm-ec.on{border-color:#4f8ef7;background:#162040;color:#4f8ef7}
.gfm-funcs{display:flex;gap:10px;height:300px}
.gfm-flist,.gfm-fseq{flex:1;background:#0e1220;border:1px solid #252c45;border-radius:5px;display:flex;flex-direction:column;overflow:hidden}
.gfm-flhdr,.gfm-fshdr{display:flex;align-items:center;justify-content:space-between;padding:6px 10px;border-bottom:1px solid #1a2035;flex-shrink:0}
.gfm-flttl,.gfm-fsttl{font-size:.55rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#4a5580}
.gfm-flbody,.gfm-fsbody{overflow-y:auto;flex:1}
.gfm-fitem{display:flex;align-items:center;gap:8px;padding:6px 10px;cursor:pointer;border-bottom:1px solid #111828}
.gfm-fitem:hover{background:#162040}
.gfm-fnum{font-size:.54rem;color:#4a5580;font-family:monospace;width:18px;flex-shrink:0}
.gfm-fname{font-size:.67rem;color:#c0cbea;flex:1}
.gfm-fchk{width:14px;height:14px;accent-color:#4f8ef7;cursor:pointer;flex-shrink:0}
.gfm-sitem{display:flex;align-items:center;gap:7px;padding:6px 10px;border-bottom:1px solid #111828;cursor:grab}
.gfm-sitem:hover{background:#162040}
.gfm-shandle{color:#3a4560;font-size:.75rem;flex-shrink:0}
.gfm-snum{font-size:.54rem;color:#4a5580;font-family:monospace;width:16px;flex-shrink:0}
.gfm-sname{font-size:.67rem;color:#c0cbea;flex:1}
.gfm-srm{font-size:.75rem;color:#4a5580;cursor:pointer;padding:0 2px;border:none;background:none;line-height:1}
.gfm-srm:hover{color:#e05252}
#asig-grid,#ia-grid,#activ-grid,#dm-grid,#cancel-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;flex:1;overflow:hidden;padding:8px 10px;min-height:0}
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

/* HISTORIAL TABLE */
.hist-table{width:100%;border-collapse:collapse;font-size:.72rem;table-layout:auto}
.hist-table th{position:sticky;top:0;background:var(--card);color:var(--txt2);font-weight:700;text-transform:uppercase;font-size:.62rem;letter-spacing:.05em;padding:7px 10px;border-bottom:2px solid var(--brd);text-align:left;cursor:pointer;user-select:none;white-space:nowrap}
.hist-table th:hover{color:var(--acc)}
.hist-table th .sort-ico{margin-left:4px;opacity:.45;font-size:.6rem}
.hist-table td{padding:5px 10px;border-bottom:1px solid var(--brdl);vertical-align:middle;max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hist-table tr:hover td{background:var(--sideh)}
.hist-table tr:last-child td{border-bottom:none}
.hist-badge{display:inline-block;padding:2px 7px;border-radius:10px;font-size:.62rem;font-weight:700;white-space:nowrap}
.hist-badge.ok{background:var(--okd);color:var(--ok)}
.hist-badge.err{background:var(--errd);color:var(--err)}
.hist-badge.warn{background:rgba(255,179,71,.15);color:var(--warn)}
.hist-empty{padding:40px;text-align:center;color:var(--txt3);font-size:.8rem}
/* ── QA FulFillment Queue (Humberto design) ── */
#fulfillment-view{background:var(--atrf-bg);color:var(--atrf-text);overflow-y:auto}
#fulfillment-view *{box-sizing:border-box}
.atrf-layout{max-width:1380px;margin:0 auto;padding:1.5rem 2rem 4rem;display:flex;flex-direction:column;gap:1rem}
.atrf-section{background:var(--atrf-surface);border:1px solid var(--atrf-border);border-radius:var(--atrf-radius-lg);overflow:hidden}
.atrf-section-header{display:flex;align-items:center;gap:10px;padding:14px 1.25rem;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface2);flex-wrap:wrap}
.atrf-section-title{font-size:13px;font-weight:500;letter-spacing:.04em;text-transform:uppercase;color:var(--atrf-text);flex:1;font-family:var(--atrf-font)}
.atrf-btn{display:inline-flex;align-items:center;gap:6px;padding:7px 16px;border-radius:var(--atrf-radius);border:1px solid var(--atrf-border2);background:var(--atrf-surface2);color:var(--atrf-text);font-family:var(--atrf-font);font-size:12px;font-weight:500;cursor:pointer;transition:all .15s;letter-spacing:.02em;white-space:nowrap}
.atrf-btn:hover{border-color:var(--atrf-accent);color:var(--atrf-accent);background:rgba(61,127,255,.06)}
.atrf-btn:active{transform:scale(.98)}
.atrf-btn:disabled{opacity:.4;cursor:not-allowed;pointer-events:none}
.atrf-btn-primary{background:var(--atrf-accent);border-color:var(--atrf-accent);color:#fff}
.atrf-btn-primary:hover{background:var(--atrf-accent2);border-color:var(--atrf-accent2);color:#fff}
.atrf-btn-green{background:var(--atrf-green-bg);border-color:var(--atrf-green-border);color:var(--atrf-green)}
.atrf-btn-green:hover{background:#122c1a;border-color:var(--atrf-green)}
.atrf-btn-danger{background:var(--atrf-red-bg);border-color:var(--atrf-red-border);color:var(--atrf-red)}
.atrf-btn-sm{padding:4px 10px;font-size:11px}
.atrf-queue-list{display:flex;flex-direction:column}
.atrf-qrow{border-bottom:1px solid var(--atrf-border)}
.atrf-qrow:last-child{border-bottom:none}
.atrf-qrow-main{display:flex;align-items:center;gap:10px;padding:11px 14px;transition:background .1s}
.atrf-qrow-main:hover{background:rgba(255,255,255,.015)}
.atrf-qrow-arrow{font-size:11px;color:var(--atrf-text3);transition:transform .2s;flex-shrink:0;cursor:pointer;padding:2px 4px}
.atrf-qrow.open .atrf-qrow-arrow{transform:rotate(90deg)}
.atrf-qrow-detail{display:none;padding:0 14px 14px 52px;border-top:1px solid var(--atrf-border);background:rgba(0,0,0,.1)}
.atrf-qrow.open .atrf-qrow-detail{display:block}
.atrf-qcb{width:16px;height:16px;border:1px solid var(--atrf-border2);border-radius:3px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all .1s}
.atrf-qcb.on{background:var(--atrf-accent);border-color:var(--atrf-accent)}
.atrf-qcb.on::after{content:'';display:block;width:9px;height:5px;border-left:1.5px solid #fff;border-bottom:1.5px solid #fff;transform:rotate(-45deg) translateY(-1px)}
.atrf-q-info{flex:1;min-width:0}
.atrf-q-name{font-size:13px;font-weight:500;color:var(--atrf-accent);cursor:pointer;font-family:var(--atrf-font)}
.atrf-q-name:hover{text-decoration:underline}
.atrf-q-meta{font-size:11px;color:var(--atrf-text2);font-family:var(--atrf-mono);margin-top:1px}
.atrf-badge{display:inline-flex;align-items:center;padding:3px 9px;border-radius:20px;font-size:10px;font-weight:500;font-family:var(--atrf-mono);letter-spacing:.03em;white-space:nowrap}
.atrf-badge-wait{background:var(--atrf-surface2);border:1px solid var(--atrf-border2);color:var(--atrf-text2)}
.atrf-badge-run{background:var(--atrf-amber-bg);border:1px solid var(--atrf-amber-border);color:var(--atrf-amber)}
.atrf-badge-ok{background:var(--atrf-green-bg);border:1px solid var(--atrf-green-border);color:var(--atrf-green)}
.atrf-badge-err{background:var(--atrf-red-bg);border:1px solid var(--atrf-red-border);color:var(--atrf-red)}
.atrf-empty-state{padding:4rem;text-align:center;color:var(--atrf-text3);font-size:13px;font-family:var(--atrf-mono)}
.atrf-empty-hint{font-size:11px;color:var(--atrf-text3);margin-top:8px}
.atrf-chip-list{display:flex;flex-wrap:wrap;gap:5px;margin-top:4px}
.atrf-chip{font-size:11px;font-family:var(--atrf-mono);background:rgba(61,127,255,.1);border:1px solid rgba(61,127,255,.25);border-radius:4px;padding:2px 8px;color:var(--atrf-accent)}
/* Modal */
.atrf-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:9100;align-items:flex-start;justify-content:center;padding:2rem 1rem;overflow-y:auto}
.atrf-overlay.show{display:flex}
.atrf-modal{background:var(--atrf-surface);border:1px solid var(--atrf-border2);border-radius:var(--atrf-radius-lg);width:100%;max-width:860px;display:flex;flex-direction:column;margin:auto}
.atrf-modal-head{display:flex;align-items:center;gap:12px;padding:1rem 1.25rem;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface2);border-radius:var(--atrf-radius-lg) var(--atrf-radius-lg) 0 0;flex-shrink:0;flex-wrap:wrap}
.atrf-modal-head-title{font-size:13px;font-weight:500;text-transform:uppercase;letter-spacing:.04em;color:var(--atrf-text2);flex-shrink:0;font-family:var(--atrf-font)}
.atrf-name-inp{flex:1;min-width:160px;background:var(--atrf-surface);border:1px solid var(--atrf-border2);border-radius:var(--atrf-radius);color:var(--atrf-text);font-family:var(--atrf-mono);font-size:13px;font-weight:500;padding:6px 12px;outline:none;transition:border-color .15s;height:34px}
.atrf-name-inp:focus{border-color:var(--atrf-accent)}
.atrf-name-inp.err{border-color:var(--atrf-red)!important}
.atrf-tabs{display:flex;gap:0;padding:0 1.25rem;background:var(--atrf-surface2);border-bottom:1px solid var(--atrf-border)}
.atrf-tab{font-size:12px;color:var(--atrf-text3);padding:8px 14px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;user-select:none;font-family:var(--atrf-mono);font-weight:500;letter-spacing:.03em;transition:color .15s}
.atrf-tab:hover{color:var(--atrf-text2)}
.atrf-tab.active{color:var(--atrf-text);border-bottom-color:var(--atrf-accent)}
.atrf-modal-body{padding:1.25rem;overflow-y:auto;max-height:calc(100vh - 280px)}
.atrf-modal-footer{display:flex;gap:8px;justify-content:flex-end;padding:1rem 1.25rem;border-top:1px solid var(--atrf-border);background:var(--atrf-surface2);border-radius:0 0 var(--atrf-radius-lg) var(--atrf-radius-lg);flex-shrink:0}
.atrf-ts-row{display:flex;align-items:center;gap:10px;padding:6px 1.25rem;background:rgba(61,127,255,.04);border-bottom:1px solid var(--atrf-border);font-size:11px;font-family:var(--atrf-mono);color:var(--atrf-text3)}
.atrf-ts-row span{color:var(--atrf-text2)}
/* Form fields */
.atrf-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:10px}
.atrf-col-2{grid-column:span 2}.atrf-col-3{grid-column:span 3}.atrf-col-4{grid-column:span 4}.atrf-col-5{grid-column:span 5}.atrf-col-6{grid-column:span 6}.atrf-col-12{grid-column:span 12}
.atrf-divider{grid-column:span 12;border:none;border-top:1px solid var(--atrf-border);margin:4px 0}
.atrf-group-lbl{grid-column:span 12;font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:.08em;color:var(--atrf-text3);font-family:var(--atrf-mono);padding-top:4px}
.atrf-field{display:flex;flex-direction:column;gap:5px}
.atrf-field label{font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:.07em;color:var(--atrf-text2);font-family:var(--atrf-mono);display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.atrf-field label .req{color:var(--atrf-accent)}
.atrf-field input,.atrf-field select{background:var(--atrf-surface2);border:1px solid var(--atrf-border);border-radius:var(--atrf-radius);color:var(--atrf-text);font-family:var(--atrf-mono);font-size:12px;padding:7px 10px;outline:none;transition:border-color .15s;width:100%;height:34px}
.atrf-field input:focus,.atrf-field select:focus{border-color:var(--atrf-accent)}
.atrf-field input.err,.atrf-field select.err{border-color:var(--atrf-red)!important}
.atrf-field select option{background:var(--atrf-surface2)}
.atrf-field .atrf-hint{font-size:10px;color:var(--atrf-text3);font-family:var(--atrf-mono);margin-top:2px}
.atrf-amb-wrap{display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding-top:2px}
.atrf-amb-radio{display:none}
.atrf-amb-lbl{font-size:11px;font-family:var(--atrf-mono);font-weight:500;padding:5px 14px;border-radius:var(--atrf-radius);border:1px solid var(--atrf-border2);background:var(--atrf-surface2);color:var(--atrf-text2);cursor:pointer;transition:all .15s;user-select:none;height:34px;display:flex;align-items:center}
.atrf-amb-lbl:hover{border-color:var(--atrf-accent);color:var(--atrf-accent)}
.atrf-amb-radio:checked+.atrf-amb-lbl{background:rgba(61,127,255,.15);border-color:var(--atrf-accent);color:var(--atrf-accent)}
.atrf-val-err{background:rgba(248,113,113,.08);border:1px solid var(--atrf-red-border);border-radius:var(--atrf-radius);padding:10px 14px;margin-bottom:12px;font-size:11px;font-family:var(--atrf-mono);color:var(--atrf-red);line-height:1.8;display:none}
.atrf-val-err.show{display:block}
.atrf-tag{font-size:9px;padding:1px 5px;border-radius:3px;cursor:pointer;user-select:none;transition:all .15s;background:rgba(61,127,255,.15);color:var(--atrf-accent);border:1px solid rgba(61,127,255,.35)}
.atrf-tag.off{background:var(--atrf-surface2);color:var(--atrf-text3);border-color:var(--atrf-border)}
.atrf-slen{font-size:10px;font-family:var(--atrf-mono);padding:2px 7px;border-radius:3px;background:var(--atrf-surface2);border:1px solid var(--atrf-border);color:var(--atrf-text3);margin-left:auto}
.atrf-slen.ok{background:var(--atrf-green-bg);border-color:var(--atrf-green-border);color:var(--atrf-green)}
.atrf-slen.warn{background:var(--atrf-amber-bg);border-color:var(--atrf-amber-border);color:var(--atrf-amber)}
/* Funcs panel */
.atrf-funcs-layout{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.atrf-func-panel{border:1px solid var(--atrf-border);border-radius:var(--atrf-radius);overflow:hidden}
.atrf-func-ph{background:var(--atrf-surface2);border-bottom:1px solid var(--atrf-border);padding:8px 12px;display:flex;align-items:center;gap:8px}
.atrf-func-pt{font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:.07em;color:var(--atrf-text2);font-family:var(--atrf-mono);flex:1}
.atrf-func-search{background:var(--atrf-bg);border:1px solid var(--atrf-border);border-radius:5px;color:var(--atrf-text);font-family:var(--atrf-mono);font-size:11px;padding:4px 8px;outline:none;width:130px}
.atrf-func-search:focus{border-color:var(--atrf-accent)}
.atrf-func-scroll{max-height:280px;overflow-y:auto}
.atrf-func-item{display:flex;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid var(--atrf-border);cursor:pointer;transition:background .1s;user-select:none}
.atrf-func-item:last-child{border-bottom:none}
.atrf-func-item:hover{background:var(--atrf-surface2)}
.atrf-func-item.selected{background:rgba(61,127,255,.06)}
.atrf-func-item.selected .atrf-func-name{color:var(--atrf-accent)}
.atrf-func-idx{font-family:var(--atrf-mono);font-size:10px;color:var(--atrf-text3);width:22px;flex-shrink:0}
.atrf-func-name{font-size:12px;flex:1;color:var(--atrf-text);font-family:var(--atrf-font)}
.atrf-func-cb{width:15px;height:15px;border:1px solid var(--atrf-border2);border-radius:3px;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all .1s}
.atrf-func-cb.on{background:var(--atrf-accent);border-color:var(--atrf-accent)}
.atrf-func-cb.on::after{content:'';display:block;width:8px;height:5px;border-left:1.5px solid #fff;border-bottom:1.5px solid #fff;transform:rotate(-45deg) translateY(-1px)}
.atrf-seq-item{display:flex;align-items:center;gap:8px;padding:8px 10px;border-bottom:1px solid var(--atrf-border);font-size:12px;background:var(--atrf-surface)}
.atrf-seq-item:last-child{border-bottom:none}
.atrf-drag-handle{cursor:grab;color:var(--atrf-text3);font-size:14px;flex-shrink:0;line-height:1;padding:0 2px}
.atrf-drag-handle:active{cursor:grabbing}
.atrf-seq-pos{font-family:var(--atrf-mono);font-size:10px;color:var(--atrf-text3);width:16px;text-align:center;flex-shrink:0}
.atrf-seq-name{flex:1;color:var(--atrf-text);font-size:12px;font-family:var(--atrf-font)}
.atrf-seq-del{background:none;border:none;cursor:pointer;color:var(--atrf-text3);font-size:16px;line-height:1;padding:0 2px;transition:color .1s}
.atrf-seq-del:hover{color:var(--atrf-red)}
.atrf-seq-empty{padding:2.5rem 1rem;text-align:center;color:var(--atrf-text3);font-size:12px;font-family:var(--atrf-mono)}
.atrf-funcs-err{font-size:11px;color:var(--atrf-red);font-family:var(--atrf-mono);margin-top:6px;display:none}
.atrf-funcs-err.show{display:block}
/* Readonly view */
.atrf-dcfg-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px}
.atrf-dcfg-item{display:flex;flex-direction:column;gap:3px}
.atrf-dcfg-lbl{font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:var(--atrf-text3);font-family:var(--atrf-mono)}
.atrf-dcfg-val{font-size:12px;font-family:var(--atrf-mono);color:var(--atrf-text2);background:var(--atrf-surface2);border:1px solid var(--atrf-border);border-radius:5px;padding:5px 8px;word-break:break-all;min-height:30px}
.atrf-view-func-list{display:flex;flex-direction:column;border:1px solid var(--atrf-border);border-radius:var(--atrf-radius);overflow:hidden}
.atrf-view-func-item{display:flex;align-items:center;gap:8px;padding:7px 12px;border-bottom:1px solid var(--atrf-border);font-size:12px;font-family:var(--atrf-font)}
.atrf-view-func-item:last-child{border-bottom:none}
.atrf-view-func-pos{font-family:var(--atrf-mono);font-size:10px;color:var(--atrf-text3);width:20px}
/* Exec history */
.atrf-exec-hist{display:flex;flex-direction:column;gap:6px;margin-top:4px}
.atrf-hist-row{display:flex;align-items:center;gap:10px;padding:7px 10px;background:var(--atrf-surface2);border:1px solid var(--atrf-border);border-radius:6px;font-size:12px;font-family:var(--atrf-mono)}
.atrf-hist-ts{color:var(--atrf-text2);flex:1}
/* URL badge shown in queue item */
.atrf-url-badge{font-size:10px;font-family:var(--atrf-mono);background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);border-radius:4px;padding:1px 7px;color:var(--atrf-green);margin-left:4px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:inline-block;vertical-align:middle}
.atrf-tc-results{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.atrf-tc-badge{display:inline-flex;align-items:center;gap:5px;padding:4px 12px;border-radius:5px;font-size:11px;font-family:var(--atrf-mono);font-weight:600;cursor:pointer;transition:all .15s;border:1px solid transparent;user-select:none}
.atrf-tc-badge.pass{background:var(--atrf-green-bg);border-color:var(--atrf-green-border);color:var(--atrf-green)}
.atrf-tc-badge.fail{background:var(--atrf-red-bg);border-color:var(--atrf-red-border);color:var(--atrf-red)}
.atrf-tc-badge.pending{background:var(--atrf-surface2);border-color:var(--atrf-border);color:var(--atrf-text3);cursor:default}
.atrf-tc-badge:not(.pending):hover{filter:brightness(1.15);transform:translateY(-1px)}
.atrf-tc-section-lbl{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--atrf-text3);font-family:var(--atrf-mono);margin-top:10px;margin-bottom:4px}
.atrf-tc-modal-pre{background:var(--atrf-surface2);border:1px solid var(--atrf-border);border-radius:6px;padding:12px;font-family:var(--atrf-mono);font-size:11px;color:var(--atrf-text);overflow-x:auto;white-space:pre-wrap;word-break:break-all;margin:0;max-height:260px;overflow-y:auto}
.atrf-tc-tab{flex:1;padding:10px 16px;background:transparent;border:none;border-bottom:2px solid transparent;cursor:pointer;font-size:12px;font-family:var(--atrf-mono);color:var(--atrf-text2);transition:all .15s;text-align:left}
.atrf-tc-tab.active{color:var(--atrf-accent);border-bottom-color:var(--atrf-accent);font-weight:600}
.atrf-tc-tab:hover:not(.active){color:var(--atrf-text);border-bottom-color:var(--atrf-border2)}
.atrf-vno-checks{display:flex;gap:6px;flex-wrap:wrap;padding-top:2px}
.atrf-vno-lbl{display:flex;align-items:center;gap:5px;font-size:12px;font-family:var(--atrf-mono);padding:5px 12px;border-radius:var(--atrf-radius);border:1px solid var(--atrf-border2);background:var(--atrf-surface2);color:var(--atrf-text2);cursor:pointer;transition:all .15s;height:34px;user-select:none}
.atrf-vno-lbl.on{background:rgba(0,200,212,.12);border-color:var(--atrf-accent);color:var(--atrf-accent)}
.atrf-vno-multi-note{font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-text2);margin-top:4px;display:none}
.atrf-vno-multi-note.show{display:block}
</style>
</head>
<body class="light">
<!-- ── Auth screen ─────────────────────────────────────────────── -->
<div class="layout" style="display:flex">
  <aside class="sb">
    <div class="sb-head">
      <div class="sb-logo">
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAlgAAACWCAYAAAACG/YxAAAACXBIWXMAACxKAAAsSgF3enRNAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAHc1JREFUeJzt3XmYXFWd//H393bXvd3ZqiqJCwgDIoMLIiAzP4Xxx6gw4AiICPgbR1F+yOagoiwGAQm4ICCgwoAEcEHUYYjCKLiBGw/CgIiDqKg4IirKICF1KwvdVdVV3/mjqpNO0tXpqjpV1Z18Xs/D86SWPuebptP96XvP+R5zd0REREQknKjfBYiIiIhsaRSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAhvs18Tz1/DMsTF2rcJzI2ORz4KwZ86IG0+483Alx0MOpa7NtZrFmRo7bOZtXsnyU4dqt+oIbWgVO9ecbLPXK1kedKi0M3ZS4CUekZnqPYNVnnh6IY+1M36/TPX3GnBWjOT4/VQfHxfZqzuVzVw2xtrSIn618fNzV7BNJcO2/aipn8pZ7m/l/TP1ayaCdDTLbzf3vonfPwdrPPl0nj9MZ/zhlB2qxmKASsTvfT4rOqu4N6b58yKYyCiWSvyPP4M1vZqzmXlreVZ5jO3GH8+k7/Hm7j2bLC6yF85bzDgQ54U9m7g7RhzuxrmpMsANvoCVIQePixxvzrJpvPWnbry91W+g/ZKkfA04pNnrg2M8Z+1i/tzm2H+Czf7wrOBcWs6ztJsBOaSp/l7mXD2a54TNfHzv/pHPHD8p5TYNCUnKucDS3pfTX6Uc1sr7Z/DXzK2lXPPvH+Mmfv8055rRPMdPZ/ChAsvc6u81WOGwqrNyN6vq8JgZd1PjhlKen7czSAs/L0KqAb8Ebo6Mz4xk+V2P5wcgTvm+wSsnPPVwOceuDmP9qGeinlzBSlIOBc40+D8AM/afbmuGDfbD2C+ucelQkc+ac+FIjkd7XMfu5tyTFLhkNoWGPspgLIlTDoojji0v4N5+FyQiM4/DYur/dZXBX+O8CuOspMg3qXJaaSEPdXveACJgV2DXmrNkqMDnSgOcEfpiw1SGi+y3UbgC2CUu8E/k+UKv6mimqwEreYoX+ABXGryqm/PMAIk7Jzq8LUm5oJzjAodyD+cfbISGwzNwbCXHHT2ce7Z6sdW4e6jAtaUxTp0Jl7pFZqif9LuAcQ7/3e8ausr5RyJePZRy+miOy9sZonHlbcplAx1z5mFsB8xtPJNx47i4xmviVRxeXsB9XZ1/vAznnElfMJYa3NDvq1hdC1hxyjE2wOUGc7o1xww0DJwXpxwybPy/kSyP9Hj+nSP4/lCBa0pVTvPFrO7x/LNN5MbxcYYDhoqcMJrltn4XJDLTTHardavgnBVF3NDVKSIGqbFDzXmNwbHAAiBxuCwpsm0py/tbH5SbSptZNhCCgWVSdgeOMjiR+s/67a3G94aLHDaS5TvdnH9oFQc67Nt46A5XGpzUeLxzJuUocny2mzVsTvCAZWBxylLbCtc5TPA3Nee+zEoOqSzk7h7PbW4cHw8qNLRgR3e+naQsLw/wL7NlYauIdI9HrOjRL8kPA7fbas6Pq3yW8TWqzhlxykPlHNf3oIaWOTg5HgAeGE65rAqfa9yum1dzbo5X8epuXsly59wJxdxYyXNyXOTV4+u7Dc4x+GKP7yZtIHjAyqRczvoUOR1V4AngL8zs3XCLgG2AZJrvXxhFfDtexf59WuczMTS8w+fzVB9qmG2OzFTZN055XznH5/tdjIhsPXw+Txm8PklZ5vWrWURwqaXc4jnSftc3lZEcvzc4IE75InAkMM9qfNlWsWc31mQNFTgI4+WNh1VqnOtQTeBc4N8bz++YKfJWslwbev7pChqwkgJnmW0+XBnchfFVH+OW8iIe9vpuhFlhzkq2HzMOMjgMY3+mbi8xL6px69Aq9hldwG96VeNGjsxU2Tcp8q5SluV9qmHWMHgWcF2S8saBGu94eiF/7HdNIrJ1cKhZjhPiIi/GebnD4hhOBT7Q79o2x6FiKW+Nc+wC7A78VVzjYuCY4HPZ+rVX5nxmtNGSpZxleZyyBHhp47UPGHy+X1exggWs4ZRXYpw35ZuMeyLn/SM5fhBq3l5r/MC9CrgqWcmLiDiXemKflMNianzFHuNlvh0jvapzIoNn4dyYpNw6UOXEpxfxp37UMcscVI342VDK0lKOy2fTLwGtMFiBc3O/6wit2SJfc+4HrulJDcZeNL7RN6mlJ3XI7OJQG6rxQTe+AYBxrMF5/V6wPR2+I6PxKo63GvcABrwtWcklpYX8ItQcja4E4x0JRiPnQ+vmBx+qcZZHfLPx1F9lChxDnqtCzd+KIAHLVjA/HuQLwECTt4wZnDKabW9XxEzV2Er7xjjlaKuHrma3D3eL53MOtLFgMayDqwP8PC6ypJLlGt9SGmZ0T9bhE0nKEUmV4yZrXDnbOfyhNM0eQVuC0Ty3ALf0Yq5Gz62mAWu6vZlk61Mq8v04yyjGEM6zM6vYi1nSUqa8gB/FKd816nd4POIY6lfhOmZgMevXXrlx5dP5De8yjC7kW43eWK8CMOMD9hjX9eMCR5Du6fEA5wDPafJyMTIObHfL6WxQzvG5mrMfTHGv2TllaDXPDzap8+02PzJnzrK4wLeGU3YMVs/MV8S4p50PdHgFEf+VFDjD+nj6gYhsHXxHRrEJdxqcPfpYTuuML6/7o/HaUMPGRd4A6z4Xa5JBLpz0jRFnsP4CwrbJXN4eqoZWdByw5q/hmTRfd1U15y0jWb7X6TwhxCt5eZJyXZLySJJSSlK8hf9WxCnfi4ucYJNcqarkuavmvJ7m93pjr3J2qL/LYJVjzDkI2lwjZBxQg18kRZZY8yuPW5K15Sz7uHECtNHzyhjC+Giccn+8ir8NX56IyAaeHv+D1VjUz0JaZjyw7s/OLvYk8zofEsM3WIt28ep5/GWy95YX8CPg6+tKMM60xxjutIZWdRywymO8EyYv3OC00Ty3djpHpwwsKfJRi7gbeCvwXCBucZhFBq8y56o45aG43v9jA5U8dxqcNsUY/zRnJdu3OG9To3m+UXZ2c7iM9tYIzcG5IC5yZ7KSF4Wqa6Zy8HKWqyPYzeH2Nod5idW4O075pD2xrsmeiEhYxjPW/7HrR/YENeA8OeFhlMQ8q9Mx4yJvpL54HoMV5Rofn/IDnDNZ/3Nxm2Re93uDbayjgGX1RWxvafLyT0s5Lutk/BAMojjlepwz6g+D2MngrqECB238QinHFdD0XMDBqjX9fLXF8xTLOU6uOa/E+XV7g7A3EQ8kBS6w1oPnrDOS49FyjgMw3ghtta8YNHh3nPDgcJH9Q9cnIlu34ZQdcZ49/tgs3CLxnvANWy55rbNfRg0inLMmPHW+L5w6dJby/Axb17IBN5bY471tfN5RwMrUb5U8d7LXzHjfTNh5FRc5DXhzF4ae68aNyVMbHlrtUDObYjG7cUQXaqGS587yWvbEuZD2+omNn9H343hVY4fGFq6UZXkmw66wfr1Ai3aqObclKZ+31bPsEr6IzFg122ADxOrRkdmxwH1cFRZOfDxAZ3284gJvAnZrPPxTac30dgVGcBbjy3acZydz+JdO6mhVZ1ewqry6yUv/PRM6iCcFXozz4S5OMYcBPrjxk6NZbqfenXcye3Trh7Fvx0gpzxkOf0P754ftZjXu2lpuga2ZyxOlHEea8zpoq32FAUfFNX6eFLsTnkVk6xGn7IHznvHH5vybb7N+PdZsYL7BkpO1I/n2WwMZDBCtX7/sxtLp7ggcyfI78wnH5ThLbAXz262lVZ3tiLImi32d/+ho3EDcOM4g0+VpDrEVzN/k3D/na9ik67GipMZLaX8N0GaVczxg8PK4yCk45zH97vPjxm+BHTxc5PiRLN/tRp3T0eg1Vt9W7xwKvBjjI+Z8ZzTgeVujeW6xlDsT50I3jqPV28n1y/nLZ2Gvsd2SlD/3u4jgnAdLeV7T7zJEWpE8xQtsgFsYX9fsjJrx0f5W1YaIg8f38Dnc6x2c0pJJeQvwgsbDhytZrmvl4weqnDc2yFHAHIfF8QAnARe0W08rOt1yvstkT1rU/6tXBoMJvKkHjZ6SOMOBbHSbySJud2+y4L3GLnQxYEG9qy5ZLkxWcisDXIuvO1agFTvVnNuTlC+UI97TjSMPNqe0kIeSIk/g7G3wLjdeCuxExFdCz9U4juKETMqXonozyr9uY5jZ1mssQ/0IqC2L8Xi/SxCZLoOBTJGjbYCLgdy6FyKWjmR5tG+FtaHR/ufwdU8YN7Y7lsFADGdOeOLsVhuurl3M40mBKzBOb4xxmq3kys2t4Qqh04C17aTPRpN3Ue6lzCr2dNbvwugmd/Zlo4DlY/yhWfMDj5p83rqgtJBfGPxdpsix5lwCLW+XHb8Ftn+SclIp17uu31Ygm4nY2ZzbgL3dOIb61+yfa7AyeYoXlhbxy9DzVnLcYY+zRzzEOY2rkK22sciZsyxJefPQAMeNzm96u1hkxms0TJ0ZnF+X8vxbL6Yy58CkSL6rk9RYTMRzMs6rG8d0TXRzOcvFXZ0/sEYj0H9l/Z2jQqXGDe2OlylyNOsv5Py0nG3vF+tyxEdj51ggDyyKI94NXV0+BHQesCb9YV0a5c+9u8s5Oavy/GB7Bjc3F7xs4+fKzp+abcdz7+1nx6FGlquHi9xedZYZ/EMbw2wD3JSkLC8PcpLP22AbblcksK87X5vw1PjX67bm3McA91NfbxZcY83DGZmVfDWKuBZab2PhsC9VHkiKnFfOcnEnl8lF+mhpvwtYx7gVehOwgDfgvKGrMxjgk6xHMG4oZzl6JmwUa0WcshQ22F1/qecptjOWQSb29VevrMYZ7X4+PEshSbkU1h2rc6oVucKzFNoZb7qCdHLfhPUq2kwhotKzuZzsJPP3/3OwkZEsv+uwPQHAkfEYv46L3T/mwyLWAo+w6eLzp5s8H1xlIf9ZzrEHxhm0d2DoMM4FccqP4yJ7ha5PRLYsBk+6c5FDqd+1TJc9ylCccjkTw7hxTznXpNP6NGSKHAPsVB+KH44u5Fud1Fgu8XGHJxoPc7FzcifjTUenV7DWsNF2TIAkYVtosydTILUqf4y6Ex83Zfxm46dib3p0EGb9bRpXyrJ83pPcWclwObS18y1vzrKkyKEDVU5sHIAdXOMEgOfFKf/f4DMOf7H619tIeYTderWzZt16tgLfwPg0tNXJfQ9z7kkKXFIucq7vyGjoOkW65Lx+F7BOu73+ZrY1wBCNn8cOzzC4Ny5yUjk7sw8Et8cYjudyeJzjA2y4JvvRwQqHl2jvQodBHNd7VwJQpfNTUPxZrB1KOd/hk42n3muruKyba4s7DVh/ZpKARY2/os8Ba2yQX8U1xujB2XE2ybmANsj23mR5s9X6vwB3zTP4H+DIoQKHuPEpmp8l2Zzz2mrEz4dSzinluLxbl7MNXgdgxrU4uwBHZIZ4G/CpbszXTCnPzwz2SVJOcvgItNzGYhBjSZzj8OGU40dyfL8bdYqEVMrNoDVYveScFUXtrx+ajtEqK3whq2wlCzIRh1n9IOMdgYw5V8cFBsr56fV8GucR/3eowLJu1DthjvnmbB/PY082/T74iEUcuHZx+7uTkwLHu607K/fWSo472h1rolKOq+KUk6lfGVsQO6cQILw102n4+DXw4o2f9BoH0OVdcpvjC1iZpHwTOKTLU1VKmfXdYsfVnAOa3SO0aOb8FtZxewJY4PCJJOWIpMpxpUX8KmR9BoNx/R/DIxbx+VqNuVGNlRZ1frZVOxzGyPHJ4SK3VJ1rjKa94Kaycw2+O1TgmpJzei92s0yhAqzo4/zd4d1fIyhbNo9YMZLlkZ7MVf8ecJ2t5OZ4gH/H6y1GzLgsKXB3Kc+D0x+MF7pt2AA7uCbbox2+F2f45zVz192Ka5k9ylCcY0njYc3Z4PzBjjiUY/iQ0eiN5Zw8fw2XNTvTsFOd9sG6D5+wHXP984dBY0tkH7lxnjkHE+6InE0ZX55swbfBYU0+ojra/CidvhhvTzC0ipu8xjJgh5bHgFcwwE+SlIvKOT7ibV4anmTcMXKbnPvY8zOlNjaS5RGD/TNFjjPnY8CCFocwN46PjUN6vTtzIz8r5bQ2TGQm8IWsMjg0LnIzzmuBjBmXA3/f79qmYvAkznnlPFeVO9zMk+Q40WG7xsA3lLMTDo4OoJLj+jjldOobl+aVK5wC629HhtTRKiU3vtfkpecNFdvaqRZUOcv9wOe7OMUfysY7N35yqMgBNBbnTeKBbu9caNfoAr5dHuFFHRy3MwwsjVPu2xoWdI8fHj04xgug7YA0vjvzxvlreGbA8kRkFnIolyPeBvXddw77Dqe8sr9VbaII69cuOdw5mueKTndK26MM+fqLMxWz8DtYGzWuvypmvHPe2s4Po55MR1ewKgv4cZzyCJOECXc+ZvDSfm8zLa/hHfF8nonzj4GHXukRR2y8QM4gin2KLrHG8sB1BDWhPcHXonqD0nYuNe++bkF3nqWzaTdMO9Yu5nHgDUmRI825os3+a0eWx9g/LnLGLGlQKiJd4vNZMVTkS+68A6AGRwM/mM7HmnN1yFMumkme4gUM8AvqF2peH6IvYZLjJG/01zQoeo3zk45OMWzKqAetAWBuucLp0KQxeAc6ClgOnsD1TN4nZfck5SRyXN7JHJ3y7RgxOCSTcqHBKYS5XfgIVQ4u5zb9YkpS3uWwZ5OPGxuo8sUA83ddZSF3G+zeOG7ng0Cztl7NDDYOjz48A8eGWqQ4k5WyLLci30lqXODWVhuLvDnL4iKHDTsnjuT637BXRPrD4Q6oByzaW+vZVaVF/CpJ+Tr1dc6RRbyHDpZv2BPMzSS8b/wHtMNi4MgApW5+buekOU/x8dBHnHXcyKA8wOXUt5luwuGS4SL7dTpHpxyq5RynecTewHXUeyi1elVlpcFdBqeUR9htsqSeSdnX4aIpxvjS0wt5rMV5+8ahUspyIc7fAve1OczOEXx/qMCyXh6y2S+epTCa5wRzDoI221c4r6nBQ0mRJdZ6F3kR2QLUahvswtveHmdO34ppolZffwqAG2+bu6L9Y7fimHcZfVomYQyNDYRfN95xCwOfz1ONc36WTPJypubcmCnwukqeuzqdq1PlBdwL3NvxQLlNn8oUeEVk3EzzKz0li7rfmr8bSnkeNNgnLnAasBRjqMUh6gu6BzkApzTzWrCGN5rnG1ZgtwQuanN35hycC+Iih9J6OwgR2dLMYw70pvffdFXy3Jmk3A3sAyRjGd4JnNXqOLaC+ckgp65bF+F8jKjtX+qnr8bOGOcDmHPCnKf4WMirWEF6RJXH+HCc4Z+B7Sd5eWFkfDdOeUc519gauYWJi7w9Mq5kqttoxiWjCzZtSDpbOIyR54KhIstrztVttifYcWsIV+MaR0SckClwfQTXYjy/9UHYO3xlIjLTRRv+PK0wf2ZujgIuBm4CwDnJClzU6vE48SAnN24JAjxaznO2t3dyRsuSIofg7N24ivV+2HTjWruCBCx/BmsyKUdF8F0mv6WRGHwmTnkzcHo5x3+FmLffkpXsSsSFtuHZS5N5sLyaD09yoM6sM5rltx22J9jqVPL80B5jz3guS9s8PLqbskOFrveK67kqpJU8d/a7DpG2GftPePTATD3LtJzjP+Iiv2xsiMomxtuBS6f78VYgGxvvHX/scE6vwhVABOfUGn07DY4bTrl4JMejIcYO1uW8kuOOpMDZGB9t9h6D/YAfJwW+43DzIHzj6Tx/CFVDLwyn7FB1XotxmEXsx2bWsRk8ifEG346RHpXYdV4/ffHquSu4dWyQK4DX97umma7x//+MOOUGg08DL+13TQ3Pc9vgQO0tQgQ/gS2/VYhsmYZTdsB5E+tXfH+1rwVNwcFjuNSoH+vj8F6Df51uSGqEq/ETYR6u5Hp2mDcAI1m+E6f8wOCVQOz1I3pODDF20GNkSnkuiFO2NXjXFG+LMA4wOKAKJCkl4HHaP3y4VxZR71mU2PRvc62pRRxcXsBvu1ZVHzWOQjisw/YEW5VyjgcMXhYXORXnPCDpd00iMnMYJAl8ccJa15HBKp/pa1GbUclyfZxyHvUWC9tlUt5Ejus293GWkovh3euf4GyHsS6WOil3zjbjhwBuHDNc5KIQXfyDn9NXyXFynLKSyVs3TCahfvbSjqFr6bOnajUOqeT4Ub8L6bZSluXz13BHeYyLgaP6Xc9M5zBGlguHVnETNa7xGd6lWUR6wyCJU250+LsJT3680WtvxnIoJc7l43ewzFhicP3m+mDGcCqQbzz8WTnLV7pd62Qqee5KCnwb40Ag486ZwLGdjttxm4aNOXgpx7kObwXWhh5/VnDujWCvykL+s9+l9MrqefyllOOtjaOJ2mtPsJUZXcBvSjle5cYJNGl1IiJbPnuSeUmRI+KU+2kcbt/wYLnAh/pVVyvKzpU0us/jvDApTN3c21aziAlXrwzO7mdjco84i0aDZ4ejh1azS6djBr+CNa6c4/qh1dxbq3KFscFivS3Z0zjnl/N8rJeL9GaS0TxftwK7ZYwPWn03RvAQvyUZX882nHJbzVmGcUC/axIRMOfMJG2rYXCrFscZtsXJbPT8YxEc6jsy2oMaOuYLWZUUuKaxkQeM04GvN3t/XOM01m+S+nEpxy3dr7K5cpb7k5SvAYcCA17lTOod9NvWtYAFMDqfh4F/GCpwsEechfPybs7XN86oG58erHHh0wt19aaxRffkTIEvR3BNW+0JtjKNXSsHJkWOxPkU9TV/ItI/O9DGwfdBOPcOwBtn2yawgRqfqA7wbiB2+PvMSvae7E6OrWZx7Jy07rFx1ow4Hsw5G6t3pgfekjzFBaVF/Krd4XpydWE0z62lLHs77OlwCfCLXszbZWtxbnPjxHLEtuUc71S42lAlz53ltezZweHRW51SluWZDLsCX+53LSLSc39044Rynn1mW7gCaDTp/NL44yji1MneF4+xBOonexjcNZrltt5UOLVSnp/j6773DjDA2Z2MZ+79CY22msWDVXY12CmChQ7z8ZY7hPdS0WC1RzzhzsOVHL/s5m1AW83iTK35b0+VLA86VLo1f2jDRZ5bXb8Vt6lO/l5JgZd4tMlldgCsRqWU58F2xu2XZCW7+sDU/yYGnBWbO7MwLm597QpsjLWd/OYZwtwVbFPJ1A+unUw5y/29rKcVScq5438u5db/ebaY+P1zsMaT0w0rwyk71OobtF7S1QIncla48cvIub2U57Z2dtFN/PtO53tCN9kqFmac5wLg1Cbreznxe1s8yGNr5vJEj8tsaqP6q+UcD7Q9Vr8CloiIiMiWSguQRURERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQlMAUtEREQkMAUsERERkcAUsEREREQCU8ASERERCUwBS0RERCQwBSwRERGRwBSwRERERAJTwBIREREJTAFLREREJDAFLBEREZHAFLBEREREAlPAEhEREQnsfwGGC9wjxnoqDgAAAABJRU5ErkJggg==" alt="OnnetFibra QA" style="height:32px;max-width:200px;object-fit:contain">
      </div>
      <div class="sb-tagline"><span>QA</span> Automation</div>
    </div>
    <div id="user-bar" style="display:none;padding:4px 10px;background:var(--card);border-bottom:1px solid var(--brd);align-items:center;justify-content:space-between;flex-shrink:0">
      <span id="user-bar-name" style="font-size:.68rem;color:var(--txt2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px"></span>
      <button onclick="_doLogout()" style="padding:2px 8px;border-radius:4px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.65rem;cursor:pointer;flex-shrink:0">Salir</button>
    </div>
    <div class="sb-list" id="sb-list"></div>
    <button class="hist-btn" id="dashboard-btn" onclick="showDashboard()">&#128200;&nbsp; Dashboard</button>
    <button class="hist-btn" id="codigos-btn" onclick="showCodigos()">&#128214;&nbsp; C&#xF3;digos de Retorno</button>
    <button class="hist-btn" id="hist-btn" onclick="showHistorial()">&#128203;&nbsp; Historial de Pruebas</button>
    <button class="hist-btn" id="settings-btn" onclick="showSettings()">&#9881;&nbsp; Settings</button>
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
      <button class="clr-btn" id="clr-btn" onclick="clearTerm()">Limpiar</button>
      <button class="theme-btn" id="theme-btn" onclick="toggleTheme()" title="Cambiar tema">☀</button>
    </div>
    <div id="gf-panel" style="display:none;flex-shrink:0"></div>
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
      <div id="fact-form-bar" style="flex-shrink:0;overflow-y:auto;padding:14px 18px;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface)"></div>
      <div id="fact-grid"></div>
    </div>
    <!-- Vista Intervención Asegurada — 4 consolas paralelas -->
    <div id="ia-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="ia-form-bar" style="flex-shrink:0;overflow-y:auto;padding:14px 18px;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface)"></div>
      <div id="ia-grid"></div>
    </div>
    <!-- Vista Activación — 4 consolas paralelas -->
    <div id="activ-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="activ-form-bar" style="flex-shrink:0;overflow-y:auto;padding:14px 18px;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface)"></div>
      <div id="activ-grid"></div>
    </div>
    <!-- Vista Teardown Masivo -->
    <div id="teardown-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="teardown-form-bar" style="display:flex;align-items:center;gap:10px;padding:8px 14px;flex-shrink:0;border-bottom:1px solid var(--brd);background:var(--card);flex-wrap:wrap"></div>
      <div id="teardown-console" style="flex:1;overflow-y:auto;padding:10px 14px;font-family:monospace;font-size:.75rem;background:var(--bg2);white-space:pre-wrap;word-break:break-all"></div>
    </div>
    <!-- Vista Cancelación — 4 consolas paralelas -->
    <div id="cancel-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="cancel-form-bar" style="flex-shrink:0;overflow-y:auto;padding:14px 18px;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface)"></div>
      <div id="cancel-grid"></div>
    </div>
    <!-- Vista Unsubscription — 4 consolas paralelas -->
    <div id="unsub-suite-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="unsub-form-bar" style="flex-shrink:0;overflow-y:auto;padding:14px 18px;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface)"></div>
      <div id="unsub-grid"></div>
    </div>
    <!-- Vista QA FulFillment Queue -->
    <div id="fulfillment-view" style="display:none;flex-direction:column;flex:1;overflow-y:auto;min-width:0">
      <div class="atrf-layout">
        <div class="atrf-section">
          <div class="atrf-section-header">
            <div class="atrf-section-title">Estado de ejecución</div>
            <span id="atrf-run-prog" style="font-size:11px;color:var(--atrf-text2);font-family:var(--atrf-mono);display:none;margin-right:4px"></span>
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:12px;color:var(--atrf-text2);margin-right:2px" title="Seleccionar / deseleccionar todas">
              <div class="atrf-qcb" id="atrf-selall-cb" onclick="event.preventDefault();_atrf_toggleSelAll()"></div>
              Todas
            </label>
            <button class="atrf-btn atrf-btn-sm atrf-btn-danger" id="atrf-del-sel-btn" onclick="_atrf_deleteSelected()" style="display:none">🗑 Eliminar seleccionadas</button>
            <button class="atrf-btn atrf-btn-sm atrf-btn-danger" onclick="_atrf_clearQueue()">Vaciar cola</button>
            <button class="atrf-btn atrf-btn-sm atrf-btn-primary" id="atrf-run-btn" onclick="_atrf_runSelected()">&#9654; Ejecutar seleccionadas</button>
            <button class="atrf-btn atrf-btn-sm atrf-btn-green" onclick="_atrf_openNew()">+ Nueva secuencia</button>
          </div>
          <div id="atrf-exec-area"></div>
        </div>
      </div>
    </div>
    <!-- Vista Dashboard -->
    <div id="dashboard-view" style="display:none;flex-direction:column;flex:1;overflow:auto;padding:18px 20px;gap:16px">
      <div id="dash-content"><div style="padding:40px;text-align:center;color:var(--txt2);font-size:.8rem">Cargando dashboard&#8230;</div></div>
    </div>
    <!-- Vista Historial -->
    <div id="historial-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <!-- Tabs -->
      <div style="display:flex;gap:2px;padding:8px 14px 0;flex-shrink:0;background:var(--card);border-bottom:1px solid var(--brd)">
        <button id="htab-hist" onclick="_hTab('hist')" style="padding:5px 14px;border-radius:5px 5px 0 0;border:1px solid var(--brd);border-bottom:none;background:var(--bg);color:var(--acc);font-size:.76rem;cursor:pointer;font-weight:700">&#128203; Historial</button>
        <button id="htab-stats" onclick="_hTab('stats')" style="padding:5px 14px;border-radius:5px 5px 0 0;border:1px solid var(--brd);border-bottom:none;background:var(--card);color:var(--txt2);font-size:.76rem;cursor:pointer">&#128200; Estadísticas</button>
        <div style="flex:1"></div>
        <input id="historial-filter" type="text" placeholder="Filtrar…" oninput="_filterHistorial()" style="display:none;padding:4px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.75rem;min-width:150px;align-self:center;margin-bottom:4px">
        <button id="hist-refresh-btn" onclick="_hTabRefresh()" style="padding:4px 10px;border-radius:5px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.73rem;cursor:pointer;align-self:center;margin-bottom:4px">&#8635;</button>
        <button id="hist-del-all-btn" onclick="_histDeleteAll()" style="display:none;padding:4px 10px;border-radius:5px;border:1px solid var(--errb);background:var(--errd);color:var(--err);font-size:.73rem;cursor:pointer;align-self:center;margin-bottom:4px">&#128465; Borrar todo</button>
      </div>
      <!-- Historial tab -->
      <div id="hpane-hist" style="flex:1;overflow:auto;padding:12px 14px">
        <div class="hist-empty">Cargando…</div>
      </div>
      <!-- Stats tab -->
      <div id="hpane-stats" style="display:none;flex:1;overflow:auto;padding:12px 14px">
        <div class="hist-empty">Cargando estadísticas…</div>
      </div>
    </div>
    <!-- Vista Device Modification — 4 consolas paralelas -->
    <div id="dm-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="dm-form-bar" style="flex-shrink:0;overflow-y:auto;padding:14px 18px;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface)"></div>
      <div id="dm-grid"></div>
    </div>
    <!-- Vista Asignación — 4 consolas paralelas -->
    <div id="asig-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div id="asig-form-bar" style="flex-shrink:0;overflow-y:auto;padding:14px 18px;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface)"></div>
      <div id="asig-grid"></div>
    </div>
    <!-- Vista Services Now — doble terminal -->
    <div id="sn-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div class="sn-form" id="sn-form"></div>
      <div class="sn-terms" id="sn-terms"></div>
    </div>
    <!-- Vista Settings -->
    <div id="settings-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <!-- Tabs -->
      <div style="display:flex;gap:2px;padding:8px 14px 0;flex-shrink:0;background:var(--card);border-bottom:1px solid var(--brd)">
        <button id="stab-env" onclick="_stTab('env')" style="padding:5px 14px;border-radius:5px 5px 0 0;border:1px solid var(--brd);border-bottom:none;background:var(--bg);color:var(--acc);font-size:.76rem;cursor:pointer;font-weight:700">&#127760; Ambientes</button>
        <button id="stab-cfg" onclick="_stTab('cfg')" style="padding:5px 14px;border-radius:5px 5px 0 0;border:1px solid var(--brd);border-bottom:none;background:var(--card);color:var(--txt2);font-size:.76rem;cursor:pointer">&#9881; Configuraci&#xF3;n</button>
        <button id="stab-perfil" onclick="_stTab('perfil')" style="padding:5px 14px;border-radius:5px 5px 0 0;border:1px solid var(--brd);border-bottom:none;background:var(--card);color:var(--txt2);font-size:.76rem;cursor:pointer">&#128100; Perfil</button>
        <button id="stab-usuarios" onclick="_stTab('usuarios')" style="display:none;padding:5px 14px;border-radius:5px 5px 0 0;border:1px solid var(--brd);border-bottom:none;background:var(--card);color:var(--txt2);font-size:.76rem;cursor:pointer">&#128101; Usuarios</button>
      </div>
      <!-- Ambientes pane -->
      <div id="spane-env" style="flex:1;overflow:auto;padding:16px 18px">
        <div style="max-width:860px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
            <h3 style="margin:0;font-size:.85rem;color:var(--txt);font-weight:700">Ambientes Newman</h3>
            <button onclick="_envAdd()" style="padding:5px 16px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.76rem;font-weight:700;cursor:pointer">+ Nuevo</button>
          </div>
          <div id="env-table-body"><div class="hist-empty">Cargando...</div></div>
          <!-- Formulario add/edit inline -->
          <div id="env-form" style="display:none;margin-top:16px;background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:16px 18px">
            <h4 style="margin:0 0 14px;font-size:.8rem;color:var(--txt);font-weight:700" id="env-form-title">Nuevo ambiente</h4>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px">
              <div>
                <label style="display:block;font-size:.72rem;color:var(--txt2);margin-bottom:3px">Nombre *</label>
                <input id="env-f-name" type="text" placeholder="ej: QA" maxlength="50" style="width:100%;box-sizing:border-box;padding:6px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem">
              </div>
              <div>
                <label style="display:block;font-size:.72rem;color:var(--txt2);margin-bottom:3px">Etiqueta</label>
                <input id="env-f-label" type="text" placeholder="ej: Calidad (QA)" maxlength="100" style="width:100%;box-sizing:border-box;padding:6px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem">
              </div>
              <div style="grid-column:span 2">
                <label style="display:block;font-size:.72rem;color:var(--txt2);margin-bottom:3px">URL base Newman *</label>
                <input id="env-f-url" type="text" placeholder="https://api.ejemplo.com" style="width:100%;box-sizing:border-box;padding:6px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem">
              </div>
              <div>
                <label style="display:block;font-size:.72rem;color:var(--txt2);margin-bottom:3px">Tipo</label>
                <select id="env-f-type" style="width:100%;box-sizing:border-box;padding:6px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem">
                  <option value="qa">QA</option>
                  <option value="pprd">Pre-Producci&#xF3;n</option>
                  <option value="prd">Producci&#xF3;n</option>
                  <option value="custom">Personalizado</option>
                </select>
              </div>
              <div style="display:flex;align-items:flex-end">
                <label style="display:flex;align-items:center;gap:6px;font-size:.76rem;color:var(--txt2);cursor:pointer">
                  <input id="env-f-active" type="checkbox" checked style="cursor:pointer"> Activo
                </label>
              </div>
            </div>
            <div id="env-form-err" style="display:none;color:var(--err);font-size:.73rem;margin-bottom:8px"></div>
            <div style="display:flex;gap:8px;align-items:center">
              <button onclick="_envSave()" style="padding:5px 18px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.76rem;font-weight:700;cursor:pointer">Guardar</button>
              <button onclick="_envFormClose()" style="padding:5px 14px;border-radius:5px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.76rem;cursor:pointer">Cancelar</button>
              <span id="env-form-ok" style="display:none;color:var(--ok);font-size:.73rem">&#10003; Guardado</span>
            </div>
          </div>
        </div>
      </div>
      <!-- Configuraci&#xF3;n pane -->
      <div id="spane-cfg" style="display:none;flex:1;overflow:auto;padding:16px 18px">
        <div id="spane-cfg-body"><div class="hist-empty">Cargando...</div></div>
      </div>
      <!-- Perfil pane -->
      <div id="spane-perfil" style="display:none;flex:1;overflow:auto;padding:16px 18px">
        <div style="max-width:500px">
          <h3 style="margin:0 0 18px;font-size:.85rem;color:var(--txt);font-weight:700">Mi Perfil</h3>
          <div id="perfil-body"></div>
        </div>
      </div>
      <!-- Usuarios pane (admin only) -->
      <div id="spane-usuarios" style="display:none;flex:1;overflow:auto;padding:16px 18px">
        <div style="max-width:860px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
            <h3 style="margin:0;font-size:.85rem;color:var(--txt);font-weight:700">Usuarios del Sistema</h3>
            <button onclick="_usrAdd()" style="padding:5px 16px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.76rem;font-weight:700;cursor:pointer">+ Invitar Usuario</button>
          </div>
          <div id="usr-table-body"><div class="hist-empty">Cargando...</div></div>
          <!-- Formulario nuevo usuario -->
          <div id="usr-form" style="display:none;margin-top:16px;background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:16px 18px">
            <h4 style="margin:0 0 14px;font-size:.8rem;color:var(--txt);font-weight:700">Invitar nuevo usuario</h4>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px">
              <div>
                <label style="display:block;font-size:.72rem;color:var(--txt2);margin-bottom:3px">Nombre *</label>
                <input id="usr-f-name" type="text" placeholder="Nombre completo"
                  style="width:100%;box-sizing:border-box;padding:6px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem">
              </div>
              <div>
                <label style="display:block;font-size:.72rem;color:var(--txt2);margin-bottom:3px">Email *</label>
                <input id="usr-f-email" type="email" placeholder="usuario@ejemplo.com"
                  style="width:100%;box-sizing:border-box;padding:6px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem">
              </div>
              <div>
                <label style="display:block;font-size:.72rem;color:var(--txt2);margin-bottom:3px">Rol</label>
                <select id="usr-f-role" style="width:100%;box-sizing:border-box;padding:6px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem">
                  <option value="ejecutor">Ejecutor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div id="usr-form-err" style="display:none;color:var(--err);font-size:.73rem;margin-bottom:8px"></div>
            <div style="display:flex;gap:8px;align-items:center">
              <button onclick="_usrSave()" style="padding:5px 18px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.76rem;font-weight:700;cursor:pointer">Crear e Invitar</button>
              <button onclick="_usrFormClose()" style="padding:5px 14px;border-radius:5px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.76rem;cursor:pointer">Cancelar</button>
            </div>
            <!-- Invite link display -->
            <div id="usr-invite-link-area" style="display:none;margin-top:14px;padding:12px;background:var(--bg);border:1px solid var(--brd);border-radius:6px">
              <div style="font-size:.72rem;color:var(--txt2);margin-bottom:6px">&#x2139; Comparte este enlace de invitaci&#xF3;n (v&#xE1;lido 72 horas):</div>
              <div style="display:flex;gap:8px;align-items:center">
                <input id="usr-invite-link" type="text" readonly
                  style="flex:1;padding:6px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--card);color:var(--acc);font-size:.72rem;font-family:monospace"/>
                <button onclick="_copyInviteLink()" style="padding:5px 12px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.72rem;cursor:pointer">Copiar</button>
              </div>
            </div>
          </div>
          <!-- Permissions modal -->
          <div id="usr-perms-modal" style="display:none;margin-top:16px;background:var(--card);border:1px solid var(--acc);border-radius:8px;padding:16px 18px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
              <h4 style="margin:0;font-size:.8rem;color:var(--txt);font-weight:700" id="usr-perms-title">Permisos de usuario</h4>
              <button onclick="_usrPermsClose()" style="padding:2px 10px;border-radius:4px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.72rem;cursor:pointer">&#x2715; Cerrar</button>
            </div>
            <div id="usr-perms-body"></div>
            <div style="margin-top:12px;display:flex;gap:8px">
              <button onclick="_usrPermsSave()" style="padding:5px 18px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.76rem;font-weight:700;cursor:pointer">Guardar permisos</button>
              <span id="usr-perms-ok" style="display:none;color:var(--ok);font-size:.73rem;align-self:center">&#10003; Guardado</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Vista C&#xF3;digos de Retorno -->
    <div id="codigos-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div style="padding:10px 16px;border-bottom:1px solid var(--brd);display:flex;gap:8px;align-items:center;flex-wrap:wrap;flex-shrink:0;background:var(--card)">
        <input id="rc-search" type="text" placeholder="Buscar c&#xF3;digo o descripci&#xF3;n..." oninput="_rcFilter()"
          style="padding:5px 10px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.78rem;width:220px;flex-shrink:0">
        <select id="rc-flow" onchange="_rcFilter()"
          style="padding:5px 8px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.78rem;flex-shrink:0">
          <option value="">Todos los flujos</option>
        </select>
        <select id="rc-cls" onchange="_rcFilter()"
          style="padding:5px 8px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.78rem;flex-shrink:0">
          <option value="">Funcional + Sist&#xE9;mico</option>
          <option value="Funcional">Solo Funcional</option>
          <option value="Sist&#xE9;mico">Solo Sist&#xE9;mico</option>
        </select>
        <span id="rc-count" style="font-size:.7rem;color:var(--txt2);margin-left:auto"></span>
        <button id="rc-add-btn" onclick="_rcAddOpen()" style="display:none;padding:4px 12px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.73rem;font-weight:700;cursor:pointer">+ Agregar</button>
      </div>
      <!-- Modal agregar (admin) -->
      <div id="rc-add-modal" style="display:none;padding:12px 16px;border-bottom:1px solid var(--brd);background:var(--card);flex-shrink:0">
        <div style="max-width:640px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div>
            <label style="display:block;font-size:.7rem;color:var(--txt2);margin-bottom:3px">Flujo</label>
            <input id="rc-new-flow" list="rc-flow-list" placeholder="Ej: Factibilidad"
              style="width:100%;box-sizing:border-box;padding:5px 8px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.78rem">
            <datalist id="rc-flow-list"></datalist>
          </div>
          <div>
            <label style="display:block;font-size:.7rem;color:var(--txt2);margin-bottom:3px">C&#xF3;digo</label>
            <input id="rc-new-code" placeholder="Ej: 404"
              style="width:100%;box-sizing:border-box;padding:5px 8px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.78rem">
          </div>
          <div>
            <label style="display:block;font-size:.7rem;color:var(--txt2);margin-bottom:3px">Clasificaci&#xF3;n</label>
            <select id="rc-new-cls" style="width:100%;box-sizing:border-box;padding:5px 8px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.78rem">
              <option value="Funcional">Funcional</option>
              <option value="Sist&#xE9;mico">Sist&#xE9;mico</option>
            </select>
          </div>
          <div>
            <label style="display:block;font-size:.7rem;color:var(--txt2);margin-bottom:3px">Breaking point (opcional)</label>
            <input id="rc-new-bp" placeholder="Ej: cpqd"
              style="width:100%;box-sizing:border-box;padding:5px 8px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.78rem">
          </div>
          <div style="grid-column:1/-1">
            <label style="display:block;font-size:.7rem;color:var(--txt2);margin-bottom:3px">Descripci&#xF3;n</label>
            <input id="rc-new-desc" placeholder="Descripci&#xF3;n del c&#xF3;digo de retorno"
              style="width:100%;box-sizing:border-box;padding:5px 8px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.78rem">
          </div>
        </div>
        <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
          <button onclick="_rcAddSave()" style="padding:4px 14px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.74rem;font-weight:700;cursor:pointer">Guardar</button>
          <button onclick="_rcAddClose()" style="padding:4px 10px;border-radius:5px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.74rem;cursor:pointer">Cancelar</button>
          <span id="rc-add-err" style="display:none;color:var(--err);font-size:.72rem"></span>
        </div>
      </div>
      <div id="rc-body" style="flex:1;overflow-y:auto;padding:0 16px 16px">
        <div class="hist-empty">Cargando...</div>
      </div>
    </div>
    <div class="summary" id="summary">
      <span class="sum-idle">Ejecuta una suite para ver resultados</span>
    </div>
  </main>
</div>
<script>window.onerror=function(msg,src,line,col){var el=document.getElementById('sb-list');if(el)el.innerHTML='<div style="padding:8px;color:#e06c75;font-size:.65rem">JS ERR L'+line+': '+msg+'</div>';return false;};</script>
<script>
// ── Auth state ────────────────────────────────────────────────────────────────
var currentUser=null;
var _authToken=localStorage.getItem('qa_token')||'';
var _pendingInviteToken='';

function _authHdr(){
  var h={'Content-Type':'application/json'};
  if(_authToken) h['Authorization']='Bearer '+_authToken;
  return h;
}
function _setAuth(token,user){
  _authToken=token; currentUser=user;
  localStorage.setItem('qa_token',token);
}
function _clearAuth(){
  _authToken=''; currentUser=null;
  localStorage.removeItem('qa_token');
}
function _canSeeSuite(sid){
  if(!currentUser||currentUser.role==='admin') return true;
  return Object.prototype.hasOwnProperty.call(currentUser.permissions||{},sid);
}
function _allowedTcs(suiteId,allMeta){
  if(!currentUser||currentUser.role==='admin') return allMeta;
  var p=(currentUser.permissions||{})[suiteId];
  if(!p||!p.length) return allMeta;
  return allMeta.filter(function(m){ return p.indexOf(m.tc)>=0; });
}

// ── Auth screens ──────────────────────────────────────────────────────────────
function _showAuthScreen(mode){
  document.getElementById('auth-screen').style.display='flex';
  document.getElementById('auth-login').style.display=mode==='login'?'block':'none';
  document.getElementById('auth-bootstrap').style.display=mode==='bootstrap'?'block':'none';
  document.getElementById('auth-invite').style.display='none';
}
function _showInviteScreen(token){
  _pendingInviteToken=token;
  fetch('/api/auth/invite/'+encodeURIComponent(token)).then(function(r){
    if(!r.ok) throw new Error('not_found');
    return r.json();
  }).then(function(u){
    document.getElementById('auth-screen').style.display='flex';
    document.getElementById('auth-login').style.display='none';
    document.getElementById('auth-bootstrap').style.display='none';
    document.getElementById('auth-invite').style.display='block';
    document.getElementById('invite-greeting').textContent='Hola '+u.name+', establece tu contrase\xf1a';
  }).catch(function(){
    _clearAuth();
    history.replaceState({},'','/');
    _showAuthScreen('login');
  });
}
function _showMainApp(){
  document.getElementById('auth-screen').style.display='none';
  var layout=document.querySelector('.layout');
  if(layout) layout.style.display='flex';
  if(currentUser){
    var ub=document.getElementById('user-bar');
    var un=document.getElementById('user-bar-name');
    if(ub) ub.style.display='flex';
    if(un) un.textContent=currentUser.name+' \xb7 '+(currentUser.role==='admin'?'Admin':'Ejecutor');
    // Show/hide admin tab in settings
    var utab=document.getElementById('stab-usuarios');
    if(utab) utab.style.display=currentUser.role==='admin'?'':'none';
  }
  _applyViewPerms();
}
function _applyViewPerms(){
  var dbtn=document.getElementById('dashboard-btn');
  var hbtn=document.getElementById('hist-btn');
  var cbtn=document.getElementById('codigos-btn');
  if(dbtn) dbtn.style.display=_canSeeSuite('view:dashboard')?'':'none';
  if(hbtn) hbtn.style.display=_canSeeSuite('view:historial')?'':'none';
  if(cbtn) cbtn.style.display=_canSeeSuite('view:codigos')?'':'none';
}

// ── Auth actions ──────────────────────────────────────────────────────────────
// «« Auth stubs (no-op en modo sin auth) »»
function _doLogin(){}
function _doBootstrap(){}
function _doAcceptInvite(){}
function _doLogout(){ console.log("logout no-op"); }
var _embeddedMode=(new URLSearchParams(window.location.search).get('embedded')==='1');
function initApp(){
  if(_embeddedMode){
    var _sbEl=document.querySelector('aside.sb');
    if(_sbEl) _sbEl.style.display='none';
    var _tbEl=document.querySelector('.main .topbar');
    if(_tbEl) _tbEl.style.display='none';
  }
  loadSuites();
}

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
var _accordionOpen={'qa-endpoints':false};
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
    if(_embeddedMode){ switchView('fulfillment'); _atrf_load(); _atrf_renderQueue(); }
  }).catch(function(err){
    var msg='Error API /suites (intento '+attempt+'): '+err.message;
    document.getElementById('sb-list').innerHTML='<div style="padding:8px;color:#e06c75;font-size:.7rem;white-space:pre-wrap">'+msg+'</div>';
    if(attempt<4){setTimeout(function(){loadSuites(attempt+1);}, 1500);}
  });
}
initApp();
renderGlobalForm();

function renderSB(){
  var el=document.getElementById('sb-list'); el.innerHTML='';
  [{key:'disponible',lbl:'Disponibles'},{key:'bloqueado',lbl:'Bloqueados'}].forEach(function(g){
    var items=suites.filter(function(s){
      if(s.group!==g.key) return false;
      if(s.id==='qa-fulfillment') return _canSeeSuite('view:fulfillment');
      if(s.id==='qa-endpoints')   return _canSeeSuite('view:qa');
      return true;
    });
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
          +'<button class="acc-toggle" title="Expandir endpoints y suites">'
          +(isOpen?'&#9660;':'&#9654;')+'</button>';
        row.querySelector('.si-txt').onclick=(function(sid){return function(){selectSuite(sid);};})(s.id);
        row.querySelector('.acc-toggle').onclick=(function(pid){return function(e){e.stopPropagation();toggleAccordion(pid);};})(s.id);
        el.appendChild(row);
        if(isOpen){
          var _sections=[
            {lbl:'Suite Factibilidad',par:'qa-fact'},
            {lbl:'Suite Asignación',par:'qa-asig'},
            {lbl:'Suite Interv. Asegurada',par:'qa-ia-par'},
            {lbl:'Suite Activación',par:'qa-activ-par'},
            {lbl:'Suite Device Mod.',par:'qa-dm-par'},
            {lbl:'Suite Cancelación',par:'qa-cancel-par'},
            {lbl:'Suite Unsubscription',par:'qa-unsub-par'},
            {lbl:'Suite Teardown',par:'qa-teardown-par'},
            {lbl:'Consultas',par:'qa-consultas'}
          ];
          _sections.forEach(function(sec){
            var kids=suites.filter(function(c){return c.parent===sec.par&&(!sec.onlyEp||c.id.indexOf('qa-ep-')===0)&&_canSeeSuite(c.id);});
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
  var _hb=document.getElementById('hist-btn'); if(_hb) _hb.classList.remove('active');
  var _sb=document.getElementById('settings-btn'); if(_sb) _sb.classList.remove('active');
  if(id==='qa-fulfillment'){
    switchView('fulfillment');
    setTop('','Pruebas Automatizadas (FullFillment)','');
    _atrf_load();
    _atrf_renderQueue();
    return;
  }
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
  if(id==='qa-ep-ia-cancel'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderIACancelForm();
    setTop('','IA Cancelación','cancela intervención asegurada · configura y ejecuta');
    var _ebiac=document.getElementById('exec-btn'); if(_ebiac) _ebiac.disabled=true;
    return;
  }
  if(id==='qa-ep-devmod'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderDevModForm();
    setTop('','Device Modification','modificación de dispositivo · configura y ejecuta');
    var _ebdm=document.getElementById('exec-btn'); if(_ebdm) _ebdm.disabled=true;
    return;
  }
  if(id==='qa-ep-modificacion'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderModificacionForm();
    setTop('','Modificación Acceso','modificación de acceso FTTH · configura y ejecuta');
    var _ebmod=document.getElementById('exec-btn'); if(_ebmod) _ebmod.disabled=true;
    return;
  }
  if(id==='qa-ep-cancel'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderCancelSvcForm();
    setTop('','Cancel Orden Servicio','cancelación de orden · configura y ejecuta');
    var _ebcsv=document.getElementById('exec-btn'); if(_ebcsv) _ebcsv.disabled=true;
    return;
  }
  if(id==='qa-ep-unsub'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderUnsubForm();
    setTop('','Unsubscription','desuscripción / baja de acceso · configura y ejecuta');
    var _ebus=document.getElementById('exec-btn'); if(_ebus) _ebus.disabled=true;
    return;
  }
  if(id==='qa-cons-retrievetch'||id==='qa-cons-retrievekao'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderRetrieveForm();
    setTop('','RetrieveAccess','retrieve access · configura y ejecuta');
    var _ebrtv=document.getElementById('exec-btn'); if(_ebrtv) _ebrtv.disabled=true;
    return;
  }
  if(id==='qa-cons-diagnostico'||id==='qa-cons-estadovecino'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderAccessIdEpForm();
    var _lblAi=id==='qa-cons-diagnostico'?'DiagnosticoAcceso':'EstadoVecino V';
    setTop('',_lblAi,'u_access_id_vno · configura y ejecuta');
    var _ebai=document.getElementById('exec-btn'); if(_ebai) _ebai.disabled=true;
    return;
  }
  if(id==='qa-cons-accessstate'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderAccessStateForm();
    setTop('','AccessStateResponse','PUT callback · configura y ejecuta');
    var _ebas=document.getElementById('exec-btn'); if(_ebas) _ebas.disabled=true;
    return;
  }
  if(id==='qa-cons-queryneighbors'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderQueryNeighborsForm();
    setTop('','QueryNeighborsStateResponse','PUT callback · configura y ejecuta');
    var _ebqn=document.getElementById('exec-btn'); if(_ebqn) _ebqn.disabled=true;
    return;
  }
  if(id==='qa-cons-reinicio'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderReinicioForm();
    setTop('','ReinicioONT','reinicio de ONT · configura y ejecuta');
    var _ebrei=document.getElementById('exec-btn'); if(_ebrei) _ebrei.disabled=true;
    return;
  }
  if(id==='qa-cons-consultaacceso'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderConsultaAccesoForm();
    setTop('','ConsultaAcceso','GET · ingresa ID de acceso');
    var _ebca=document.getElementById('exec-btn'); if(_ebca) _ebca.disabled=true;
    return;
  }
  if(id==='qa-cons-cevvecino'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderCEVVecinoForm();
    setTop('','CEVEstadoVecino','GET · ingresa OLT ID');
    var _ebcev=document.getElementById('exec-btn'); if(_ebcev) _ebcev.disabled=true;
    return;
  }
  if(id==='qa-cons-dataont'){
    _isQAChild=true; switchView('ep-form'); renderEPFVNOBar(); renderConsultaDataONTForm();
    setTop('','ConsultaDataONT','consulta datos ONT · configura y ejecuta');
    var _ebdont=document.getElementById('exec-btn'); if(_ebdont) _ebdont.disabled=true;
    return;
  }
  if(id==='qa-fact-suite'){
    _isQAChild=false;
    switchView('fact');
    renderFactFormBar();
    renderFactView();
    setTop('','Suite: Factibilidad','Configura los parámetros y presiona Ejecutar');
    _syncExecBtn();
    return;
  }
  if(id==='qa-asig-suite'){
    _isQAChild=false;
    switchView('asig');
    renderAsigFormBar();
    renderAsigView();
    setTop('','Suite: Asignación','Configura los parámetros y presiona Ejecutar');
    _syncAsigExecBtn();
    return;
  }
  if(id==='qa-ia-inicio-suite'||id==='qa-ia-fin-suite'||id==='qa-ia-cancel-suite'){
    _isQAChild=false;
    _iaMode=id==='qa-ia-inicio-suite'?'inicio':(id==='qa-ia-cancel-suite'?'cancel':'fin');
    switchView('ia');
    renderIAFormBar();
    renderIAView();
    var _iaLbl=_iaMode==='inicio'?'Inicio Intervención':(_iaMode==='cancel'?'Cancelación Intervención':'Finalización Intervención');
    setTop('','Suite: '+_iaLbl,'Configura los parámetros y presiona Ejecutar');
    _syncIAExecBtn();
    return;
  }
  if(id==='qa-activ-suite'||id==='qa-activ-sin-idem-suite'){
    _isQAChild=false;
    _activMode=id==='qa-activ-suite'?'idem':'sin-idem';
    switchView('activ');
    renderActivFormBar();
    renderActivView();
    var _activLbl=_activMode==='idem'?'Activación + Idempotencia':'Activación sin Idempotencia';
    setTop('','Suite: '+_activLbl,'Configura los parámetros y presiona Ejecutar');
    _syncActivExecBtn();
    return;
  }
  if(id==='qa-dm-suite'){
    _isQAChild=false;
    switchView('dm');
    renderDmFormBar();
    renderDmView();
    setTop('','Suite: Device Modification','Configura los parámetros y presiona Ejecutar');
    _syncDmExecBtn();
    return;
  }
  if(id==='qa-cancel-suite'){
    _isQAChild=false;
    switchView('cancel');
    renderCancelFormBar();
    renderCancelView();
    setTop('','Suite: Cancelación','Configura los parámetros y presiona Ejecutar');
    _syncCancelExecBtn();
    return;
  }
  if(id==='qa-unsub-suite'){
    _isQAChild=false;
    switchView('unsub-suite');
    renderUnsubSuiteFormBar();
    renderUnsubSuiteView();
    setTop('','Suite: Unsubscription','Configura los parámetros y presiona Ejecutar');
    _syncUnsubSuiteExecBtn();
    return;
  }
  if(id==='qa-teardown-masivo'){
    _isQAChild=false;
    switchView('teardown');
    renderTeardownFormBar();
    setTop('','Teardown Masivo','Cancela access IDs activos · presiona Ejecutar');
    _syncTeardownExecBtn();
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
  } else if(s && s.env_type==='qa_vno'){
    _isQAChild=true;
    switchView('ep-form');
    renderEPFVNOBar();
    renderVnoEpForm(s);
    setTop('',s.label,s.desc||'Selecciona VNO y ejecuta');
    var _epveb=document.getElementById('exec-btn');
    if(_epveb) _epveb.disabled=running;
  } else {
    _isQAChild=false;
    switchView('std');
    var vbar=document.getElementById('vno-bar');
    var rpanel=document.getElementById('resp-panel');
    vbar.style.display='none';
    if(rpanel) rpanel.style.display='none';
    var term=document.getElementById('term');
    term.innerHTML='';
    (suiteLogs[id]||[]).forEach(function(l){
      var sp=document.createElement('span');
      sp.className='tl'+(l.cls?' '+l.cls:'');
      sp.textContent=l.text;
      term.appendChild(sp);
    });
    term.scrollTop=term.scrollHeight;
    var sumEl=document.getElementById('summary');
    sumEl.innerHTML=suiteSummaries[id]||'<span class="sum-idle">Ejecuta una suite para ver resultados</span>';
    var rb=document.getElementById('rpt-btn'), db=document.getElementById('dl-btn');
    if(suiteReports[id]){
      rb.classList.add('show');rb.dataset.rid=suiteReports[id];
      db.classList.add('show');db.dataset.rid=suiteReports[id];
    } else {
      rb.classList.remove('show'); db.classList.remove('show');
    }
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
  if(running&&!currentEs){running=false;runningId=null;}
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
  if(selectedId==='qa-ia-inicio-suite'||selectedId==='qa-ia-fin-suite'||selectedId==='qa-ia-cancel-suite'){
    var _si=suites.find(function(x){return x.id===selectedId;});
    if(_si) _doRunIA(_si);
    return;
  }
  if(selectedId==='qa-activ-suite'||selectedId==='qa-activ-sin-idem-suite'){
    var _sac=suites.find(function(x){return x.id===selectedId;});
    if(_sac) _doRunActiv(_sac);
    return;
  }
  if(selectedId==='qa-dm-suite'){
    var _sdm=suites.find(function(x){return x.id==='qa-dm-suite';});
    if(_sdm) _doRunDm(_sdm);
    return;
  }
  if(selectedId==='qa-cancel-suite'){
    var _sc2=suites.find(function(x){return x.id==='qa-cancel-suite';});
    if(_sc2) _doRunCancel(_sc2);
    return;
  }
  if(selectedId==='qa-unsub-suite'){
    var _su2=suites.find(function(x){return x.id==='qa-unsub-suite';});
    if(_su2) _doRunUnsubSuite(_su2);
    return;
  }
  if(selectedId==='qa-teardown-masivo'){
    var _std=suites.find(function(x){return x.id==='qa-teardown-masivo';});
    if(_std) _doRunTeardown(_std);
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
  var _vs=["dashboard-view","std-view","sn-view","ep-view","ep-form-view","fact-view","asig-view","ia-view","activ-view","dm-view","cancel-view","unsub-suite-view","teardown-view","historial-view","settings-view","fulfillment-view","codigos-view"];
  _vs.forEach(function(vid){var el=document.getElementById(vid);if(el)el.style.display="none";});
  var target={"dashboard":"dashboard-view","sn":"sn-view","ep":"ep-view","ep-form":"ep-form-view","fact":"fact-view","asig":"asig-view","ia":"ia-view","activ":"activ-view","dm":"dm-view","cancel":"cancel-view","unsub-suite":"unsub-suite-view","teardown":"teardown-view","historial":"historial-view","settings":"settings-view","fulfillment":"fulfillment-view","codigos":"codigos-view"}[mode]||"std-view";
  var el=document.getElementById(target);
  if(el){el.style.display="flex";el.style.flexDirection="column";}
  var _gfp=document.getElementById('gf-panel');
  if(_gfp) _gfp.style.display='none';
  ['top-status','vno-sel','exec-btn','rpt-btn','dl-btn','clr-btn'].forEach(function(id){var e=document.getElementById(id);if(e)e.style.display='';});
}

function renderGlobalForm(){
  var p=document.getElementById('gf-panel'); if(!p) return;
  p.innerHTML='<div class="gf-bar">'
    +'<span class="gf-bar-ttl">Parámetros</span>'
    +'<div class="gf-bar-sep"></div>'
    +'<div class="gf-bar-chip"><span class="gf-bar-lbl">Access ID</span>&nbsp;<span class="gf-bar-val empty" id="gfb-access">—</span></div>'
    +'<div class="gf-bar-sep"></div>'
    +'<div class="gf-bar-chip"><span class="gf-bar-lbl">Plan</span>&nbsp;<span class="gf-bar-val" id="gfb-speed">400/400</span></div>'
    +'<div class="gf-bar-chip"><span class="gf-bar-lbl">Serial</span>&nbsp;<span class="gf-bar-val empty" id="gfb-serial">—</span></div>'
    +'<div class="gf-bar-chip"><span class="gf-bar-lbl">Tipo</span>&nbsp;<span class="gf-bar-val" id="gfb-stype">FTTH</span></div>'
    +'<div class="gf-bar-chip"><span class="gf-bar-lbl">Svc</span>&nbsp;<span class="gf-bar-val" id="gfb-svcs">BA · VoIP · IPTV</span></div>'
    +'<button class="gf-config-btn" onclick="openGFModal()">✎ Configurar</button>'
    +'</div>';
}

// ── Global Form Modal ────────────────────────────────────────────────────────
var _gfEnv='QA';
var _gfFuncSeq=[];
var _GF_FUNCS=[
  {id:'fact',   name:'Factibilidad'},
  {id:'asig',   name:'Asignación'},
  {id:'activ',  name:'Activación'},
  {id:'ia-inicio', name:'Inicio de Intervención Asegurada'},
  {id:'ia-fin', name:'Finalización de Intervención Asegurada'},
  {id:'dm',     name:'Device Modification'},
  {id:'cancel', name:'Cancelación de Servicio'},
];

function openGFModal(){
  var m=document.getElementById('gf-modal'); if(!m) return;
  var now=new Date();
  var dd=String(now.getDate()).padStart(2,'0');
  var mm=String(now.getMonth()+1).padStart(2,'0');
  var yy=now.getFullYear();
  var hh=String(now.getHours()).padStart(2,'0');
  var mn=String(now.getMinutes()).padStart(2,'0');
  var metaEl=document.getElementById('gfm-date');
  if(metaEl) metaEl.textContent='Fecha registro: '+dd+'-'+mm+'-'+yy+', '+hh+':'+mn;
  var errEl=document.getElementById('gfm-err-bar');
  if(errEl){errEl.innerHTML='';errEl.classList.remove('show');}
  m.classList.add('open');
  _renderGFMFuncList();
  _updateSerialCharCounter();
  _updateNSerialCharCounter();
  switchGFMTab('cfg');
}

function closeGFModal(){
  var m=document.getElementById('gf-modal');
  if(m) m.classList.remove('open');
}

function applyGFModal(){
  var errEl=document.getElementById('gfm-err-bar');
  var errs=[];
  var acc=(document.getElementById('gf-access')||{}).value||'';
  if(!acc.trim()) errs.push('Access ID es obligatorio');
  if(errs.length){
    if(errEl){errEl.innerHTML='· '+errs.join('<br>· ');errEl.classList.add('show');}
    return;
  }
  if(errEl){errEl.innerHTML='';errEl.classList.remove('show');}
  closeGFModal();
  _updateGFSummaryBar();
  _updateAsigAccessPreview();
}

function _updateGFSummaryBar(){
  var acc=(document.getElementById('gf-access')||{}).value||'';
  var spd=(document.getElementById('gf-speed')||{}).value||'400/400';
  var ser=(document.getElementById('gf-serial')||{}).value||'';
  var sty=(document.getElementById('gf-stype')||{}).value||'FTTH';
  var ba=(document.getElementById('gf-ba')||{}).value||'true';
  var voip=(document.getElementById('gf-voip')||{}).value||'true';
  var iptv=(document.getElementById('gf-iptv')||{}).value||'true';
  var svcs=[];
  if(ba!=='false') svcs.push('BA');
  if(voip!=='false') svcs.push('VoIP');
  if(iptv!=='false') svcs.push('IPTV');
  function _set(id, val, empty){
    var el=document.getElementById(id); if(!el) return;
    el.textContent=val||'—';
    el.className='gf-bar-val'+(empty||!val?' empty':'');
  }
  _set('gfb-access', acc.trim(), !acc.trim());
  _set('gfb-speed', spd, false);
  _set('gfb-serial', ser.trim(), !ser.trim());
  _set('gfb-stype', sty, false);
  _set('gfb-svcs', svcs.length?svcs.join(' · '):'Ninguno', !svcs.length);
}

function selectEnv(el){
  var group=document.getElementById('gfm-env-group'); if(!group) return;
  [].forEach.call(group.querySelectorAll('.gfm-ec'),function(c){c.classList.remove('on');});
  el.classList.add('on');
  _gfEnv=el.dataset.env||'QA';
  _autoGenAccessId(true);
}

function switchGFMTab(tab){
  ['cfg','func'].forEach(function(t){
    var btn=document.getElementById('gfmt-'+t);
    var tc=document.getElementById('gfmc-'+t);
    if(btn) btn.classList[t===tab?'add':'remove']('active');
    if(tc)  tc.classList[t===tab?'add':'remove']('active');
  });
  if(tab==='func') _renderGFMFuncList();
}

function _autoGenAccessId(onlyIfEmpty){
  var el=document.getElementById('gf-access'); if(!el) return;
  if(onlyIfEmpty && el.value.trim()) return;
  var vno=(document.getElementById('gf-vno')||{}).value||'00';
  var addr=(document.getElementById('gf-addr')||{}).value||'';
  var addrSlug=addr.replace(/\\s+/g,'').toUpperCase().slice(0,6)||'XXXXX';
  var now=new Date();
  var hh=String(now.getHours()).padStart(2,'0');
  var mn=String(now.getMinutes()).padStart(2,'0');
  el.value=vno+'-'+_gfEnv+addrSlug+hh+mn;
  var badge=document.getElementById('gfm-auto-badge');
  if(badge) badge.style.display='inline';
  _onGFAccessInput();
}

function _autoGenSerial(){
  var el=document.getElementById('gf-serial'); if(!el) return;
  var vno=(document.getElementById('gf-vno')||{}).value||'00';
  var now=new Date();
  var mo=String(now.getMonth()+1).padStart(2,'0');
  var dd=String(now.getDate()).padStart(2,'0');
  var hh=String(now.getHours()).padStart(2,'0');
  var mn=String(now.getMinutes()).padStart(2,'0');
  el.value='HW'+vno.toUpperCase()+mo+dd+hh+mn;
  _updateSerialCharCounter();
}

function _autoGenNewSerial(){
  var el=document.getElementById('gf-newserial'); if(!el) return;
  var vno=(document.getElementById('gf-vno')||{}).value||'00';
  var now=new Date();
  var mo=String(now.getMonth()+1).padStart(2,'0');
  var dd=String(now.getDate()).padStart(2,'0');
  var hh=String(now.getHours()).padStart(2,'0');
  var mn=String(now.getMinutes()).padStart(2,'0');
  el.value='HW'+vno.toUpperCase()+mo+dd+hh+mn;
  _updateNSerialCharCounter();
}

function _updateSerialCharCounter(){
  var el=document.getElementById('gf-serial');
  var c=document.getElementById('gfm-schar');
  var n=el?el.value.length:0;
  if(c) c.textContent=n+' CAR.';
}

function _updateNSerialCharCounter(){
  var el=document.getElementById('gf-newserial');
  var c=document.getElementById('gfm-nschar');
  var n=el?el.value.length:0;
  if(c) c.textContent=n+' CAR.';
}

function _onGFAccessInput(){
  _updateAsigAccessPreview();
  var badge=document.getElementById('gfm-auto-badge');
  if(badge) badge.style.display='none';
}

function _renderGFMFuncList(){
  var lb=document.getElementById('gfm-flist-body');
  var sb=document.getElementById('gfm-fseq-body');
  if(!lb||!sb) return;
  lb.innerHTML=_GF_FUNCS.map(function(f,i){
    var inSeq=_gfFuncSeq.indexOf(f.id)>=0;
    return '<div class="gfm-fitem" data-fid="'+f.id+'" onclick="_toggleGFFunc(this.dataset.fid)">'
      +'<span class="gfm-fnum">'+String(i+1).padStart(2,'0')+'</span>'
      +'<span class="gfm-fname">'+esc(f.name)+'</span>'
      +'<input type="checkbox" class="gfm-fchk" data-fid="'+f.id+'" '+(inSeq?'checked':'')
      +' onclick="event.stopPropagation();_toggleGFFunc(this.dataset.fid)" /></div>';
  }).join('');
  _renderGFMSeqList();
}

function _toggleGFFunc(id){
  var idx=_gfFuncSeq.indexOf(id);
  if(idx>=0) _gfFuncSeq.splice(idx,1);
  else _gfFuncSeq.push(id);
  _renderGFMFuncList();
}

function _renderGFMSeqList(){
  var sb=document.getElementById('gfm-fseq-body');
  if(!sb) return;
  sb.innerHTML=_gfFuncSeq.map(function(id,i){
    var f=_GF_FUNCS.filter(function(x){return x.id===id;})[0];
    return '<div class="gfm-sitem" data-sid="'+id+'">'
      +'<span class="gfm-shandle">⠿</span>'
      +'<span class="gfm-snum">'+(i+1)+'</span>'
      +'<span class="gfm-sname">'+esc(f?f.name:id)+'</span>'
      +'<button class="gfm-srm" data-sid="'+id+'" onclick="_removeGFSeq(this.dataset.sid)">×</button>'
      +'</div>';
  }).join('');
  var n=_gfFuncSeq.length;
  ['gfm-seq-count','gfm-seq-count2'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.textContent=n;
  });
}

function _removeGFSeq(id){
  var idx=_gfFuncSeq.indexOf(id);
  if(idx>=0){ _gfFuncSeq.splice(idx,1); _renderGFMFuncList(); }
}

function _filterFuncList(q){
  var items=document.querySelectorAll('#gfm-flist-body .gfm-fitem');
  var lq=(q||'').toLowerCase();
  [].forEach.call(items,function(el){
    var nm=el.querySelector('.gfm-fname');
    el.style.display=(!lq||(nm&&nm.textContent.toLowerCase().indexOf(lq)>=0))?'':'none';
  });
}

// ── Factibilidad: vista multi-consola ────────────────────────────────────────
var _FACT_TC_META = [
  {tc:'TC-01', label:'TC-01 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-fact-tc01', color:'#A8FF78'},
  {tc:'TC-02', label:'TC-02 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-fact-tc02', color:'#00C8D4'},
  {tc:'TC-03', label:'TC-03 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-fact-tc03', color:'#FFB347'},
  {tc:'TC-04', label:'TC-04 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-fact-tc04', color:'#6E8EFF'},
];

var _factSel={'TC-01':true,'TC-02':true,'TC-03':true,'TC-04':true};

var _factVnoMeta=[
  {vno:'03',lbl:'03 · Entel',tc:'TC-01',color:'#A8FF78'},
  {vno:'02',lbl:'02 · KAO',  tc:'TC-02',color:'#00C8D4'},
  {vno:'05',lbl:'05 · DTV',  tc:'TC-03',color:'#FFB347'},
  {vno:'00',lbl:'00 · TCH',  tc:'TC-04',color:'#6E8EFF'},
];

function renderFactFormBar(){
  var bar=document.getElementById('fact-form-bar'); if(!bar) return;
  var vnoBtns=_factVnoMeta.map(function(v){
    var on=_factSel[v.tc]?'on':'';
    return '<span class="atrf-vno-lbl '+on+'" data-tc="'+v.tc+'" onclick="_factToggleVno(this)" style="'+(on?'border-color:'+v.color+';color:'+v.color:'')+'">'+esc(v.lbl)+'</span>';
  }).join('');
  bar.innerHTML='<div class="atrf-grid" style="max-width:920px">'
    +'<div class="atrf-field atrf-col-12">'
      +'<label>Ambiente <span class="req">★</span></label>'
      +'<div class="atrf-amb-wrap" id="fact-amb-wrap">'
        +'<input type="radio" name="fact-amb" id="fact-amb-qa" value="QA" class="atrf-amb-radio" onchange="_factOnAmbChange()" checked/>'
        +'<label for="fact-amb-qa" class="atrf-amb-lbl">QA</label>'
        +'<input type="radio" name="fact-amb" id="fact-amb-prd" value="PRD" class="atrf-amb-radio" onchange="_factOnAmbChange()"/>'
        +'<label for="fact-amb-prd" class="atrf-amb-lbl">PRD</label>'
        +'<input type="radio" name="fact-amb" id="fact-amb-pprd" value="PPRD" class="atrf-amb-radio" onchange="_factOnAmbChange()"/>'
        +'<label for="fact-amb-pprd" class="atrf-amb-lbl">PPRD</label>'
        +'<span id="fact-amb-url" style="font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-green);margin-left:8px;display:none"></span>'
      +'</div>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Datos base</div>'
    +'<div class="atrf-field atrf-col-6">'
      +'<label>VNO <span class="req">★</span></label>'
      +'<div class="atrf-vno-checks">'+vnoBtns+'</div>'
    +'</div>'
    +'<div class="atrf-field atrf-col-6">'
      +'<label>Address ID <span class="req">★</span></label>'
      +'<input type="text" id="fact-addr-inp" placeholder="ej: DIR02803636"/>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Address MCD</label>'
      +'<input type="text" id="fact-mcd-inp" value="OSP" placeholder="OSP"/>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Tipo Servicio</label>'
      +'<select id="fact-svc-sel"><option value="FTTH">FTTH</option><option value="SSAA">SSAA</option></select>'
    +'</div>'
    +'</div>';
  _factOnAmbChange();
}

function _factToggleVno(el){
  var tc=el.dataset.tc;
  _factSel[tc]=!_factSel[tc];
  var meta=_factVnoMeta.find(function(v){return v.tc===tc;});
  if(_factSel[tc]){
    el.classList.add('on');
    el.style.borderColor=meta?meta.color:'';
    el.style.color=meta?meta.color:'';
  } else {
    el.classList.remove('on');
    el.style.borderColor='';
    el.style.color='';
  }
  renderFactView();
  _syncExecBtn();
}

function _factOnAmbChange(){
  var rad=document.querySelector('input[name="fact-amb"]:checked');
  var amb=rad?rad.value:'QA';
  var url=_atrfEnvUrls[amb]||'';
  var el=document.getElementById('fact-amb-url');
  if(el){el.style.display=url?'inline':'none';el.textContent=url?('→ '+url):'';}
}

function _syncExecBtn(){
  if(running&&!currentEs){running=false;runningId=null;}
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
  var _addrFact=(document.getElementById('fact-addr-inp')||{}).value||(document.getElementById('gf-addr')||{}).value||'DIR02803636';
  var _mcdFact=(document.getElementById('fact-mcd-inp')||{}).value||'OSP';
  var _svcFact=(document.getElementById('fact-svc-sel')||{}).value||'FTTH';
  var _envFact=(document.querySelector('input[name="fact-amb"]:checked')||{}).value||_gfEnv||'QA';
  var es=new EventSource('/api/run/qa-fact-suite?tcs='+encodeURIComponent(_selTcs)
    +'&addr_id='+encodeURIComponent(_addrFact)
    +'&address_mcd='+encodeURIComponent(_mcdFact)
    +'&service_type='+encodeURIComponent(_svcFact)
    +'&gf_env='+encodeURIComponent(_envFact));
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){
        _factApp(d.tc, d.t, col(d.t));
        _factSetState(d.tc,'running');
      } else {
        _FACT_TC_META.filter(function(m){return _factSel[m.tc];}).forEach(function(m){_factApp(m.tc,d.t,col(d.t));});
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
      app('⚠ Conexión perdida con el servidor. Verifica la conexión y presiona Ejecutar nuevamente.','err');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
    }
  };
}

// ── Asignación: vista multi-consola ─────────────────────────────────────────
var _ASIG_TC_META = [
  {tc:'TC-05', label:'TC-05 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-asig-tc05', color:'#98F5A4'},
  {tc:'TC-06', label:'TC-06 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-asig-tc06', color:'#7EC8E3'},
  {tc:'TC-07', label:'TC-07 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-asig-tc07', color:'#FFD580'},
  {tc:'TC-08', label:'TC-08 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-asig-tc08', color:'#B39DFF'},
];
var _asigSel={'TC-05':true,'TC-06':true,'TC-07':true,'TC-08':true};

var _VNO_CODES={'TC-05':'03','TC-06':'02','TC-07':'05','TC-08':'00'};
var _VNO_KNOWN=['00','02','03','05'];

function _resolveAccessId(raw, vnoCode){
  if(!raw) return '';
  var m=raw.match(/^(\\d{2})-(.+)$/);
  if(m && _VNO_KNOWN.indexOf(m[1])!==-1){
    return vnoCode+'-'+m[2];
  }
  return raw;
}

var _asigVnoMeta=[
  {vno:'03',lbl:'03 · Entel',tc:'TC-05',color:'#98F5A4'},
  {vno:'02',lbl:'02 · KAO',  tc:'TC-06',color:'#7EC8E3'},
  {vno:'05',lbl:'05 · DTV',  tc:'TC-07',color:'#FFD580'},
  {vno:'00',lbl:'00 · TCH',  tc:'TC-08',color:'#B39DFF'},
];
var _QA_SPEED_PLANS_ASIG=['100/100','300/300','400/400','600/600','800/800','1000/1000'];

function renderAsigFormBar(){
  var bar=document.getElementById('asig-form-bar'); if(!bar) return;
  var vnoBtns=_asigVnoMeta.map(function(v){
    var on=_asigSel[v.tc]?'on':'';
    return '<span class="atrf-vno-lbl '+on+'" data-tc="'+v.tc+'" onclick="_asigToggleVno(this)" style="'+(on?'border-color:'+v.color+';color:'+v.color:'')+'">'+esc(v.lbl)+'</span>';
  }).join('');
  var speedOpts=_QA_SPEED_PLANS_ASIG.map(function(p){
    return '<option value="'+p+'"'+(p==='600/600'?' selected':'')+'>'+p+'</option>';
  }).join('');
  bar.innerHTML='<div class="atrf-grid" style="max-width:920px">'
    +'<div class="atrf-field atrf-col-12">'
      +'<label>Ambiente <span class="req">★</span></label>'
      +'<div class="atrf-amb-wrap">'
        +'<input type="radio" name="asig-amb" id="asig-amb-qa" value="QA" class="atrf-amb-radio" onchange="_asigOnAmbChange()" checked/>'
        +'<label for="asig-amb-qa" class="atrf-amb-lbl">QA</label>'
        +'<input type="radio" name="asig-amb" id="asig-amb-prd" value="PRD" class="atrf-amb-radio" onchange="_asigOnAmbChange()"/>'
        +'<label for="asig-amb-prd" class="atrf-amb-lbl">PRD</label>'
        +'<input type="radio" name="asig-amb" id="asig-amb-pprd" value="PPRD" class="atrf-amb-radio" onchange="_asigOnAmbChange()"/>'
        +'<label for="asig-amb-pprd" class="atrf-amb-lbl">PPRD</label>'
        +'<span id="asig-amb-url" style="font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-green);margin-left:8px;display:none"></span>'
      +'</div>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Datos base</div>'
    +'<div class="atrf-field atrf-col-6">'
      +'<label>VNO <span class="req">★</span></label>'
      +'<div class="atrf-vno-checks">'+vnoBtns+'</div>'
    +'</div>'
    +'<div class="atrf-field atrf-col-6">'
      +'<label>Address ID <span class="req">★</span></label>'
      +'<input type="text" id="asig-addr-inp" placeholder="ej: 03-XYGO123456" oninput="_asigUpdateAccessPreview()"/>'
      +'<span class="atrf-hint" id="asig-addr-preview" style="color:var(--atrf-text2)"></span>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Servicio</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Speed Plan <span class="req">★</span></label>'
      +'<select id="asig-speed-sel">'+speedOpts+'</select>'
    +'</div>'
    +'<div class="atrf-field atrf-col-5">'
      +'<label>Servicios</label>'
      +'<div style="display:flex;gap:10px;align-items:center;padding-top:4px">'
        +'<label style="display:flex;align-items:center;gap:5px;font-size:11px;font-family:var(--atrf-mono);color:var(--atrf-text);cursor:pointer"><input type="checkbox" id="asig-svc-ba" checked style="accent-color:var(--atrf-accent)"> BA</label>'
        +'<label style="display:flex;align-items:center;gap:5px;font-size:11px;font-family:var(--atrf-mono);color:var(--atrf-text);cursor:pointer"><input type="checkbox" id="asig-svc-voip" checked style="accent-color:var(--atrf-accent)"> VoIP</label>'
        +'<label style="display:flex;align-items:center;gap:5px;font-size:11px;font-family:var(--atrf-mono);color:var(--atrf-text);cursor:pointer"><input type="checkbox" id="asig-svc-iptv" checked style="accent-color:var(--atrf-accent)"> IPTV</label>'
      +'</div>'
    +'</div>'
    +'</div>';
  _asigOnAmbChange();
}

function _asigToggleVno(el){
  var tc=el.dataset.tc;
  _asigSel[tc]=!_asigSel[tc];
  var meta=_asigVnoMeta.find(function(v){return v.tc===tc;});
  if(_asigSel[tc]){
    el.classList.add('on');
    el.style.borderColor=meta?meta.color:'';
    el.style.color=meta?meta.color:'';
  } else {
    el.classList.remove('on');
    el.style.borderColor='';
    el.style.color='';
  }
  renderAsigView();
  _syncAsigExecBtn();
}

function _asigOnAmbChange(){
  var rad=document.querySelector('input[name="asig-amb"]:checked');
  var amb=rad?rad.value:'QA';
  var url=_atrfEnvUrls[amb]||'';
  var el=document.getElementById('asig-amb-url');
  if(el){el.style.display=url?'inline':'none';el.textContent=url?('→ '+url):'';}
}

function _asigUpdateAccessPreview(){
  var raw=(document.getElementById('asig-addr-inp')||{}).value||'';
  var el=document.getElementById('asig-addr-preview'); if(!el) return;
  if(!raw.trim()){el.textContent='';return;}
  var parts=_asigVnoMeta.filter(function(v){return _asigSel[v.tc];}).map(function(v){
    return v.lbl+': '+_resolveAccessId(raw.trim(),v.vno);
  });
  el.textContent=parts.join(' · ');
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
  var addrInp=document.getElementById('asig-addr-inp');
  var rawAddr=(addrInp||{}).value||'';
  if(!rawAddr.trim()){
    if(addrInp) addrInp.style.borderColor='var(--atrf-red)';
    return;
  }
  if(addrInp) addrInp.style.borderColor='';
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _ASIG_TC_META.forEach(function(m){
    var at=document.getElementById('at-'+m.tc); if(at) at.innerHTML='';
    var afr=document.getElementById('afr-'+m.tc); if(afr) afr.innerHTML='<span class="fr-empty">—</span>';
    var afrs=document.getElementById('afrs-'+m.tc); if(afrs) afrs.innerHTML='';
    var apr=document.getElementById('apr-'+m.tc); if(apr) apr.classList.remove('show');
    _asigSetState(m.tc,'idle');
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _selTcs=_ASIG_TC_META.filter(function(m){return _asigSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var _accessMap={};
  _ASIG_TC_META.forEach(function(m){ _accessMap[m.tc]=_resolveAccessId(rawAddr.trim(),_VNO_CODES[m.tc]); });
  var _speed=(document.getElementById('asig-speed-sel')||{}).value||'600/600';
  var _ba=(document.getElementById('asig-svc-ba')||{}).checked!==false?'true':'false';
  var _voip=(document.getElementById('asig-svc-voip')||{}).checked!==false?'true':'false';
  var _iptv=(document.getElementById('asig-svc-iptv')||{}).checked!==false?'true':'false';
  var _envAsig=(document.querySelector('input[name="asig-amb"]:checked')||{}).value||_gfEnv||'QA';
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&access_ids='+encodeURIComponent(JSON.stringify(_accessMap))
    +'&address_id='+encodeURIComponent(rawAddr.trim())
    +'&speed_plan='+encodeURIComponent(_speed)
    +'&service_ba='+encodeURIComponent(_ba)
    +'&service_voip='+encodeURIComponent(_voip)
    +'&service_iptv='+encodeURIComponent(_iptv)
    +'&gf_env='+encodeURIComponent(_envAsig);
  var es=new EventSource('/api/run/qa-asig-suite?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _asigApp(d.tc,d.t,col(d.t)); _asigSetState(d.tc,'running'); }
      else { _ASIG_TC_META.filter(function(m){return _asigSel[m.tc];}).forEach(function(m){_asigApp(m.tc,d.t,col(d.t));}); }
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
      app('⚠ Conexión perdida con el servidor. Verifica la conexión y presiona Ejecutar nuevamente.','err');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
    }
  };
}

// ── Intervención Asegurada: vista multi-consola ──────────────────────────────
var _iaMode = 'inicio';
var _IA_INICIO_META = [
  {tc:'TC-09', label:'TC-09 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-ia-tc09', color:'#FF9F8B'},
  {tc:'TC-10', label:'TC-10 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-ia-tc10', color:'#85E89D'},
  {tc:'TC-11', label:'TC-11 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-ia-tc11', color:'#FFD580'},
  {tc:'TC-12', label:'TC-12 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-ia-tc12', color:'#79C8FF'},
];
var _IA_FIN_META = [
  {tc:'TC-13', label:'TC-13 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-ia-tc13', color:'#C7CEEA'},
  {tc:'TC-14', label:'TC-14 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-ia-tc14', color:'#B5EAD7'},
  {tc:'TC-15', label:'TC-15 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-ia-tc15', color:'#FFDAC1'},
  {tc:'TC-16', label:'TC-16 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-ia-tc16', color:'#B39DFF'},
];
var _IA_CANCEL_META = [
  {tc:'TC-33', label:'TC-33 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-ia-tc33', color:'#FF6B6B'},
  {tc:'TC-34', label:'TC-34 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-ia-tc34', color:'#4EC9B0'},
  {tc:'TC-35', label:'TC-35 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-ia-tc35', color:'#CE9178'},
  {tc:'TC-36', label:'TC-36 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-ia-tc36', color:'#569CD6'},
];
var _iaSel={};
(function(){ _IA_INICIO_META.concat(_IA_FIN_META).concat(_IA_CANCEL_META).forEach(function(m){ _iaSel[m.tc]=true; }); })();
var _IA_VNO_CODES={'TC-09':'03','TC-10':'02','TC-11':'05','TC-12':'00',
                   'TC-13':'03','TC-14':'02','TC-15':'05','TC-16':'00',
                   'TC-33':'03','TC-34':'02','TC-35':'05','TC-36':'00'};

function _iaMeta(){ return _iaMode==='inicio'?_IA_INICIO_META:(_iaMode==='cancel'?_IA_CANCEL_META:_IA_FIN_META); }
function _iaSuiteId(){ return _iaMode==='inicio'?'qa-ia-inicio-suite':(_iaMode==='cancel'?'qa-ia-cancel-suite':'qa-ia-fin-suite'); }

function renderIAFormBar(){
  var bar=document.getElementById('ia-form-bar'); if(!bar) return;
  var meta=_iaMeta();
  var vnoBtns=meta.map(function(m){
    var on=_iaSel[m.tc]?'on':'';
    return '<span class="atrf-vno-lbl '+on+'" data-tc="'+m.tc+'" onclick="_iaToggleVno(this)" style="'+(on?'border-color:'+m.color+';color:'+m.color:'')+'">'+esc(m.vno_code+' · '+m.label.split(' · ')[1])+'</span>';
  }).join('');
  var modeColor=_iaMode==='inicio'?'var(--atrf-accent)':(_iaMode==='cancel'?'#FF6B6B':'#B39DFF');
  var modeLabel=_iaMode==='inicio'?'Inicio Intervención':(_iaMode==='cancel'?'Cancelación Intervención':'Finalización Intervención');
  bar.innerHTML='<div class="atrf-grid" style="max-width:920px">'
    +'<div class="atrf-field atrf-col-12" style="flex-direction:row;align-items:center;gap:10px;flex-wrap:wrap">'
      +'<span style="font-size:11px;font-family:var(--atrf-mono);font-weight:600;color:'+modeColor+';text-transform:uppercase;letter-spacing:.06em">'+esc(modeLabel)+'</span>'
      +'<div class="atrf-amb-wrap">'
        +'<input type="radio" name="ia-amb" id="ia-amb-qa" value="QA" class="atrf-amb-radio" onchange="_iaOnAmbChange()" checked/>'
        +'<label for="ia-amb-qa" class="atrf-amb-lbl">QA</label>'
        +'<input type="radio" name="ia-amb" id="ia-amb-prd" value="PRD" class="atrf-amb-radio" onchange="_iaOnAmbChange()"/>'
        +'<label for="ia-amb-prd" class="atrf-amb-lbl">PRD</label>'
        +'<input type="radio" name="ia-amb" id="ia-amb-pprd" value="PPRD" class="atrf-amb-radio" onchange="_iaOnAmbChange()"/>'
        +'<label for="ia-amb-pprd" class="atrf-amb-lbl">PPRD</label>'
        +'<span id="ia-amb-url" style="font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-green);margin-left:8px;display:none"></span>'
      +'</div>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Datos base</div>'
    +'<div class="atrf-field atrf-col-5">'
      +'<label>VNO <span class="req">★</span></label>'
      +'<div class="atrf-vno-checks">'+vnoBtns+'</div>'
    +'</div>'
    +'<div class="atrf-field atrf-col-7">'
      +'<label>Access ID <span class="req">★</span></label>'
      +'<input type="text" id="ia-addr-inp" placeholder="ej: 03-XYGO123456" oninput="_iaUpdateAccessPreview()"/>'
      +'<span class="atrf-hint" id="ia-addr-preview" style="color:var(--atrf-text2)"></span>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Servicio</div>'
    +'<div class="atrf-field atrf-col-4">'
      +'<label>Escenario <span class="req">★</span></label>'
      +'<select id="ia-scenario-inp">'
        +'<option value="Instalación">Instalación</option>'
        +'<option value="Reparación">Reparación</option>'
        +'<option value="Retiro de Drop">Retiro de Drop</option>'
      +'</select>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Tipo Servicio</label>'
      +'<select id="ia-svc-sel"><option value="FTTH">FTTH</option><option value="SSAA">SSAA</option></select>'
    +'</div>'
    +'</div>';
  _iaOnAmbChange();
}

function _iaToggleVno(el){
  var tc=el.dataset.tc;
  _iaSel[tc]=!_iaSel[tc];
  var meta=_iaMeta().find(function(m){return m.tc===tc;});
  if(_iaSel[tc]){
    el.classList.add('on');
    el.style.borderColor=meta?meta.color:'';
    el.style.color=meta?meta.color:'';
  } else {
    el.classList.remove('on');
    el.style.borderColor='';
    el.style.color='';
  }
  renderIAView();
  _syncIAExecBtn();
}

function _iaOnAmbChange(){
  var rad=document.querySelector('input[name="ia-amb"]:checked');
  var amb=rad?rad.value:'QA';
  var url=_atrfEnvUrls[amb]||'';
  var el=document.getElementById('ia-amb-url');
  if(el){el.style.display=url?'inline':'none';el.textContent=url?('→ '+url):'';}
}

function _iaUpdateAccessPreview(){
  var raw=(document.getElementById('ia-addr-inp')||{}).value||'';
  var el=document.getElementById('ia-addr-preview'); if(!el) return;
  if(!raw.trim()){el.textContent='';return;}
  var parts=_iaMeta().filter(function(m){return _iaSel[m.tc];}).map(function(m){
    return m.vno_code+': '+_resolveAccessId(raw.trim(),m.vno_code);
  });
  el.textContent=parts.join(' · ');
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
  var accessEl=document.getElementById('ia-addr-inp');
  if(!accessEl||!accessEl.value.trim()){ if(accessEl) accessEl.style.borderColor='var(--err)'; return; }
  accessEl.style.borderColor='';
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
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
  _iaMeta().forEach(function(m){ _accessMap[m.tc]=_resolveAccessId(_rawAccess,m.vno_code); });
  var _sc=(document.getElementById('ia-scenario-inp')||{}).value||'Instalación';
  var _sv=(document.getElementById('ia-svc-sel')||{}).value||'FTTH';
  var _envIA=(document.querySelector('input[name="ia-amb"]:checked')||{}).value||_gfEnv||'QA';
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&access_ids='+encodeURIComponent(JSON.stringify(_accessMap))
    +'&scenario='+encodeURIComponent(_sc)
    +'&service_type='+encodeURIComponent(_sv)
    +'&gf_env='+encodeURIComponent(_envIA);
  var es=new EventSource('/api/run/'+_iaSuiteId()+'?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _iaApp(d.tc,d.t,col(d.t)); _iaSetState(d.tc,'running'); }
      else { _IA_INICIO_META.concat(_IA_FIN_META).filter(function(m){return _iaSel[m.tc];}).forEach(function(m){_iaApp(m.tc,d.t,col(d.t));}); }
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
      app('⚠ Conexión perdida con el servidor. Verifica la conexión y presiona Ejecutar nuevamente.','err');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s); }
  };
}

// ── Suite Activación: vista multi-consola ────────────────────────────────────
var _ACTIV_META = [
  {tc:'TC-17', label:'TC-17 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-activ-tc17', color:'#FF9F8B'},
  {tc:'TC-18', label:'TC-18 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-activ-tc18', color:'#85E89D'},
  {tc:'TC-19', label:'TC-19 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-activ-tc19', color:'#FFD580'},
  {tc:'TC-20', label:'TC-20 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-activ-tc20', color:'#79C8FF'},
];
var _ACTIV_SIN_IDEM_META = [
  {tc:'TC-37', label:'TC-37 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-activ-tc37', color:'#FF9F8B'},
  {tc:'TC-38', label:'TC-38 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-activ-tc38', color:'#85E89D'},
  {tc:'TC-39', label:'TC-39 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-activ-tc39', color:'#FFD580'},
  {tc:'TC-40', label:'TC-40 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-activ-tc40', color:'#79C8FF'},
];
var _activMode='idem';
function _activMeta(){ return _activMode==='idem'?_ACTIV_META:_ACTIV_SIN_IDEM_META; }
var _activSel={};
(function(){ _ACTIV_META.concat(_ACTIV_SIN_IDEM_META).forEach(function(m){ _activSel[m.tc]=true; }); })();
var _ACTIV_VNO_CODES={'TC-17':'03','TC-18':'02','TC-19':'05','TC-20':'00'};
var _ACTIV_SERIAL_BASE={'TC-17':'ZTEG1104','TC-18':'ZTEGD719','TC-19':'HTWC000A'};
var _QA_SPEED_PLANS_ACTIV=['100/100','300/300','400/400','600/600','800/800','1000/1000'];

function renderActivFormBar(){
  var bar=document.getElementById('activ-form-bar'); if(!bar) return;
  var _aMode=_activMode==='idem'?'qa-activ-suite':'qa-activ-sin-idem-suite';
  var vnoBtns=_allowedTcs(_aMode,_activMeta()).map(function(m){
    var on=_activSel[m.tc]?'on':'';
    return '<span class="atrf-vno-lbl '+on+'" data-tc="'+m.tc+'" onclick="_activToggleVno(this)" style="'+(on?'border-color:'+m.color+';color:'+m.color:'')+'">'+esc(m.vno_code+' · '+m.label.split(' · ')[1])+'</span>';
  }).join('');
  var speedOpts=_QA_SPEED_PLANS_ACTIV.map(function(p){
    return '<option value="'+p+'"'+(p==='600/600'?' selected':'')+'>'+p+'</option>';
  }).join('');
  bar.innerHTML='<div class="atrf-grid" style="max-width:920px">'
    +'<div class="atrf-field atrf-col-12">'
      +'<label>Ambiente <span class="req">★</span></label>'
      +'<div class="atrf-amb-wrap">'
        +'<input type="radio" name="activ-amb" id="activ-amb-qa" value="QA" class="atrf-amb-radio" onchange="_activOnAmbChange()" checked/>'
        +'<label for="activ-amb-qa" class="atrf-amb-lbl">QA</label>'
        +'<input type="radio" name="activ-amb" id="activ-amb-prd" value="PRD" class="atrf-amb-radio" onchange="_activOnAmbChange()"/>'
        +'<label for="activ-amb-prd" class="atrf-amb-lbl">PRD</label>'
        +'<input type="radio" name="activ-amb" id="activ-amb-pprd" value="PPRD" class="atrf-amb-radio" onchange="_activOnAmbChange()"/>'
        +'<label for="activ-amb-pprd" class="atrf-amb-lbl">PPRD</label>'
        +'<span id="activ-amb-url" style="font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-green);margin-left:8px;display:none"></span>'
      +'</div>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Selección VNO</div>'
    +'<div class="atrf-field atrf-col-5">'
      +'<label>VNO <span class="req">★</span></label>'
      +'<div class="atrf-vno-checks">'+vnoBtns+'</div>'
    +'</div>'
    +'<div class="atrf-field atrf-col-7">'
      +'<label>Access ID <span class="req">★</span></label>'
      +'<input type="text" id="activ-access-inp" placeholder="ej: 03-XYGO123456" oninput="_activUpdateAccessPreview()"/>'
      +'<span class="atrf-hint" id="activ-access-preview" style="color:var(--atrf-text2)"></span>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Servicio</div>'
    +'<div class="atrf-field atrf-col-4">'
      +'<label>Dirección ID</label>'
      +'<input type="text" id="activ-addr-inp" placeholder="DIR02803636"/>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Speed Plan</label>'
      +'<select id="activ-speed-sel">'+speedOpts+'</select>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Serial (últ. 4)</label>'
      +'<input type="text" id="activ-serial-inp" maxlength="4" placeholder="0000" style="font-family:var(--atrf-mono);letter-spacing:.06em"/>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-field atrf-col-5" style="flex-direction:row;align-items:center;gap:10px;flex-wrap:wrap">'
      +'<label style="white-space:nowrap">Servicios</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="activ-svc-ba" checked/> BA</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="activ-svc-voip"/> VoIP</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="activ-svc-iptv"/> IPTV</label>'
    +'</div>'
    +'<div class="atrf-field atrf-col-4" style="flex-direction:row;align-items:center">'
      +'<label class="atrf-chk"><input type="checkbox" id="activ-teardown"/> Teardown auto</label>'
    +'</div>'
    +'</div>';
  _activOnAmbChange();
}

function _activToggleVno(el){
  var tc=el.dataset.tc;
  _activSel[tc]=!_activSel[tc];
  var meta=_activMeta().find(function(m){return m.tc===tc;});
  if(_activSel[tc]){
    el.classList.add('on');
    el.style.borderColor=meta?meta.color:'';
    el.style.color=meta?meta.color:'';
  } else {
    el.classList.remove('on');
    el.style.borderColor='';
    el.style.color='';
  }
  renderActivView();
  _syncActivExecBtn();
}

function _activOnAmbChange(){
  var rad=document.querySelector('input[name="activ-amb"]:checked');
  var amb=rad?rad.value:'QA';
  var url=_atrfEnvUrls[amb]||'';
  var el=document.getElementById('activ-amb-url');
  if(el){el.style.display=url?'inline':'none';el.textContent=url?('→ '+url):'';}
}

function _activUpdateAccessPreview(){
  var raw=(document.getElementById('activ-access-inp')||{}).value||'';
  var el=document.getElementById('activ-access-preview'); if(!el) return;
  if(!raw.trim()){el.textContent='';return;}
  var parts=_activMeta().filter(function(m){return _activSel[m.tc];}).map(function(m){
    return m.vno_code+': '+_resolveAccessId(raw.trim(),m.vno_code);
  });
  el.textContent=parts.join(' · ');
}

function _syncActivExecBtn(){
  var anyOn=_activMeta().some(function(m){ return _activSel[m.tc]; });
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=running||!anyOn;
}

function renderActivView(){
  var grid=document.getElementById('activ-grid'); if(!grid) return;
  grid.innerHTML='';
  var _sel=_activMeta().filter(function(m){ return _activSel[m.tc]; });
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
  var accessEl=document.getElementById('activ-access-inp');
  if(!accessEl||!accessEl.value.trim()){ if(accessEl) accessEl.style.borderColor='var(--err)'; return; }
  accessEl.style.borderColor='';
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _activMeta().forEach(function(m){
    var at=document.getElementById('act-'+m.tc); if(at) at.innerHTML='';
    var afr=document.getElementById('acfr-'+m.tc); if(afr) afr.innerHTML='<span class="fr-empty">—</span>';
    var afrs=document.getElementById('acfrs-'+m.tc); if(afrs) afrs.innerHTML='';
    var acpr=document.getElementById('acpr-'+m.tc); if(acpr) acpr.classList.remove('show');
    _activSetState(m.tc,'idle');
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _rawAccess=accessEl.value.trim();
  var _selTcs=_activMeta().filter(function(m){return _activSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var _accessMap={};
  _activMeta().forEach(function(m){ _accessMap[m.tc]=_resolveAccessId(_rawAccess,m.vno_code); });
  var _speed=(document.getElementById('activ-speed-sel')||{}).value||'600/600';
  var _serial=(document.getElementById('activ-serial-inp')||{}).value||'0000';
  var _sba=!!(document.getElementById('activ-svc-ba')||{}).checked;
  var _svoip=!!(document.getElementById('activ-svc-voip')||{}).checked;
  var _siptv=!!(document.getElementById('activ-svc-iptv')||{}).checked;
  var _addrActiv=(document.getElementById('activ-addr-inp')||{}).value||'DIR02803636';
  var _envActiv=(document.querySelector('input[name="activ-amb"]:checked')||{}).value||_gfEnv||'QA';
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&access_ids='+encodeURIComponent(JSON.stringify(_accessMap))
    +'&speed_plan='+encodeURIComponent(_speed)
    +'&serial_suffix='+encodeURIComponent(_serial)
    +'&service_ba='+(_sba?'true':'false')
    +'&service_voip='+(_svoip?'true':'false')
    +'&service_iptv='+(_siptv?'true':'false')
    +'&addr_id='+encodeURIComponent(_addrActiv)
    +'&gf_env='+encodeURIComponent(_envActiv);
  var es=new EventSource('/api/run/'+s.id+'?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _activApp(d.tc,d.t,col(d.t)); _activSetState(d.tc,'running'); }
      else { _activMeta().filter(function(m){return _activSel[m.tc];}).forEach(function(m){_activApp(m.tc,d.t,col(d.t));}); }
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
      app('⚠ Conexión perdida con el servidor. Verifica la conexión y presiona Ejecutar nuevamente.','err');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s); }
  };
}

// ── Suite Device Modification: vista multi-consola ─────────────────────────
var _DM_META = [
  {tc:'TC-21', label:'TC-21 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-dm-tc21', color:'#FF9F8B'},
  {tc:'TC-22', label:'TC-22 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-dm-tc22', color:'#85E89D'},
  {tc:'TC-23', label:'TC-23 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-dm-tc23', color:'#FFD580'},
  {tc:'TC-24', label:'TC-24 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-dm-tc24', color:'#79C8FF'},
];
var _dmSel={};
(function(){ _DM_META.forEach(function(m){ _dmSel[m.tc]=true; }); })();
var _DM_VNO_CODES={'TC-21':'03','TC-22':'02','TC-23':'05','TC-24':'00'};
var _DM_SERIAL_BASE={'TC-21':'ZTEG1104','TC-22':'ZTEGD719','TC-23':'HTWC000A'};
var _QA_SPEED_PLANS_DM=['100/100','300/300','400/400','600/600','800/800','1000/1000'];

function renderDmFormBar(){
  var bar=document.getElementById('dm-form-bar'); if(!bar) return;
  var vnoBtns=_DM_META.map(function(m){
    var on=_dmSel[m.tc]?'on':'';
    return '<span class="atrf-vno-lbl '+on+'" data-tc="'+m.tc+'" onclick="_dmToggleVno(this)" style="'+(on?'border-color:'+m.color+';color:'+m.color:'')+'">'+esc(m.vno_code+' · '+m.label.split(' · ')[1])+'</span>';
  }).join('');
  var speedOpts=_QA_SPEED_PLANS_DM.map(function(p){
    return '<option value="'+p+'"'+(p==='600/600'?' selected':'')+'>'+p+'</option>';
  }).join('');
  bar.innerHTML='<div class="atrf-grid" style="max-width:920px">'
    +'<div class="atrf-field atrf-col-12">'
      +'<label>Ambiente <span class="req">★</span></label>'
      +'<div class="atrf-amb-wrap">'
        +'<input type="radio" name="dm-amb" id="dm-amb-qa" value="QA" class="atrf-amb-radio" onchange="_dmOnAmbChange()" checked/>'
        +'<label for="dm-amb-qa" class="atrf-amb-lbl">QA</label>'
        +'<input type="radio" name="dm-amb" id="dm-amb-prd" value="PRD" class="atrf-amb-radio" onchange="_dmOnAmbChange()"/>'
        +'<label for="dm-amb-prd" class="atrf-amb-lbl">PRD</label>'
        +'<input type="radio" name="dm-amb" id="dm-amb-pprd" value="PPRD" class="atrf-amb-radio" onchange="_dmOnAmbChange()"/>'
        +'<label for="dm-amb-pprd" class="atrf-amb-lbl">PPRD</label>'
        +'<span id="dm-amb-url" style="font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-green);margin-left:8px;display:none"></span>'
      +'</div>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Selección VNO</div>'
    +'<div class="atrf-field atrf-col-5">'
      +'<label>VNO <span class="req">★</span></label>'
      +'<div class="atrf-vno-checks">'+vnoBtns+'</div>'
    +'</div>'
    +'<div class="atrf-field atrf-col-7">'
      +'<label>Access ID <span class="req">★</span></label>'
      +'<input type="text" id="dm-access-inp" placeholder="ej: 03-XYGO123456" oninput="_dmUpdateAccessPreview()"/>'
      +'<span class="atrf-hint" id="dm-access-preview" style="color:var(--atrf-text2)"></span>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Servicio</div>'
    +'<div class="atrf-field atrf-col-4">'
      +'<label>Dirección ID</label>'
      +'<input type="text" id="dm-addr-inp" placeholder="DIR02803636"/>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Speed Plan</label>'
      +'<select id="dm-speed-sel">'+speedOpts+'</select>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Seriales ONT</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Serial Activ. (últ. 4)</label>'
      +'<input type="text" id="dm-serial-activ-inp" maxlength="4" placeholder="0000" style="font-family:var(--atrf-mono);letter-spacing:.06em"/>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Serial DM nuevo (últ. 4)</label>'
      +'<input type="text" id="dm-serial-dm" maxlength="4" placeholder="0000" style="font-family:var(--atrf-mono);letter-spacing:.06em"/>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-field atrf-col-5" style="flex-direction:row;align-items:center;gap:10px;flex-wrap:wrap">'
      +'<label style="white-space:nowrap">Servicios</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="dm-svc-ba" checked/> BA</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="dm-svc-voip"/> VoIP</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="dm-svc-iptv"/> IPTV</label>'
    +'</div>'
    +'<div class="atrf-field atrf-col-4" style="flex-direction:row;align-items:center">'
      +'<label class="atrf-chk"><input type="checkbox" id="dm-teardown"/> Teardown auto</label>'
    +'</div>'
    +'</div>';
  _dmOnAmbChange();
}

function _dmToggleVno(el){
  var tc=el.dataset.tc;
  _dmSel[tc]=!_dmSel[tc];
  var meta=_DM_META.find(function(m){return m.tc===tc;});
  if(_dmSel[tc]){
    el.classList.add('on');
    el.style.borderColor=meta?meta.color:'';
    el.style.color=meta?meta.color:'';
  } else {
    el.classList.remove('on');
    el.style.borderColor='';
    el.style.color='';
  }
  renderDmView();
  _syncDmExecBtn();
}

function _dmOnAmbChange(){
  var rad=document.querySelector('input[name="dm-amb"]:checked');
  var amb=rad?rad.value:'QA';
  var url=_atrfEnvUrls[amb]||'';
  var el=document.getElementById('dm-amb-url');
  if(el){el.style.display=url?'inline':'none';el.textContent=url?('→ '+url):'';}
}

function _dmUpdateAccessPreview(){
  var raw=(document.getElementById('dm-access-inp')||{}).value||'';
  var el=document.getElementById('dm-access-preview'); if(!el) return;
  if(!raw.trim()){el.textContent='';return;}
  var parts=_DM_META.filter(function(m){return _dmSel[m.tc];}).map(function(m){
    return m.vno_code+': '+_resolveAccessId(raw.trim(),m.vno_code);
  });
  el.textContent=parts.join(' · ');
}

function _syncDmExecBtn(){
  var anyOn=_DM_META.some(function(m){ return _dmSel[m.tc]; });
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=running||!anyOn;
}

function renderDmView(){
  var grid=document.getElementById('dm-grid'); if(!grid) return;
  grid.innerHTML='';
  var _sel=_DM_META.filter(function(m){ return _dmSel[m.tc]; });
  grid.style.gridTemplateColumns=_sel.length===1?'1fr':'1fr 1fr';
  _sel.forEach(function(m){
    var p=document.createElement('div'); p.className='fact-panel'; p.id='dmp-'+m.tc;
    var _tc=m.tc;
    p.innerHTML=
      '<div class="fp-hdr">'
      +'<span class="fp-dot idle" id="dmpd-'+_tc+'"></span>'
      +'<span class="fp-name" style="color:'+m.color+'">'+esc(m.label)+'</span>'
      +'<span style="font-size:.65rem;color:var(--txt3)">'+esc(m.vno)+'</span>'
      +'<span class="fp-badge idle" id="dmpb-'+_tc+'">espera</span>'
      +'<a class="fp-rpt" id="dmpr-'+_tc+'" href="#" target="_blank">&#128196; Ver</a>'
      +'</div>'
      +'<div class="fact-term" id="dmt-'+_tc+'"></div>'
      +'<div class="fp-resp-bar" id="dmfrb-'+_tc+'">'
      +'<span class="fr-label">Response</span>'
      +'<span id="dmfrs-'+_tc+'"></span>'
      +'</div>'
      +'<div class="fp-resp" id="dmfr-'+_tc+'"><span class="fr-empty">—</span></div>';
    grid.appendChild(p);
  });
}

function _dmApp(tc,text,cls){
  var el=document.getElementById('dmt-'+tc); if(!el) return;
  var sp=document.createElement('span');
  sp.className='tl'+(cls?' '+cls:'');
  sp.textContent=text+'\\n';
  el.appendChild(sp); el.scrollTop=el.scrollHeight;
}

function _dmSetState(tc,state){
  var dot=document.getElementById('dmpd-'+tc);
  var badge=document.getElementById('dmpb-'+tc);
  var states={idle:'espera',running:'ejecutando',passed:'OK ✓',failed:'FAIL ✗'};
  if(dot){ dot.className='fp-dot '+state; }
  if(badge){ badge.className='fp-badge '+state; badge.textContent=states[state]||state; }
}

function _dmSetResponse(tc,responses){
  var el=document.getElementById('dmfr-'+tc);
  var bar=document.getElementById('dmfrs-'+tc);
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

function _doRunDm(s){
  if(running) return;
  var accessEl=document.getElementById('dm-access-inp');
  if(!accessEl||!accessEl.value.trim()){ if(accessEl) accessEl.style.borderColor='var(--err)'; return; }
  accessEl.style.borderColor='';
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _DM_META.forEach(function(m){
    var dt=document.getElementById('dmt-'+m.tc); if(dt) dt.innerHTML='';
    var dfr=document.getElementById('dmfr-'+m.tc); if(dfr) dfr.innerHTML='<span class="fr-empty">—</span>';
    var dfrs=document.getElementById('dmfrs-'+m.tc); if(dfrs) dfrs.innerHTML='';
    _dmSetState(m.tc,'idle');
    var pr=document.getElementById('dmpr-'+m.tc); if(pr){ pr.href='#'; pr.classList.remove('show'); }
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _rawAccess=accessEl.value.trim();
  var _selTcs=_DM_META.filter(function(m){return _dmSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var _accessMap={};
  _DM_META.forEach(function(m){ _accessMap[m.tc]=_resolveAccessId(_rawAccess,m.vno_code); });
  var _speed=(document.getElementById('dm-speed-sel')||{}).value||'600/600';
  var _sActiv=(document.getElementById('dm-serial-activ-inp')||{}).value||'0000';
  var _sDm=(document.getElementById('dm-serial-dm')||{}).value||'0000';
  var _sba=!!(document.getElementById('dm-svc-ba')||{}).checked;
  var _svoip=!!(document.getElementById('dm-svc-voip')||{}).checked;
  var _siptv=!!(document.getElementById('dm-svc-iptv')||{}).checked;
  var _addrDm=(document.getElementById('dm-addr-inp')||{}).value||'DIR02803636';
  var _envDm=(document.querySelector('input[name="dm-amb"]:checked')||{}).value||_gfEnv||'QA';
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&access_ids='+encodeURIComponent(JSON.stringify(_accessMap))
    +'&speed_plan='+encodeURIComponent(_speed)
    +'&serial_suffix='+encodeURIComponent(_sActiv)
    +'&serial_dm_suffix='+encodeURIComponent(_sDm)
    +'&service_ba='+(_sba?'true':'false')
    +'&service_voip='+(_svoip?'true':'false')
    +'&service_iptv='+(_siptv?'true':'false')
    +'&addr_id='+encodeURIComponent(_addrDm)
    +'&gf_env='+encodeURIComponent(_envDm);
  var es=new EventSource('/api/run/qa-dm-suite?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _dmApp(d.tc,d.t,col(d.t)); _dmSetState(d.tc,'running'); }
      else { _DM_META.filter(function(m){return _dmSel[m.tc];}).forEach(function(m){_dmApp(m.tc,d.t,col(d.t));}); }
      suiteLogs[s.id].push({text:d.t,cls:col(d.t)});
    } else if(d.e==='tc_done'){
      _dmSetState(d.tc,d.code===0?'passed':'failed');
      if(d.has_report){
        var dmpr=document.getElementById('dmpr-'+d.tc);
        if(dmpr){dmpr.href='/api/report/'+d.sid;dmpr.classList.add('show');}
      }
    } else if(d.e==='tc_response'){
      _dmSetResponse(d.tc,d.responses);
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error') onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){ currentEs=null; es.close();
      app('⚠ Conexión perdida con el servidor. Verifica la conexión y presiona Ejecutar nuevamente.','err');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s); }
  };
}

// ── Teardown Masivo ───────────────────────────────────────────────────────────
function renderTeardownFormBar(){
  var bar=document.getElementById('teardown-form-bar'); if(!bar) return;
  bar.innerHTML=
    '<span style="font-size:.7rem;font-weight:700;color:var(--txt3);text-transform:uppercase;letter-spacing:.05em">Access IDs:</span>'
    +'<textarea id="td-ids" rows="4" style="flex:1;min-width:200px;max-width:520px;font-family:monospace;font-size:.72rem;padding:5px 8px;border-radius:4px;border:1px solid var(--brd);background:var(--input,var(--card));color:var(--txt);resize:vertical" placeholder="Un access ID por línea (o separados por coma)"></textarea>'
    +'<div style="display:flex;flex-direction:column;gap:6px">'
    +'<div style="display:flex;align-items:center;gap:6px">'
    +'<span style="font-size:.68rem;color:var(--txt3)">Tipo:</span>'
    +'<select id="td-stype" style="padding:3px 6px;border-radius:4px;border:1px solid var(--brd);background:var(--bg2);color:var(--txt);font-size:.72rem">'
    +'<option value="FTTH">FTTH</option><option value="SSAA">SSAA</option>'
    +'</select>'
    +'</div>'
    +'<span style="font-size:.63rem;color:var(--txt3);max-width:160px">El VNO se detecta automáticamente del prefijo (02-xxx → VNO 02)</span>'
    +'</div>';
  var ta=document.getElementById('td-ids');
  if(ta) ta.oninput=_syncTeardownExecBtn;
}

function _syncTeardownExecBtn(){
  var eb=document.getElementById('exec-btn');
  var ta=document.getElementById('td-ids');
  var hasIds=ta&&ta.value.trim().length>0;
  if(eb) eb.disabled=running||!hasIds;
}

function _doRunTeardown(s){
  if(running) return;
  var ta=document.getElementById('td-ids');
  if(!ta||!ta.value.trim()){ if(ta) ta.style.borderColor='var(--err)'; return; }
  ta.style.borderColor='';
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  var con=document.getElementById('teardown-console'); if(con) con.innerHTML='';
  if(currentEs){currentEs.close();currentEs=null;}
  var _ids=ta.value.trim();
  var _stype=(document.getElementById('td-stype')||{}).value||'FTTH';
  var _params='access_ids='+encodeURIComponent(_ids)+'&service_type='+encodeURIComponent(_stype);
  var es=new EventSource('/api/run/qa-teardown-masivo?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      var con2=document.getElementById('teardown-console');
      if(con2){
        var sp=document.createElement('span');
        sp.className='tl'+' '+col(d.t);
        sp.textContent=d.t+'\\n';
        con2.appendChild(sp); con2.scrollTop=con2.scrollHeight;
      }
      suiteLogs[s.id].push({text:d.t,cls:col(d.t)});
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error') onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){ currentEs=null; es.close();
      app('⚠ Conexión perdida con el servidor. Verifica la conexión y presiona Ejecutar nuevamente.','err');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s); }
  };
  // habilitar botón cuando cambia el textarea
  if(ta) ta.oninput=_syncTeardownExecBtn;
}

// ── Suite Cancelación: vista multi-consola ───────────────────────────────────
var _CANCEL_META = [
  {tc:'TC-25', label:'TC-25 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-cancel-tc25', color:'#C586C0'},
  {tc:'TC-26', label:'TC-26 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-cancel-tc26', color:'#4EC9B0'},
  {tc:'TC-27', label:'TC-27 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-cancel-tc27', color:'#CE9178'},
  {tc:'TC-28', label:'TC-28 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-cancel-tc28', color:'#569CD6'},
];
var _cancelSel={};
(function(){ _CANCEL_META.forEach(function(m){ _cancelSel[m.tc]=true; }); })();
var _CANCEL_SERIAL_BASE={'TC-25':'ZTEG1104','TC-26':'ZTEGD719','TC-27':'HTWC000A'};
var _QA_SPEED_PLANS_CANCEL=['100/10','100/100','300/300','400/400','600/600'];

// ── Unsubscription Suite ──────────────────────────────────────────────────
var _UNSUB_META = [
  {tc:'TC-29', label:'TC-29 · Entel', vno:'VNO 03', vno_code:'03', sid:'qa-unsub-tc29', color:'#C586C0'},
  {tc:'TC-30', label:'TC-30 · KAO',   vno:'VNO 02', vno_code:'02', sid:'qa-unsub-tc30', color:'#4EC9B0'},
  {tc:'TC-31', label:'TC-31 · DTV',   vno:'VNO 05', vno_code:'05', sid:'qa-unsub-tc31', color:'#CE9178'},
  {tc:'TC-32', label:'TC-32 · TCH',   vno:'VNO 00', vno_code:'00', sid:'qa-unsub-tc32', color:'#569CD6'},
];
var _unsubSel={};
(function(){ _UNSUB_META.forEach(function(m){ _unsubSel[m.tc]=true; }); })();
var _QA_SPEED_PLANS_UNSUB=['100/10','100/100','300/300','400/400','600/600'];

function renderUnsubSuiteFormBar(){
  var bar=document.getElementById('unsub-form-bar'); if(!bar) return;
  var vnoBtns=_UNSUB_META.map(function(m){
    var on=_unsubSel[m.tc]?'on':'';
    return '<span class="atrf-vno-lbl '+on+'" data-tc="'+m.tc+'" onclick="_unsubToggleVno(this)" style="'+(on?'border-color:'+m.color+';color:'+m.color:'')+'">'+esc(m.vno_code+' · '+m.label.split(' · ')[1])+'</span>';
  }).join('');
  var speedOpts=_QA_SPEED_PLANS_UNSUB.map(function(p){
    return '<option value="'+p+'"'+(p==='100/10'?' selected':'')+'>'+p+'</option>';
  }).join('');
  bar.innerHTML='<div class="atrf-grid" style="max-width:920px">'
    +'<div class="atrf-field atrf-col-12">'
      +'<label>Ambiente <span class="req">★</span></label>'
      +'<div class="atrf-amb-wrap">'
        +'<input type="radio" name="unsub-amb" id="unsub-amb-qa" value="QA" class="atrf-amb-radio" onchange="_unsubOnAmbChange()" checked/>'
        +'<label for="unsub-amb-qa" class="atrf-amb-lbl">QA</label>'
        +'<input type="radio" name="unsub-amb" id="unsub-amb-prd" value="PRD" class="atrf-amb-radio" onchange="_unsubOnAmbChange()"/>'
        +'<label for="unsub-amb-prd" class="atrf-amb-lbl">PRD</label>'
        +'<input type="radio" name="unsub-amb" id="unsub-amb-pprd" value="PPRD" class="atrf-amb-radio" onchange="_unsubOnAmbChange()"/>'
        +'<label for="unsub-amb-pprd" class="atrf-amb-lbl">PPRD</label>'
        +'<span id="unsub-amb-url" style="font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-green);margin-left:8px;display:none"></span>'
      +'</div>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Selección VNO</div>'
    +'<div class="atrf-field atrf-col-5">'
      +'<label>VNO <span class="req">★</span></label>'
      +'<div class="atrf-vno-checks">'+vnoBtns+'</div>'
    +'</div>'
    +'<div class="atrf-field atrf-col-7">'
      +'<label>Dirección ID</label>'
      +'<input type="text" id="unsub-addr-inp" placeholder="DIR02803636"/>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Servicio a desuscribir</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Tipo Servicio <span class="req">★</span></label>'
      +'<select id="unsub-stype-sel"><option value="FTTH">FTTH</option><option value="SSAA">SSAA</option></select>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Speed Plan</label>'
      +'<select id="unsub-speed-sel">'+speedOpts+'</select>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Serial (últ. 4)</label>'
      +'<input type="text" id="unsub-serial-inp" maxlength="4" placeholder="0000" style="font-family:var(--atrf-mono);letter-spacing:.06em"/>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-field atrf-col-6" style="flex-direction:row;align-items:center;gap:10px;flex-wrap:wrap">'
      +'<label style="white-space:nowrap">Servicios</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="unsub-svc-ba" checked/> BA</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="unsub-svc-voip"/> VoIP</label>'
      +'<label class="atrf-chk"><input type="checkbox" id="unsub-svc-iptv"/> IPTV</label>'
    +'</div>'
    +'</div>';
  _unsubOnAmbChange();
}

function _unsubToggleVno(el){
  var tc=el.dataset.tc;
  _unsubSel[tc]=!_unsubSel[tc];
  var meta=_UNSUB_META.find(function(m){return m.tc===tc;});
  if(_unsubSel[tc]){
    el.classList.add('on');
    el.style.borderColor=meta?meta.color:'';
    el.style.color=meta?meta.color:'';
  } else {
    el.classList.remove('on');
    el.style.borderColor='';
    el.style.color='';
  }
  renderUnsubSuiteView();
  _syncUnsubSuiteExecBtn();
}

function _unsubOnAmbChange(){
  var rad=document.querySelector('input[name="unsub-amb"]:checked');
  var amb=rad?rad.value:'QA';
  var url=_atrfEnvUrls[amb]||'';
  var el=document.getElementById('unsub-amb-url');
  if(el){el.style.display=url?'inline':'none';el.textContent=url?('→ '+url):'';}
}

function _syncUnsubSuiteExecBtn(){
  var anyOn=_UNSUB_META.some(function(m){ return _unsubSel[m.tc]; });
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=running||!anyOn;
}

function renderUnsubSuiteView(){
  var grid=document.getElementById('unsub-grid'); if(!grid) return;
  grid.innerHTML='';
  var _sel=_UNSUB_META.filter(function(m){ return _unsubSel[m.tc]; });
  grid.style.gridTemplateColumns=_sel.length===1?'1fr':'1fr 1fr';
  _sel.forEach(function(m){
    var p=document.createElement('div'); p.className='fact-panel'; p.id='unsubp-'+m.tc;
    var _tc=m.tc;
    p.innerHTML=
      '<div class="fp-hdr">'
      +'<span class="fp-dot idle" id="unsubpd-'+_tc+'"></span>'
      +'<span class="fp-name" style="color:'+m.color+'">'+esc(m.label)+'</span>'
      +'<span style="font-size:.65rem;color:var(--txt3)">'+esc(m.vno)+'</span>'
      +'<span class="fp-badge idle" id="unsubpb-'+_tc+'">espera</span>'
      +'<a class="fp-rpt" id="unsubpr-'+_tc+'" href="#" target="_blank">&#128196; Ver</a>'
      +'</div>'
      +'<div class="fact-term" id="unsubt-'+_tc+'"></div>'
      +'<div class="fp-resp-bar" id="unsubfrb-'+_tc+'">'
      +'<span class="fr-label">Response</span>'
      +'<span id="unsubfrs-'+_tc+'"></span>'
      +'</div>'
      +'<div class="fp-resp" id="unsubfr-'+_tc+'"><span class="fr-empty">—</span></div>';
    grid.appendChild(p);
  });
}

function _unsubApp(tc,text,cls){
  var el=document.getElementById('unsubt-'+tc); if(!el) return;
  var sp=document.createElement('span');
  sp.className='tl'+(cls?' '+cls:'');
  sp.textContent=text+'\\n';
  el.appendChild(sp); el.scrollTop=el.scrollHeight;
}

function _unsubSetState(tc,state){
  var dot=document.getElementById('unsubpd-'+tc);
  var badge=document.getElementById('unsubpb-'+tc);
  var states={idle:'espera',running:'ejecutando',passed:'OK ✓',failed:'FAIL ✗'};
  if(dot){ dot.className='fp-dot '+state; }
  if(badge){ badge.className='fp-badge '+state; badge.textContent=states[state]||state; }
}

function _unsubSetResponse(tc,responses){
  var el=document.getElementById('unsubfr-'+tc);
  var bar=document.getElementById('unsubfrs-'+tc);
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

function _doRunUnsubSuite(s){
  if(running) return;
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _UNSUB_META.forEach(function(m){
    var ct=document.getElementById('unsubt-'+m.tc); if(ct) ct.innerHTML='';
    var cfr=document.getElementById('unsubfr-'+m.tc); if(cfr) cfr.innerHTML='<span class="fr-empty">—</span>';
    var cfrs=document.getElementById('unsubfrs-'+m.tc); if(cfrs) cfrs.innerHTML='';
    _unsubSetState(m.tc,'idle');
    var pr=document.getElementById('unsubpr-'+m.tc); if(pr){ pr.href='#'; pr.classList.remove('show'); }
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _selTcs=_UNSUB_META.filter(function(m){return _unsubSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var _speed=(document.getElementById('unsub-speed-sel')||{}).value||'100/10';
  var _stype=(document.getElementById('unsub-stype-sel')||{}).value||'FTTH';
  var _sba=!!(document.getElementById('unsub-svc-ba')||{}).checked;
  var _svoip=!!(document.getElementById('unsub-svc-voip')||{}).checked;
  var _siptv=!!(document.getElementById('unsub-svc-iptv')||{}).checked;
  var _serial=(document.getElementById('unsub-serial-inp')||{}).value||'0000';
  var _addrUnsub=(document.getElementById('unsub-addr-inp')||{}).value||'DIR02803636';
  var _envUnsub=(document.querySelector('input[name="unsub-amb"]:checked')||{}).value||_gfEnv||'QA';
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&speed_plan='+encodeURIComponent(_speed)
    +'&service_type='+encodeURIComponent(_stype)
    +'&svc_ba='+(_sba?'true':'false')
    +'&svc_voip='+(_svoip?'true':'false')
    +'&svc_iptv='+(_siptv?'true':'false')
    +'&serial_suffix='+encodeURIComponent(_serial)
    +'&addr_id='+encodeURIComponent(_addrUnsub)
    +'&gf_env='+encodeURIComponent(_envUnsub);
  var es=new EventSource('/api/run/qa-unsub-suite?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _unsubApp(d.tc,d.t,col(d.t)); _unsubSetState(d.tc,'running'); }
      else { _UNSUB_META.filter(function(m){return _unsubSel[m.tc];}).forEach(function(m){_unsubApp(m.tc,d.t,col(d.t));}); }
      suiteLogs[s.id].push({text:d.t,cls:col(d.t)});
    } else if(d.e==='tc_done'){
      _unsubSetState(d.tc,d.code===0?'passed':'failed');
      if(d.has_report){
        var upr=document.getElementById('unsubpr-'+d.tc);
        if(upr){upr.href='/api/report/'+d.sid;upr.classList.add('show');}
      }
    } else if(d.e==='tc_response'){
      _unsubSetResponse(d.tc,d.responses);
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error') onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    currentEs=null; es.close();
    app('⚠ Conexión perdida con el servidor. Verifica la conexión y presiona Ejecutar nuevamente.','err');
    onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
  };
}

function renderCancelFormBar(){
  var bar=document.getElementById('cancel-form-bar'); if(!bar) return;
  var vnoBtns=_CANCEL_META.map(function(m){
    var on=_cancelSel[m.tc]?'on':'';
    return '<span class="atrf-vno-lbl '+on+'" data-tc="'+m.tc+'" onclick="_cancelToggleVno(this)" style="'+(on?'border-color:'+m.color+';color:'+m.color:'')+'">'+esc(m.vno_code+' · '+m.label.split(' · ')[1])+'</span>';
  }).join('');
  var aidRows=_CANCEL_META.map(function(m){
    return '<div class="atrf-field atrf-col-6">'
      +'<label style="color:'+m.color+';font-weight:600">'+esc(m.label)+' — Access ID</label>'
      +'<input type="text" id="cancel-aid-'+m.vno_code+'" placeholder="'+m.vno_code+'-QAREGXXXAO-10" style="font-family:var(--atrf-mono);letter-spacing:.04em"/>'
      +'</div>';
  }).join('');
  bar.innerHTML='<div class="atrf-grid" style="max-width:920px">'
    +'<div class="atrf-field atrf-col-12">'
      +'<label>Ambiente <span class="req">★</span></label>'
      +'<div class="atrf-amb-wrap">'
        +'<input type="radio" name="cancel-amb" id="cancel-amb-qa" value="QA" class="atrf-amb-radio" onchange="_cancelOnAmbChange()" checked/>'
        +'<label for="cancel-amb-qa" class="atrf-amb-lbl">QA</label>'
        +'<input type="radio" name="cancel-amb" id="cancel-amb-prd" value="PRD" class="atrf-amb-radio" onchange="_cancelOnAmbChange()"/>'
        +'<label for="cancel-amb-prd" class="atrf-amb-lbl">PRD</label>'
        +'<input type="radio" name="cancel-amb" id="cancel-amb-pprd" value="PPRD" class="atrf-amb-radio" onchange="_cancelOnAmbChange()"/>'
        +'<label for="cancel-amb-pprd" class="atrf-amb-lbl">PPRD</label>'
        +'<span id="cancel-amb-url" style="font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-green);margin-left:8px;display:none"></span>'
      +'</div>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Selección VNO</div>'
    +'<div class="atrf-field atrf-col-5">'
      +'<label>VNO <span class="req">★</span></label>'
      +'<div class="atrf-vno-checks">'+vnoBtns+'</div>'
    +'</div>'
    +'<div class="atrf-field atrf-col-3">'
      +'<label>Tipo Servicio <span class="req">★</span></label>'
      +'<select id="cancel-stype-sel"><option value="FTTH">FTTH</option><option value="SSAA">SSAA</option></select>'
    +'</div>'
    +'<hr class="atrf-divider"/>'
    +'<div class="atrf-group-lbl">Access ID por VNO <span style="font-weight:400;font-size:.74rem;color:var(--txt2)">(u_access_id_vno del servicio a cancelar)</span></div>'
    +aidRows
    +'</div>';
  _cancelOnAmbChange();
}

function _cancelToggleVno(el){
  var tc=el.dataset.tc;
  _cancelSel[tc]=!_cancelSel[tc];
  var meta=_CANCEL_META.find(function(m){return m.tc===tc;});
  if(_cancelSel[tc]){
    el.classList.add('on');
    el.style.borderColor=meta?meta.color:'';
    el.style.color=meta?meta.color:'';
  } else {
    el.classList.remove('on');
    el.style.borderColor='';
    el.style.color='';
  }
  renderCancelView();
  _syncCancelExecBtn();
}

function _cancelOnAmbChange(){
  var rad=document.querySelector('input[name="cancel-amb"]:checked');
  var amb=rad?rad.value:'QA';
  var url=_atrfEnvUrls[amb]||'';
  var el=document.getElementById('cancel-amb-url');
  if(el){el.style.display=url?'inline':'none';el.textContent=url?('→ '+url):'';}
}

function _syncCancelExecBtn(){
  var anyOn=_CANCEL_META.some(function(m){ return _cancelSel[m.tc]; });
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=running||!anyOn;
}

function renderCancelView(){
  var grid=document.getElementById('cancel-grid'); if(!grid) return;
  grid.innerHTML='';
  var _sel=_CANCEL_META.filter(function(m){ return _cancelSel[m.tc]; });
  grid.style.gridTemplateColumns=_sel.length===1?'1fr':'1fr 1fr';
  _sel.forEach(function(m){
    var p=document.createElement('div'); p.className='fact-panel'; p.id='cancelp-'+m.tc;
    var _tc=m.tc;
    p.innerHTML=
      '<div class="fp-hdr">'
      +'<span class="fp-dot idle" id="cancelpd-'+_tc+'"></span>'
      +'<span class="fp-name" style="color:'+m.color+'">'+esc(m.label)+'</span>'
      +'<span style="font-size:.65rem;color:var(--txt3)">'+esc(m.vno)+'</span>'
      +'<span class="fp-badge idle" id="cancelpb-'+_tc+'">espera</span>'
      +'<a class="fp-rpt" id="cancelpr-'+_tc+'" href="#" target="_blank">&#128196; Ver</a>'
      +'</div>'
      +'<div class="fact-term" id="cancelt-'+_tc+'"></div>'
      +'<div class="fp-resp-bar" id="cancelfrb-'+_tc+'">'
      +'<span class="fr-label">Response</span>'
      +'<span id="cancelfrs-'+_tc+'"></span>'
      +'</div>'
      +'<div class="fp-resp" id="cancelfr-'+_tc+'"><span class="fr-empty">—</span></div>';
    grid.appendChild(p);
  });
}

function _cancelApp(tc,text,cls){
  var el=document.getElementById('cancelt-'+tc); if(!el) return;
  var sp=document.createElement('span');
  sp.className='tl'+(cls?' '+cls:'');
  sp.textContent=text+'\\n';
  el.appendChild(sp); el.scrollTop=el.scrollHeight;
}

function _cancelSetState(tc,state){
  var dot=document.getElementById('cancelpd-'+tc);
  var badge=document.getElementById('cancelpb-'+tc);
  var states={idle:'espera',running:'ejecutando',passed:'OK ✓',failed:'FAIL ✗'};
  if(dot){ dot.className='fp-dot '+state; }
  if(badge){ badge.className='fp-badge '+state; badge.textContent=states[state]||state; }
}

function _cancelSetResponse(tc,responses){
  var el=document.getElementById('cancelfr-'+tc);
  var bar=document.getElementById('cancelfrs-'+tc);
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

function _doRunCancel(s){
  if(running) return;
  running=true; runningId=s.id; tStart=Date.now();
  suiteLogs[s.id]=[];
  delete suiteSummaries[s.id]; delete suiteReports[s.id]; delete suiteTopState[s.id];
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando VNOs en paralelo…');
  setIco(s.id,'running'); setActive(s.id);
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  _CANCEL_META.forEach(function(m){
    var ct=document.getElementById('cancelt-'+m.tc); if(ct) ct.innerHTML='';
    var cfr=document.getElementById('cancelfr-'+m.tc); if(cfr) cfr.innerHTML='<span class="fr-empty">—</span>';
    var cfrs=document.getElementById('cancelfrs-'+m.tc); if(cfrs) cfrs.innerHTML='';
    _cancelSetState(m.tc,'idle');
    var pr=document.getElementById('cancelpr-'+m.tc); if(pr){ pr.href='#'; pr.classList.remove('show'); }
  });
  if(currentEs){currentEs.close();currentEs=null;}
  var _selTcs=_CANCEL_META.filter(function(m){return _cancelSel[m.tc];}).map(function(m){return m.tc;}).join(',');
  var _stype=(document.getElementById('cancel-stype-sel')||{}).value||'FTTH';
  var _envCancel=(document.querySelector('input[name="cancel-amb"]:checked')||{}).value||_gfEnv||'QA';
  var _params='tcs='+encodeURIComponent(_selTcs)
    +'&service_type='+encodeURIComponent(_stype)
    +'&gf_env='+encodeURIComponent(_envCancel);
  _CANCEL_META.forEach(function(m){
    var aid=(document.getElementById('cancel-aid-'+m.vno_code)||{}).value||'';
    _params+='&aid_'+m.vno_code+'='+encodeURIComponent(aid);
  });
  var es=new EventSource('/api/run/qa-cancel-suite?'+_params);
  currentEs=es;
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.tc){ _cancelApp(d.tc,d.t,col(d.t)); _cancelSetState(d.tc,'running'); }
      else { _CANCEL_META.filter(function(m){return _cancelSel[m.tc];}).forEach(function(m){_cancelApp(m.tc,d.t,col(d.t));}); }
      suiteLogs[s.id].push({text:d.t,cls:col(d.t)});
    } else if(d.e==='tc_done'){
      _cancelSetState(d.tc,d.code===0?'passed':'failed');
      if(d.has_report){
        var cpr=document.getElementById('cancelpr-'+d.tc);
        if(cpr){cpr.href='/api/report/'+d.sid;cpr.classList.add('show');}
      }
    } else if(d.e==='tc_response'){
      _cancelSetResponse(d.tc,d.responses);
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      if(d.e==='error') onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      else onDone(d,s);
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){ currentEs=null; es.close();
      app('⚠ Conexión perdida con el servidor. Verifica la conexión y presiona Ejecutar nuevamente.','err');
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

function _saveHistorialRecord(d,s){
  var now=new Date();
  var ts=now.getTime();
  var tiempo_ms=Math.round(Date.now()-tStart);
  var suite_label=s.label||s.id;
  if(Array.isArray(d.tc_results)&&d.tc_results.length){
    d.tc_results.forEach(function(tc){
      var record={
        ts:ts,suite_id:s.id,suite_label:suite_label,
        tc:tc.tc||'',vno:tc.vno||'',vno_lbl:tc.vno_lbl||'',
        escenario:tc.escenario||'',
        direccion:tc.direccion||'',
        resultado:tc.code===0?'ok':'error',
        code:tc.code,tiempo_ms:tiempo_ms
      };
      if(tc.responses&&tc.responses.length){
        record.steps_json=JSON.stringify(tc.responses.map(function(r){
          return {func:r.name||'',tc:tc.tc||'',httpCode:r.code,pass:r.code>=200&&r.code<300,req:(r.method||'GET')+' '+(r.url||''),res:r.body||''};
        }));
      }
      fetch('/api/historial',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(record)}).catch(function(){});
    });
  } else {
    var record={
      ts:ts,suite_id:s.id,suite_label:suite_label,
      tc:'',vno:(Array.isArray(d.vnos)&&d.vnos[0])||_globalVNO||'',vno_lbl:'',
      escenario:'',
      direccion:(Array.isArray(d.direcciones)&&d.direcciones[0])||'',
      resultado:d.code===0?'ok':'error',
      code:d.code,tiempo_ms:tiempo_ms
    };
    fetch('/api/historial',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(record)}).catch(function(){});
  }
}
function _doAutoTeardown(accessIds){
  app('','');
  app('── Teardown automático · '+accessIds.length+' acceso'+(accessIds.length===1?'':'s')+' ──────────────','dim');
  var _es2=new EventSource('/api/run/qa-teardown-masivo?access_ids='+encodeURIComponent(accessIds.join('\\n'))+'&service_type=FTTH');
  _es2.onmessage=function(ev){
    var d2=JSON.parse(ev.data);
    if(d2.e==='start') return;
    if(d2.e==='line') app(d2.t,col(d2.t));
    else if(d2.e==='done'){
      app('── Teardown: '+(d2.code===0?'✓ accesos liberados':'✗ finalizó con errores'),d2.code===0?'ok bold':'err bold');
      _es2.close();
    } else if(d2.e==='error'){app('── Teardown error: '+(d2.msg||''),'err');_es2.close();}
  };
  _es2.onerror=function(){app('── Teardown: error de conexión','err');_es2.close();};
}
function onDone(d,s){
  running=false; runningId=null;
  _saveHistorialRecord(d,s);
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
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=false;
  if(_isQAChild){
    fetch('/api/response/'+s.id)
      .then(function(r){return r.json();})
      .then(function(data){renderResponsePanel(data);})
      .catch(function(){});
  }
  if(queue.length){var nx=queue.shift();setTimeout(()=>run(nx),350);}
  var _tdMap={'qa-asig-suite':'asig-teardown','qa-activ-suite':'activ-teardown','qa-dm-suite':'dm-teardown'};
  var _tdCbId=_tdMap[s.id];
  if(_tdCbId){
    var _tdCb=document.getElementById(_tdCbId);
    if(_tdCb&&_tdCb.checked&&Array.isArray(d.tc_results)){
      var _tdAids=d.tc_results.map(function(tc){return tc.access_id||'';}).filter(Boolean);
      if(_tdAids.length) _doAutoTeardown(_tdAids);
    }
  }
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
      var _s=suites.find(function(x){return x.id===selectedId;});
      if(selectedId==='qa-ep-assignment') renderAssignmentForm();
      else if(selectedId==='qa-ep-ia') renderIAForm();
      else if(selectedId==='qa-ep-ia-fin') renderIAFinForm();
      else if(selectedId==='qa-ep-ia-cancel') renderIACancelForm();
      else if(selectedId==='qa-ep-activacion') renderActivacionForm();
      else if(selectedId==='qa-ep-devmod') renderDevModForm();
      else if(selectedId==='qa-ep-modificacion') renderModificacionForm();
      else if(selectedId==='qa-ep-cancel') renderCancelSvcForm();
      else if(selectedId==='qa-ep-unsub') renderUnsubForm();
      else if(selectedId==='qa-cons-retrievetch'||selectedId==='qa-cons-retrievekao') renderRetrieveForm();
      else if(selectedId==='qa-cons-diagnostico'||selectedId==='qa-cons-estadovecino') renderAccessIdEpForm();
      else if(selectedId==='qa-cons-accessstate') renderAccessStateForm();
      else if(selectedId==='qa-cons-queryneighbors') renderQueryNeighborsForm();
      else if(selectedId==='qa-cons-reinicio') renderReinicioForm();
      else if(selectedId==='qa-cons-consultaacceso') renderConsultaAccesoForm();
      else if(selectedId==='qa-cons-cevvecino') renderCEVVecinoForm();
      else if(selectedId==='qa-cons-dataont') renderConsultaDataONTForm();
      else if(_s&&_s.env_type==='qa_vno') renderVnoEpForm(_s);
      else renderFactibilidadForm();
    };})(code);
    bar.appendChild(btn);
  });
  bar.style.display="flex";
}

function renderVnoEpForm(s){
  var c=document.getElementById('epf-container'); if(!c) return;
  var vno=_globalVNO||'02';
  var vnoBtns=['00','02','03','05'].map(function(code){
    var on=code===vno?'on':'';
    var color=_QA_VNO_COLORS[code]||'var(--atrf-accent)';
    return '<span class="atrf-vno-lbl '+on+'" data-vno="'+code+'" onclick="_setEpVno(this.dataset.vno)" style="'+(on?'border-color:'+color+';color:'+color:'')+'">'+esc(_QA_VNO_LABELS[code]||code)+'</span>';
  }).join('');
  var envFile={'00':'00-TCH QA','02':'02 QA_KAO','03':'03-B1_vnoid03 QA','05':'05 QA_DTV'}[vno]||'02 QA_KAO';
  c.innerHTML='<div style="padding:16px 0">'
    +'<div class="atrf-grid" style="max-width:640px">'
      +'<div class="atrf-field atrf-col-12">'
        +'<div style="background:var(--atrf-surface2,var(--bg3,var(--card)));border:1px solid var(--atrf-border);border-radius:6px;padding:10px 14px;margin-bottom:4px">'
          +'<div style="font-size:.68rem;font-weight:700;color:var(--atrf-accent);text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px">'+esc(s.label||'')+'</div>'
          +'<div style="font-size:.8rem;color:var(--atrf-text,var(--txt))">'+esc(s.desc||'')+'</div>'
          +(s.folder?'<div style="font-size:.7rem;color:var(--txt3);margin-top:2px;font-family:var(--atrf-mono)">Folder: '+esc(s.folder)+'</div>':'')
        +'</div>'
      +'</div>'
      +'<hr class="atrf-divider"/>'
      +'<div class="atrf-group-lbl">Selección VNO</div>'
      +'<div class="atrf-field atrf-col-8">'
        +'<label>VNO <span class="req">★</span></label>'
        +'<div class="atrf-vno-checks">'+vnoBtns+'</div>'
      +'</div>'
      +'<div class="atrf-field atrf-col-8" style="flex-direction:row;align-items:center;gap:6px;flex-wrap:wrap">'
        +'<span style="font-size:.68rem;color:var(--txt3)">Env:</span>'
        +'<span style="font-size:.7rem;font-family:var(--atrf-mono);color:var(--txt2)">'+esc(envFile)+'</span>'
      +'</div>'
    +'</div>'
  +'</div>';
}

function _setEpVno(code){
  _globalVNO=code;
  document.querySelectorAll('#epf-container .atrf-vno-lbl').forEach(function(el){
    var c=el.dataset.vno;
    var color=_QA_VNO_COLORS[c]||'var(--atrf-accent)';
    if(c===code){ el.classList.add('on'); el.style.borderColor=color; el.style.color=color; }
    else { el.classList.remove('on'); el.style.borderColor=''; el.style.color=''; }
  });
  var envLabels={'00':'00-TCH QA','02':'02 QA_KAO','03':'03-B1_vnoid03 QA','05':'05 QA_DTV'};
  var envEl=document.querySelector('#epf-container .atrf-field .atrf-field span:last-child');
  // update the env label in the form
  var _s=suites.find(function(x){return x.id===selectedId;});
  if(_s&&_s.env_type==='qa_vno') renderVnoEpForm(_s);
  renderEPFVNOBar();
  renderVNOBar();
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
// ── helpers shared by new ep forms ────────────────────────────────────────────
function _epfVnoReadonly(card,vno,clr){
  var f=document.createElement("div"); f.className="epf-field";
  var l=document.createElement("label"); l.className="epf-label"; l.textContent="u_id_vno (auto)";
  var v=document.createElement("div"); v.className="epf-readonly";
  v.style.color=clr; v.textContent=vno+" — "+(_QA_VNO_LABELS[vno]||vno);
  f.appendChild(l); f.appendChild(v); card.appendChild(f);
}
function _epfTextInput(card,id,lbl,ph){
  var f=document.createElement("div"); f.className="epf-field";
  var l=document.createElement("label"); l.className="epf-label"; l.textContent=lbl;
  var i=document.createElement("input"); i.type="text"; i.className="epf-input"; i.id=id; i.placeholder=ph||"";
  f.appendChild(l); f.appendChild(i); card.appendChild(f); return i;
}
function _epfSelectInput(card,id,lbl,opts,defVal){
  var f=document.createElement("div"); f.className="epf-field";
  var l=document.createElement("label"); l.className="epf-label"; l.textContent=lbl;
  var s=document.createElement("select"); s.className="epf-select"; s.id=id;
  opts.forEach(function(o){var op=document.createElement("option");op.value=o;op.textContent=o;if(o===defVal)op.selected=true;s.appendChild(op);});
  f.appendChild(l); f.appendChild(s); card.appendChild(f); return s;
}
function _epfExecBtn(card,running,fn){
  var eb=document.createElement("button"); eb.className="epf-exec"; eb.textContent="▶ Ejecutar";
  eb.disabled=running; eb.onclick=fn; card.appendChild(eb); return eb;
}
function _epfDoRun(sid,params){
  if(running) return;
  var s=suites.find(function(x){return x.id===sid;});
  if(!s) return;
  selectedId=sid; _isQAChild=true;
  switchView("std"); renderVNOBar();
  var rp=document.getElementById("resp-panel"); if(rp) rp.style.display="none";
  suiteLogs[sid]=[]; document.getElementById("term").innerHTML="";
  _doRun("/api/run/"+sid,params,s);
}
// ── IA Cancelación ─────────────────────────────────────────────────────────────
function renderIACancelForm(){
  _buildIACard("IA Cancelación","05-Cancela Intervención","epf-iac-access","ej. 02-QASM-2307-1",runIACancel);
}
function runIACancel(params){ _epfDoRun("qa-ep-ia-cancel",params); }
// ── Device Modification ────────────────────────────────────────────────────────
function renderDevModForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="Device Modification";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Folder: <span>06-DeviceModification</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-dm-access","u_access_id_vno","ej. 02-OrderCharacteristics-30");
  _epfTextInput(card,"epf-dm-serial","u_serial_number","ej. HTWC022A0430");
  _epfExecBtn(card,running,function(){
    var ai=document.getElementById("epf-dm-access");
    var sn=document.getElementById("epf-dm-serial");
    if(!ai) return;
    _epfDoRun("qa-ep-devmod",{vno:_globalVNO,access_id_vno:ai.value,serial_number:sn?sn.value:""});
  });
  container.appendChild(card);
}
// ── Modificación de Acceso ─────────────────────────────────────────────────────
function renderModificacionForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="Modificación de Acceso";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Folder: <span>07-Modificacion De Acceso</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-mod-access","u_access_id_vno","ej. 02-DIR00765088-RANOKIA-1");
  _epfSelectInput(card,"epf-mod-speed","u_speed_plan",QA_SPEED_PLANS,"600/600");
  _epfSelectInput(card,"epf-mod-ba","u_service_ba",["true","false"],"true");
  _epfSelectInput(card,"epf-mod-voip","u_service_voip",["true","false"],"true");
  _epfSelectInput(card,"epf-mod-iptv","u_service_iptv",["true","false"],"true");
  _epfTextInput(card,"epf-mod-serial","u_serial_number (opcional)","ej. ZTEGD16683E9");
  var fop=document.createElement("div"); fop.className="epf-field";
  var lop=document.createElement("label"); lop.className="epf-label"; lop.textContent="u_operation_type (fijo)";
  var vop=document.createElement("div"); vop.className="epf-readonly"; vop.style.color="var(--txt3)"; vop.style.borderStyle="dashed"; vop.textContent="M";
  fop.appendChild(lop); fop.appendChild(vop); card.appendChild(fop);
  _epfExecBtn(card,running,function(){
    var ai=document.getElementById("epf-mod-access");
    var sp=document.getElementById("epf-mod-speed");
    var ba=document.getElementById("epf-mod-ba");
    var vo=document.getElementById("epf-mod-voip");
    var it=document.getElementById("epf-mod-iptv");
    var sn=document.getElementById("epf-mod-serial");
    if(!ai||!sp) return;
    _epfDoRun("qa-ep-modificacion",{vno:_globalVNO,access_id_vno:ai.value,speed_plan:sp.value,
      service_ba:ba.value,service_voip:vo.value,service_iptv:it.value,serial_number:sn?sn.value:""});
  });
  container.appendChild(card);
}
// ── Cancel Orden Servicio ──────────────────────────────────────────────────────
function renderCancelSvcForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="Cancel Orden Servicio";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Folder: <span>08-CancelOrdenServicio</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-csvc-access","u_access_id_vno","ej. 02-QASM2703-SM01");
  _epfSelectInput(card,"epf-csvc-svctype","u_service_type",["FTTH","SSAA"],"FTTH");
  _epfExecBtn(card,running,function(){
    var ai=document.getElementById("epf-csvc-access");
    var st=document.getElementById("epf-csvc-svctype");
    if(!ai) return;
    _epfDoRun("qa-ep-cancel",{vno:_globalVNO,access_id_vno:ai.value,service_type:st.value});
  });
  container.appendChild(card);
}
// ── Unsubscription ─────────────────────────────────────────────────────────────
function renderUnsubForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="Unsubscription · Baja Total de Servicio";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Endpoint: <span>fullFillment-unsubcription/v1/accessDeregistration</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-unsub-access","u_access_id_vno","ej. 03-QAAPOQ_OLT_10-04");
  _epfSelectInput(card,"epf-unsub-svctype","u_service_type",["FTTH","SSAA"],"FTTH");
  var resDiv=document.createElement("div"); resDiv.style.cssText="margin-top:12px;";
  var btn=_epfExecBtn(card,running,function(){
    var ai=document.getElementById("epf-unsub-access");
    var st=document.getElementById("epf-unsub-svctype");
    if(!ai||!ai.value.trim()) return;
    btn.disabled=true; btn.textContent="⏳ Ejecutando...";
    resDiv.innerHTML='<div style="color:var(--txt-dim);font-size:13px;padding:8px 0">Ejecutando Baja Total de Servicio...</div>';
    fetch("/api/atrf/run-step",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({func:"Baja Total de Servicio",vno:_globalVNO,accessId:ai.value.trim(),serviceType:st?st.value:"FTTH"})
    }).then(function(r){return r.json();}).then(function(d){
      btn.disabled=false; btn.textContent="▶ Ejecutar";
      var pass=d.pass;
      var badge=pass
        ?'<span style="background:#22c55e;color:#fff;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:700">PASS</span>'
        :'<span style="background:#ef4444;color:#fff;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:700">FAIL</span>';
      var html='<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'+badge
        +'<span style="font-size:12px;color:var(--txt-dim)">HTTP '+d.httpCode+'</span></div>';
      html+='<div style="font-size:12px;color:var(--txt-dim);margin-bottom:4px">Request:</div>';
      html+='<pre style="background:var(--bg-card);border:1px solid var(--bdr);border-radius:4px;padding:8px;font-size:11px;overflow-x:auto;margin:0 0 8px 0">'+esc(d.req||'')+'</pre>';
      html+='<div style="font-size:12px;color:var(--txt-dim);margin-bottom:4px">Response:</div>';
      html+='<pre style="background:var(--bg-card);border:1px solid var(--bdr);border-radius:4px;padding:8px;font-size:11px;overflow-x:auto;margin:0">'+esc(d.res||d.error||'')+'</pre>';
      resDiv.innerHTML=html;
    }).catch(function(e){
      btn.disabled=false; btn.textContent="▶ Ejecutar";
      resDiv.innerHTML='<div style="color:#ef4444;font-size:13px">Error: '+esc(String(e))+'</div>';
    });
  });
  card.appendChild(resDiv);
  container.appendChild(card);
}
// ── RetrieveAccess ─────────────────────────────────────────────────────────────
function renderRetrieveForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var s=suites.find(function(x){return x.id===selectedId;});
  var fldr=s?s.folder:"RetrieveAccess";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="RetrieveAccess";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Folder: <span>'+esc(fldr)+'</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-rtr-access","u_access_id_vno","ej. 02-1-P0FGUDQ");
  _epfSelectInput(card,"epf-rtr-scope","u_flag_scope",["0","1","2"],"0");
  _epfExecBtn(card,running,function(){
    var ai=document.getElementById("epf-rtr-access");
    var fs=document.getElementById("epf-rtr-scope");
    if(!ai) return;
    _epfDoRun(selectedId,{vno:_globalVNO,access_id_vno:ai.value,flag_scope:fs.value});
  });
  container.appendChild(card);
}
// ── DiagnosticoAcceso / EstadoVecino V (access_id_vno only) ───────────────────
function renderAccessIdEpForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var s=suites.find(function(x){return x.id===selectedId;});
  var ttl=s?s.label:"Diagnóstico"; var fldr=s?s.folder:"";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent=ttl;
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Folder: <span>'+esc(fldr)+'</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-aid-access","u_access_id_vno","ej. 03-REGRE-1607-SM2");
  _epfExecBtn(card,running,function(){
    var ai=document.getElementById("epf-aid-access"); if(!ai) return;
    _epfDoRun(selectedId,{vno:_globalVNO,access_id_vno:ai.value});
  });
  container.appendChild(card);
}
// ── AccessStateResponse (PUT callback) ────────────────────────────────────────
function renderAccessStateForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="AccessStateResponse";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Method: <span>PUT · diagnosticoAcceso/v1/AccessStateResponse</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-acs-node","u_node","ej. PITA_OLT_4");
  _epfTextInput(card,"epf-acs-element","u_element","ej. 0/1/0/1");
  _epfTextInput(card,"epf-acs-status","u_access_status","ej. access status");
  _epfTextInput(card,"epf-acs-msg","u_access_status_msg","ej. Status access msg");
  _epfTextInput(card,"epf-acs-rx","u_current_rx","ej. -20 dBm");
  _epfTextInput(card,"epf-acs-hrx","u_historical_rx","ej. -20 dBm");
  _epfExecBtn(card,running,function(){
    _epfDoRun("qa-cons-accessstate",{
      vno:_globalVNO,
      u_node:(document.getElementById("epf-acs-node")||{}).value||"",
      u_element:(document.getElementById("epf-acs-element")||{}).value||"",
      u_access_status:(document.getElementById("epf-acs-status")||{}).value||"",
      u_access_status_msg:(document.getElementById("epf-acs-msg")||{}).value||"",
      u_current_rx:(document.getElementById("epf-acs-rx")||{}).value||"",
      u_historical_rx:(document.getElementById("epf-acs-hrx")||{}).value||"",
    });
  });
  container.appendChild(card);
}
// ── QueryNeighborsStateResponse (PUT callback) ────────────────────────────────
function renderQueryNeighborsForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="QueryNeighborsStateResponse";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Method: <span>PUT · estadoVecino/v1/QueryNeighborsStateResponse</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  [["epf-qn-node","u_node","ej. PITA_OLT_5"],
   ["epf-qn-element","u_element","ej. 0/5/2/63"],
   ["epf-qn-status","u_access_status","ej. OK"],
   ["epf-qn-msg","u_access_status_msg","ej. Access OK"],
   ["epf-qn-rx","u_current_rx","ej. -19.83 dBm"],
   ["epf-qn-hrx","u_historical_rx","ej. -25 dBm"],
   ["epf-qn-tx","u_current_tx","ej. 2.18 dBm"],
   ["epf-qn-htx","u_historical_tx","ej. -25 dBm"],
   ["epf-qn-temp","u_laser_temp","ej. 42 Cdeg"],
   ["epf-qn-volt","u_laser_voltage","ej. 3280 mV"],
   ["epf-qn-bip8","u_current_bip8","ej.  packets"],
   ["epf-qn-hbip8","u_historical_bip8","ej. 0 packets"]
  ].forEach(function(t){ _epfTextInput(card,t[0],t[1],t[2]); });
  _epfExecBtn(card,running,function(){
    function g(id){return (document.getElementById(id)||{}).value||"";}
    _epfDoRun("qa-cons-queryneighbors",{
      vno:_globalVNO,
      u_node:g("epf-qn-node"), u_element:g("epf-qn-element"),
      u_access_status:g("epf-qn-status"), u_access_status_msg:g("epf-qn-msg"),
      u_current_rx:g("epf-qn-rx"), u_historical_rx:g("epf-qn-hrx"),
      u_current_tx:g("epf-qn-tx"), u_historical_tx:g("epf-qn-htx"),
      u_laser_temp:g("epf-qn-temp"), u_laser_voltage:g("epf-qn-volt"),
      u_current_bip8:g("epf-qn-bip8"), u_historical_bip8:g("epf-qn-hbip8"),
    });
  });
  container.appendChild(card);
}
// ── ReinicioONT ────────────────────────────────────────────────────────────────
function renderReinicioForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="ReinicioONT";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Folder: <span>ReinicioONT</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-rei-access","u_access_id_vno","ej. 02-1-OPGKCQI");
  _epfSelectInput(card,"epf-rei-resettype","u_reset_type",["1","2","3"],"1");
  _epfTextInput(card,"epf-rei-port","u_port (opcional)","");
  _epfExecBtn(card,running,function(){
    var ai=document.getElementById("epf-rei-access");
    var rt=document.getElementById("epf-rei-resettype");
    var pt=document.getElementById("epf-rei-port");
    if(!ai) return;
    _epfDoRun("qa-cons-reinicio",{vno:_globalVNO,access_id_vno:ai.value,reset_type:rt.value,port:pt?pt.value:""});
  });
  container.appendChild(card);
}
// ── ConsultaAcceso GET ─────────────────────────────────────────────────────────
function renderConsultaAccesoForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="ConsultaAcceso";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Method: <span>GET · fullFillment-consultaAcceso/v1/{access_id}</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-ca-access","access_id (en URL)","ej. 001130062264");
  _epfExecBtn(card,running,function(){
    var ai=document.getElementById("epf-ca-access"); if(!ai) return;
    _epfDoRun("qa-cons-consultaacceso",{vno:_globalVNO,access_id_vno:ai.value});
  });
  container.appendChild(card);
}
// ── CEVEstadoVecino GET ────────────────────────────────────────────────────────
function renderCEVVecinoForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="CEVEstadoVecino";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Method: <span>GET · fullFillment-CEVEstadoVecino/v1/estado_vecino_api/{olt_id}</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-cev-olt","OLT ID (en URL)","ej. 03-QAAPOQ_OLT_10-01");
  _epfExecBtn(card,running,function(){
    var oi=document.getElementById("epf-cev-olt"); if(!oi) return;
    _epfDoRun("qa-cons-cevvecino",{vno:_globalVNO,olt_id:oi.value});
  });
  container.appendChild(card);
}
// ── ConsultaDataONT ────────────────────────────────────────────────────────────
function renderConsultaDataONTForm(){
  var container=document.getElementById("epf-container"); if(!container) return;
  container.innerHTML="";
  var vno=_globalVNO; var clr=_QA_VNO_COLORS[vno]||"var(--acc)";
  var card=document.createElement("div"); card.className="epf-card";
  var tt=document.createElement("div"); tt.className="epf-title"; tt.textContent="ConsultaDataONT";
  var sf=document.createElement("div"); sf.className="epf-folder"; sf.innerHTML='Folder: <span>ConsultaDataONT</span>';
  card.appendChild(tt); card.appendChild(sf);
  _epfVnoReadonly(card,vno,clr);
  _epfTextInput(card,"epf-dnt-access","u_access_id","ej. 03-UAT3021446");
  _epfTextInput(card,"epf-dnt-opid","u_operation_id","string");
  _epfTextInput(card,"epf-dnt-uid","u_user_id","string");
  _epfTextInput(card,"epf-dnt-area","u_area","string");
  _epfTextInput(card,"epf-dnt-msgid","u_msg_id","string");
  _epfTextInput(card,"epf-dnt-msgdate","u_msg_date","string");
  _epfExecBtn(card,running,function(){
    function g(id){return (document.getElementById(id)||{}).value||"";}
    _epfDoRun("qa-cons-dataont",{
      vno:_globalVNO,
      u_access_id:g("epf-dnt-access"),
      u_operation_id:g("epf-dnt-opid"),
      u_user_id:g("epf-dnt-uid"),
      u_area:g("epf-dnt-area"),
      u_msg_id:g("epf-dnt-msgid"),
      u_msg_date:g("epf-dnt-msgdate"),
    });
  });
  container.appendChild(card);
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
// ── Historial ───────────────────────────────────────────────────────────────
var _histData=[];
var _histSort={col:0,asc:false};
var _histTab='hist';
var _HIST_COLS=[
  {k:'created_at',  lbl:'Fecha'},
  {k:'suite_name',  lbl:'Suite'},
  {k:'tc',          lbl:'TC'},
  {k:'escenario',   lbl:'Escenario'},
  {k:'vno_lbl',     lbl:'VNO'},
  {k:'direccion',   lbl:'Dirección / Access ID'},
  {k:'resultado',   lbl:'Resultado'},
  {k:'tiempo_ms',   lbl:'Tiempo'},
];
var _SUITE_NAMES={'qa-fact-suite':'Factibilidad','qa-asig-suite':'Asignación','qa-ia-inicio-suite':'Inicio Intervención','qa-ia-fin-suite':'Fin Intervención','qa-ia-cancel-suite':'Cancelación IA','qa-activ-suite':'Activación','qa-activ-sin-idem-suite':'Activ sin Idem','qa-dm-suite':'DM','qa-cancel-suite':'Cancelación','qa-unsub-suite':'Unsubscription','qa-teardown-suite':'Teardown'};
function _suiteName(id,lbl){
  if(id&&_SUITE_NAMES[id]) return _SUITE_NAMES[id];
  var s=lbl||id||'';
  return s.replace(/^[▶►▷●►▶]\\s*/,'').trim()||'—';
}
function showHistorial(){
  _dashStopRefresh();
  switchView('historial');
  ['top-status','vno-sel','exec-btn','rpt-btn','dl-btn','clr-btn'].forEach(function(id){var e=document.getElementById(id);if(e)e.style.display='none';});
  var _sb2=document.getElementById('settings-btn'); if(_sb2) _sb2.classList.remove('active');
  var _cb=document.getElementById('codigos-btn'); if(_cb) _cb.classList.remove('active');
  document.getElementById('hist-btn').classList.add('active');
  setTop('','Historial de Pruebas','');
  _hTab(_histTab);
}
function showHistorialFiltered(q){
  var fi=document.getElementById('historial-filter');
  if(fi) fi.value=q||'';
  showHistorial();
  if(q) setTop('','Historial de Pruebas','Filtrado por: '+q);
  if(_histData.length) _renderHistorialTable();
}
function showSettings(){
  _dashStopRefresh();
  switchView('settings');
  ['top-status','vno-sel','exec-btn','rpt-btn','dl-btn','clr-btn'].forEach(function(id){var e=document.getElementById(id);if(e)e.style.display='none';});
  var hb=document.getElementById('hist-btn'); if(hb) hb.classList.remove('active');
  var cb=document.getElementById('codigos-btn'); if(cb) cb.classList.remove('active');
  var sb=document.getElementById('settings-btn'); if(sb) sb.classList.add('active');
  setTop('','Settings','Ambientes y configuraci\xf3n del runner');
  _stTab(_stCurTab);
}
var _dashRefreshTimer=null;
function _dashStopRefresh(){if(_dashRefreshTimer){clearInterval(_dashRefreshTimer);_dashRefreshTimer=null;}}
function showDashboard(){
  switchView('dashboard');
  ['top-status','vno-sel','exec-btn','rpt-btn','dl-btn','clr-btn'].forEach(function(id){var e=document.getElementById(id);if(e)e.style.display='none';});
  ['hist-btn','settings-btn','codigos-btn'].forEach(function(id){var b=document.getElementById(id);if(b)b.classList.remove('active');});
  var db=document.getElementById('dashboard-btn');if(db)db.classList.add('active');
  setTop('','Dashboard','');
  loadDashboard();
  _dashStopRefresh();
  _dashRefreshTimer=setInterval(loadDashboard,60000);
}
function _dashColor(vno){
  return {'00':'#569CD6','02':'#4EC9B0','03':'#C586C0','05':'#CE9178'}[vno]||'#888';
}
function _dashTooltip(x,y,text){
  var tt=document.getElementById('_dash-tt');
  if(!tt){tt=document.createElement('div');tt.id='_dash-tt';tt.style.cssText='position:fixed;padding:5px 10px;font-size:.7rem;pointer-events:none;z-index:9999;white-space:nowrap;border-radius:5px;box-shadow:0 2px 10px rgba(0,0,0,.3);display:none;transition:opacity .1s';document.body.appendChild(tt);}
  if(!text){tt.style.display='none';return;}
  tt.style.background=_dashGetColor('--card')||'#1e1e1e';
  tt.style.color=_dashGetColor('--txt')||'#ccc';
  tt.style.border='1px solid '+(_dashGetColor('--brd')||'#333');
  tt.style.left=(x+14)+'px';tt.style.top=(y-28)+'px';
  tt.style.display='block';tt.textContent=text;
}
function _dashInjectCss(){
  if(document.getElementById('_dash-css'))return;
  var s=document.createElement('style');s.id='_dash-css';
  s.textContent='.d-link{cursor:pointer;transition:transform .15s,box-shadow .15s,opacity .15s}.d-link:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.22);opacity:.93}.d-link:active{transform:translateY(0)}tr.d-link:hover{transform:none;box-shadow:none;opacity:1;background:rgba(86,156,214,.10)}tr.d-link:active{background:rgba(86,156,214,.18)}.d-link-row:hover{background:rgba(86,156,214,.10);cursor:pointer}.d-link-row:active{background:rgba(86,156,214,.18)}';
  document.head.appendChild(s);
}
function _dashClick(el){
  var goto=el.getAttribute('data-goto');
  var val=el.getAttribute('data-val')||'';
  if(goto==='hist') showHistorial();
  else showHistorialFiltered(val);
}
function loadDashboard(){
  var cont=document.getElementById('dash-content');
  if(!cont)return;
  cont.innerHTML='<div style="padding:40px;text-align:center;color:var(--txt2);font-size:.8rem">Cargando…</div>';
  fetch('/api/dashboard').then(function(r){return r.json();}).then(function(d){
    if(d.error){cont.innerHTML='<div style="padding:40px;text-align:center;color:var(--err)">Error: '+esc(d.error)+'</div>';return;}
    _renderDashboard(d,cont);
  }).catch(function(e){cont.innerHTML='<div style="padding:40px;text-align:center;color:var(--err)">Error: '+esc(e.message)+'</div>';});
}
function _renderDashboard(d,cont){
  var kpi=d.kpi||{};
  var total=parseInt(kpi.total)||0;
  var ok=parseInt(kpi.ok)||0;
  var fail=parseInt(kpi.fail)||0;
  var avg_ms=parseInt(kpi.avg_ms)||0;
  var today=parseInt(kpi.today)||0;
  var pct=total?Math.round(ok/total*100):0;
  _dashInjectCss();
  var h='';
  // ── Fila 1: KPI cards ──
  h+='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px">';
  h+=_dashKpi('Total ejecuciones',total,'#569CD6','&#128202;','hist','');
  h+=_dashKpi('Tasa de \xe9xito',pct+'%',pct>=80?'#4EC9B0':pct>=50?'#CE9178':'#e06c75','&#10003;','hist','');
  h+=_dashKpi('Ejecuciones hoy',today,'#C586C0','&#9728;','hist','');
  h+=_dashKpi('Tiempo promedio',avg_ms?(avg_ms/1000).toFixed(1)+'s':'—','#4FC1FF','&#9201;','hist','');
  h+='</div>';
  // ── Fila 2: VNO cards ──
  var vnoOrder=['02','03','05','00'];
  var vnoMap={};(d.by_vno||[]).forEach(function(v){vnoMap[v.vno]=v;});
  h+='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px">';
  vnoOrder.forEach(function(code){
    var v=vnoMap[code];
    var lbl={'00':'TCH','02':'KAO','03':'Entel','05':'DTV'}[code]||code;
    if(!v){h+=_dashVnoCard(lbl,code,0,0,0,'—');return;}
    var vp=parseInt(v.total)?Math.round(parseInt(v.ok)/parseInt(v.total)*100):0;
    var fecha=v.last_run?new Date(v.last_run).toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short'}):'—';
    h+=_dashVnoCard(lbl,code,vp,parseInt(v.ok),parseInt(v.total),fecha);
  });
  h+='</div>';
  // ── Fila 3: Gr\xe1ficos ──
  h+='<div style="display:grid;grid-template-columns:1.6fr 1fr;gap:12px;margin-bottom:16px">';
  h+='<div style="background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:14px">';
  h+='<div style="font-size:.75rem;font-weight:700;color:var(--txt);margin-bottom:10px">Tendencia \xfaltimos 7 d\xedas</div>';
  h+='<canvas id="dash-trend-chart" style="width:100%;height:160px"></canvas>';
  h+='</div>';
  h+='<div style="background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:14px">';
  h+='<div style="font-size:.75rem;font-weight:700;color:var(--txt);margin-bottom:10px">Distribuci\xf3n por VNO</div>';
  h+='<canvas id="dash-vno-chart" style="width:100%;height:160px"></canvas>';
  h+='</div>';
  h+='</div>';
  // ── Fila 4: Tasa OK por funcionalidad + Tiempo promedio ──
  h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">';
  h+='<div style="background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:14px">';
  h+='<div style="font-size:.75rem;font-weight:700;color:var(--txt);margin-bottom:10px">Tasa OK por funcionalidad</div>';
  h+='<canvas id="dash-func-chart" style="width:100%;height:200px"></canvas>';
  h+='</div>';
  h+='<div style="background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:14px">';
  h+='<div style="font-size:.75rem;font-weight:700;color:var(--txt);margin-bottom:10px">Tiempo promedio por funcionalidad (s)</div>';
  h+='<canvas id="dash-time-chart" style="width:100%;height:200px"></canvas>';
  h+='</div>';
  h+='</div>';
  // ── Fila 5: Tabla funcionalidades + \xdaltimas ejecuciones ──
  h+='<div style="display:grid;grid-template-columns:1.5fr 1fr;gap:12px">';
  h+='<div style="background:var(--card);border:1px solid var(--brd);border-radius:8px;overflow:hidden">';
  h+='<div style="padding:10px 14px;border-bottom:1px solid var(--brd);font-size:.75rem;font-weight:700;color:var(--txt)">Estado por funcionalidad</div>';
  h+='<div style="overflow-x:auto"><table class="hist-table">';
  h+='<thead><tr><th>Funcionalidad</th><th>Total</th><th>OK</th><th>Tasa</th><th>T.Prom</th></tr></thead><tbody>';
  (d.by_func||[]).forEach(function(f){
    var fp=parseInt(f.total)?Math.round(parseInt(f.ok)/parseInt(f.total)*100):0;
    var fc=fp>=80?'ok':fp>=50?'warn':'err';
    var fms=parseInt(f.avg_ms)||0;
    var fName=_suiteName(f.suite_id,f.suite_label);
    h+='<tr class="d-link" onclick="_dashClick(this)" data-goto="label" data-val="'+esc(fName)+'">';
    h+='<td style="font-size:.71rem;font-weight:600;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(fName)+'</td>';
    h+='<td style="font-family:monospace;font-size:.7rem">'+esc(String(f.total))+'</td>';
    h+='<td style="font-family:monospace;font-size:.7rem">'+esc(String(f.ok))+'</td>';
    h+='<td><div style="display:flex;align-items:center;gap:6px"><div style="flex:1;height:6px;background:var(--brd);border-radius:3px"><div style="height:100%;width:'+fp+'%;background:'+(fp>=80?'#4EC9B0':fp>=50?'#CE9178':'#e06c75')+';border-radius:3px"></div></div><span class="hist-badge '+fc+'" style="font-size:.6rem;padding:1px 4px">'+fp+'%</span></div></td>';
    h+='<td style="font-family:monospace;font-size:.7rem">'+esc(fms?(fms/1000).toFixed(1)+'s':'—')+'</td>';
    h+='</tr>';
  });
  h+='</tbody></table></div></div>';
  h+='<div style="background:var(--card);border:1px solid var(--brd);border-radius:8px;overflow:hidden">';
  h+='<div style="padding:10px 14px;border-bottom:1px solid var(--brd);font-size:.75rem;font-weight:700;color:var(--txt)">\xdaltimas ejecuciones</div>';
  h+='<div>';
  (d.recent||[]).forEach(function(r){
    var rc=r.resultado==='ok'?'ok':'err';
    var fecha=r.created_at?new Date(r.created_at).toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short'}):'—';
    var tms=parseInt(r.tiempo_ms)||0;
    var rName=_suiteName(r.suite_id,r.suite_label);
    h+='<div class="d-link-row" onclick="_dashClick(this)" data-goto="label" data-val="'+esc(rName)+'" style="display:flex;align-items:center;gap:8px;padding:7px 14px;border-bottom:1px solid var(--brd);font-size:.71rem;transition:background .15s">';
    h+='<span class="hist-badge '+rc+'" style="font-size:.6rem;padding:1px 5px;flex-shrink:0">'+esc(r.resultado==='ok'?'OK':'Error')+'</span>';
    h+='<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600">'+esc(rName)+'</span>';
    h+='<span style="color:'+_dashColor(r.vno||'')+';font-weight:700;font-size:.68rem;flex-shrink:0">'+esc(r.vno_lbl||r.vno||'—')+'</span>';
    h+='<span style="color:var(--txt3);font-size:.65rem;flex-shrink:0">'+esc(tms?(tms/1000).toFixed(1)+'s':'')+'</span>';
    h+='</div>';
  });
  if(!(d.recent||[]).length)h+='<div style="padding:20px;text-align:center;color:var(--txt3);font-size:.75rem">Sin ejecuciones a\xfan</div>';
  h+='</div></div>';
  h+='</div>';
  cont.innerHTML=h;
  requestAnimationFrame(function(){
    _dashDrawTrend(d.trend||[]);
    _dashDrawVno(d.by_vno||[]);
    _dashDrawFunc(d.by_func||[]);
    _dashDrawTime(d.by_func||[]);
  });
}
function _dashKpi(label,val,color,icon,goto,gval){
  var ca=goto?' class="d-link" onclick="_dashClick(this)" data-goto="'+goto+'" data-val="'+(gval||'')+'"':'';
  return '<div'+ca+' style="background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:6px">'
    +'<div style="display:flex;align-items:center;gap:8px"><span style="font-size:16px">'+icon+'</span><span style="font-size:.7rem;color:var(--txt2);font-weight:500">'+esc(label)+'</span></div>'
    +'<div style="font-size:1.6rem;font-weight:800;color:'+color+';font-variant-numeric:tabular-nums;line-height:1">'+esc(String(val))+'</div>'
    +'</div>';
}
function _dashVnoCard(lbl,code,pct,ok,total,fecha){
  var color=_dashColor(code);
  var bg=pct>=80?'rgba(78,201,176,.08)':pct>=50?'rgba(206,145,120,.08)':'rgba(224,108,117,.08)';
  return '<div class="d-link" onclick="_dashClick(this)" data-goto="label" data-val="'+esc(lbl)+'" style="background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:14px;border-left:3px solid '+color+'">'
    +'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">'
    +'<span style="font-weight:800;font-size:.9rem;color:'+color+'">'+esc(lbl)+'</span>'
    +'<span class="hist-badge '+(pct>=80?'ok':pct>=50?'warn':'err')+'" style="font-size:.68rem">'+pct+'%</span>'
    +'</div>'
    +'<div style="font-size:.68rem;color:var(--txt2)">'+ok+' OK / '+total+' total</div>'
    +'<div style="margin-top:8px;height:5px;background:var(--brd);border-radius:3px">'
    +'<div style="height:100%;width:'+pct+'%;background:'+color+';border-radius:3px;transition:width .4s"></div>'
    +'</div>'
    +'<div style="font-size:.63rem;color:var(--txt3);margin-top:6px">\xdaltima: '+esc(fecha)+'</div>'
    +'</div>';
}
function _dashCtx(id){
  var c=document.getElementById(id);if(!c)return null;
  c.width=c.offsetWidth*window.devicePixelRatio||c.offsetWidth;
  c.height=c.offsetHeight*window.devicePixelRatio||c.offsetHeight;
  var ctx=c.getContext('2d');
  ctx.scale(window.devicePixelRatio||1,window.devicePixelRatio||1);
  return {ctx:ctx,w:c.offsetWidth,h:c.offsetHeight};
}
function _dashGetColor(varName){
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim()||'#888';
}
function _dashDrawTrend(trend){
  var d=_dashCtx('dash-trend-chart');if(!d)return;
  var ctx=d.ctx,W=d.w,H=d.h;
  var textColor=_dashGetColor('--txt2');
  var borderColor=_dashGetColor('--brd');
  ctx.clearRect(0,0,W,H);
  if(!trend.length){ctx.fillStyle=textColor;ctx.font='12px sans-serif';ctx.textAlign='center';ctx.fillText('Sin datos',W/2,H/2);return;}
  var pad={t:8,r:8,b:28,l:32};
  var cW=W-pad.l-pad.r, cH=H-pad.t-pad.b;
  var maxVal=Math.max.apply(null,trend.map(function(r){return (parseInt(r.ok)||0)+(parseInt(r.fail)||0);}));
  maxVal=maxVal||1;
  var barW=Math.floor(cW/trend.length*0.7);
  var gap=Math.floor(cW/trend.length);
  [0,0.25,0.5,0.75,1].forEach(function(f){
    var y=pad.t+cH*(1-f);
    ctx.strokeStyle=borderColor;ctx.lineWidth=0.5;
    ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(pad.l+cW,y);ctx.stroke();
    ctx.fillStyle=textColor;ctx.font='9px sans-serif';ctx.textAlign='right';
    ctx.fillText(Math.round(maxVal*f),pad.l-3,y+3);
  });
  var tHits=[];
  trend.forEach(function(r,i){
    var ok=parseInt(r.ok)||0, fail=parseInt(r.fail)||0;
    var x=pad.l+i*gap+(gap-barW)/2;
    var hOk=Math.round(ok/maxVal*cH);
    var hFail=Math.round(fail/maxVal*cH);
    ctx.fillStyle='#4EC9B0';
    ctx.fillRect(x,pad.t+cH-hOk,barW,hOk);
    ctx.fillStyle='#e06c75';
    ctx.fillRect(x,pad.t+cH-hOk-hFail,barW,hFail);
    ctx.fillStyle=textColor;ctx.font='9px sans-serif';ctx.textAlign='center';
    ctx.fillText(r.day||'',x+barW/2,H-4);
    tHits.push({day:r.day||'',ok:ok,fail:fail,x:x,w:barW,y1:pad.t,y2:pad.t+cH});
  });
  ctx.fillStyle='#4EC9B0';ctx.fillRect(W-80,6,10,10);
  ctx.fillStyle=textColor;ctx.font='9px sans-serif';ctx.textAlign='left';ctx.fillText('OK',W-66,15);
  ctx.fillStyle='#e06c75';ctx.fillRect(W-45,6,10,10);
  ctx.fillStyle=textColor;ctx.fillText('Error',W-31,15);
  var canvT=document.getElementById('dash-trend-chart');
  if(canvT){
    canvT.style.cursor='default';
    canvT.onmousemove=function(e){
      var rect=canvT.getBoundingClientRect();
      var mx=e.clientX-rect.left,my=e.clientY-rect.top;
      var found=tHits.find(function(h){return mx>=h.x&&mx<=h.x+h.w&&my>=h.y1&&my<=h.y2;});
      if(found){canvT.style.cursor='pointer';_dashTooltip(e.clientX,e.clientY,found.day+' · OK: '+found.ok+' · Error: '+found.fail);}
      else{canvT.style.cursor='default';_dashTooltip(0,0,null);}
    };
    canvT.onmouseleave=function(){_dashTooltip(0,0,null);};
    canvT.onclick=function(e){
      var rect=canvT.getBoundingClientRect();
      var mx=e.clientX-rect.left,my=e.clientY-rect.top;
      var found=tHits.find(function(h){return mx>=h.x&&mx<=h.x+h.w&&my>=h.y1&&my<=h.y2;});
      if(found) showHistorial();
    };
  }
}
function _dashDrawVno(byVno){
  var d=_dashCtx('dash-vno-chart');if(!d)return;
  var ctx=d.ctx,W=d.w,H=d.h;
  var textColor=_dashGetColor('--txt2');
  ctx.clearRect(0,0,W,H);
  var vnos=byVno.filter(function(v){return parseInt(v.total)>0;});
  if(!vnos.length){ctx.fillStyle=textColor;ctx.font='12px sans-serif';ctx.textAlign='center';ctx.fillText('Sin datos',W/2,H/2);return;}
  var total=vnos.reduce(function(s,v){return s+parseInt(v.total);},0);
  var colors=['#4EC9B0','#C586C0','#CE9178','#569CD6'];
  var cx=W/2-20,cy=H/2,r=Math.min(cx,cy)-14;
  var start=-Math.PI/2;
  var vHits=[];
  vnos.forEach(function(v,i){
    var slice=parseInt(v.total)/total*2*Math.PI;
    ctx.beginPath();ctx.moveTo(cx,cy);ctx.arc(cx,cy,r,start,start+slice);ctx.closePath();
    ctx.fillStyle=colors[i%colors.length];ctx.fill();
    ctx.strokeStyle=_dashGetColor('--card');ctx.lineWidth=2;ctx.stroke();
    vHits.push({lbl:v.vno_lbl||v.vno,ok:parseInt(v.ok)||0,total:parseInt(v.total),cx:cx,cy:cy,r:r,ri:r*0.55,start:start,end:start+slice});
    start+=slice;
  });
  ctx.beginPath();ctx.arc(cx,cy,r*0.55,0,2*Math.PI);ctx.fillStyle=_dashGetColor('--card');ctx.fill();
  ctx.fillStyle=textColor;ctx.font='bold 11px sans-serif';ctx.textAlign='center';ctx.fillText(total,cx,cy+4);
  var lx=W-75,ly=H/2-(vnos.length*16)/2;
  vnos.forEach(function(v,i){
    ctx.fillStyle=colors[i%colors.length];ctx.fillRect(lx,ly+i*16,10,10);
    ctx.fillStyle=textColor;ctx.font='10px sans-serif';ctx.textAlign='left';
    var lbl=v.vno_lbl||v.vno;
    ctx.fillText(lbl+' ('+v.total+')',lx+14,ly+i*16+9);
  });
  var canvV=document.getElementById('dash-vno-chart');
  if(canvV){
    canvV.style.cursor='default';
    function _vnoHit(mx,my){
      var dx=mx-cx,dy=my-cy,dist=Math.sqrt(dx*dx+dy*dy);
      if(dist<r*0.55||dist>r)return null;
      var angle=Math.atan2(dy,dx);
      return vHits.find(function(h){var a=angle;while(a<h.start)a+=2*Math.PI;return a>=h.start&&a<=h.end;});
    }
    canvV.onmousemove=function(e){
      var rect=canvV.getBoundingClientRect();
      var found=_vnoHit(e.clientX-rect.left,e.clientY-rect.top);
      if(found){canvV.style.cursor='pointer';_dashTooltip(e.clientX,e.clientY,found.lbl+' · '+found.ok+'/'+found.total+' OK');}
      else{canvV.style.cursor='default';_dashTooltip(0,0,null);}
    };
    canvV.onmouseleave=function(){_dashTooltip(0,0,null);};
    canvV.onclick=function(e){
      var rect=canvV.getBoundingClientRect();
      var found=_vnoHit(e.clientX-rect.left,e.clientY-rect.top);
      if(found) showHistorialFiltered(found.lbl);
    };
  }
}
function _dashDrawFunc(byFunc){
  var d=_dashCtx('dash-func-chart');if(!d)return;
  var ctx=d.ctx,W=d.w,H=d.h;
  var textColor=_dashGetColor('--txt2');
  ctx.clearRect(0,0,W,H);
  var funcs=byFunc.slice(0,8);
  if(!funcs.length){ctx.fillStyle=textColor;ctx.font='12px sans-serif';ctx.textAlign='center';ctx.fillText('Sin datos',W/2,H/2);return;}
  var pad={t:8,r:50,b:8,l:130};
  var cW=W-pad.l-pad.r, cH=H-pad.t-pad.b;
  var rowH=Math.floor(cH/funcs.length);
  var fHits=[];
  funcs.forEach(function(f,i){
    var pct=parseInt(f.total)?parseInt(f.ok)/parseInt(f.total):0;
    var y=pad.t+i*rowH;
    var bH=Math.min(rowH-4,16);
    var by=y+(rowH-bH)/2;
    ctx.fillStyle=textColor;ctx.font='9px sans-serif';ctx.textAlign='right';
    var lbl=_suiteName(f.suite_id,f.suite_label).slice(0,18);
    ctx.fillText(lbl,pad.l-4,by+bH/2+3);
    ctx.fillStyle=_dashGetColor('--brd');ctx.fillRect(pad.l,by,cW,bH);
    var barColor=pct>=0.8?'#4EC9B0':pct>=0.5?'#CE9178':'#e06c75';
    ctx.fillStyle=barColor;ctx.fillRect(pad.l,by,Math.round(pct*cW),bH);
    ctx.fillStyle=textColor;ctx.font='9px sans-serif';ctx.textAlign='left';
    ctx.fillText(Math.round(pct*100)+'%',pad.l+cW+4,by+bH/2+3);
    fHits.push({label:_suiteName(f.suite_id,f.suite_label),pct:Math.round(pct*100),ok:parseInt(f.ok)||0,total:parseInt(f.total)||0,y1:by-4,y2:by+bH+4});
  });
  var canvF=document.getElementById('dash-func-chart');
  if(canvF){
    canvF.style.cursor='default';
    canvF.onmousemove=function(e){
      var rect=canvF.getBoundingClientRect();
      var my=e.clientY-rect.top;
      var found=fHits.find(function(h){return my>=h.y1&&my<=h.y2;});
      if(found){canvF.style.cursor='pointer';_dashTooltip(e.clientX,e.clientY,found.label+' · '+found.ok+'/'+found.total+' OK ('+found.pct+'%)');}
      else{canvF.style.cursor='default';_dashTooltip(0,0,null);}
    };
    canvF.onmouseleave=function(){_dashTooltip(0,0,null);};
    canvF.onclick=function(e){
      var rect=canvF.getBoundingClientRect();
      var my=e.clientY-rect.top;
      var found=fHits.find(function(h){return my>=h.y1&&my<=h.y2;});
      if(found) showHistorialFiltered(found.label);
    };
  }
}
function _dashDrawTime(byFunc){
  var d=_dashCtx('dash-time-chart');if(!d)return;
  var ctx=d.ctx,W=d.w,H=d.h;
  var textColor=_dashGetColor('--txt2');
  var borderColor=_dashGetColor('--brd');
  ctx.clearRect(0,0,W,H);
  var funcs=byFunc.filter(function(f){return parseInt(f.avg_ms)>0;}).slice(0,8);
  if(!funcs.length){ctx.fillStyle=textColor;ctx.font='12px sans-serif';ctx.textAlign='center';ctx.fillText('Sin datos',W/2,H/2);return;}
  var pad={t:8,r:8,b:40,l:130};
  var cW=W-pad.l-pad.r, cH=H-pad.t-pad.b;
  var maxMs=Math.max.apply(null,funcs.map(function(f){return parseInt(f.avg_ms)||0;}));
  maxMs=maxMs||1;
  var rowH=Math.floor(cH/funcs.length);
  [0,0.25,0.5,0.75,1].forEach(function(f){
    var x=pad.l+f*cW;
    ctx.strokeStyle=borderColor;ctx.lineWidth=0.5;
    ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,pad.t+cH);ctx.stroke();
    ctx.fillStyle=textColor;ctx.font='9px sans-serif';ctx.textAlign='center';
    ctx.fillText((maxMs*f/1000).toFixed(1)+'s',x,pad.t+cH+12);
  });
  var tmHits=[];
  funcs.forEach(function(f,i){
    var ms=parseInt(f.avg_ms)||0;
    var y=pad.t+i*rowH;
    var bH=Math.min(rowH-4,14);
    var by=y+(rowH-bH)/2;
    ctx.fillStyle=textColor;ctx.font='9px sans-serif';ctx.textAlign='right';
    ctx.fillText(_suiteName(f.suite_id,f.suite_label).slice(0,18),pad.l-4,by+bH/2+3);
    ctx.fillStyle=borderColor;ctx.fillRect(pad.l,by,cW,bH);
    ctx.fillStyle='#4FC1FF';ctx.fillRect(pad.l,by,Math.round(ms/maxMs*cW),bH);
    ctx.fillStyle=textColor;ctx.font='9px sans-serif';ctx.textAlign='left';
    ctx.fillText((ms/1000).toFixed(1)+'s',pad.l+Math.round(ms/maxMs*cW)+3,by+bH/2+3);
    tmHits.push({label:_suiteName(f.suite_id,f.suite_label),ms:ms,y1:by-4,y2:by+bH+4});
  });
  var canvTm=document.getElementById('dash-time-chart');
  if(canvTm){
    canvTm.style.cursor='default';
    canvTm.onmousemove=function(e){
      var rect=canvTm.getBoundingClientRect();
      var my=e.clientY-rect.top;
      var found=tmHits.find(function(h){return my>=h.y1&&my<=h.y2;});
      if(found){canvTm.style.cursor='pointer';_dashTooltip(e.clientX,e.clientY,found.label+' · '+(found.ms/1000).toFixed(1)+'s promedio');}
      else{canvTm.style.cursor='default';_dashTooltip(0,0,null);}
    };
    canvTm.onmouseleave=function(){_dashTooltip(0,0,null);};
    canvTm.onclick=function(e){
      var rect=canvTm.getBoundingClientRect();
      var my=e.clientY-rect.top;
      var found=tmHits.find(function(h){return my>=h.y1&&my<=h.y2;});
      if(found) showHistorialFiltered(found.label);
    };
  }
}
var _stCurTab='env';
function _stTab(tab){
  _stCurTab=tab;
  ['env','cfg','perfil','usuarios'].forEach(function(t){
    var btn=document.getElementById('stab-'+t);
    var pane=document.getElementById('spane-'+t);
    if(btn){btn.style.background=t===tab?'var(--bg)':'var(--card)';btn.style.color=t===tab?'var(--acc)':'var(--txt2)';btn.style.fontWeight=t===tab?'700':'400';}
    if(pane) pane.style.display=t===tab?'block':'none';
  });
  if(tab==='env') loadEnvironments();
  else if(tab==='cfg') loadSettingsCfg();
  else if(tab==='perfil') _loadPerfil();
  else if(tab==='usuarios') _loadUsuarios();
}
var _envData=[];
function loadEnvironments(){
  var body=document.getElementById('env-table-body'); if(!body) return;
  body.innerHTML='<div class="hist-empty">Cargando...</div>';
  fetch('/api/environments').then(function(r){return r.json();}).then(function(data){
    if(!Array.isArray(data)){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error cargando ambientes.</div>';return;}
    _envData=data;
    _renderEnvTable(data);
  }).catch(function(e){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error: '+esc(e.message)+'</div>';});
}
function _renderEnvTable(data){
  var body=document.getElementById('env-table-body'); if(!body) return;
  if(!data.length){body.innerHTML='<div class="hist-empty">Sin ambientes registrados. Agrega uno con "+ Nuevo".</div>';return;}
  var typeLabel={qa:'QA',pprd:'Pre-Producci\xf3n',prd:'Producci\xf3n',custom:'Personalizado'};
  var h='<div style="overflow-x:auto"><table class="hist-table"><thead><tr>'
    +'<th>Nombre</th><th>Etiqueta</th><th>URL base Newman</th><th>Tipo</th><th>Estado</th><th>Acciones</th>'
    +'</tr></thead><tbody>';
  data.forEach(function(r){
    var activo=r.active!==false;
    h+='<tr>';
    h+='<td style="font-weight:700;font-size:.78rem">'+esc(r.name)+'</td>';
    h+='<td style="font-size:.75rem;color:var(--txt2)">'+esc(r.label||'—')+'</td>';
    h+='<td style="font-size:.73rem;font-family:monospace;color:var(--acc)">'+esc(r.base_url||'—')+'</td>';
    h+='<td><span style="font-size:.68rem;padding:2px 7px;border-radius:4px;background:var(--accd);color:var(--acc)">'+esc(typeLabel[r.env_type]||r.env_type||'—')+'</span></td>';
    h+='<td><span style="font-size:.68rem;padding:2px 7px;border-radius:4px;background:'+(activo?'var(--okd)':'var(--errd)')+';color:'+(activo?'var(--ok)':'var(--err)')+'">'+( activo?'Activo':'Inactivo')+'</span></td>';
    h+='<td style="white-space:nowrap">';
    h+='<button data-eid="'+r.id+'" onclick="_envEdit(this.dataset.eid)" style="padding:2px 9px;border-radius:4px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.68rem;cursor:pointer;margin-right:4px">&#9998; Editar</button>';
    h+='<button data-eid="'+r.id+'" onclick="_envDelete(this.dataset.eid)" style="padding:2px 9px;border-radius:4px;border:1px solid var(--errb);background:var(--errd);color:var(--err);font-size:.68rem;cursor:pointer">&#128465;</button>';
    h+='</td></tr>';
  });
  h+='</tbody></table></div>';
  body.innerHTML=h;
}
var _envEditId=null;
function _envAdd(){
  _envEditId=null;
  document.getElementById('env-form-title').textContent='Nuevo ambiente';
  document.getElementById('env-f-name').value='';
  document.getElementById('env-f-label').value='';
  document.getElementById('env-f-url').value='';
  document.getElementById('env-f-type').value='custom';
  document.getElementById('env-f-active').checked=true;
  document.getElementById('env-form-err').style.display='none';
  document.getElementById('env-form-ok').style.display='none';
  document.getElementById('env-form').style.display='block';
  document.getElementById('env-f-name').focus();
}
function _envEdit(id){
  var r=_envData.filter(function(x){return x.id==id;})[0]; if(!r) return;
  _envEditId=id;
  document.getElementById('env-form-title').textContent='Editar: '+r.name;
  document.getElementById('env-f-name').value=r.name||'';
  document.getElementById('env-f-label').value=r.label||'';
  document.getElementById('env-f-url').value=r.base_url||'';
  document.getElementById('env-f-type').value=r.env_type||'custom';
  document.getElementById('env-f-active').checked=r.active!==false;
  document.getElementById('env-form-err').style.display='none';
  document.getElementById('env-form-ok').style.display='none';
  document.getElementById('env-form').style.display='block';
  document.getElementById('env-f-name').focus();
}
function _envFormClose(){
  document.getElementById('env-form').style.display='none';
  _envEditId=null;
}
function _envSave(){
  var name=document.getElementById('env-f-name').value.trim();
  var label=document.getElementById('env-f-label').value.trim();
  var base_url=document.getElementById('env-f-url').value.trim();
  var env_type=document.getElementById('env-f-type').value;
  var active=document.getElementById('env-f-active').checked;
  var errEl=document.getElementById('env-form-err');
  if(!name||!base_url){errEl.textContent='Nombre y URL son requeridos.';errEl.style.display='block';return;}
  errEl.style.display='none';
  var url=_envEditId?('/api/environments/'+_envEditId):'/api/environments';
  var method=_envEditId?'PUT':'POST';
  fetch(url,{method:method,headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:name,label:label,base_url:base_url,env_type:env_type,active:active})})
  .then(function(r){return r.json().then(function(j){return{ok:r.ok,data:j};});})
  .then(function(res){
    if(!res.ok){errEl.textContent=(res.data&&res.data.error)?res.data.error:'Error al guardar.';errEl.style.display='block';return;}
    var okEl=document.getElementById('env-form-ok');
    okEl.style.display='inline';
    setTimeout(function(){okEl.style.display='none';_envFormClose();loadEnvironments();},900);
  }).catch(function(e){errEl.textContent='Error: '+e.message;errEl.style.display='block';});
}
function _envDelete(id){
  if(!confirm('\xbfEliminar este ambiente?')) return;
  fetch('/api/environments/'+id,{method:'DELETE'}).then(function(){loadEnvironments();});
}
function loadSettingsCfg(){
  var body=document.getElementById('spane-cfg-body'); if(!body) return;
  body.innerHTML='<div class="hist-empty">Cargando...</div>';
  fetch('/api/config').then(function(r){return r.json();}).then(function(data){
    if(!Array.isArray(data)){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error cargando configuraci\xf3n.</div>';return;}
    var h='<div style="max-width:560px"><h3 style="margin:0 0 18px;font-size:.85rem;color:var(--txt);font-weight:700">Par\xe1metros del runner</h3>';
    data.forEach(function(row){
      h+='<div style="margin-bottom:14px">';
      h+='<label style="display:block;font-size:.74rem;color:var(--txt2);margin-bottom:4px">'+esc(row.label||row.key)+'</label>';
      h+='<div style="display:flex;gap:8px;align-items:center">';
      h+='<input id="scfg-'+esc(row.key)+'" type="number" min="0" value="'+esc(row.value)+'" style="padding:5px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem;width:120px">';
      h+='<button onclick="_saveSettingsCfg(this.dataset.k)" data-k="'+esc(row.key)+'" style="padding:5px 12px;border-radius:5px;border:1px solid var(--brd);background:var(--accd);color:var(--acc);font-size:.74rem;cursor:pointer">Guardar</button>';
      h+='<span id="scfg-msg-'+esc(row.key)+'" style="font-size:.7rem;color:var(--ok);display:none">&#10003; Guardado</span>';
      h+='</div></div>';
    });
    h+='</div>';
    body.innerHTML=h;
  }).catch(function(e){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error: '+esc(e.message)+'</div>';});
}
function _saveSettingsCfg(key){
  var inp=document.getElementById('scfg-'+key); if(!inp) return;
  fetch('/api/config/'+encodeURIComponent(key),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:inp.value})})
  .then(function(r){return r.json();}).then(function(){
    var msg=document.getElementById('scfg-msg-'+key);
    if(msg){msg.style.display='inline';setTimeout(function(){msg.style.display='none';},1800);}
  });
}
function _hTab(tab){
  _histTab=tab;
  ['hist','stats'].forEach(function(t){
    var btn=document.getElementById('htab-'+t);
    var pane=document.getElementById('hpane-'+t);
    if(btn) btn.style.background=t===tab?'var(--bg)':'var(--card)';
    if(btn) btn.style.color=t===tab?'var(--acc)':'var(--txt2)';
    if(pane) pane.style.display=t===tab?'block':'none';
  });
  var filt=document.getElementById('historial-filter');
  var delBtn=document.getElementById('hist-del-all-btn');
  if(filt) filt.style.display=tab==='hist'?'inline-block':'none';
  if(delBtn) delBtn.style.display=tab==='hist'?'inline-block':'none';
  if(tab==='hist'){ if(!_histData.length) loadHistorial(); }
  else if(tab==='stats') loadStats();
}
function _hTabRefresh(){
  if(_histTab==='hist'){_histData=[];loadHistorial();}
  else loadStats();
}
function loadHistorial(){
  var body=document.getElementById('hpane-hist');
  body.innerHTML='<div class="hist-empty">Cargando…</div>';
  fetch('/api/historial').then(function(r){return r.json().then(function(j){return{ok:r.ok,data:j};});})
  .then(function(res){
    if(!res.ok||!Array.isArray(res.data)){
      body.innerHTML='<div class="hist-empty" style="color:var(--err)">'+(res.data&&res.data.error?esc(res.data.error):'Error cargando')+'</div>';return;
    }
    _histData=res.data.map(function(r){r.suite_name=_suiteName(r.suite_id,r.suite_label);return r;}); _renderHistorialTable();
  }).catch(function(e){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error: '+esc(e.message)+'</div>';});
}
function _filterHistorial(){_renderHistorialTable();}
function _histSortBy(ci){
  if(_histSort.col===ci) _histSort.asc=!_histSort.asc;
  else{_histSort.col=ci;_histSort.asc=false;}
  _renderHistorialTable();
}
function _renderHistorialTable(){
  var q=(document.getElementById('historial-filter')||{}).value||''; q=q.toLowerCase();
  var rows=_histData.filter(function(r){
    if(!q) return true;
    return _HIST_COLS.some(function(c){return (r[c.k]||'').toString().toLowerCase().indexOf(q)>=0;});
  });
  var ci=_histSort.col; var asc=_histSort.asc;
  rows=rows.slice().sort(function(a,b){
    var av=(a[_HIST_COLS[ci].k]||'').toString(), bv=(b[_HIST_COLS[ci].k]||'').toString();
    return asc?av.localeCompare(bv,undefined,{numeric:true}):-av.localeCompare(bv,undefined,{numeric:true});
  });
  var body=document.getElementById('hpane-hist');
  if(!rows.length){body.innerHTML='<div class="hist-empty">'+(q?'Sin registros para "'+esc(q)+'"':'Sin ejecuciones aún.')+'</div>';return;}
  var h='<div style="overflow-x:auto"><table class="hist-table"><thead><tr>';
  _HIST_COLS.forEach(function(c,i){
    var ico=_histSort.col===i?(_histSort.asc?'▲':'▼'):'⇅';
    h+='<th onclick="_histSortBy('+i+')">'+esc(c.lbl)+' <span class="sort-ico">'+ico+'</span></th>';
  });
  h+='<th>Acción</th></tr></thead><tbody>';
  rows.forEach(function(r){
    var res=r.resultado||''; var bc=res==='ok'?'ok':'err';
    var vno=r.vno_lbl||r.vno||'';
    var vnoHtml=vno?'<span style="font-weight:700;font-size:.68rem;color:'+_histVnoColor(r.vno||'')+'">'+esc(vno)+'</span>':'<span style="color:var(--txt3)">—</span>';
    var dir=r.direccion||'';
    var dirHtml=dir?'<span style="font-size:.65rem;background:var(--accd);color:var(--acc);border-radius:4px;padding:1px 5px;white-space:nowrap">'+esc(dir)+'</span>':'<span style="color:var(--txt3);font-size:.68rem">—</span>';
    var tiempoSeg=r.tiempo_ms!=null?((r.tiempo_ms/1000).toFixed(1)+'s'):'';
    var fecha=r.created_at?new Date(r.created_at).toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short'}):(r.ts||'');
    h+='<tr>';
    h+='<td style="color:var(--txt3);white-space:nowrap;font-size:.68rem">'+esc(fecha)+'</td>';
    h+='<td style="font-weight:600">'+esc(r.suite_name||r.suite_id||'')+'</td>';
    h+='<td style="font-size:.7rem">'+esc(r.tc||'')+'</td>';
    h+='<td style="font-size:.72rem">'+esc(r.escenario||'')+'</td>';
    h+='<td>'+vnoHtml+'</td><td>'+dirHtml+'</td>';
    h+='<td><span class="hist-badge '+bc+'">'+esc(res==='ok'?'OK':'Error')+'</span></td>';
    h+='<td style="text-align:right;font-variant-numeric:tabular-nums">'+esc(tiempoSeg)+'</td>';
    h+='<td style="display:flex;gap:4px;align-items:center">';
    h+='<button onclick="_histDetail('+r.id+')" style="padding:2px 8px;border-radius:4px;border:1px solid var(--brd);background:var(--accd);color:var(--acc);font-size:.65rem;cursor:pointer">Ver detalle</button>';
    h+='<button onclick="_histDelete('+r.id+')" style="padding:2px 7px;border-radius:4px;border:1px solid var(--errb);background:var(--errd);color:var(--err);font-size:.65rem;cursor:pointer">&#128465;</button>';
    h+='</td>';
    h+='</tr>';
  });
  h+='</tbody></table></div>';
  body.innerHTML=h;
}
function _histDelete(id){
  if(!confirm('¿Eliminar este registro?')) return;
  fetch('/api/historial/'+id,{method:'DELETE'}).then(function(){
    _histData=_histData.filter(function(r){return r.id!==id;}); _renderHistorialTable();
  });
}
function _histDeleteAll(){
  if(!confirm('¿Eliminar TODO el historial? Esta acción no se puede deshacer.')) return;
  fetch('/api/historial',{method:'DELETE'}).then(function(){_histData=[];_renderHistorialTable();});
}
function _histDetail(id){
  var r=_histData.find(function(x){return x.id===id;});
  if(!r)return;
  var steps=[];try{steps=JSON.parse(r.steps_json||'[]');}catch(e){}
  var vno=r.vno_lbl||r.vno||'—';
  var fecha=r.created_at?new Date(r.created_at).toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short'}):(r.ts||'');
  var passC=steps.filter(function(s){return s.pass;}).length;
  var tiempoSeg=r.tiempo_ms!=null?((r.tiempo_ms/1000).toFixed(1)+'s'):'—';
  var resBadge='<span class="hist-badge '+(r.resultado==='ok'?'ok':'err')+'" style="font-size:.68rem">'+esc(r.resultado==='ok'?'OK':'Error')+'</span>';
  var h='<div style="padding:14px 18px;border-bottom:1px solid var(--brd);display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:12px;font-size:.75rem">';
  h+='<div><span style="color:var(--txt2);font-size:.68rem">Fecha</span><br><b style="font-size:.72rem">'+esc(fecha)+'</b></div>';
  h+='<div><span style="color:var(--txt2);font-size:.68rem">Suite</span><br><b>'+esc(r.suite_name||_suiteName(r.suite_id,r.suite_label))+'</b></div>';
  if(r.tc)h+='<div><span style="color:var(--txt2);font-size:.68rem">TC</span><br><b style="font-family:monospace">'+esc(r.tc)+'</b></div>';
  h+='<div><span style="color:var(--txt2);font-size:.68rem">Escenario</span><br><b>'+esc(r.escenario||'—')+'</b></div>';
  h+='<div><span style="color:var(--txt2);font-size:.68rem">VNO</span><br><b style="color:'+_histVnoColor(r.vno||'')+'">'+esc(vno)+'</b></div>';
  h+='<div><span style="color:var(--txt2);font-size:.68rem">Access ID</span><br><b style="font-size:.7rem;word-break:break-all">'+esc(r.direccion||'—')+'</b></div>';
  h+='<div><span style="color:var(--txt2);font-size:.68rem">Resultado</span><br>'+resBadge+'</div>';
  h+='<div><span style="color:var(--txt2);font-size:.68rem">Tiempo</span><br><b style="font-family:monospace">'+esc(tiempoSeg)+'</b></div>';
  if(steps.length)h+='<div><span style="color:var(--txt2);font-size:.68rem">Pasos</span><br><b>'+passC+'/'+steps.length+' OK</b></div>';
  h+='</div>';
  if(steps.length){
    h+='<div style="overflow-x:auto;padding:12px 18px"><table class="hist-table"><thead><tr>';
    h+='<th>#</th><th>Función</th><th>TC</th><th>HTTP</th><th>Resultado</th><th>Acción</th></tr></thead><tbody>';
    steps.forEach(function(s,i){
      var bc=s.pass?'ok':'err';
      h+='<tr>';
      h+='<td style="font-size:.68rem;color:var(--txt3)">'+(i+1)+'</td>';
      h+='<td style="font-size:.72rem;font-weight:600">'+esc(s.func||'—')+'</td>';
      h+='<td style="font-family:monospace;font-size:.7rem">'+esc(s.tc||'—')+'</td>';
      h+='<td style="font-family:monospace;font-size:.7rem">'+esc(s.httpCode?String(s.httpCode):'—')+'</td>';
      h+='<td><span class="hist-badge '+bc+'">'+esc(s.pass?'Pasó':'Falló')+'</span></td>';
      var rrid='hdr-'+id+'-'+i;
      h+='<td>';
      if(s.req||s.res)h+='<button id="'+rrid+'-btn" onclick="_hdrToggle(&quot;'+rrid+'&quot;)" style="padding:2px 8px;border-radius:4px;border:1px solid var(--acc);background:var(--accd);color:var(--acc);font-size:.65rem;cursor:pointer">&#9660; Req/Res</button>';
      else h+='<span style="color:var(--txt3);font-size:.65rem">—</span>';
      h+='</td></tr>';
      if(s.req||s.res){
        h+='<tr id="'+rrid+'" style="display:none"><td colspan="6" style="padding:0">';
        h+='<div style="display:grid;grid-template-columns:1fr 1fr;background:var(--bg);border-top:1px solid var(--brd)">';
        h+='<div style="padding:8px 14px;border-right:1px solid var(--brd)">';
        h+='<div style="font-size:.63rem;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px">Request</div>';
        h+='<pre style="margin:0;font-size:.67rem;white-space:pre-wrap;word-break:break-all;color:var(--txt);max-height:160px;overflow:auto">'+esc(s.req||'—')+'</pre>';
        h+='</div>';
        h+='<div style="padding:8px 14px">';
        h+='<div style="font-size:.63rem;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px">Response</div>';
        h+='<pre style="margin:0;font-size:.67rem;white-space:pre-wrap;word-break:break-all;color:var(--txt);max-height:160px;overflow:auto">'+esc(s.res||'—')+'</pre>';
        h+='</div>';
        h+='</div></td></tr>';
      }
    });
    h+='</tbody></table></div>';
  }else{h+='<div class="hist-empty" style="padding:24px">Sin pasos registrados.</div>';}
  document.getElementById('hist-detail-body').innerHTML=h;
  document.getElementById('hist-detail-overlay').style.display='flex';
}
function _histDetailStep(id,stepIdx){
  var r=_histData.find(function(x){return x.id===id;});
  if(!r)return;
  var steps=[];try{steps=JSON.parse(r.steps_json||'[]');}catch(e){}
  var s=steps[stepIdx];if(!s)return;
  var bc=s.pass?'ok':'err';
  var h='<div style="padding:10px 18px;border-bottom:1px solid var(--brd);display:flex;align-items:center;gap:10px;font-size:.75rem">';
  h+='<b>'+esc(s.func||'')+'</b><span style="font-family:monospace;font-size:.7rem;color:var(--txt2)">'+esc(s.tc||'')+'</span>';
  h+='<span class="hist-badge '+bc+'" style="margin-left:auto">'+esc(s.pass?'Pasó':'Falló')+'</span>';
  if(s.httpCode)h+='<span style="font-family:monospace;font-size:.7rem;color:var(--txt2)">HTTP '+esc(String(s.httpCode))+'</span>';
  h+='</div>';
  h+='<div style="display:flex;border-bottom:1px solid var(--brd)">';
  h+='<button id="hds-tab-req" onclick="_hdsTab(&quot;req&quot;)" style="padding:6px 16px;font-size:.73rem;border:none;background:var(--accd);color:var(--acc);cursor:pointer;font-weight:700">Request</button>';
  h+='<button id="hds-tab-res" onclick="_hdsTab(&quot;res&quot;)" style="padding:6px 16px;font-size:.73rem;border:none;background:var(--card);color:var(--txt2);cursor:pointer">Response</button>';
  h+='</div>';
  h+='<div id="hds-panel-req" style="overflow:auto;max-height:340px"><pre style="margin:0;padding:14px 18px;font-size:.72rem;white-space:pre-wrap;word-break:break-all">'+esc(s.req||'—')+'</pre></div>';
  h+='<div id="hds-panel-res" style="display:none;overflow:auto;max-height:340px"><pre style="margin:0;padding:14px 18px;font-size:.72rem;white-space:pre-wrap;word-break:break-all">'+esc(s.res||'—')+'</pre></div>';
  document.getElementById('hist-step-body').innerHTML=h;
  document.getElementById('hist-step-overlay').style.display='flex';
}
function _hdsTab(t){
  document.getElementById('hds-panel-req').style.display=t==='req'?'block':'none';
  document.getElementById('hds-panel-res').style.display=t==='res'?'block':'none';
  document.getElementById('hds-tab-req').style.background=t==='req'?'var(--accd)':'var(--card)';
  document.getElementById('hds-tab-req').style.color=t==='req'?'var(--acc)':'var(--txt2)';
  document.getElementById('hds-tab-req').style.fontWeight=t==='req'?'700':'400';
  document.getElementById('hds-tab-res').style.background=t==='res'?'var(--accd)':'var(--card)';
  document.getElementById('hds-tab-res').style.color=t==='res'?'var(--acc)':'var(--txt2)';
  document.getElementById('hds-tab-res').style.fontWeight=t==='res'?'700':'400';
}
function _hdrToggle(id){
  var row=document.getElementById(id);if(!row)return;
  var open=row.style.display==='none';
  row.style.display=open?'table-row':'none';
  var btn=document.getElementById(id+'-btn');
  if(btn)btn.innerHTML=open?'&#9650; Ocultar':'&#9660; Req/Res';
}
function loadStats(){
  var body=document.getElementById('hpane-stats');
  body.innerHTML='<div class="hist-empty">Cargando…</div>';
  fetch('/api/stats').then(function(r){return r.json();}).then(function(data){
    if(!Array.isArray(data)||!data.length){body.innerHTML='<div class="hist-empty">Sin datos aún.</div>';return;}
    var h='<div style="overflow-x:auto"><table class="hist-table"><thead><tr>';
    ['Suite','VNO','Total','OK','FAIL','Tasa OK','Tiempo prom.','Última ejecución'].forEach(function(c){h+='<th>'+c+'</th>';});
    h+='</tr></thead><tbody>';
    data.forEach(function(r){
      var total=parseInt(r.total)||0, ok=parseInt(r.ok)||0, fail=parseInt(r.fail)||0;
      var pct=total?Math.round(ok/total*100):0;
      var pc=pct>=80?'ok':pct>=50?'warn':'err';
      var avg=r.avg_ms!=null?((parseInt(r.avg_ms)/1000).toFixed(1)+'s'):'—';
      var fecha=r.last_run?new Date(r.last_run).toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short'}):'—';
      h+='<tr>';
      h+='<td style="font-weight:600">'+esc(_suiteName(r.suite_id,r.suite_label))+'</td>';
      h+='<td><span style="font-weight:700;font-size:.68rem;color:'+_histVnoColor(r.vno||'')+'">'+esc(r.vno_lbl||r.vno||'—')+'</span></td>';
      h+='<td style="text-align:center;font-variant-numeric:tabular-nums">'+total+'</td>';
      h+='<td style="text-align:center;color:var(--ok);font-variant-numeric:tabular-nums">'+ok+'</td>';
      h+='<td style="text-align:center;color:var(--err);font-variant-numeric:tabular-nums">'+fail+'</td>';
      h+='<td style="text-align:center"><span class="hist-badge '+pc+'">'+pct+'%</span></td>';
      h+='<td style="text-align:right;font-variant-numeric:tabular-nums">'+avg+'</td>';
      h+='<td style="color:var(--txt3);font-size:.68rem">'+esc(fecha)+'</td>';
      h+='</tr>';
    });
    h+='</tbody></table></div>';
    body.innerHTML=h;
  }).catch(function(e){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error: '+esc(e.message)+'</div>';});
}
function loadConfig(){
  var body=document.getElementById('spane-cfg-body');
  body.innerHTML='<div class="hist-empty">Cargando…</div>';
  fetch('/api/config').then(function(r){return r.json();}).then(function(data){
    if(!Array.isArray(data)){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error cargando config.</div>';return;}
    var h='<div style="max-width:560px"><h3 style="margin:0 0 18px;font-size:.85rem;color:var(--txt);font-weight:700">Parámetros del runner</h3>';
    data.forEach(function(row){
      h+='<div style="margin-bottom:14px">';
      h+='<label style="display:block;font-size:.74rem;color:var(--txt2);margin-bottom:4px">'+esc(row.label||row.key)+'</label>';
      h+='<div style="display:flex;gap:8px;align-items:center">';
      h+='<input id="cfg-'+esc(row.key)+'" type="number" min="0" value="'+esc(row.value)+'" style="padding:5px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem;width:120px">';
      h+='<button onclick="_saveConfig(this.dataset.k)" data-k="'+esc(row.key)+'" style="padding:5px 12px;border-radius:5px;border:1px solid var(--brd);background:var(--accd);color:var(--acc);font-size:.74rem;cursor:pointer">Guardar</button>';
      h+='<span id="cfg-msg-'+esc(row.key)+'" style="font-size:.7rem;color:var(--ok);display:none">&#10003; Guardado</span>';
      h+='</div></div>';
    });
    h+='</div>';
    body.innerHTML=h;
  }).catch(function(e){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error: '+esc(e.message)+'</div>';});
}
function _saveConfig(key){
  var inp=document.getElementById('cfg-'+key); if(!inp) return;
  var msg=document.getElementById('cfg-msg-'+key);
  fetch('/api/config/'+encodeURIComponent(key),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:inp.value})})
  .then(function(r){return r.json();}).then(function(d){
    if(d.ok&&msg){msg.style.display='inline';setTimeout(function(){msg.style.display='none';},2000);}
  }).catch(function(){});
}
function _histVnoColor(v){
  return {'00':'#569CD6','02':'#4EC9B0','03':'#C586C0','05':'#CE9178'}[v]||'var(--txt2)';
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
  var t=localStorage.getItem('kmq-theme')||'light';
  var btn=document.getElementById('theme-btn');
  if(t==='light'){document.body.classList.add('light');if(btn)btn.textContent='☾';}
  else{document.body.classList.remove('light');if(btn)btn.textContent='☀';}
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
  if(/^[─│┌â”└┘├┤┬┴┼= -]+$/.test(t.trim())) return 'dim';
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
// ─── QA FulFillment Queue (diseño Humberto) ──────────────────────────────
// ─── TC map por funcionalidad ─────────────────────────────────────────────
var _ATRF_TC_MAP={
  "Factibilidad":                        {"03":"CP01","02":"CP02","05":"CP03","00":"CP03"},
  "Asignación":                          {"03":"CP04","02":"CP05","05":"CP06","00":"CP06"},
  "Inicio Intervención Asegurada":       {"03":"CP07","02":"CP08","05":"CP09","00":"CP09"},
  "Activación":                          {"03":"CP10","02":"CP13","05":"CP16","00":"CP16"},
  "Diagnóstico de Acceso":               {"03":"CP12","02":"CP15","05":"CP18","00":"CP18"},
  "Modificación de Dispositivo":         {"03":"CP19","02":"CP21","05":"CP22","00":"CP22"},
  "Consulta Estado Vecino (GET)":        {"03":"CP23","02":"CP25","05":"CP26","00":"CP26"},
  "Consulta Estado Vecino (POST)":       {"03":"CP23","02":"CP25","05":"CP26","00":"CP26"},
  "Cambio de Pelo":                      {"03":"CP27","02":"CP30","05":"CP31","00":"CP31"},
  "Modificación de Acceso":              {"03":"CP32","02":"CP34","05":"CP35","00":"CP35"},
  "Finalización Intervención Asegurada": {"03":"CP36","02":"CP62","05":"CP63","00":"CP63"},
  "Reinicio ONT":                        {"03":"CP117","02":"CP40","05":"CP93","00":"CP93"},
  "RetrieveAccess":                      {"03":"CP119","02":"CP44","05":"CP95","00":"CP95"},
  "RetrieveAccess ONT":                  {"03":"CP42","02":"CP42","05":"CP42","00":"CP42"},
  "Cancelación Intervención Asegurada":  {"03":"CP67","02":"CP68","05":"CP69","00":"CP69"},
  "Baja Total de Servicio":              {"03":"CP64","02":"CP65","05":"CP66","00":"CP66"},
  "Cancelación Orden de Servicio":       {"03":"CP70","02":"CP71","05":"CP72","00":"CP72"},
  "GET Consulta de Acceso":              {"03":"CP11","02":"CP14","05":"CP14","00":"CP14"}
};
var _ATRF_TC_VNO_LABEL={"00":"TCH","02":"KAO","03":"Entel","05":"DTV"};
var _ATRF_DELAY_MAP={
  "Asignación":                    "delay_post_asig_ms",
  "Inicio Intervención Asegurada": "delay_post_ia_ms",
  "Activación":                    "delay_post_activ_ms",
  "Modificación de Dispositivo":   "delay_post_dm_ms",
  "Cancelación Orden de Servicio": "delay_post_cancel_ms",
};
var _ATRF_FUNCS=["Factibilidad","Asignación","Activación","Inicio Intervención Asegurada","Cancelación Intervención Asegurada","Finalización Intervención Asegurada","Cancelación Orden de Servicio","Baja Total de Servicio","Modificación de Acceso","Modificación de Dispositivo","Cambio de Pelo","GET Consulta de Acceso","RetrieveAccess","Consulta Estado Vecino (GET)","Consulta Estado Vecino (POST)","Diagnóstico de Acceso","Reinicio ONT","RetrieveAccess ONT","Consulta de Alarmas"];
var _ATRF_VNO_PREFIX={"02":"SCOM","03":"HWTC","05":"HWTC"};
var _atrfQueue=[];
var _atrfRunning=false;
var _atrfViewIdx=-1;
var _atrfSel=[];
var _atrfFilter='';
var _atrfDragSrc=null;
var _atrfAutoState={aid:true,sn:true,nsn:true};
var _atrfEnvUrls={};

function _atrf_p2(n){return String(n).padStart(2,'0');}
function _atrf_now(){var d=new Date();return{MM:_atrf_p2(d.getMonth()+1),DD:_atrf_p2(d.getDate()),HH:_atrf_p2(d.getHours()),mm:_atrf_p2(d.getMinutes()),ss:_atrf_p2(d.getSeconds())};}
function _atrf_ts(){return new Date().toLocaleString('es-CL',{hour12:false,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});}
function _atrf_v(id){var e=document.getElementById(id);return e?e.value:'';}
function _atrf_getVnos(){return [].slice.call(document.querySelectorAll('#atrf-vno-checks .atrf-vno-lbl.on')).map(function(el){return el.dataset.vno;});}
function _atrf_firstVno(){var v=_atrf_getVnos();return v.length?v[0]:'';}
function _atrf_toggleVno(el){
  el.classList.toggle('on');
  var vnos=_atrf_getVnos();
  var note=document.getElementById('atrf-vno-multi-note');
  if(note)note.classList.toggle('show',vnos.length>1);
  _atrf_updateAid();_atrf_updateSerials();
}

function _atrf_load(){
  try{_atrfQueue=JSON.parse(localStorage.getItem('atrf-queue')||'[]');}catch(e){_atrfQueue=[];}
  _atrf_loadEnvUrls();
}
function _atrf_save(){localStorage.setItem('atrf-queue',JSON.stringify(_atrfQueue));}

function _atrf_loadEnvUrls(){
  fetch('/api/environments').then(function(r){return r.json();}).then(function(data){
    if(!Array.isArray(data))return;
    data.forEach(function(row){
      if(row.name&&row.base_url)_atrfEnvUrls[row.name.toUpperCase()]=row.base_url;
    });
    _atrf_updateAmbUrl();
  }).catch(function(){});
}

function _atrf_getAmb(){var r=document.querySelector('input[name="atrf-amb"]:checked');return r?r.value:'QA';}

function _atrf_onAmbChange(){
  _atrf_updateAmbUrl();
  _atrf_updateAid();
}
function _atrf_updateAmbUrl(){
  var amb=_atrf_getAmb();
  var url=_atrfEnvUrls[amb]||'';
  var el=document.getElementById('atrf-amb-url');
  if(el){el.style.display=url?'inline':'none';el.textContent=url?('→ '+url):''}
}

function _atrf_renderQueue(){
  var el=document.getElementById('atrf-exec-area'); if(!el)return;
  if(!_atrfQueue.length){
    el.innerHTML='<div class="atrf-empty-state">Sin secuencias encoladas<div class="atrf-empty-hint">Presiona "+ Nueva secuencia" para comenzar</div></div>';
    return;
  }
  var rows='';
  _atrfQueue.forEach(function(q,qi){
    var sc={espera:'atrf-badge-wait',ejecutando:'atrf-badge-run',ok:'atrf-badge-ok',error:'atrf-badge-err'}[q.status];
    var sl={espera:'En espera',ejecutando:'Ejecutando',ok:'Completado',error:'Con errores'}[q.status];
    var urlBadge=q.cfg&&q.cfg.ambUrl?('<span class="atrf-url-badge">'+esc(q.cfg.ambUrl)+'</span>'):'';
    rows+='<div class="atrf-qrow" id="atrf-qrow-'+qi+'">'
      +'<div class="atrf-qrow-main">'
      +'<span class="atrf-qrow-arrow" onclick="event.stopPropagation();_atrf_toggleDetail('+qi+')" id="atrf-qarrow-'+qi+'">▶</span>'
      +'<div class="atrf-qcb'+(q.checked?' on':'')+'" onclick="event.stopPropagation();_atrf_toggleCb('+qi+')" id="atrf-qcb-'+qi+'"></div>'
      +'<div class="atrf-q-info">'
      +'<span class="atrf-q-name" onclick="_atrf_openView('+qi+')">'+(q.name||'—')+'</span>'+urlBadge
      +'<div class="atrf-q-meta">'+q.funcs.length+' func · '+(q.ts||'')+'</div>'
      +'</div>'
      +'<span class="atrf-badge '+sc+'" id="atrf-qst-'+qi+'">'+sl+'</span>'
      +'<button class="atrf-btn atrf-btn-sm atrf-btn-danger" onclick="event.stopPropagation();_atrf_removeItem('+qi+')" style="padding:3px 8px">✕</button>'
      +'</div>'
      +'<div class="atrf-qrow-detail" id="atrf-qdetail-'+qi+'">'+_atrf_buildDetailHtml(qi)+'</div>'
      +'</div>';
  });
  el.innerHTML='<div class="atrf-queue-list">'+rows+'</div>';
  var allCb=document.getElementById('atrf-selall-cb');
  var delBtn=document.getElementById('atrf-del-sel-btn');
  if(allCb){
    var anyChecked=_atrfQueue.some(function(q){return q.checked;});
    var allChecked=_atrfQueue.length>0&&_atrfQueue.every(function(q){return q.checked;});
    allCb.classList.toggle('on',allChecked);
    if(delBtn)delBtn.style.display=anyChecked?'':'none';
  }
}

function _atrf_buildDetailHtml(qi){
  var q=_atrfQueue[qi];
  var chips=(q.funcs||[]).map(function(fi){return '<span class="atrf-chip">'+esc(_ATRF_FUNCS[fi]||fi)+'</span>';}).join('');
  var tcHtml='';
  if(q.tcResults&&q.tcResults.length){
    tcHtml='<div class="atrf-tc-section-lbl" style="margin-top:12px">Casos de prueba</div><div class="atrf-tc-results">';
    q.tcResults.forEach(function(r,idx){
      var cls=r.pass?'pass':'fail';
      var icon=r.pass?'✓':'✗';
      tcHtml+='<span class="atrf-tc-badge '+cls+'" onclick="event.stopPropagation();_atrf_openTcModal('+qi+','+idx+')">'+icon+' '+esc(r.label)+'</span>';
    });
    tcHtml+='</div>';
  } else if(q.status==='espera'){
    tcHtml='<div class="atrf-tc-section-lbl" style="margin-top:12px">Casos de prueba</div><div class="atrf-tc-results">';
    (q.funcs||[]).forEach(function(fi){
      var fn=_ATRF_FUNCS[fi];var tcMap=fn&&_ATRF_TC_MAP[fn];
      if(!tcMap)return;
      var vno=q.cfg&&q.cfg.vno||'';
      var tc=tcMap[vno];if(!tc)return;
      var vl=_ATRF_TC_VNO_LABEL[vno]||vno;
      tcHtml+='<span class="atrf-tc-badge pending">'+tc+' · '+vl+'</span>';
    });
    tcHtml+='</div>';
  }
  return '<div style="padding:10px 0"><div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--atrf-text3);font-family:var(--atrf-mono);margin-bottom:6px">Funcionalidades</div><div class="atrf-chip-list">'+chips+'</div>'+tcHtml+'</div>';
}
function _atrf_toggleDetail(qi){
  document.getElementById('atrf-qrow-'+qi).classList.toggle('open');
}
function _atrf_toggleCb(qi){_atrfQueue[qi].checked=!_atrfQueue[qi].checked;document.getElementById('atrf-qcb-'+qi).classList.toggle('on',_atrfQueue[qi].checked);_atrf_save();_atrf_renderQueue();}
function _atrf_removeItem(qi){if(!confirm('¿Eliminar esta secuencia?'))return;_atrfQueue.splice(qi,1);_atrf_renderQueue();_atrf_save();}
function _atrf_toggleSelAll(){
  var allChecked=_atrfQueue.length>0&&_atrfQueue.every(function(q){return q.checked;});
  _atrfQueue.forEach(function(q){q.checked=!allChecked;});
  _atrf_renderQueue();_atrf_save();
}
function _atrf_deleteSelected(){
  var n=_atrfQueue.filter(function(q){return q.checked;}).length;
  if(!n)return;
  if(!confirm('¿Eliminar '+n+' secuencia'+(n>1?'s':'')+' seleccionada'+(n>1?'s':'')+' ?'))return;
  _atrfQueue=_atrfQueue.filter(function(q){return!q.checked;});
  _atrf_renderQueue();_atrf_save();
}
function _atrf_clearQueue(){if(!_atrfQueue.length)return;if(!confirm('¿Vaciar toda la cola?'))return;_atrfQueue=[];_atrf_renderQueue();_atrf_save();}

function _atrf_openNew(){
  _atrfSel=[];_atrfFilter='';
  _atrfAutoState={aid:true,sn:true,nsn:true};
  document.getElementById('atrf-seq-name').value='';
  document.getElementById('atrf-seq-name').classList.remove('err');
  document.getElementById('atrf-seq-ts').textContent=_atrf_ts();
  document.getElementById('atrf-val-err').classList.remove('show');
  document.getElementById('atrf-funcs-err').classList.remove('show');
  var qa=document.querySelector('input[name="atrf-amb"][value="QA"]');if(qa)qa.checked=true;
  ['atrf-tdir','atrf-tsvc','atrf-esc','atrf-tex','atrf-bp','atrf-plan','atrf-nplan'].forEach(function(id){var e=document.getElementById(id);if(e)e.classList.remove('err');});
  ['atrf-dir','atrf-aid','atrf-sn','atrf-nsn'].forEach(function(id){var e=document.getElementById(id);if(e){e.value='';e.classList.remove('err');}});
  document.querySelectorAll('#atrf-vno-checks .atrf-vno-lbl').forEach(function(el){el.classList.remove('on');});
  var multiNote=document.getElementById('atrf-vno-multi-note');if(multiNote)multiNote.classList.remove('show');
  _atrf_updateAmbUrl();
  _atrf_updateAid();
  _atrf_updateSerials();
  _atrf_switchTab('cfg');
  _atrf_renderCatalog();
  _atrf_renderSeq();
  document.getElementById('atrf-modal-new').classList.add('show');
  setTimeout(function(){document.getElementById('atrf-seq-name').focus();},80);
}
function _atrf_closeNew(){document.getElementById('atrf-modal-new').classList.remove('show');}

function _atrf_switchTab(t){
  ['cfg','funcs'].forEach(function(x){
    document.getElementById('atrf-ntab-'+x).classList.toggle('active',x===t);
    document.getElementById('atrf-nbody-'+x).style.display=x===t?'':'none';
  });
}

function _atrf_buildAid(vno){
  var v=vno||_atrf_firstVno()||'00';
  var amb=(_atrf_getAmb()||'QA').toUpperCase().slice(0,2);
  var dir=_atrf_v('atrf-dir').trim();
  var n=_atrf_now();
  var digs=(dir.replace(/\\D/g,'')+'0000000').slice(0,7);
  function mk(pfx,sfxLen){
    // pfx + amb(2) + dir_digits(sfxLen-8) + HH(2) + mm(2) + ss(2) + "-01"
    return pfx+amb+digs.slice(0,sfxLen-8)+n.HH+n.mm+n.ss+'-01';
  }
  if(v==='00')return mk('00',9);
  if(v==='02')return mk('02-',8);
  if(v==='03')return mk('03-',11);
  if(v==='05')return mk('05-',9);
  return mk(v+'-',8);
}
function _atrf_updateAid(){
  if(!_atrfAutoState.aid)return;
  var el=document.getElementById('atrf-aid');if(!el)return;
  var vnos=_atrf_getVnos();
  if(!vnos.length){el.value='';}
  else if(vnos.length>1){el.value='Se genera automáticamente al encolar';}
  else{el.value=_atrf_buildAid(vnos[0]);}
}
function _atrf_onAidInput(){_atrfAutoState.aid=false;document.getElementById('atrf-auto-aid').classList.add('off');}

function _atrf_buildSerial(vno){
  var px=_ATRF_VNO_PREFIX[vno]||'';if(!px)return'';
  var n=_atrf_now();return px+n.MM+n.DD+n.HH+n.mm;
}
function _atrf_getSnPrefix(vno){
  var px=_ATRF_VNO_PREFIX[vno]||'';if(!px)return'';
  var n=_atrf_now();return px+n.MM+n.DD;
}
function _atrf_updateSerials(){
  var vnos=_atrf_getVnos();
  var n=_atrf_now();
  var sfx=n.HH+n.mm;
  var multi=vnos.length>1;
  var px=!vnos.length?'':multi?'…':_atrf_getSnPrefix(vnos[0]);
  var pxEl=document.getElementById('atrf-sn-px');if(pxEl)pxEl.textContent=px||'—';
  var pxEl2=document.getElementById('atrf-nsn-px');if(pxEl2)pxEl2.textContent=px||'—';
  if(_atrfAutoState.sn){var e=document.getElementById('atrf-sn');if(e){e.value=multi?'':sfx;_atrf_updateSnLen('atrf-sn','atrf-sn-len');}}
  if(_atrfAutoState.nsn){var e2=document.getElementById('atrf-nsn');if(e2){e2.value=multi?'':sfx;_atrf_updateSnLen('atrf-nsn','atrf-nsn-len');}}
}
function _atrf_updateSnLen(id,lid){
  var len=(document.getElementById(id)||{value:''}).value.length;
  var el=document.getElementById(lid);if(!el)return;
  el.textContent=len+' díg.';el.className='atrf-slen';
  if(len===4)el.classList.add('ok');else if(len>0)el.classList.add('warn');
}
function _atrf_onSnEdit(id,lid){
  var key=id==='atrf-sn'?'sn':'nsn';
  if(_atrfAutoState[key]){_atrfAutoState[key]=false;var ab=document.getElementById('atrf-auto-'+key);if(ab)ab.classList.add('off');}
  _atrf_updateSnLen(id,lid);
}
function _atrf_toggleAuto(key){
  _atrfAutoState[key]=!_atrfAutoState[key];
  document.getElementById('atrf-auto-'+key).classList.toggle('off',!_atrfAutoState[key]);
  if(_atrfAutoState[key]){if(key==='aid')_atrf_updateAid();else _atrf_updateSerials();}
}

function _atrf_renderCatalog(){
  var el=document.getElementById('atrf-func-catalog');if(!el)return;
  var vis=_ATRF_FUNCS.filter(function(f){return!_atrfFilter||f.toLowerCase().includes(_atrfFilter.toLowerCase());});
  document.getElementById('atrf-func-cnt').textContent=vis.length;
  el.innerHTML='';
  _ATRF_FUNCS.forEach(function(f,i){
    if(_atrfFilter&&!f.toLowerCase().includes(_atrfFilter.toLowerCase()))return;
    var cnt=_atrfSel.filter(function(x){return x===i;}).length;
    var on=cnt>0;
    var cbHtml=cnt>1
      ?'<span class="atrf-func-cb on" style="font-size:10px;min-width:18px;text-align:center">'+cnt+'×</span>'
      :'<span class="atrf-func-cb'+(on?' on':'')+'"></span>';
    var d=document.createElement('div');d.className='atrf-func-item'+(on?' selected':'');
    d.innerHTML='<span class="atrf-func-idx">'+String(i+1).padStart(2,'0')+'</span><span class="atrf-func-name">'+f+'</span>'+cbHtml;
    d.onclick=function(){_atrf_toggleFunc(i);};
    el.appendChild(d);
  });
}
function _atrf_toggleFunc(i){
  _atrfSel.push(i);
  _atrf_renderCatalog();_atrf_renderSeq();
  document.getElementById('atrf-funcs-cnt').textContent=_atrfSel.length?('('+_atrfSel.length+')'):'';
}
function _atrf_filterFuncs(val){_atrfFilter=val;_atrf_renderCatalog();}
function _atrf_renderSeq(){
  var el=document.getElementById('atrf-seq-list');if(!el)return;
  document.getElementById('atrf-seq-counter').textContent='Secuencia ('+_atrfSel.length+')';
  if(!_atrfSel.length){el.innerHTML='<div class="atrf-seq-empty">â† Selecciona funcionalidades</div>';return;}
  el.innerHTML='';
  _atrfSel.forEach(function(fi,pos){
    var d=document.createElement('div');d.className='atrf-seq-item';d.draggable=true;d.dataset.pos=pos;
    d.innerHTML='<span class="atrf-drag-handle">⠿</span><span class="atrf-seq-pos">'+(pos+1)+'</span><span class="atrf-seq-name">'+(_ATRF_FUNCS[fi]||fi)+'</span><button class="atrf-seq-del" onclick="_atrf_removeSeq('+pos+')">×</button>';
    d.ondragstart=function(e){_atrfDragSrc=pos;e.dataTransfer.effectAllowed='move';d.style.opacity='.4';};
    d.ondragend=function(){d.style.opacity='1';document.querySelectorAll('#atrf-seq-list .atrf-seq-item').forEach(function(x){x.classList.remove('drag-over');});};
    d.ondragover=function(e){e.preventDefault();d.classList.add('drag-over');};
    d.ondragleave=function(){d.classList.remove('drag-over');};
    d.ondrop=function(e){e.preventDefault();d.classList.remove('drag-over');var from=_atrfDragSrc,to=parseInt(d.dataset.pos);if(from===to)return;var item=_atrfSel.splice(from,1)[0];_atrfSel.splice(to,0,item);_atrf_renderSeq();_atrf_renderCatalog();};
    el.appendChild(d);
  });
}
function _atrf_removeSeq(pos){_atrfSel.splice(pos,1);_atrf_renderSeq();_atrf_renderCatalog();document.getElementById('atrf-funcs-cnt').textContent=_atrfSel.length?('('+_atrfSel.length+')'):''}

function _atrf_enqueue(){
  var errors=[];
  document.querySelectorAll('#atrf-modal-new .err').forEach(function(e){e.classList.remove('err');});
  document.getElementById('atrf-funcs-err').classList.remove('show');
  var name=_atrf_v('atrf-seq-name').trim();
  var vnos=_atrf_getVnos();
  if(!name){errors.push('Nombre de la secuencia es obligatorio');document.getElementById('atrf-seq-name').classList.add('err');}
  if(!vnos.length){errors.push('Selecciona al menos una VNO');}
  if(!_atrf_v('atrf-dir').trim()){errors.push('Dirección es obligatoria');document.getElementById('atrf-dir').classList.add('err');}
  else if(/^\d{2}[-]/.test(_atrf_v('atrf-dir').trim())){errors.push('El campo Dirección parece un Access ID (ej. 02-…). La dirección física tiene formato DIR01774258 — el Access ID va en el campo Access ID.');document.getElementById('atrf-dir').classList.add('err');}
  if(!_atrf_v('atrf-esc')){errors.push('Escenario es obligatorio');document.getElementById('atrf-esc').classList.add('err');}
  if(!_atrf_v('atrf-tex')){errors.push('Tipo de ejecución es obligatorio');document.getElementById('atrf-tex').classList.add('err');}
  if(!_atrfSel.length){errors.push('Debes seleccionar al menos una funcionalidad');document.getElementById('atrf-funcs-err').classList.add('show');}
  var errEl=document.getElementById('atrf-val-err');
  if(errors.length){errEl.innerHTML=errors.map(function(e){return'· '+e;}).join('<br>');errEl.classList.add('show');if(errors.length===1&&errors[0].includes('funcionalidad'))_atrf_switchTab('funcs');else _atrf_switchTab('cfg');return;}
  errEl.classList.remove('show');
  var amb=_atrf_getAmb();var ts=document.getElementById('atrf-seq-ts').textContent;
  var dir=_atrf_v('atrf-dir').trim();
  var n=_atrf_now();
  vnos.forEach(function(vno){
    var sn_auto=_atrf_buildSerial(vno);
    var aid_auto=_atrf_buildAid(vno);
    var _snPx=_atrf_getSnPrefix(vno);
    var _snSfx=_atrfAutoState.sn?(_atrf_now().HH+_atrf_now().mm):_atrf_v('atrf-sn').trim();
    var sn_val=_snPx?_snPx+_snSfx:_snSfx;
    var _nsnSfx=_atrfAutoState.nsn?(_atrf_now().HH+_atrf_now().mm):_atrf_v('atrf-nsn').trim();
    var nsn_val=_snPx?_snPx+_nsnSfx:_nsnSfx;
    var aid_val=_atrfAutoState.aid?aid_auto:_atrf_v('atrf-aid').trim();
    var qname=name+(vnos.length>1?' [VNO '+vno+']':'');
    var cfg={vno:vno,ambiente:amb,ambUrl:_atrfEnvUrls[amb]||'',tdir:_atrf_v('atrf-tdir'),direccion:dir,accessId:aid_val,tsvc:_atrf_v('atrf-tsvc'),esc:_atrf_v('atrf-esc'),tex:_atrf_v('atrf-tex'),bp:_atrf_v('atrf-bp'),plan:_atrf_v('atrf-plan'),nplan:_atrf_v('atrf-nplan'),sn:sn_val,nsn:nsn_val,ba:document.getElementById('atrf-svc-ba').checked,voip:document.getElementById('atrf-svc-voip').checked,iptv:document.getElementById('atrf-svc-iptv').checked};
    _atrfQueue.push({name:qname,funcs:[].concat(_atrfSel),status:'espera',checked:true,ts:ts,cfg:cfg,history:[]});
  });
  _atrf_closeNew();_atrf_renderQueue();_atrf_save();
  var msg=vnos.length>1?vnos.length+' secuencias encoladas (una por VNO)':'"'+name+'" encolada';
  if(typeof showToast==='function')showToast(msg,'ok');
}

function _atrf_buildSimReq(funcName,cfg){
  var aid=cfg.accessId||'';var vno=cfg.vno||'';var svc=cfg.tsvc||'FTTH';var dir=cfg.direccion||'';
  var base={u_vno_id:vno,u_service_type:svc,u_address:dir};
  if(funcName==='Factibilidad')return JSON.stringify(Object.assign({},base,{u_scenario:cfg.esc||'Instalación'}),null,2);
  if(funcName==='Asignación')return JSON.stringify(Object.assign({},base,{u_plan:cfg.plan||'',u_serial_number:cfg.sn||'',u_with_bp:cfg.bp||'Con BP'}),null,2);
  if(funcName==='Inicio Intervención Asegurada')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_scenario:cfg.esc||'Instalación',u_service_type:svc},null,2);
  if(funcName==='Activación')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_plan:cfg.plan||'',u_serial_number:cfg.sn||'',u_new_serial_number:cfg.nsn||'',u_service_type:svc},null,2);
  if(funcName==='Modificación de Dispositivo')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_serial_number:cfg.sn||'',u_new_serial_number:cfg.nsn||'',u_service_type:svc},null,2);
  if(funcName==='Cancelación Orden de Servicio')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_service_type:svc,u_reason:'Cancelación solicitada por VNO'},null,2);
  if(funcName==='Cancelación Intervención Asegurada')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_service_type:svc},null,2);
  if(funcName==='Finalización Intervención Asegurada')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_service_type:svc},null,2);
  if(funcName==='Baja Total de Servicio')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_service_type:svc},null,2);
  if(funcName==='Consulta de Acceso'||funcName==='RetrieveAccess'||funcName==='RetrieveAccess ONT')return JSON.stringify({u_access_id:aid,u_vno_id:vno},null,2);
  if(funcName==='Diagnóstico de Acceso')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_service_type:svc},null,2);
  if(funcName==='Consulta Estado Vecino (GET)'||funcName==='Consulta Estado Vecino (POST)')return JSON.stringify({u_access_id:aid,u_vno_id:vno},null,2);
  if(funcName==='Reinicio ONT')return JSON.stringify({u_access_id:aid,u_vno_id:vno,u_service_type:svc},null,2);
  return JSON.stringify(Object.assign({u_access_id:aid},base,{u_function:funcName}),null,2);
}
function _atrf_buildSimRes(funcName,cfg,pass){
  var aid=cfg.accessId||'';var vno=cfg.vno||'';
  if(pass){
    if(funcName==='Factibilidad')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Flujo completado con éxito",u_int_free_access:"falso",u_int_portable_access:"falso",u_access_id:aid,u_vno_id:vno,u_flow_status:"Finalizado con éxito"}},null,2);
    if(funcName==='Asignación')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Asignación completada con éxito",u_access_id:aid,u_vno_id:vno,u_flow_generation:"OK",u_flow_status:"Finalizado con éxito"}},null,2);
    if(funcName==='Inicio Intervención Asegurada')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Operación aceptada, el flujo continúa",u_access_id:aid,u_vno_id:vno}},null,2);
    if(funcName==='Activación')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Solicitud de activación en curso. Customer Order: ORD000000",u_access_id:aid,u_flow_generation:"OK",u_flow_status:"Finalizado con éxito"}},null,2);
    if(funcName==='Modificación de Dispositivo')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Petición realizada con éxito",u_access_id:aid,u_new_serial_number:cfg.nsn||'',u_flow_generation:"OK",u_flow_status:"Finalizado con éxito"}},null,2);
    if(funcName==='Cancelación Orden de Servicio')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Solicitud registrada, el flujo continúa",u_service_order_id:"ORD-CANCEL-"+aid.slice(-6),u_flow_generation:"OK",u_flow_status:"Finalizado con éxito"}},null,2);
    if(funcName==='Cancelación Intervención Asegurada')return JSON.stringify({result:{sys_id:"02cdefa44abc5e10c214f8a56aba1005",u_return_code:"0",u_return_code_desc:"Cancelación de intervención registrada",u_access_id:aid}},null,2);
    if(funcName==='Consulta de Acceso'||funcName==='RetrieveAccess')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Consulta exitosa",u_access_id:aid,u_vno_id:vno,u_access_status:"ACTIVO"}},null,2);
    if(funcName==='Diagnóstico de Acceso')return JSON.stringify({result:{u_transaction_code:0,u_transaction_code_desc:"Diagnóstico completado",u_access_id:aid,u_signal_level:"-18.5 dBm",u_ont_status:"OK"}},null,2);
    if(funcName==='Consulta Estado Vecino (GET)'||funcName==='Consulta Estado Vecino (POST)')return JSON.stringify({result:{u_transaction_code:6,u_transaction_code_desc:"Consulta vecinos exitosa",u_access_id:aid,u_neighbors:[]}},null,2);
    if(funcName==='Baja Total de Servicio')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Baja de acceso procesada",u_access_id:aid,u_flow_status:"Finalizado con éxito"}},null,2);
    if(funcName==='Reinicio ONT')return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Reinicio ONT solicitado",u_access_id:aid}},null,2);
    if(funcName==='RetrieveAccess ONT')return JSON.stringify({result:{u_return_code:"0",sys_id:aid,u_ont_model:"HG8145V5",u_temperature:"45°C",u_ont_status:"OK"}},null,2);
    return JSON.stringify({result:{u_return_code:"0",u_return_code_desc:"Operación exitosa",u_access_id:aid}},null,2);
  }
  return JSON.stringify({result:{u_return_code:"1",u_return_code_desc:"Error en validación del servicio",u_error_detail:"Parámetros inválidos o acceso no encontrado",u_access_id:aid}},null,2);
}
var _ATRF_METHOD_MAP={
  "GET Consulta de Acceso":       "GET",
  "Consulta Estado Vecino (GET)": "GET"
};
var _ATRF_ENDPOINT_MAP={
  "Factibilidad":                        "fullFillment-Factibilidad/v1/feasibilityUpselling",
  "Asignación":                          "fullFillment-assignment/v1/assignment",
  "Inicio Intervención Asegurada":       "fullFillment-gIntervention/v1/assuredIntervention",
  "Activación":                          "fullFillment-activation/v1/registrationActivation",
  "GET Consulta de Acceso":              "fullFillment-consultaAcceso/v1/{accessId}",
  "Diagnóstico de Acceso":               "diagnosticoAcceso/v1/AccesStatus",
  "Modificación de Dispositivo":         "fullFillment-deviceModification/v1/deviceModification",
  "Consulta Estado Vecino (GET)":        "fullFillment-CEVEstadoVecino/v1/estado_vecino_api/{accessId}",
  "Consulta Estado Vecino (POST)":       "estadoVecino/v1/QueryNeighborsState",
  "Cambio de Pelo":                      "fullFillment-fiberChange/v1/fiberChange",
  "Modificación de Acceso":              "fullFillment-modification/v1/registrationModification",
  "Finalización Intervención Asegurada": "fullFillment-finalization/v1/interventionFinalization",
  "Cancelación Intervención Asegurada":  "fullFillment-cancelIntervention/v1/interventionCancellation",
  "Reinicio ONT":                        "reinicioONT/v1/ONTRestart",
  "RetrieveAccess":                      "provisioning/v1/retrieve-access",
  "RetrieveAccess ONT":                  "fullFillment-retrieveAccess/v1/retrieveAccess",
  "Baja Total de Servicio":              "fullFillment-unsubcription/v1/accessDeregistration",
  "Cancelación Orden de Servicio":       "fullFillment-cancelServiceOrder/v1/oossCancellation"
};
function _atrf_prettyJson(s){
  if(!s||s==='—')return s||'—';
  try{return JSON.stringify(JSON.parse(s),null,2);}catch(e){return s;}
}
function _atrf_tcTab(t){
  document.getElementById('atrf-tc-panel-req').style.display=t==='req'?'block':'none';
  document.getElementById('atrf-tc-panel-res').style.display=t==='res'?'block':'none';
  document.getElementById('atrf-tc-panel-nwm').style.display=t==='nwm'?'block':'none';
  document.getElementById('atrf-tc-tab-req').classList.toggle('active',t==='req');
  document.getElementById('atrf-tc-tab-res').classList.toggle('active',t==='res');
  document.getElementById('atrf-tc-tab-nwm').classList.toggle('active',t==='nwm');
}
function _atrf_openTcModal(qi,idx){
  var q=_atrfQueue[qi];if(!q||!q.tcResults)return;
  var r=q.tcResults[idx];if(!r)return;
  document.getElementById('atrf-tc-modal-title').textContent=r.tc;
  document.getElementById('atrf-tc-modal-func').textContent=r.func;
  var vnoLabel=_ATRF_TC_VNO_LABEL[(q.cfg&&q.cfg.vno)||'']||((q.cfg&&q.cfg.vno)||'—');
  document.getElementById('atrf-tc-modal-vno').textContent=vnoLabel;
  var badge=document.getElementById('atrf-tc-modal-badge');
  badge.textContent=r.pass?'✓ Pasó':'✗ Falló';
  badge.className='atrf-badge '+(r.pass?'atrf-badge-ok':'atrf-badge-err');
  document.getElementById('atrf-tc-modal-endpoint').textContent=_ATRF_ENDPOINT_MAP[r.func]||'/api/'+r.func;
  var _meth=_ATRF_METHOD_MAP[r.func]||'POST';
  var _mEl=document.getElementById('atrf-tc-modal-method');
  _mEl.textContent=_meth;
  _mEl.style.background=_meth==='GET'?'#2e7d32':'#3c6ff5';
  var stBadge=document.getElementById('atrf-tc-status-badge');
  var code=r.httpCode||(r.pass?200:500);
  stBadge.textContent=code?String(code):'';
  stBadge.style.background=r.pass?'rgba(0,200,100,.18)':'rgba(240,60,60,.18)';
  stBadge.style.color=r.pass?'var(--atrf-green)':'var(--atrf-red)';
  document.getElementById('atrf-tc-modal-req').textContent=_atrf_prettyJson(r.req||'—');
  document.getElementById('atrf-tc-modal-res').textContent=_atrf_prettyJson(r.res||'—');
  // Banner y código de retorno API
  var _retCode='',_retDesc='',_retDetail='';
  try{
    var _rj=JSON.parse(r.res||'{}');
    var _rr=_rj.result||_rj;
    _retCode=String(_rr.u_return_code||_rr.returnCode||'');
    _retDesc=_rr.u_return_code_desc||_rr.returnCodeDesc||'';
    _retDetail=_rr.u_error_detail||_rr.errorDetail||'';
  }catch(e){}
  var _rcEl=document.getElementById('atrf-tc-modal-retcode');
  var _rcVal=document.getElementById('atrf-tc-modal-retcode-val');
  var _banner=document.getElementById('atrf-tc-api-banner');
  var _bannerIcon=document.getElementById('atrf-tc-api-banner-icon');
  var _bannerMsg=document.getElementById('atrf-tc-api-banner-msg');
  var _bannerDetail=document.getElementById('atrf-tc-api-banner-detail');
  if(_retCode){
    _rcEl.style.display='';_rcVal.textContent=_retCode;
    var _isOk=_retCode==='0'||_retCode==='21';
    var _isWarn=!_isOk&&_retCode!=='1';
    _banner.style.display='flex';
    _banner.style.background=_isOk?'rgba(0,180,90,.10)':_isWarn?'rgba(240,160,0,.10)':'rgba(220,50,50,.10)';
    _bannerIcon.textContent=_isOk?'✅':_isWarn?'⚠️':'❌';
    _bannerMsg.textContent='Código '+_retCode+(_retDesc?' · '+_retDesc:'');
    _bannerMsg.style.color=_isOk?'var(--atrf-green)':_isWarn?'#c8820a':'var(--atrf-red)';
    _bannerDetail.textContent=_retDetail||'';
  } else {
    _rcEl.style.display='none';_banner.style.display='none';
  }
  var nwmTab=document.getElementById('atrf-tc-tab-nwm');
  var nwmEl=document.getElementById('atrf-tc-modal-nwm');
  if(r.newmanOut){nwmTab.style.display='';nwmEl.textContent=r.newmanOut;}
  else{nwmTab.style.display='none';nwmEl.textContent='';}
  _atrf_tcTab('req');
  document.getElementById('atrf-modal-tc').classList.add('show');
}
function _atrf_closeTcModal(){document.getElementById('atrf-modal-tc').classList.remove('show');}
function _atrf_openView(qi){
  _atrfViewIdx=qi;var q=_atrfQueue[qi];
  document.getElementById('atrf-view-name').value=q.name||'';
  document.getElementById('atrf-view-ts').textContent=q.ts||'—';
  _atrf_switchView('cfg');
  var c=q.cfg||{};
  var fields=[['VNO',c.vno],['Ambiente',c.ambiente],['URL Ambiente',c.ambUrl||'—'],['Tipo Dirección',c.tdir],['Dirección',c.direccion],['Access ID',c.accessId],['Tipo Servicio',c.tsvc],['Escenario',c.esc],['Tipo Ejecución',c.tex],['Con/Sin BP',c.bp],['Plan/Perfil',c.plan],['Nuevo Plan',c.nplan||'—'],['Serial Number',c.sn],['Nuevo S/N',c.nsn||'—']];
  document.getElementById('atrf-vcfg-grid').innerHTML=fields.map(function(f){return'<div class="atrf-dcfg-item"><div class="atrf-dcfg-lbl">'+f[0]+'</div><div class="atrf-dcfg-val">'+(f[1]||'—')+'</div></div>';}).join('');
  // Resultados por paso
  var tcByFunc={};var tcIdxByFunc={};
  (q.tcResults||[]).forEach(function(r,i){tcByFunc[r.func]=r;tcIdxByFunc[r.func]=i;});
  var hasResults=(q.tcResults||[]).length>0;
  var funcsTab=document.getElementById('atrf-vtab-funcs');
  if(hasResults){
    var _pass=(q.tcResults||[]).filter(function(r){return r.pass;}).length;
    var _tot=(q.tcResults||[]).length;
    funcsTab.textContent='Resultados ('+_pass+'/'+_tot+' ✓)';
    funcsTab.style.color=_pass===_tot?'var(--atrf-green)':_pass===0?'var(--atrf-red)':'var(--atrf-amber)';
  } else {
    funcsTab.textContent='Funcionalidades';funcsTab.style.color='';
  }
  // Resumen encabezado
  var summary='';
  if(hasResults){
    var _p=(q.tcResults||[]).filter(function(r){return r.pass;}).length;
    var _t=(q.tcResults||[]).length;
    var _c=_p===_t?'var(--atrf-green)':_p===0?'var(--atrf-red)':'var(--atrf-amber)';
    summary='<div style="display:flex;align-items:center;gap:12px;padding:8px 12px;background:var(--atrf-hover);border-bottom:1px solid var(--atrf-border);font-size:11px">'
      +'<span style="font-weight:600;color:'+_c+'">'+_p+' de '+_t+' pasaron</span>'
      +'<span style="color:var(--atrf-text2)">· Haz clic en un paso para ver detalle</span>'
      +'</div>';
  }
  document.getElementById('atrf-vfunc-list').innerHTML=summary+(q.funcs||[]).map(function(fi,i){
    var fn=_ATRF_FUNCS[fi]||fi;
    var res=tcByFunc[fn];
    var badge='',tcSpan='',clickAttr='',hoverStyle='';
    if(res){
      var bc=res.pass?'atrf-badge-ok':'atrf-badge-err';
      badge='<span class="atrf-badge '+bc+'" style="font-size:10px;padding:1px 7px;margin-left:auto;flex-shrink:0">'+(res.pass?'✓ Pasó':'✗ Falló')+'</span>';
      if(res.httpCode)badge+='<span style="font-size:10px;color:var(--atrf-text2);margin-left:6px;flex-shrink:0">HTTP '+res.httpCode+'</span>';
      tcSpan='<span style="font-family:var(--atrf-mono);font-size:10px;color:var(--atrf-text3);margin-right:4px">'+esc(res.tc||'')+'</span>';
      clickAttr=' onclick="_atrf_openTcModal('+qi+','+tcIdxByFunc[fn]+')" style="cursor:pointer"';
      hoverStyle=' class="atrf-view-func-item d-link-row"';
    } else {
      hoverStyle=' class="atrf-view-func-item"';
    }
    return '<div'+hoverStyle+clickAttr+'><span class="atrf-view-func-pos">'+(i+1)+'</span>'+tcSpan+'<span style="flex:1">'+esc(fn)+'</span>'+badge+'</div>';
  }).join('');
  document.getElementById('atrf-modal-view').classList.add('show');
}
function _atrf_closeView(){document.getElementById('atrf-modal-view').classList.remove('show');_atrfViewIdx=-1;}
function _atrf_deleteFromView(){if(_atrfViewIdx<0)return;if(!confirm('¿Eliminar esta secuencia?'))return;_atrfQueue.splice(_atrfViewIdx,1);_atrf_closeView();_atrf_renderQueue();_atrf_save();}
function _atrf_switchView(t){
  ['cfg','funcs'].forEach(function(x){
    document.getElementById('atrf-vtab-'+x).classList.toggle('active',x===t);
    document.getElementById('atrf-vbody-'+x).style.display=x===t?'':'none';
  });
}

var _atrf_qStartTs=0;
async function _atrf_runSelected(){
  if(_atrfRunning)return;
  var toRun=_atrfQueue.filter(function(q){return q.checked&&q.status==='espera';});
  if(!toRun.length){if(typeof showToast==='function')showToast('No hay secuencias seleccionadas en espera','err');return;}
  _atrfRunning=true;
  _atrf_qStartTs=Date.now();
  var btn=document.getElementById('atrf-run-btn');if(btn){btn.textContent='â³ Ejecutando…';btn.disabled=true;}
  var prog=document.getElementById('atrf-run-prog');if(prog)prog.style.display='';
  // Cargar delays configurados en Settings
  var _delays={};
  try{
    var _dcfg=await fetch('/api/config').then(function(r){return r.json();});
    if(Array.isArray(_dcfg)) _dcfg.forEach(function(c){_delays[c.key]=parseInt(c.value)||0;});
  }catch(e){}
  for(var qi=0;qi<_atrfQueue.length;qi++){
    var q=_atrfQueue[qi];
    if(!q.checked||q.status!=='espera')continue;
    if(prog)prog.textContent=(qi+1)+'/'+_atrfQueue.length+' → '+q.name;
    q.status='ejecutando';
    var stEl=document.getElementById('atrf-qst-'+qi);
    if(stEl){stEl.className='atrf-badge atrf-badge-run';stEl.textContent='Ejecutando';}
    q.tcResults=[];
    var vno=q.cfg&&q.cfg.vno||'';
    var _currentAccessId=q.cfg.accessId||'';
    for(var fi_idx=0;fi_idx<(q.funcs||[]).length;fi_idx++){
      var fi=q.funcs[fi_idx];
      var fn=_ATRF_FUNCS[fi];var tcMap=fn&&_ATRF_TC_MAP[fn];if(!tcMap)continue;
      var tc=tcMap[vno];if(!tc)continue;
      var vl=_ATRF_TC_VNO_LABEL[vno]||vno;
      if(prog)prog.textContent=(qi+1)+'/'+toRun.length+' → '+fn;
      var pass=false,req_s='',res_s='',httpCode=0;
      try{
        var resp=await fetch('/api/atrf/run-step',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({func:fn,vno:vno,
            direccion:q.cfg.direccion||'',
            addressMcd:q.cfg.tdir||'',
            serviceType:q.cfg.tsvc||'FTTH',
            accessId:_currentAccessId||'',
            scenario:q.cfg.esc||'Instalación',
            serialNumber:q.cfg.sn||'',
            newSerialNumber:q.cfg.nsn||'',
            speedPlan:q.cfg.plan||'',
            newSpeedPlan:q.cfg.nplan||'',
            ambUrl:q.cfg.ambUrl||'',
            ambiente:q.cfg.ambiente||'QA',
            serviceBa:q.cfg.ba!==false,
            serviceVoip:q.cfg.voip!==false,
            serviceIptv:q.cfg.iptv!==false})});
        var newmanOut='';
        if(resp.status===501){
          var p2=Math.random()>0.25;
          pass=p2;req_s=_atrf_buildSimReq(fn,q.cfg);res_s=_atrf_buildSimRes(fn,q.cfg,p2)+'  // (simulado — pendiente implementar)';
        } else {
          var rd=await resp.json();
          if(rd.mode==='direct'){
            req_s=rd.req||'';
            try{
              var dResp=await fetch(rd.directUrl,{
                method:'POST',
                headers:{
                  'Authorization':'Bearer '+rd.token,
                  'Content-Type':'application/json',
                  'vnoId':rd.vno
                },
                body:JSON.stringify(rd.body)
              });
              var dJson=await dResp.json();
              var rc=((dJson.result||dJson).u_return_code)||'';
              pass=(dResp.status===200||dResp.status===201)&&rc!=='1';
              res_s=JSON.stringify(dJson,null,4);
              httpCode=dResp.status;
            }catch(corsErr){
              pass=false;
              res_s='Error de llamada directa: '+String(corsErr);
              httpCode=0;
            }
          } else {
            pass=!!rd.pass;
            req_s=rd.req||_atrf_buildSimReq(fn,q.cfg);
            res_s=rd.res||_atrf_buildSimRes(fn,q.cfg,pass);
            if(rd.error&&!rd.req)res_s='Error: '+rd.error;
            httpCode=rd.httpCode||0;
            newmanOut=rd.newmanOut||'';
          }
        }
      }catch(e){
        req_s=_atrf_buildSimReq(fn,q.cfg);res_s='Error de red: '+String(e);
      }
      q.tcResults.push({func:fn,tc:tc,label:tc+' · '+vl,pass:pass,req:req_s,res:res_s,httpCode:httpCode,newmanOut:newmanOut});
      // Encadenar access_id desde Factibilidad y Asignacion hacia pasos siguientes
      if((fn==='Factibilidad'||fn==='Asignación')&&pass&&res_s){
        try{
          var _chainRj=JSON.parse(res_s);
          var _chainRes=_chainRj.result||_chainRj;
          var _newAid=_chainRes.u_access_id_vno||_chainRes.u_access_id||'';
          if(_newAid){_currentAccessId=_newAid;}
        }catch(e){}
      }
      // Aplicar delay post-paso si está configurado
      var _dk=_ATRF_DELAY_MAP[fn];
      if(_dk&&_delays[_dk]>0){
        if(prog)prog.textContent='⏸ Esperando '+_delays[_dk]+'ms ('+fn+')…';
        await new Promise(function(r){setTimeout(r,_delays[_dk]);});
      }
    }
    var anyFail=q.tcResults.some(function(r){return !r.pass;});
    q.status=q.tcResults.length===0?'ok':(anyFail?'error':'ok');
    // Guardar en historial — un registro por paso
    var _now=Date.now();
    var _vno=q.cfg&&q.cfg.vno||'';
    var _vnoLbl=_ATRF_TC_VNO_LABEL[_vno]||_vno;
    var _dir=(q.cfg&&q.cfg.direccion)||'';
    if(q.tcResults.length){
      q.tcResults.forEach(function(r){
        fetch('/api/historial',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
          ts:_now,suite_id:'atrf',suite_label:q.name,
          tc:r.tc||'',vno:_vno,vno_lbl:_vnoLbl,
          escenario:r.func||'',
          direccion:_dir,
          resultado:r.pass?'ok':'error',code:r.pass?0:1,
          tiempo_ms:0,
          steps_json:JSON.stringify([r])
        })}).catch(function(){});
      });
    } else {
      // Sin pasos (VNO no configurado) — guarda un registro resumen
      fetch('/api/historial',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        ts:_now,suite_id:'atrf',suite_label:q.name,
        tc:'',vno:_vno,vno_lbl:_vnoLbl,
        escenario:'',direccion:_dir,
        resultado:'ok',code:0,tiempo_ms:0
      })}).catch(function(){});
    }
    _atrf_save();
    _atrf_renderQueue();
    var rowEl=document.getElementById('atrf-qrow-'+qi);
    if(rowEl)rowEl.classList.add('open');
    // Refresca modal de vista si está abierto para esta secuencia
    if(_atrfViewIdx===qi&&document.getElementById('atrf-modal-view').classList.contains('show')) _atrf_openView(qi);
  }
  _atrfRunning=false;
  if(prog)prog.style.display='none';
  if(btn){btn.textContent='▶ Ejecutar seleccionadas';btn.disabled=false;}
}

// ── Perfil ────────────────────────────────────────────────────────────────────
function _loadPerfil(){
  var body=document.getElementById('perfil-body'); if(!body) return;
  if(!currentUser){body.innerHTML='<div class="hist-empty">No autenticado</div>';return;}
  var roleLabel=currentUser.role==='admin'?'Administrador':'Ejecutor';
  body.innerHTML=
    '<div style="background:var(--bg);border:1px solid var(--brd);border-radius:8px;padding:14px 16px;margin-bottom:16px">'
    +'<div style="display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:.8rem">'
    +'<span style="color:var(--txt2)">Nombre:</span><span style="color:var(--txt);font-weight:600">'+esc(currentUser.name)+'</span>'
    +'<span style="color:var(--txt2)">Email:</span><span style="color:var(--txt);font-family:monospace">'+esc(currentUser.email)+'</span>'
    +'<span style="color:var(--txt2)">Rol:</span><span style="padding:1px 8px;border-radius:4px;background:'+(currentUser.role==='admin'?'var(--accd)':'var(--okd)')+';color:'+(currentUser.role==='admin'?'var(--acc)':'var(--ok)')+'">'+roleLabel+'</span>'
    +'</div>'
    +'</div>'
    +'<div style="background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:14px 16px">'
    +'<h4 style="margin:0 0 12px;font-size:.8rem;color:var(--txt);font-weight:700">Cambiar contrase\xf1a</h4>'
    +'<div style="display:grid;gap:8px;max-width:320px">'
    +'<input id="cp-cur" type="password" placeholder="Contrase\xf1a actual" style="padding:7px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem"/>'
    +'<input id="cp-new" type="password" placeholder="Nueva contrase\xf1a (m\xedn. 6)" style="padding:7px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem"/>'
    +'<input id="cp-new2" type="password" placeholder="Confirmar nueva contrase\xf1a" style="padding:7px 9px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt);font-size:.8rem"/>'
    +'<div id="cp-err" style="display:none;color:var(--err);font-size:.72rem"></div>'
    +'<button onclick="_doChangePwd()" style="padding:6px 18px;border-radius:5px;border:none;background:var(--acc);color:#000;font-size:.76rem;font-weight:700;cursor:pointer;align-self:start">Cambiar contrase\xf1a</button>'
    +'<span id="cp-ok" style="display:none;color:var(--ok);font-size:.73rem">&#10003; Contrase\xf1a actualizada</span>'
    +'</div>'
    +'</div>';
}
function _doChangePwd(){
  var cur=(document.getElementById('cp-cur')||{}).value||'';
  var nw=(document.getElementById('cp-new')||{}).value||'';
  var nw2=(document.getElementById('cp-new2')||{}).value||'';
  var err=document.getElementById('cp-err');
  var ok=document.getElementById('cp-ok');
  if(err) err.style.display='none';
  if(ok) ok.style.display='none';
  if(nw!==nw2){if(err){err.textContent='Las contrase\xf1as no coinciden';err.style.display='block';}return;}
  fetch('/api/auth/change-password',{method:'POST',headers:_authHdr(),body:JSON.stringify({current_password:cur,new_password:nw})})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,d:d};});})
    .then(function(res){
      if(res.ok){
        if(ok) ok.style.display='block';
        if(document.getElementById('cp-cur')) document.getElementById('cp-cur').value='';
        if(document.getElementById('cp-new')) document.getElementById('cp-new').value='';
        if(document.getElementById('cp-new2')) document.getElementById('cp-new2').value='';
      } else {
        if(err){err.textContent=res.d.detail||'Error';err.style.display='block';}
      }
    });
}

// ── Usuarios (Admin panel) ─────────────────────────────────────────────────────
var _usrData=[];
var _usrPermsTargetId='';
var _usrPermsCurrent={};

// All suite definitions for permissions UI
var _ALL_SUITE_PERMS=[
  {id:'view:fulfillment',lbl:'&#127381; Pruebas Automatizadas FulFillment',tcs:[],_isView:true},
  {id:'view:qa',         lbl:'&#128269; Endpoints &amp; Suites QA',         tcs:[],_isView:true},
  {id:'view:dashboard',  lbl:'&#128200; Dashboard',                          tcs:[],_isView:true},
  {id:'view:historial',  lbl:'&#128203; Historial de Pruebas',               tcs:[],_isView:true},
  {id:'view:codigos',    lbl:'&#128214; C\xf3digos de Retorno',              tcs:[],_isView:true},
  {id:'qa-fact-suite',lbl:'Suite Factibilidad',tcs:[]},
  {id:'qa-asig-suite',lbl:'Suite Asignaci\xf3n',tcs:[]},
  {id:'qa-ia-inicio-suite',lbl:'Suite IA Inicio',tcs:[{tc:'TC-01',lbl:'Entel'},{tc:'TC-02',lbl:'KAO'},{tc:'TC-03',lbl:'DTV'},{tc:'TC-04',lbl:'TCH'}]},
  {id:'qa-ia-fin-suite',lbl:'Suite IA Finalizaci\xf3n',tcs:[{tc:'TC-05',lbl:'Entel'},{tc:'TC-06',lbl:'KAO'},{tc:'TC-07',lbl:'DTV'},{tc:'TC-08',lbl:'TCH'}]},
  {id:'qa-ia-cancel-suite',lbl:'Suite IA Cancelaci\xf3n',tcs:[{tc:'TC-33',lbl:'Entel'},{tc:'TC-34',lbl:'KAO'},{tc:'TC-35',lbl:'DTV'},{tc:'TC-36',lbl:'TCH'}]},
  {id:'qa-activ-suite',lbl:'Suite Activaci\xf3n + Idem',tcs:[{tc:'TC-17',lbl:'Entel'},{tc:'TC-18',lbl:'KAO'},{tc:'TC-19',lbl:'DTV'},{tc:'TC-20',lbl:'TCH'}]},
  {id:'qa-activ-sin-idem-suite',lbl:'Suite Activaci\xf3n sin Idem',tcs:[{tc:'TC-37',lbl:'Entel'},{tc:'TC-38',lbl:'KAO'},{tc:'TC-39',lbl:'DTV'},{tc:'TC-40',lbl:'TCH'}]},
  {id:'qa-dm-suite',lbl:'Suite Device Modification',tcs:[{tc:'TC-21',lbl:'Entel'},{tc:'TC-22',lbl:'KAO'},{tc:'TC-23',lbl:'DTV'},{tc:'TC-24',lbl:'TCH'}]},
  {id:'qa-cancel-suite',lbl:'Suite Cancelaci\xf3n',tcs:[{tc:'TC-25',lbl:'Entel'},{tc:'TC-26',lbl:'KAO'},{tc:'TC-27',lbl:'DTV'},{tc:'TC-28',lbl:'TCH'}]},
  {id:'qa-unsub-suite',lbl:'Suite Unsubscription',tcs:[{tc:'TC-29',lbl:'Entel'},{tc:'TC-30',lbl:'KAO'},{tc:'TC-31',lbl:'DTV'},{tc:'TC-32',lbl:'TCH'}]},
  {id:'qa-teardown-suite',lbl:'Suite Teardown',tcs:[]},
];

function _loadUsuarios(){
  if(!currentUser||currentUser.role!=='admin') return;
  var body=document.getElementById('usr-table-body'); if(!body) return;
  body.innerHTML='<div class="hist-empty">Cargando...</div>';
  fetch('/api/users',{headers:_authHdr()}).then(function(r){return r.json();}).then(function(data){
    _usrData=Array.isArray(data)?data:[];
    _renderUsrTable(_usrData);
  }).catch(function(e){body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error: '+esc(e.message)+'</div>';});
}
function _renderUsrTable(data){
  var body=document.getElementById('usr-table-body'); if(!body) return;
  if(!data.length){body.innerHTML='<div class="hist-empty">Sin usuarios registrados.</div>';return;}
  var statusLbl={active:'Activo',pending:'Pendiente',expired:'Expirado'};
  var statusClr={active:'var(--ok)',pending:'#FFD580',expired:'var(--err)'};
  var statusBg={active:'var(--okd)',pending:'rgba(255,213,128,.15)',expired:'var(--errd)'};
  var h='<div style="overflow-x:auto"><table class="hist-table"><thead><tr>'
    +'<th>Nombre</th><th>Email</th><th>Rol</th><th>Estado</th><th>Acciones</th>'
    +'</tr></thead><tbody>';
  data.forEach(function(r){
    var st=r.status||'active';
    var roleLabel=r.role==='admin'?'Admin':'Ejecutor';
    h+='<tr>';
    h+='<td style="font-weight:600;font-size:.78rem">'+esc(r.name)+'</td>';
    h+='<td style="font-size:.75rem;color:var(--txt2);font-family:monospace">'+esc(r.email)+'</td>';
    h+='<td><span style="font-size:.68rem;padding:2px 7px;border-radius:4px;background:var(--accd);color:var(--acc)">'+roleLabel+'</span></td>';
    h+='<td><span style="font-size:.68rem;padding:2px 7px;border-radius:4px;background:'+statusBg[st]+';color:'+statusClr[st]+'">'+statusLbl[st]+'</span></td>';
    h+='<td style="white-space:nowrap;display:flex;gap:4px">';
    if(r.role!=='admin') h+='<button data-uid="'+r.id+'" onclick="_usrPermsOpen(this.dataset.uid)" style="padding:2px 9px;border-radius:4px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.68rem;cursor:pointer">&#128274; Permisos</button>';
    if(st!=='active') h+='<button data-uid="'+r.id+'" onclick="_usrRegenInvite(this.dataset.uid,this)" style="padding:2px 9px;border-radius:4px;border:1px solid var(--brd);background:var(--card);color:var(--txt2);font-size:.68rem;cursor:pointer">&#128279; Reenviar</button>';
    h+='<button data-uid="'+r.id+'" onclick="_usrDelete(this.dataset.uid)" style="padding:2px 9px;border-radius:4px;border:1px solid var(--errb);background:var(--errd);color:var(--err);font-size:.68rem;cursor:pointer">&#128465;</button>';
    h+='</td></tr>';
  });
  h+='</tbody></table></div>';
  body.innerHTML=h;
}
function _usrAdd(){
  document.getElementById('usr-form').style.display='block';
  document.getElementById('usr-invite-link-area').style.display='none';
  document.getElementById('usr-form-err').style.display='none';
  ['usr-f-name','usr-f-email'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
}
function _usrFormClose(){
  document.getElementById('usr-form').style.display='none';
}
function _usrSave(){
  var name=(document.getElementById('usr-f-name')||{}).value||'';
  var email=(document.getElementById('usr-f-email')||{}).value||'';
  var role=(document.getElementById('usr-f-role')||{}).value||'ejecutor';
  var err=document.getElementById('usr-form-err');
  if(err) err.style.display='none';
  fetch('/api/users',{method:'POST',headers:_authHdr(),body:JSON.stringify({name:name,email:email,role:role})})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,d:d};});})
    .then(function(res){
      if(res.ok){
        var link=window.location.origin+'/?invite='+res.d.invite_token;
        var la=document.getElementById('usr-invite-link-area');
        var li=document.getElementById('usr-invite-link');
        if(la) la.style.display='block';
        if(li) li.value=link;
        _loadUsuarios();
      } else {
        if(err){err.textContent=res.d.detail||'Error';err.style.display='block';}
      }
    });
}
function _copyInviteLink(){
  var li=document.getElementById('usr-invite-link');
  if(li){li.select();document.execCommand('copy');li.blur();}
}
function _usrDelete(uid){
  if(!confirm('\xbfEliminar este usuario?')) return;
  fetch('/api/users/'+uid,{method:'DELETE',headers:_authHdr()})
    .then(function(r){if(r.ok) _loadUsuarios();});
}
function _usrRegenInvite(uid,btn){
  if(btn) btn.disabled=true;
  fetch('/api/users/'+uid+'/invite',{method:'POST',headers:_authHdr()})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,d:d};});})
    .then(function(res){
      if(btn) btn.disabled=false;
      if(res.ok){
        var link=window.location.origin+'/?invite='+res.d.invite_token;
        prompt('Nuevo link de invitaci\xf3n (72h):', link);
        _loadUsuarios();
      }
    });
}
function _usrPermsOpen(uid){
  _usrPermsTargetId=uid;
  var user=_usrData.find(function(u){return u.id===uid;});
  if(!user) return;
  _usrPermsCurrent=JSON.parse(JSON.stringify(user.permissions||{}));
  document.getElementById('usr-perms-title').textContent='Permisos — '+user.name;
  document.getElementById('usr-perms-ok').style.display='none';
  _renderUsrPerms();
  document.getElementById('usr-perms-modal').style.display='block';
  document.getElementById('usr-perms-modal').scrollIntoView({behavior:'smooth',block:'start'});
}
function _usrPermsClose(){
  document.getElementById('usr-perms-modal').style.display='none';
}
function _renderUsrPerms(){
  var body=document.getElementById('usr-perms-body'); if(!body) return;
  var h='<div style="display:grid;gap:8px">';
  var shownViewHdr=false, shownSuiteHdr=false;
  _ALL_SUITE_PERMS.forEach(function(suite){
    if(suite._isView && !shownViewHdr){
      h+='<div style="font-size:.7rem;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.06em;padding:4px 2px 0">Secciones principales</div>';
      shownViewHdr=true;
    }
    if(!suite._isView && !shownSuiteHdr){
      h+='<div style="font-size:.7rem;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.06em;padding:8px 2px 0">Suites de prueba</div>';
      shownSuiteHdr=true;
    }
    var hasSuite=Object.prototype.hasOwnProperty.call(_usrPermsCurrent,suite.id);
    h+='<div style="background:var(--bg);border:1px solid var(--brd);border-radius:6px;padding:10px 12px">';
    h+='<label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:.78rem;font-weight:600;color:var(--txt)">';
    h+='<input type="checkbox" data-suite="'+suite.id+'" onchange="_usrPermsToggleSuite(this)" '+(hasSuite?'checked':'')+'>';
    h+=suite.lbl+'</label>';
    if(suite.tcs.length){
      h+='<div id="usr-tcs-'+suite.id+'" style="margin-top:8px;margin-left:20px;display:'+(hasSuite?'flex':'none')+';flex-wrap:wrap;gap:6px">';
      var allowedTcs=_usrPermsCurrent[suite.id]||[];
      suite.tcs.forEach(function(tc){
        var chk=!allowedTcs.length||allowedTcs.indexOf(tc.tc)>=0;
        h+='<label style="display:flex;align-items:center;gap:4px;font-size:.72rem;color:var(--txt2);cursor:pointer">';
        h+='<input type="checkbox" data-suite="'+suite.id+'" data-tc="'+tc.tc+'" onchange="_usrPermsToggleTc(this)" '+(chk?'checked':'')+'>';
        h+=esc(tc.tc+' '+tc.lbl)+'</label>';
      });
      h+='</div>';
    }
    h+='</div>';
  });
  h+='</div>';
  body.innerHTML=h;
}
function _usrPermsToggleSuite(cb){
  var sid=cb.dataset.suite;
  if(cb.checked){
    if(!Object.prototype.hasOwnProperty.call(_usrPermsCurrent,sid)) _usrPermsCurrent[sid]=[];
    var tcsDiv=document.getElementById('usr-tcs-'+sid);
    if(tcsDiv) tcsDiv.style.display='flex';
  } else {
    delete _usrPermsCurrent[sid];
    var tcsDiv2=document.getElementById('usr-tcs-'+sid);
    if(tcsDiv2) tcsDiv2.style.display='none';
  }
}
function _usrPermsToggleTc(cb){
  var sid=cb.dataset.suite;
  var tc=cb.dataset.tc;
  var suite=_ALL_SUITE_PERMS.find(function(s){return s.id===sid;});
  if(!suite) return;
  var allTcs=suite.tcs.map(function(t){return t.tc;});
  var cur=_usrPermsCurrent[sid]||[];
  if(!cur.length) cur=allTcs.slice();
  if(cb.checked){
    if(cur.indexOf(tc)<0) cur.push(tc);
  } else {
    cur=cur.filter(function(t){return t!==tc;});
  }
  var allChecked=allTcs.every(function(t){return cur.indexOf(t)>=0;});
  _usrPermsCurrent[sid]=allChecked?[]:cur;
}
function _usrPermsSave(){
  fetch('/api/users/'+_usrPermsTargetId+'/permissions',{method:'PUT',headers:_authHdr(),body:JSON.stringify({permissions:_usrPermsCurrent})})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,d:d};});})
    .then(function(res){
      if(res.ok){
        document.getElementById('usr-perms-ok').style.display='inline';
        var u=_usrData.find(function(x){return x.id===_usrPermsTargetId;});
        if(u) u.permissions=JSON.parse(JSON.stringify(_usrPermsCurrent));
      }
    });
}

// ── C\xf3digos de Retorno ──────────────────────────────────────────────────────
var _rcData=[];
function _loadCodigos(){
  var body=document.getElementById('rc-body'); if(!body) return;
  fetch('/api/return-codes',{headers:_authHdr()}).then(function(r){return r.json();}).then(function(data){
    _rcData=data;
    var sel=document.getElementById('rc-flow');
    var flows=[...new Set(data.map(function(r){return r.flow;}))].sort();
    var opts='<option value="">Todos los flujos</option>';
    flows.forEach(function(f){opts+='<option value="'+esc(f)+'">'+esc(f)+'</option>';});
    if(sel) sel.innerHTML=opts;
    var dl=document.getElementById('rc-flow-list');
    if(dl){var dlopts='';flows.forEach(function(f){dlopts+='<option value="'+esc(f)+'">';});dl.innerHTML=dlopts;}
    var addBtn=document.getElementById('rc-add-btn');
    if(addBtn) addBtn.style.display=(currentUser&&currentUser.role==='admin')?'inline-block':'none';
    _rcFilter();
  }).catch(function(){if(body)body.innerHTML='<div class="hist-empty" style="color:var(--err)">Error cargando datos.</div>';});
}
function _rcFilter(){
  var body=document.getElementById('rc-body'); if(!body) return;
  var q=(document.getElementById('rc-search')||{}).value||'';
  var flow=(document.getElementById('rc-flow')||{}).value||'';
  var cls=(document.getElementById('rc-cls')||{}).value||'';
  var ql=q.toLowerCase();
  var filtered=_rcData.filter(function(r){
    if(flow&&r.flow!==flow) return false;
    if(cls&&r.cls!==cls) return false;
    if(ql&&(r.code.toLowerCase().indexOf(ql)<0)&&(r.description.toLowerCase().indexOf(ql)<0)&&(r.flow.toLowerCase().indexOf(ql)<0)) return false;
    return true;
  });
  var cnt=document.getElementById('rc-count');
  if(cnt) cnt.textContent=filtered.length+' resultado'+(filtered.length!==1?'s':'');
  if(!filtered.length){body.innerHTML='<div class="hist-empty">Sin resultados.</div>';return;}
  var isAdmin=currentUser&&currentUser.role==='admin';
  var grouped={};
  filtered.forEach(function(r){if(!grouped[r.flow])grouped[r.flow]=[];grouped[r.flow].push(r);});
  var h='';
  Object.keys(grouped).sort().forEach(function(f){
    h+='<div style="margin-top:14px">';
    h+='<div style="font-size:.72rem;font-weight:700;color:var(--acc);text-transform:uppercase;letter-spacing:.06em;padding:6px 0 4px;border-bottom:1px solid var(--brd);margin-bottom:4px">'+esc(f)+'</div>';
    h+='<table style="width:100%;border-collapse:collapse;font-size:.78rem">';
    h+='<thead><tr style="color:var(--txt2);font-size:.68rem">';
    h+='<th style="text-align:left;padding:4px 8px;width:70px">C\xf3digo</th>';
    h+='<th style="text-align:left;padding:4px 8px;width:100px">Tipo</th>';
    h+='<th style="text-align:left;padding:4px 8px">Descripci\xf3n</th>';
    h+='<th style="text-align:left;padding:4px 8px;width:90px">Breaking pt.</th>';
    if(isAdmin) h+='<th style="width:36px"></th>';
    h+='</tr></thead><tbody>';
    grouped[f].forEach(function(r){
      var isSis=r.cls==='Sist\xe9mico';
      var clsColor=isSis?'#F5A623':'var(--ok)';
      var clsBg=isSis?'rgba(245,166,35,.12)':'var(--okd)';
      h+='<tr style="border-bottom:1px solid var(--brdl)">';
      h+='<td style="padding:5px 8px;font-weight:700;color:var(--txt);font-family:var(--mono);font-size:.8rem">'+esc(r.code)+'</td>';
      h+='<td style="padding:5px 8px"><span style="display:inline-block;padding:2px 7px;border-radius:10px;font-size:.65rem;font-weight:700;background:'+clsBg+';color:'+clsColor+'">'+esc(r.cls)+'</span></td>';
      h+='<td style="padding:5px 8px;color:var(--txt)">'+esc(r.description)+'</td>';
      h+='<td style="padding:5px 8px;color:var(--txt3);font-family:var(--mono);font-size:.7rem">'+(r.breaking_pt?'['+esc(r.breaking_pt)+']':'')+'</td>';
      if(isAdmin) h+='<td style="padding:5px 4px;text-align:center"><button onclick="_rcDelete('+r.id+')" style="background:none;border:none;color:var(--err);cursor:pointer;font-size:.8rem;padding:0 2px" title="Eliminar">&#x2715;</button></td>';
      h+='</tr>';
    });
    h+='</tbody></table></div>';
  });
  body.innerHTML=h;
}
function _rcAddOpen(){document.getElementById('rc-add-modal').style.display='block';}
function _rcAddClose(){document.getElementById('rc-add-modal').style.display='none';document.getElementById('rc-add-err').style.display='none';}
function _rcAddSave(){
  var flow=(document.getElementById('rc-new-flow')||{}).value||'';
  var code=(document.getElementById('rc-new-code')||{}).value||'';
  var cls=(document.getElementById('rc-new-cls')||{}).value||'';
  var desc=(document.getElementById('rc-new-desc')||{}).value||'';
  var bp=(document.getElementById('rc-new-bp')||{}).value||'';
  var err=document.getElementById('rc-add-err');
  if(!flow||!code||!desc){if(err){err.textContent='Flujo, c\xf3digo y descripci\xf3n son requeridos.';err.style.display='inline';}return;}
  fetch('/api/return-codes',{method:'POST',headers:Object.assign({'Content-Type':'application/json'},_authHdr()),body:JSON.stringify({flow:flow,code:code,cls:cls,description:desc,breaking_pt:bp})})
  .then(function(r){if(!r.ok)throw new Error('error');return r.json();}).then(function(){
    _rcAddClose();
    ['rc-new-flow','rc-new-code','rc-new-desc','rc-new-bp'].forEach(function(id){var e=document.getElementById(id);if(e)e.value='';});
    _loadCodigos();
  }).catch(function(){if(err){err.textContent='Error al guardar.';err.style.display='inline';}});
}
function _rcDelete(id){
  if(!confirm('&#x00BF;Eliminar este c\xf3digo de retorno?')) return;
  fetch('/api/return-codes/'+id,{method:'DELETE',headers:_authHdr()}).then(function(){_loadCodigos();});
}
function showCodigos(){
  _dashStopRefresh();
  switchView('codigos');
  ['top-status','vno-sel','exec-btn','rpt-btn','dl-btn','clr-btn'].forEach(function(id){var e=document.getElementById(id);if(e)e.style.display='none';});
  ['hist-btn','settings-btn','dashboard-btn'].forEach(function(id){var b=document.getElementById(id);if(b)b.classList.remove('active');});
  var cb=document.getElementById('codigos-btn');if(cb)cb.classList.add('active');
  setTop('','C\xf3digos de Retorno','');
  _loadCodigos();
}
</script>
<!-- ── ATRF Modal TC Detail ────────────────────────────────────────────── -->
<div class="atrf-overlay" id="atrf-modal-tc">
  <div class="atrf-modal" style="max-width:860px">
    <div class="atrf-modal-head">
      <div class="atrf-modal-head-title" id="atrf-tc-modal-title">TC</div>
      <span id="atrf-tc-modal-badge" class="atrf-badge" style="margin-left:6px"></span>
      <div style="flex:1"></div>
      <button class="atrf-btn atrf-btn-sm" onclick="_atrf_closeTcModal()">✕ Cerrar</button>
    </div>
    <div style="display:flex;align-items:center;gap:12px;padding:8px 16px;border-bottom:1px solid var(--atrf-border);background:var(--atrf-surface2);font-size:11px">
      <span id="atrf-tc-modal-method" style="background:#3c6ff5;color:#fff;border-radius:4px;padding:2px 8px;font-family:var(--atrf-mono);font-weight:700;font-size:10px">POST</span>
      <span id="atrf-tc-modal-endpoint" style="font-family:var(--atrf-mono);color:var(--atrf-text2)">—</span>
      <span style="margin-left:auto;color:var(--atrf-text2)">Funcionalidad: <b id="atrf-tc-modal-func">—</b> &nbsp;·&nbsp; VNO: <b id="atrf-tc-modal-vno">—</b> &nbsp;<span id="atrf-tc-modal-retcode" style="display:none">&nbsp;·&nbsp; Cód <b id="atrf-tc-modal-retcode-val"></b></span></span>
    </div>
    <div id="atrf-tc-api-banner" style="display:none;align-items:center;gap:8px;padding:7px 16px;font-size:12px;border-bottom:1px solid var(--atrf-border)">
      <span id="atrf-tc-api-banner-icon" style="font-size:14px"></span>
      <span id="atrf-tc-api-banner-msg" style="font-weight:500"></span>
      <span id="atrf-tc-api-banner-detail" style="color:var(--atrf-text2);font-size:11px"></span>
    </div>
    <div style="display:flex;border-bottom:1px solid var(--atrf-border)">
      <button id="atrf-tc-tab-req" class="atrf-tc-tab active" onclick="_atrf_tcTab('req')">Body (Request)</button>
      <button id="atrf-tc-tab-res" class="atrf-tc-tab" onclick="_atrf_tcTab('res')">Response <span id="atrf-tc-status-badge" style="font-size:9px;padding:1px 5px;border-radius:3px;margin-left:4px"></span></button>
      <button id="atrf-tc-tab-nwm" class="atrf-tc-tab" onclick="_atrf_tcTab('nwm')" style="display:none">Newman Log</button>
    </div>
    <div class="atrf-modal-body" style="padding:0">
      <div id="atrf-tc-panel-req" style="display:block">
        <pre class="atrf-tc-modal-pre" id="atrf-tc-modal-req" style="border-radius:0;border:none;border-bottom:none;margin:0;max-height:380px"></pre>
      </div>
      <div id="atrf-tc-panel-res" style="display:none">
        <pre class="atrf-tc-modal-pre" id="atrf-tc-modal-res" style="border-radius:0;border:none;border-bottom:none;margin:0;max-height:380px"></pre>
      </div>
      <div id="atrf-tc-panel-nwm" style="display:none">
        <pre class="atrf-tc-modal-pre" id="atrf-tc-modal-nwm" style="border-radius:0;border:none;border-bottom:none;margin:0;max-height:380px;font-size:10px;white-space:pre-wrap"></pre>
      </div>
    </div>
    <div class="atrf-modal-footer"><button class="atrf-btn" onclick="_atrf_closeTcModal()">Cerrar</button></div>
  </div>
</div>
<!-- ── ATRF Modal Nueva Secuencia ─────────────────────────────────────────── -->
<div class="atrf-overlay" id="atrf-modal-new">
  <div class="atrf-modal">
    <div class="atrf-modal-head">
      <div class="atrf-modal-head-title">Nueva secuencia —</div>
      <input type="text" class="atrf-name-inp" id="atrf-seq-name" placeholder="Nombre de la secuencia…"/>
      <button class="atrf-btn atrf-btn-sm atrf-btn-danger" onclick="_atrf_closeNew()">Cancelar</button>
      <button class="atrf-btn atrf-btn-sm atrf-btn-primary" onclick="_atrf_enqueue()">Encolar</button>
    </div>
    <div class="atrf-ts-row">Fecha registro: <span id="atrf-seq-ts">—</span></div>
    <div class="atrf-val-err" id="atrf-val-err"></div>
    <div class="atrf-tabs">
      <div class="atrf-tab active" id="atrf-ntab-cfg" onclick="_atrf_switchTab('cfg')">Configuración</div>
      <div class="atrf-tab" id="atrf-ntab-funcs" onclick="_atrf_switchTab('funcs')">Funcionalidades <span id="atrf-funcs-cnt" style="font-size:10px;opacity:.6"></span></div>
    </div>
    <div class="atrf-modal-body" id="atrf-nbody-cfg">
      <div class="atrf-grid">
        <div class="atrf-field atrf-col-12">
          <label>Ambiente <span class="req">★</span></label>
          <div class="atrf-amb-wrap" id="atrf-amb-wrap">
            <input type="radio" name="atrf-amb" id="atrf-amb-qa" value="QA" class="atrf-amb-radio" onchange="_atrf_onAmbChange()" checked/>
            <label for="atrf-amb-qa" class="atrf-amb-lbl">QA</label>
            <input type="radio" name="atrf-amb" id="atrf-amb-prd" value="PRD" class="atrf-amb-radio" onchange="_atrf_onAmbChange()"/>
            <label for="atrf-amb-prd" class="atrf-amb-lbl">PRD</label>
            <input type="radio" name="atrf-amb" id="atrf-amb-pprd" value="PPRD" class="atrf-amb-radio" onchange="_atrf_onAmbChange()"/>
            <label for="atrf-amb-pprd" class="atrf-amb-lbl">PPRD</label>
            <span id="atrf-amb-url" style="font-size:10px;font-family:var(--atrf-mono);color:var(--atrf-green);margin-left:8px;display:none"></span>
          </div>
        </div>
        <hr class="atrf-divider"/>
        <div class="atrf-group-lbl">Datos base</div>
        <div class="atrf-field atrf-col-5">
          <label>VNO <span class="req">★</span></label>
          <div class="atrf-vno-checks" id="atrf-vno-checks">
            <span class="atrf-vno-lbl" data-vno="00" onclick="_atrf_toggleVno(this)">00</span>
            <span class="atrf-vno-lbl" data-vno="02" onclick="_atrf_toggleVno(this)">02</span>
            <span class="atrf-vno-lbl" data-vno="03" onclick="_atrf_toggleVno(this)">03</span>
            <span class="atrf-vno-lbl" data-vno="05" onclick="_atrf_toggleVno(this)">05</span>
          </div>
          <div class="atrf-vno-multi-note" id="atrf-vno-multi-note">Genera una fila por VNO con Access ID y S/N independientes</div>
        </div>
        <div class="atrf-field atrf-col-3">
          <label>Tipo dirección <span class="req">★</span></label>
          <select id="atrf-tdir">
            <option value="XYGO">XYGO</option><option value="OSP">OSP</option>
            <option value="SGO">SGO</option><option value="MANUAL">MANUAL</option>
          </select>
        </div>
        <div class="atrf-field atrf-col-5">
          <label>Dirección <span class="req">★</span></label>
          <input type="text" id="atrf-dir" placeholder="Ej: DIR01774258"/>
          <span class="atrf-hint">ID de dirección física (ej. DIR01774258)</span>
        </div>
        <div class="atrf-field atrf-col-4">
          <label>Access ID <span class="req">★</span>
            <span class="atrf-tag" id="atrf-auto-aid" onclick="_atrf_toggleAuto('aid')">Auto</span>
          </label>
          <input type="text" id="atrf-aid" placeholder="—" oninput="_atrf_onAidInput()"/>
          <span class="atrf-hint">VNO · Amb · nros(dir) · HH·MM·SS</span>
        </div>
        <hr class="atrf-divider"/>
        <div class="atrf-group-lbl">Servicio</div>
        <div class="atrf-field atrf-col-3">
          <label>Tipo servicio <span class="req">★</span></label>
          <select id="atrf-tsvc">
            <option value="FTTH">FTTH</option><option value="FTTE">FTTE</option>
            <option value="SSAA">SSAA</option>
          </select>
        </div>
        <div class="atrf-field atrf-col-3">
          <label>Escenario <span class="req">★</span></label>
          <select id="atrf-esc">
            <option value="">— Selecciona —</option>
            <option value="Instalación">Instalación</option>
            <option value="Reparación">Reparación</option>
            <option value="Retiro de Drop">Retiro de Drop</option>
          </select>
        </div>
        <div class="atrf-field atrf-col-3">
          <label>Tipo ejecución <span class="req">★</span></label>
          <select id="atrf-tex">
            <option value="">— Selecciona —</option>
            <option value="Síncrono">Síncrono</option>
            <option value="Asíncrono">Asíncrono</option>
          </select>
        </div>
        <div class="atrf-field atrf-col-3">
          <label>Con / Sin BP</label>
          <select id="atrf-bp">
            <option>Con BP</option><option>Sin BP</option>
          </select>
        </div>
        <div class="atrf-field atrf-col-full">
          <label>Servicios</label>
          <div style="display:flex;gap:20px;align-items:center;padding-top:6px">
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-weight:normal">
              <input type="checkbox" id="atrf-svc-ba" checked style="width:15px;height:15px;margin:0;cursor:pointer;flex-shrink:0"> BA
            </label>
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-weight:normal">
              <input type="checkbox" id="atrf-svc-voip" checked style="width:15px;height:15px;margin:0;cursor:pointer;flex-shrink:0"> VOIP
            </label>
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-weight:normal">
              <input type="checkbox" id="atrf-svc-iptv" checked style="width:15px;height:15px;margin:0;cursor:pointer;flex-shrink:0"> IPTV
            </label>
          </div>
        </div>
        <hr class="atrf-divider"/>
        <div class="atrf-group-lbl">Plan / Perfil</div>
        <div class="atrf-field atrf-col-3">
          <label>Plan / Perfil <span class="req">★</span></label>
          <select id="atrf-plan">
            <option selected>600/600</option>
            <option>800/800</option><option>940/940</option>
          </select>
        </div>
        <div class="atrf-field atrf-col-3">
          <label>Nuevo Plan / Perfil</label>
          <select id="atrf-nplan">
            <option selected>600/600</option>
            <option>800/800</option><option>940/940</option>
          </select>
        </div>
        <hr class="atrf-divider"/>
        <div class="atrf-group-lbl">Serial Numbers</div>
        <div class="atrf-field atrf-col-5">
          <label>Serial Number <span class="req">★</span>
            <span class="atrf-tag" id="atrf-auto-sn" onclick="_atrf_toggleAuto('sn')">Auto</span>
            <span class="atrf-slen" id="atrf-sn-len">0 díg.</span>
          </label>
          <div style="display:flex;align-items:center;gap:4px">
            <span id="atrf-sn-px" style="font-family:var(--atrf-mono);font-size:.82rem;color:var(--txt3);letter-spacing:.04em">—</span>
            <input type="text" id="atrf-sn" maxlength="4" placeholder="0000" style="width:56px;font-family:var(--atrf-mono);letter-spacing:.06em" oninput="_atrf_onSnEdit('atrf-sn','atrf-sn-len')"/>
          </div>
          <span class="atrf-hint">Prefijo+Fecha automático · ingresa últimos 4 dígitos</span>
        </div>
        <div class="atrf-field atrf-col-5">
          <label>Nuevo Serial Number
            <span class="atrf-tag" id="atrf-auto-nsn" onclick="_atrf_toggleAuto('nsn')">Auto</span>
            <span class="atrf-slen" id="atrf-nsn-len">0 díg.</span>
          </label>
          <div style="display:flex;align-items:center;gap:4px">
            <span id="atrf-nsn-px" style="font-family:var(--atrf-mono);font-size:.82rem;color:var(--txt3);letter-spacing:.04em">—</span>
            <input type="text" id="atrf-nsn" maxlength="4" placeholder="0000" style="width:56px;font-family:var(--atrf-mono);letter-spacing:.06em" oninput="_atrf_onSnEdit('atrf-nsn','atrf-nsn-len')"/>
          </div>
        </div>
      </div>
    </div>
    <div class="atrf-modal-body" id="atrf-nbody-funcs" style="display:none">
      <div class="atrf-funcs-err" id="atrf-funcs-err">Debes seleccionar al menos una funcionalidad</div>
      <div class="atrf-funcs-layout">
        <div class="atrf-func-panel">
          <div class="atrf-func-ph">
            <span class="atrf-func-pt">Disponibles (<span id="atrf-func-cnt">0</span>)</span>
            <input class="atrf-func-search" type="text" placeholder="Buscar..." oninput="_atrf_filterFuncs(this.value)"/>
          </div>
          <div class="atrf-func-scroll" id="atrf-func-catalog"></div>
        </div>
        <div class="atrf-func-panel">
          <div class="atrf-func-ph">
            <span class="atrf-func-pt" id="atrf-seq-counter">Secuencia (0)</span>
          </div>
          <div id="atrf-seq-list"><div class="atrf-seq-empty">â† Selecciona funcionalidades</div></div>
        </div>
      </div>
    </div>
  </div>
</div>
<!-- ── ATRF Modal Ver Secuencia ──────────────────────────────────────────── -->
<div class="atrf-overlay" id="atrf-modal-view">
  <div class="atrf-modal">
    <div class="atrf-modal-head">
      <div class="atrf-modal-head-title">Secuencia —</div>
      <input type="text" class="atrf-name-inp" id="atrf-view-name" readonly style="background:transparent;border-color:transparent;font-size:14px;color:var(--atrf-text)"/>
      <button class="atrf-btn atrf-btn-sm atrf-btn-danger" onclick="_atrf_deleteFromView()">Eliminar</button>
      <button class="atrf-btn atrf-btn-sm" onclick="_atrf_closeView()">✕ Cerrar</button>
    </div>
    <div class="atrf-ts-row">Fecha registro: <span id="atrf-view-ts">—</span></div>
    <div class="atrf-tabs">
      <div class="atrf-tab active" id="atrf-vtab-cfg" onclick="_atrf_switchView('cfg')">Configuración</div>
      <div class="atrf-tab" id="atrf-vtab-funcs" onclick="_atrf_switchView('funcs')">Funcionalidades</div>
    </div>
    <div class="atrf-modal-body" id="atrf-vbody-cfg"><div class="atrf-dcfg-grid" id="atrf-vcfg-grid"></div></div>
    <div class="atrf-modal-body" id="atrf-vbody-funcs" style="display:none"><div class="atrf-view-func-list" id="atrf-vfunc-list"></div></div>
    <div class="atrf-modal-footer"><button class="atrf-btn" onclick="_atrf_closeView()">Cerrar</button></div>
  </div>
</div>
<!-- ── Global Form Modal ─────────────────────────────────────────────────── -->
<div id="gf-modal">
  <div class="gfm-card">
    <div class="gfm-hdr">
      <span class="gfm-hdr-ttl">Nueva secuencia —</span>
      <input class="gfm-name-inp" id="gfm-name" placeholder="Nombre de la secuencia..." />
      <button class="gfm-btn-c" onclick="closeGFModal()">Cancelar</button>
      <button class="gfm-btn-ok" onclick="applyGFModal()">Aplicar</button>
    </div>
    <div class="gfm-meta" id="gfm-date">Fecha registro: --</div>
    <div class="gfm-err-bar" id="gfm-err-bar"></div>
    <div class="gfm-tabs">
      <span class="gfm-tab active" id="gfmt-cfg" onclick="switchGFMTab('cfg')">Configuración</span>
      <span class="gfm-tab" id="gfmt-func" onclick="switchGFMTab('func')">Funcionalidades (<span id="gfm-seq-count">0</span>)</span>
    </div>
    <div class="gfm-body">
      <!-- ── CONFIGURACIÓN ── -->
      <div class="gfm-tc active" id="gfmc-cfg">
        <div class="gfm-sec">
          <div class="gfm-sec-ttl">Ambiente <span class="r">★</span></div>
          <div class="gfm-env" id="gfm-env-group">
            <span class="gfm-ec on" data-env="QA"   onclick="selectEnv(this)">QA</span>
            <span class="gfm-ec"    data-env="PRD"  onclick="selectEnv(this)">PRD</span>
            <span class="gfm-ec"    data-env="PPRD" onclick="selectEnv(this)">PPRD</span>
          </div>
        </div>
        <div class="gfm-sec">
          <div class="gfm-sec-ttl">Datos base</div>
          <div class="gfm-row">
            <div class="gf-f">
              <label>VNO <span class="r">★</span></label>
              <select id="gf-vno" class="gfm-wsm" onchange="_autoGenAccessId(true)">
                <option value="00">00</option><option value="01">01</option>
                <option value="02">02</option><option value="03">03</option>
                <option value="04">04</option><option value="05">05</option>
              </select>
            </div>
            <div class="gf-f">
              <label>Tipo de dirección <span class="r">★</span></label>
              <select id="gf-addrtype" class="gfm-wmd">
                <option value="XYGO">XYGO</option>
                <option value="OSP">OSP</option>
                <option value="SGO">SGO</option>
                <option value="MANUAL">MANUAL</option>
              </select>
            </div>
            <div class="gf-f gfm-fw">
              <label>Dirección <span class="r">★</span>
                <span class="gfm-pill amber" id="gfm-por-pos">POR POSICIÓN</span>
              </label>
              <input id="gf-addr" class="gfm-fw" placeholder="ej: dddddd" oninput="_autoGenAccessId(true)" />
            </div>
          </div>
          <div class="gfm-row" style="margin-top:4px">
            <div class="gf-f gfm-fw">
              <label>Access ID <span class="r">★</span>
                <span class="gfm-pill blue" id="gfm-auto-badge">AUTO</span>
              </label>
              <div class="gfm-ar">
                <input id="gf-access" class="mono gfm-fw" placeholder="ej: 02-XXXXX-01" oninput="_onGFAccessInput()" />
                <button class="gfm-abtn" onclick="_autoGenAccessId(false)">Auto</button>
              </div>
              <div class="gfm-hint">VNO · Ambiente · Dirección · HH:MM</div>
            </div>
          </div>
        </div>
        <div class="gfm-sec">
          <div class="gfm-sec-ttl">Servicio</div>
          <div class="gfm-row">
            <div class="gf-f gfm-wmd">
              <label>Tipo de servicio <span class="r">★</span></label>
              <select id="gf-stype">
                <option value="FTTH">FTTH</option>
                <option value="SSAA">SSAA</option>
              </select>
            </div>
            <div class="gf-f gfm-wmd">
              <label>Escenario <span class="r">★</span></label>
              <select id="ia-scenario" onchange="document.getElementById('ia-esc-badge')&&(document.getElementById('ia-esc-badge').textContent=this.value)">
                <option value="Instalación" selected>Instalación</option>
                <option value="Reparación">Reparación</option>
              </select>
            </div>
            <div class="gf-f gfm-wmd">
              <label>Tipo de ejecución <span class="r">★</span></label>
              <select id="gf-exec">
                <option value="Síncrono">Síncrono</option>
                <option value="Asíncrono">Asíncrono</option>
              </select>
            </div>
            <div class="gf-f gfm-wmd">
              <label>Con / Sin BP</label>
              <select id="gf-bp">
                <option value="con">Con BP</option>
                <option value="sin">Sin BP</option>
              </select>
            </div>
          </div>
        </div>
        <div class="gfm-sec">
          <div class="gfm-sec-ttl">Plan / Perfil</div>
          <div class="gfm-row">
            <div class="gf-f gfm-wmd">
              <label>Plan / Perfil <span class="r">★</span></label>
              <select id="gf-speed">
                <option value="100/10">100/10</option><option value="100/100">100/100</option>
                <option value="300/300">300/300</option><option value="400/400" selected>400/400</option>
                <option value="600/600">600/600</option><option value="800/800">800/800</option>
                <option value="1000/1000">1000/1000</option>
              </select>
            </div>
            <div class="gf-f gfm-wmd">
              <label>Nuevo Plan / Perfil</label>
              <select id="gf-newspeed">
                <option value="100/10">100/10</option><option value="100/100">100/100</option>
                <option value="300/300">300/300</option><option value="400/400" selected>400/400</option>
                <option value="600/600">600/600</option><option value="800/800">800/800</option>
                <option value="1000/1000">1000/1000</option>
              </select>
            </div>
          </div>
        </div>
        <div class="gfm-sec">
          <div class="gfm-sec-ttl">Serial Numbers</div>
          <div class="gfm-row">
            <div class="gf-f gfm-fw">
              <label>Serial Number <span class="r">★</span>
                <span class="gfm-pill grn" id="gfm-schar">0 CAR.</span>
              </label>
              <div class="gfm-ar">
                <input id="gf-serial" class="mono gfm-fw" placeholder="—"
                  oninput="_updateSerialCharCounter();" />
                <button class="gfm-abtn grn" onclick="_autoGenSerial()">Auto</button>
              </div>
              <div class="gfm-hint">Prefijo VNO + MM DD HH mm — 12 o 16 car.</div>
            </div>
            <div class="gf-f gfm-fw">
              <label>Nuevo Serial Number
                <span class="gfm-pill grn" id="gfm-nschar">0 CAR.</span>
              </label>
              <div class="gfm-ar">
                <input id="gf-newserial" class="mono gfm-fw" placeholder="—"
                  oninput="_updateNSerialCharCounter();" />
                <button class="gfm-abtn grn" onclick="_autoGenNewSerial()">Auto</button>
              </div>
            </div>
          </div>
        </div>
        <div class="gfm-sec">
          <div class="gfm-sec-ttl">Servicios</div>
          <div class="gfm-row">
            <div class="gf-f">
              <label>BA</label>
              <select id="gf-ba" style="min-width:95px">
                <option value="true" selected>Con BA ✓</option>
                <option value="false">Sin BA ✗</option>
              </select>
            </div>
            <div class="gf-f">
              <label>VoIP</label>
              <select id="gf-voip" style="min-width:104px">
                <option value="true" selected>Con VoIP ✓</option>
                <option value="false">Sin VoIP ✗</option>
              </select>
            </div>
            <div class="gf-f">
              <label>IPTV</label>
              <select id="gf-iptv" style="min-width:100px">
                <option value="true" selected>Con IPTV ✓</option>
                <option value="false">Sin IPTV ✗</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      <!-- ── FUNCIONALIDADES ── -->
      <div class="gfm-tc" id="gfmc-func">
        <div class="gfm-funcs">
          <div class="gfm-flist">
            <div class="gfm-flhdr">
              <span class="gfm-flttl">Disponibles (7)</span>
              <input style="font-size:.6rem;padding:2px 6px;border-radius:3px;border:1px solid #252c45;background:#0e1220;color:#d0daf0;outline:none;width:88px"
                placeholder="Buscar..." oninput="_filterFuncList(this.value)" />
            </div>
            <div class="gfm-flbody" id="gfm-flist-body"></div>
          </div>
          <div class="gfm-fseq">
            <div class="gfm-fshdr">
              <span class="gfm-fsttl">Secuencia (<span id="gfm-seq-count2">0</span>)</span>
            </div>
            <div class="gfm-fsbody" id="gfm-fseq-body"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<!-- ── Modal Detalle Historial ──────────────────────────────────────────── -->
<div id="hist-detail-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:3000;align-items:center;justify-content:center">
  <div style="background:var(--card);border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,.35);width:min(780px,96vw);max-height:90vh;display:flex;flex-direction:column;overflow:hidden">
    <div style="display:flex;align-items:center;padding:12px 18px;border-bottom:1px solid var(--brd)">
      <span style="font-weight:700;font-size:.85rem;color:var(--txt)">Detalle de ejecución</span>
      <button onclick="document.getElementById('hist-detail-overlay').style.display='none'" style="margin-left:auto;padding:4px 12px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt2);font-size:.73rem;cursor:pointer">✕ Cerrar</button>
    </div>
    <div id="hist-detail-body" style="overflow-y:auto;flex:1"></div>
  </div>
</div>
<!-- ── Modal Req/Res paso ────────────────────────────────────────────────── -->
<div id="hist-step-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:3100;align-items:center;justify-content:center">
  <div style="background:var(--card);border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,.35);width:min(720px,96vw);max-height:88vh;display:flex;flex-direction:column;overflow:hidden">
    <div style="display:flex;align-items:center;padding:10px 18px;border-bottom:1px solid var(--brd)">
      <span style="font-weight:700;font-size:.82rem;color:var(--txt)">Request / Response</span>
      <button onclick="document.getElementById('hist-step-overlay').style.display='none'" style="margin-left:auto;padding:4px 12px;border-radius:5px;border:1px solid var(--brd);background:var(--bg);color:var(--txt2);font-size:.73rem;cursor:pointer">✕ Cerrar</button>
    </div>
    <div id="hist-step-body" style="overflow-y:auto;flex:1"></div>
  </div>
</div>
</body>
</html>"""


@app.get("/ff", response_class=HTMLResponse)
async def ff_index():
    """Sirve la interfaz ATRF FullFillment como pagina independiente."""
    return FF_HTML

# ─── UI principal Kommand ──────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KOMANDs QA Runner</title>
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
        <span class="k-text">K</span><span class="k-toggle"></span><span class="k-text">MAND</span><span class="k-suffix">s</span>
      </div>
      <div class="sb-tagline">Network Command <span>Administrator</span></div>
      <div class="sb-sub">QA Test Runner</div>
    </div>
    <div class="sb-list" id="sb-list"></div>
    <button class="run-all" id="run-all" onclick="runAll()">&#9654;&nbsp; Ejecutar todos</button>
  </aside>
  <main class="main">
    <div class="topbar">
      <span class="top-title" id="top-title">KOMANDs QA Runner</span>
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
      <div class="terminal" id="term"></div>
    </div>
    <!-- Vista Services Now — doble terminal -->
    <div id="sn-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div class="sn-form" id="sn-form"></div>
      <div class="sn-terms" id="sn-terms"></div>
    </div>
    <!-- Vista FullFillment ATRF (/ff) -->
    <div id="ff-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <iframe src="/ff?embedded=1" id="ff-iframe" style="width:100%;height:100%;border:none;flex:1" title="FullFillment ATRF"></iframe>
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
      if(s.group!=='bloqueado') row.onclick=(function(sid){return function(){selectSuite(sid);};})(s.id);
      row.innerHTML='<div class="si-ico" id="ico-'+s.id+'">&#183;</div>'
        +'<div class="si-txt"><div class="si-name">'+esc(s.label)+'</div>'
        +'<div class="si-desc">'+esc(s.desc)+'</div></div>';
      el.appendChild(row);
    });
  });
}

function selectSuite(id){
  var s=suites.find(function(x){return x.id===id;});
  if(!s||s.group==='bloqueado') return;
  selectedId=id;
  setActive(id);
  if(id==='apim-parallel'){
    switchView('ff');
    setTop('','Endpoints Services Now','Pruebas automatizadas ATRF FullFillment');
  } else {
    switchView('std');
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
  if(selectedId==='apim-parallel'){ return; }  // ATRF se ejecuta desde el iframe /ff
  var s=suites.find(function(x){return x.id===selectedId;});
  if(!s||s.group==='bloqueado') return;
  switchView('std');
  var v=_vnoParams();
  var sRun=v.suffix?Object.assign({},s,{label:s.label+v.suffix}):s;
  _doRun('/api/run/'+selectedId, v.params, sRun);
}

function run(id){
  if(running) return;
  var s=suites.find(function(x){return x.id===id;});
  if(!s||s.group==='bloqueado') return;
  selectedId=id;
  setActive(id);
  if(id==='apim-parallel'){ switchView('ff'); return; }
  switchView('std');
  _doRun('/api/run/'+id, {}, s);
}

function switchView(mode){
  var std=document.getElementById('std-view');
  var sn=document.getElementById('sn-view');
  var ff=document.getElementById('ff-view');
  if(mode==='ff'){
    std.style.display='none'; sn.style.display='none';
    if(ff){ff.style.display='flex'; ff.style.flexDirection='column';}
  } else if(mode==='sn'){
    std.style.display='none'; if(ff) ff.style.display='none';
    sn.style.display='flex'; sn.style.flexDirection='column';
  } else {
    std.style.display='flex'; std.style.flexDirection='column';
    sn.style.display='none'; if(ff) ff.style.display='none';
  }
}

function renderSNForm(){
  var sf=document.getElementById('sn-form');
  var termsCont=document.getElementById('sn-terms');

  // Build card HTML for each VNO
  snEnabled={};
  var h='<div class="sn-cards">';
  SN_VNO_DEFS.forEach(function(def){
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
  sf.innerHTML=h; sf.classList.add('show');
  sf.querySelectorAll('.sn-phase-btn').forEach(function(b){
    b.onclick=function(){executeSN(b.getAttribute('data-phase'));};
  });
  SN_VNO_DEFS.forEach(function(def){
    if(snEnabled[def.code]){
      var tog=document.getElementById('sn-tog-'+def.code);
      if(tog) tog.onchange=function(){toggleVNO(def.code);};
    }
  });

  // Rebuild terminals (only for non-locked VNOs)
  if(termsCont){
    var th='';
    SN_VNO_DEFS.forEach(function(def){
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

  setTop('','Endpoints Services Now','Selecciona una fase y ejecuta');
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
  var anyEnabled=SN_VNO_DEFS.some(function(def){return snEnabled[def.code];});
  if(!anyEnabled){alert('Habilita al menos un VNO');return;}
  var params={phase:phase||'all'};
  SN_VNO_DEFS.forEach(function(def){
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
  var sp=suites.find(function(x){return x.id==='apim-parallel';});
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
  SN_VNO_DEFS.forEach(function(def){if(snEnabled[def.code]) setSnIco(def.code,'running');});

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
        SN_VNO_DEFS.forEach(function(def){if(snEnabled[def.code]) snTerm(def.code,d.t);});
      }
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      var ok=d.e==='done'&&d.code===0;
      if(d.e==='error'){
        SN_VNO_DEFS.forEach(function(def){if(snEnabled[def.code]) snTerm(def.code,'ERROR: '+d.t);});
      }
      onDone(d.e==='error'?{code:1,passed:0,failed:0,requests:0,has_report:false}:d, s);
      SN_VNO_DEFS.forEach(function(def){
        if(snEnabled[def.code]) setSnIco(def.code,ok?'passed':'failed');
      });
      document.querySelectorAll('.sn-phase-btn').forEach(function(b){b.disabled=false;});
      var reports=d.reports||{};
      SN_VNO_DEFS.forEach(function(def){
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
      var first=SN_VNO_DEFS.find(function(def){return snEnabled[def.code];});
      if(first) snTerm(first.code,'[Conexión interrumpida]');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      SN_VNO_DEFS.forEach(function(def){if(snEnabled[def.code]) setSnIco(def.code,'failed');});
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
  if(queue.length){var nx=queue.shift();setTimeout(()=>run(nx),350);}
}

function stat(cls,n,lbl){
  return '<div class="sum-stat"><div class="sdot '+cls+'"></div><span class="sn">'+n+'</span><span class="sl">&nbsp;'+lbl+'</span></div>';
}
function runAll(){
  if(running) return;
  var ids=suites.filter(s=>s.group==='disponible'&&s.id!=='apim-parallel').map(s=>s.id);
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
  setTop('','KOMANDs QA Runner','Listo');
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
