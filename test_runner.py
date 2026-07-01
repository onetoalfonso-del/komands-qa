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

PY     = sys.executable
NEWMAN = shutil.which("newman") or "newman"

# ─── Suites ──────────────────────────────────────────────────────────────────
SUITES = [
    {
        "id": "t1", "group": "disponible",
        "label": "T1 — Spec API + Regresión (mock)",
        "desc":  "608 casos pytest · suite completa",
        "cmd":   [PY, "-u", "-m", "pytest", "tests/", "-v", "--tb=short",
                  "--color=no", "--no-header", "-q",
                  "--ignore=tests/integration",
                  "--html=reporte_t1.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_t1.html"), "requires": None,
    },
    {
        "id": "t2", "group": "disponible",
        "label": "T2 — Comandos CLI (mock)",
        "desc":  "Nokia/Huawei · comandos CLI",
        "cmd":   [PY, "-u", "-m", "pytest", "tests/", "-v", "--tb=short",
                  "-k", "activation or cli or command",
                  "--color=no", "--no-header",
                  "--html=reporte_t2.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_t2.html"), "requires": None,
    },
    {
        "id": "t3", "group": "disponible",
        "label": "T3 — Respuesta OLT (mock)",
        "desc":  "Parseo Nokia + INDEX Huawei",
        "cmd":   [PY, "-u", "-m", "pytest", "tests/", "-v", "--tb=short",
                  "-k", "olt or parsing or response or operation_status",
                  "--color=no", "--no-header",
                  "--html=reporte_t3.html", "--self-contained-html"],
        "cwd":   str(ROOT), "report": str(ROOT / "reporte_t3.html"), "requires": None,
    },
    {
        "id": "newman-dev", "group": "disponible",
        "label": "Endpoints Kommand Dev",
        "desc":  "Contrato API real · onf-komands.cl:9016",
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
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_apim_vno03.html"],
        "cwd":   str(BP_DIR),
        "report": str(BP_DIR / "reporte_apim_vno03.html"),
        "requires": str(BP_DIR / "VnoB1_vnoid03 PRE.postman_environment.json"),
        "params": [
            {"key": "accessId",  "label": "Access ID",   "default": "03-TESTPREPROD-DIR02873675-8"},
            {"key": "serial",    "label": "Serial ONT",  "default": "SCOM13032001"},
            {"key": "speedPlan", "label": "Speed Plan",  "default": "940/940"},
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
                  "--insecure",
                  "--reporters", "cli,htmlextra",
                  "--reporter-htmlextra-export", "reporte_apim_vno02.html"],
        "cwd":   str(BP_DIR),
        "report": str(BP_DIR / "reporte_apim_vno02.html"),
        "requires": str(BP_DIR / "VnoB1_vnoid02 PRE ClaroVTR.postman_environment.json"),
        "params": [
            {"key": "accessId",  "label": "Access ID",   "default": "02-TESTPREPROD-DIR02803674-2"},
            {"key": "serial",    "label": "Serial ONT",  "default": "SCOM13022002"},
            {"key": "speedPlan", "label": "Speed Plan",  "default": "600/600"},
        ],
    },
    {
        "id": "apim-parallel", "group": "disponible",
        "label": "Endpoints Services Now",
        "desc":  "VNO-02 ClaroVTR · VNO-03 Entel · elige uno o ambos",
        "cmd": None, "cwd": None, "report": None, "requires": None,
        "parallel": ["apim-vno02", "apim-vno03"],
    },
    {
        "id": "t7", "group": "disponible",
        "label": "T7 — Seguridad OWASP (real)",
        "desc":  "JWT · Headers · Métodos HTTP · onf-komands.cl:9016",
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
        "id": "t4", "group": "bloqueado",
        "label": "T4 — Flujo E2E OLTs reales",
        "desc":  "POST→callback no disponible aún",
        "blocker": "Requiere endpoint de callback accesible desde servidor DEV",
        "cmd": None, "cwd": None, "report": None, "requires": None,
    },
    {
        "id": "t6", "group": "bloqueado",
        "label": "T6 — Paridad VNO + OLT",
        "desc":  "VNO-02 ClaroVTR · VNO-03 Entel",
        "blocker": "Requiere datos reales de VNO-02 y VNO-03",
        "cmd": None, "cwd": None, "report": None, "requires": None,
    },
    {
        "id": "t8", "group": "bloqueado",
        "label": "T8 — Performance k6 / SLOs",
        "desc":  "Latencia p95 · throughput · error rate",
        "blocker": "Requiere ambiente dedicado y SLOs definidos",
        "cmd": None, "cwd": None, "report": None, "requires": None,
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
    return SUITES


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
               "NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}

        cmd = _apply_params(suite["cmd"], overrides)
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
    """Ejecuta suites APIM VNO-02 y/o VNO-03, mezclando output con prefijo [VNO-XX]."""
    import asyncio
    params = dict(request.query_params)

    run02 = params.pop("run02", "true").lower() != "false"
    run03 = params.pop("run03", "true").lower() != "false"

    suite02 = SUITE_MAP.get("apim-vno02")
    suite03 = SUITE_MAP.get("apim-vno03")

    overrides02 = {k[3:]: v for k, v in params.items() if k.startswith("02_")}
    overrides03 = {k[3:]: v for k, v in params.items() if k.startswith("03_")}

    async def sse():
        yield f"data: {json.dumps({'e':'start','id':'apim-parallel','label':'Endpoints Services Now'})}\n\n"

        env = {**os.environ,
               "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
               "PYTHONUNBUFFERED": "1",
               "NO_COLOR": "1", "TERM": "dumb", "FORCE_COLOR": "0"}

        to_run = []
        if run03: to_run.append((suite03, "VNO-03", overrides03))
        if run02: to_run.append((suite02, "VNO-02", overrides02))

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
        code = max(exit_codes) if exit_codes else 0
        yield f"data: {json.dumps({'e':'done','code':code,'passed':passed,'failed':failed,'requests':requests,'has_report':False,'report_id':'apim-parallel'})}\n\n"
        await asyncio.sleep(0.15)

    return StreamingResponse(sse(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform",
                 "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"})


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
.sn-card.off{opacity:.32;pointer-events:none}
.sn-card-hdr{display:flex;justify-content:space-between;align-items:center}
.sn-name{font-size:.8rem;font-weight:700;display:flex;align-items:center;gap:8px}
.sn-badge{font-size:.58rem;font-weight:700;letter-spacing:.05em;padding:2px 7px;border-radius:100px;background:var(--brd);color:var(--txt2)}
.sn-run{width:100%;padding:7px;border-radius:6px;background:var(--ok);border:none;color:#fff;font-size:.77rem;font-weight:700;cursor:pointer;transition:opacity .15s}
.sn-run:hover{opacity:.85}
.sn-run:disabled{opacity:.35;cursor:not-allowed}

/* SN DUAL TERMINAL */
.sn-terms{display:flex;flex:1;overflow:hidden;min-height:0}
.sn-term{flex:1;display:flex;flex-direction:column;overflow:hidden;border-right:1px solid var(--brd)}
.sn-term:last-child{border-right:none}
.sn-thdr{padding:6px 13px;font-size:.7rem;font-weight:600;flex-shrink:0;background:var(--card);border-bottom:1px solid var(--brd);display:flex;align-items:center;gap:7px}
.sn-thdr .ico{width:14px;height:14px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:.55rem;background:var(--brd);color:var(--txt3)}

/* TERMINAL */
.terminal{flex:1;overflow-y:auto;overflow-x:hidden;padding:12px 16px;background:var(--term);font-family:var(--mono);font-size:.76rem;line-height:1.6}
.terminal::-webkit-scrollbar{width:4px}
.terminal::-webkit-scrollbar-thumb{background:var(--brd);border-radius:2px}
.terminal:empty::after{content:"Selecciona una suite del panel izquierdo para ejecutar";color:var(--txt3);font-family:var(--sans);font-size:.8rem}
.tl{display:block;white-space:pre-wrap;word-break:break-all}
.tl.ok{color:var(--ok)}.tl.err{color:var(--err)}.tl.warn{color:var(--warn)}
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
        <span class="k-text">K</span><span class="k-toggle"></span><span class="k-text">MANDs</span><span class="k-suffix">s</span>
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
      <button class="exec-btn" id="exec-btn" onclick="executeSelected()" disabled>&#9654; Ejecutar</button>
      <button class="rpt-btn" id="rpt-btn" onclick="openReport()">&#128196; Ver reporte</button>
      <button class="rpt-btn" id="dl-btn" onclick="downloadReport()">&#11015; Descargar</button>
      <button class="clr-btn" onclick="clearTerm()">Limpiar</button>
      <button class="theme-btn" id="theme-btn" onclick="toggleTheme()" title="Cambiar tema">☀</button>
    </div>
    <!-- Vista estándar -->
    <div id="std-view" style="display:flex;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div class="terminal" id="term"></div>
    </div>
    <!-- Vista Services Now — doble terminal -->
    <div id="sn-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;min-width:0">
      <div class="sn-form" id="sn-form"></div>
      <div class="sn-terms">
        <div class="sn-term">
          <div class="sn-thdr" style="color:#C586C0">
            <div class="ico" id="ico-sn03">&#183;</div>VNO-03 Entel
          </div>
          <div class="terminal" id="term-03"></div>
        </div>
        <div class="sn-term">
          <div class="sn-thdr" style="color:#4EC9B0">
            <div class="ico" id="ico-sn02">&#183;</div>VNO-02 ClaroVTR
          </div>
          <div class="terminal" id="term-02"></div>
        </div>
      </div>
    </div>
    <div class="summary" id="summary">
      <span class="sum-idle">Ejecuta una suite para ver resultados</span>
    </div>
  </main>
</div>

<script>
var suites=[], currentEs=null, running=false, queue=[], tStart=0, selectedId=null;
var snEnabled={'02':true,'03':true};

fetch('/api/suites').then(r=>r.json()).then(data=>{suites=data;renderSB();});

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
    switchView('sn');
    renderSNForm();
  } else {
    switchView('std');
    setTop('',s.label,'Seleccionado — presiona Ejecutar');
  }
  var eb=document.getElementById('exec-btn');
  if(eb) eb.disabled=running;
}

function executeSelected(){
  if(running||!selectedId) return;
  if(selectedId==='apim-parallel'){ executeSN(); return; }
  var s=suites.find(function(x){return x.id===selectedId;});
  if(!s||s.group==='bloqueado') return;
  switchView('std');
  _doRun('/api/run/'+selectedId, {}, s);
}

function run(id){
  if(running) return;
  var s=suites.find(function(x){return x.id===id;});
  if(!s||s.group==='bloqueado') return;
  selectedId=id;
  setActive(id);
  if(id==='apim-parallel'){ switchView('sn'); renderSNForm(); return; }
  switchView('std');
  _doRun('/api/run/'+id, {}, s);
}

function switchView(mode){
  var std=document.getElementById('std-view');
  var sn=document.getElementById('sn-view');
  if(mode==='sn'){
    std.style.display='none';
    sn.style.display='flex'; sn.style.flexDirection='column';
  } else {
    std.style.display='flex'; std.style.flexDirection='column';
    sn.style.display='none';
  }
}

function renderSNForm(){
  var s02=suites.find(function(x){return x.id==='apim-vno02';})||{params:[],id:'apim-vno02'};
  var s03=suites.find(function(x){return x.id==='apim-vno03';})||{params:[],id:'apim-vno03'};
  function card(vno, label, color, s){
    var h='<div class="sn-card" id="sn-card-'+vno+'">';
    h+='<div class="sn-card-hdr">';
    h+='<div class="sn-name" style="color:'+color+'">';
    h+='<label class="tog"><input type="checkbox" id="sn-tog-'+vno+'" checked>'
      +'<span class="tog-sl"></span></label>';
    h+=esc(label);
    h+='</div>';
    h+='<span class="sn-badge">VNO '+vno+'</span>';
    h+='</div>';
    (s.params||[]).forEach(function(p){
      h+='<div class="pp-group">'
        +'<label>'+esc(p.label)+'</label>'
        +'<input class="sn-inp" id="sn-'+vno+'-'+p.key+'" value="'+esc(p.default)+'" placeholder="'+esc(p.label)+'">'
        +'</div>';
    });
    h+='</div>';
    return h;
  }
  var sf=document.getElementById('sn-form');
  var h='<div class="sn-cards">';
  h+=card('03','Entel','#C586C0',s03);
  h+=card('02','ClaroVTR','#4EC9B0',s02);
  h+='</div>';
  h+='<button class="sn-run" id="sn-run-btn" onclick="executeSN()">&#9654; Ejecutar pruebas</button>';
  sf.innerHTML=h; sf.classList.add('show');
  document.getElementById('sn-tog-02').onchange=function(){toggleVNO('02');};
  document.getElementById('sn-tog-03').onchange=function(){toggleVNO('03');};
  snEnabled={'02':true,'03':true};
  snTerm('03',''); snTerm('02','');
  setTop('','Endpoints Services Now','Configura y ejecuta');
}

function toggleVNO(vno){
  var tog=document.getElementById('sn-tog-'+vno);
  var card=document.getElementById('sn-card-'+vno);
  snEnabled[vno]=tog.checked;
  card.classList.toggle('off',!tog.checked);
  card.querySelectorAll('.sn-inp').forEach(function(inp){inp.disabled=!tog.checked;});
}

function executeSN(){
  if(running) return;
  if(!snEnabled['02']&&!snEnabled['03']){alert('Habilita al menos un VNO');return;}
  var params={run02:snEnabled['02']?'true':'false', run03:snEnabled['03']?'true':'false'};
  var s02=suites.find(function(x){return x.id==='apim-vno02';});
  var s03=suites.find(function(x){return x.id==='apim-vno03';});
  if(snEnabled['02']&&s02){
    (s02.params||[]).forEach(function(p){
      var el=document.getElementById('sn-02-'+p.key);
      if(el) params['02_'+p.key]=el.value;
    });
  }
  if(snEnabled['03']&&s03){
    (s03.params||[]).forEach(function(p){
      var el=document.getElementById('sn-03-'+p.key);
      if(el) params['03_'+p.key]=el.value;
    });
  }
  var sp=suites.find(function(x){return x.id==='apim-parallel';});
  _doRunSN(params,sp);
}

function _doRunSN(params,s){
  running=true; tStart=Date.now();
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecutando…</span>';
  setTop('running',s.label,'Ejecutando'); setIco(s.id,'running');
  document.getElementById('sn-run-btn').disabled=true;
  document.getElementById('run-all').disabled=true;
  var eb=document.getElementById('exec-btn'); if(eb) eb.disabled=true;
  if(snEnabled['03']) setSnIco('03','running');
  if(snEnabled['02']) setSnIco('02','running');

  var qs=Object.keys(params).map(function(k){return encodeURIComponent(k)+'='+encodeURIComponent(params[k]);}).join('&');
  var url='/api/run-parallel'+(qs?'?'+qs:'');

  if(currentEs){currentEs.close();currentEs=null;}
  var es=new EventSource(url);
  currentEs=es;

  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.e==='line'){
      if(d.vno==='VNO-02') snTerm('02',d.t);
      else if(d.vno==='VNO-03') snTerm('03',d.t);
      else { snTerm('03',d.t); snTerm('02',d.t); }
    } else if(d.e==='done'||d.e==='error'){
      currentEs=null; es.close();
      var ok=d.e==='done'&&d.code===0;
      if(d.e==='error') snTerm('03','ERROR: '+d.t);
      onDone(d.e==='error'?{code:1,passed:0,failed:0,requests:0,has_report:false}:d, s);
      if(snEnabled['03']) setSnIco('03',ok?'passed':'failed');
      if(snEnabled['02']) setSnIco('02',ok?'passed':'failed');
      document.getElementById('sn-run-btn').disabled=false;
    }
  };
  es.onerror=function(){
    if(running&&currentEs===es){
      currentEs=null; es.close();
      snTerm('03','[Conexión interrumpida]');
      onDone({code:1,passed:0,failed:0,requests:0,has_report:false},s);
      setSnIco('03','failed'); setSnIco('02','failed');
      document.getElementById('sn-run-btn').disabled=false;
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
  running=true; tStart=Date.now();
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
  running=false;
  var elapsed=((Date.now()-tStart)/1000).toFixed(1)+'s';
  var ok=d.code===0;
  app('',''); app('── Fin: '+s.label+' '+'─'.repeat(30),'dim');
  app('Código de salida: '+d.code+'  Tiempo: '+elapsed, ok?'ok bold':'err bold');
  setIco(s.id, ok?'passed':'failed');
  setTop(ok?'passed':'failed', s.label, ok?'Completado ✓':'Falló ✗');
  var h='';
  if(d.requests) h+=stat('acc',d.requests,'requests')+'&nbsp;&nbsp;';
  h+=stat('ok',d.passed||0,'pasados')+'&nbsp;&nbsp;'+stat('err',d.failed||0,'fallidos');
  h+='<span class="st">'+esc(elapsed)+'</span>';
  document.getElementById('summary').innerHTML=h;
  if(d.has_report){
    var rb=document.getElementById('rpt-btn');rb.classList.add('show');rb.dataset.rid=d.report_id;
    var db=document.getElementById('dl-btn');db.classList.add('show');db.dataset.rid=d.report_id;
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
  document.getElementById('term').innerHTML='';
  document.getElementById('rpt-btn').classList.remove('show');
  document.getElementById('dl-btn').classList.remove('show');
  document.getElementById('summary').innerHTML='<span class="sum-idle">Ejecuta una suite para ver resultados</span>';
  setTop('','KOMANDs QA Runner','Listo');
}
function app(text,cls){
  var term=document.getElementById('term');
  var sp=document.createElement('span');
  sp.className='tl'+(cls?' '+cls:''); sp.textContent=text;
  term.appendChild(sp); term.scrollTop=term.scrollHeight;
}
function col(t){
  if(/^\\s+√/.test(t)||/^\\s+✔/.test(t)) return 'ok';
  if(/^\\s+\\d+\\.\\s+[A-Z]/.test(t)&&!/GET|POST|PUT|DELETE|PATCH/.test(t)) return 'err';
  if(/^\\s+(GET|POST|PUT|DELETE|PATCH)\\s+https?:/.test(t)) return 'acc';
  if(/expected\\s+|AssertionError/.test(t)) return 'err';
  if(/PASSED/.test(t)) return 'ok';
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

    def _write(path, name, idvno, access_id, serial, speed, addr_id, addr_mcd):
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        data = {
            "id": f"env-vno{idvno}-generated",
            "name": name,
            "values": [
                {"key": "consumerKey",    "value": ck,       "type": "default", "enabled": True},
                {"key": "consumerSecret", "value": cs,       "type": "default", "enabled": True},
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
        )
    except Exception as e:
        print(f"  [env] ERROR generando VNO-02: {e}")

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
