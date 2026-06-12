"""
Genera la carpeta 09 del flujo E2E completo con todas las combinaciones VNO x Vendor
y actualiza la colección Postman.
"""
import json

COLLECTION_PATH = "collection Kommand/SN a Kommand.postman_collection.json"

COMBOS = [
    {"label": "09a", "vendor": "Nokia",  "vno": "DTV",   "olt": "OLT-SAN-001", "ont_id": 101, "serial": "ALCLF1234567"},
    {"label": "09b", "vendor": "Huawei", "vno": "DTV",   "olt": "OLT-SAN-002", "ont_id": 201, "serial": "HWTCF1234567"},
    {"label": "09c", "vendor": "Nokia",  "vno": "CVTR",  "olt": "OLT-SAN-001", "ont_id": 102, "serial": "ALCLF2345678"},
    {"label": "09d", "vendor": "Huawei", "vno": "CVTR",  "olt": "OLT-SAN-002", "ont_id": 202, "serial": "HWTCF2345678"},
    {"label": "09e", "vendor": "Nokia",  "vno": "ENTEL", "olt": "OLT-SAN-001", "ont_id": 103, "serial": "ALCLF3456789"},
    {"label": "09f", "vendor": "Huawei", "vno": "ENTEL", "olt": "OLT-SAN-002", "ont_id": 203, "serial": "HWTCF3456789"},
    {"label": "09g", "vendor": "Nokia",  "vno": "TCH",   "olt": "OLT-SAN-001", "ont_id": 104, "serial": "ALCLF4567890"},
]

HEADERS_POST = [
    {"key": "X-Source-System",    "value": "SN_PROVISION"},
    {"key": "X-Correlation-ID",   "value": "{{$guid}}"},
    {"key": "X-Source-System-ID", "value": "{{sys_id}}"},
    {"key": "Content-Type",       "value": "application/json"},
]

HEADERS_GET = [
    {"key": "X-Source-System",  "value": "SN_QUERY"},
    {"key": "X-Correlation-ID", "value": "{{$guid}}"},
]


def post_test(label, step, name, txn_var, extra_sets=None):
    lines = [
        "pm.test('202 Accepted recibido', function() { pm.response.to.have.status(202); });",
        "var json = pm.response.json();",
        "pm.test('txn_id UUID válido', function() {",
        "    pm.expect(json.txn_id).to.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);",
        "});",
        "pm.test('status ACCEPTED', function() { pm.expect(json.status).to.eql('ACCEPTED'); });",
        f"pm.environment.set('{txn_var}', json.txn_id);",
    ]
    if extra_sets:
        lines += extra_sets
    lines.append(f"console.log('[{label} {step:02d}] {name}:', json.txn_id);")
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": lines}}]


def get_status_test(label, step, name, txn_var):
    lines = [
        "pm.test('200 OK recibido', function() { pm.response.to.have.status(200); });",
        "var json = pm.response.json();",
        f"pm.test('txn_id coincide', function() {{ pm.expect(json.txn_id).to.eql(pm.environment.get('{txn_var}')); }});",
        "pm.test('status válido', function() {",
        "    pm.expect(['ACCEPTED','IN_PROGRESS','COMPLETED','FAILED']).to.include(json.status);",
        "});",
        f"console.log('[{label} {step:02d}] {name}:', json.status);",
    ]
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": lines}}]


def get_access_test(label, step, access_var):
    lines = [
        "pm.test('200 OK recibido', function() { pm.response.to.have.status(200); });",
        "var json = pm.response.json();",
        "pm.test('status ACTIVE', function() { pm.expect(json.status).to.eql('ACTIVE'); });",
        "pm.test('olt_name presente', function() { pm.expect(json).to.have.property('olt_name'); });",
        f"console.log('[{label} {step:02d}] Acceso activo OLT:', json.olt_name);",
    ]
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": lines}}]


def post_item(step, name, endpoint, body, event):
    return {
        "name": f"{step:02d} {name}",
        "event": event,
        "request": {
            "method": "POST",
            "header": HEADERS_POST,
            "body": {"mode": "raw", "raw": json.dumps(body, indent=2), "options": {"raw": {"language": "json"}}},
            "url": {"raw": "{{baseURL}}/" + endpoint, "host": ["{{baseURL}}"], "path": [endpoint]},
        },
    }


def get_status_item(step, name, txn_var, event):
    return {
        "name": f"{step:02d} {name}",
        "event": event,
        "request": {
            "method": "GET",
            "header": HEADERS_GET,
            "url": {
                "raw": "{{baseURL}}/transaction/{{" + txn_var + "}}/status",
                "host": ["{{baseURL}}"],
                "path": ["transaction", "{{" + txn_var + "}}", "status"],
            },
        },
    }


def get_access_item(step, access_var, event):
    return {
        "name": f"{step:02d} Consultar Acceso Activo",
        "event": event,
        "request": {
            "method": "GET",
            "header": HEADERS_GET,
            "url": {
                "raw": "{{baseURL}}/access/{{" + access_var + "}}",
                "host": ["{{baseURL}}"],
                "path": ["access", "{{" + access_var + "}}"],
            },
        },
    }


def make_subfolder(c):
    lbl   = c["label"]
    vno   = c["vno"]
    olt   = c["olt"]
    vid   = c["ont_id"]
    ser   = c["serial"]
    vend  = c["vendor"]
    txn   = f"e2e_{lbl}_txn_id"
    acc   = f"e2e_{lbl}_access_id"
    acc_v = f"ACC-{vno}-{lbl.upper()}-001"

    items = [
        # 01 Alta
        post_item(1, f"Alta — Activation {vend} {vno}", "activation",
                  {"vno_code": vno, "olt_name": olt, "slot": 1, "port": 3,
                   "ont_id": vid, "serial_ont": ser, "speed_profile": "100M-UP-DOWN",
                   "external_order_id": f"ORD-{lbl.upper()}-001"},
                  post_test(lbl, 1, "Alta encolada", txn,
                            extra_sets=[f"pm.environment.set('{acc}', '{acc_v}');"])),
        # 02 Verificar Alta
        get_status_item(2, "Verificar Estado Alta", txn,
                        get_status_test(lbl, 2, "Estado Alta", txn)),
        # 03 Consultar acceso
        get_access_item(3, acc,
                        get_access_test(lbl, 3, acc)),
        # 04 Modificación
        post_item(4, f"Modificación Speed Change {vend} {vno}", "modification",
                  {"vno_code": vno, "olt_name": olt, "slot": 1, "port": 3,
                   "ont_id": vid, "modification_type": "speed_change",
                   "new_speed_profile": "200M-UP-DOWN",
                   "external_order_id": f"ORD-{lbl.upper()}-002"},
                  post_test(lbl, 4, "Modificación encolada", txn)),
        # 05 Verificar Modificación
        get_status_item(5, "Verificar Estado Modificación", txn,
                        get_status_test(lbl, 5, "Estado Modificación", txn)),
        # 06 Reset ONT
        post_item(6, f"Reset ONT {vend} {vno}", "reset-ont",
                  {"vno_code": vno, "olt_name": olt, "slot": 1, "port": 3,
                   "ont_id": vid, "external_order_id": f"ORD-{lbl.upper()}-003"},
                  post_test(lbl, 6, "Reset ONT encolado", txn)),
        # 07 Verificar Reset
        get_status_item(7, "Verificar Estado Reset ONT", txn,
                        get_status_test(lbl, 7, "Estado Reset ONT", txn)),
        # 08 Baja
        post_item(8, f"Baja — Unsuscription {vend} {vno}", "unsuscription",
                  {"vno_code": vno, "olt_name": olt, "slot": 1, "port": 3,
                   "ont_id": vid, "external_order_id": f"ORD-{lbl.upper()}-004"},
                  post_test(lbl, 8, "Baja encolada", txn)),
        # 09 Verificar Baja
        get_status_item(9, "Verificar Estado Baja — COMPLETED", txn,
                        get_status_test(lbl, 9, "Estado Baja COMPLETED", txn)),
    ]

    return {
        "name": f"{lbl} — {vend} + {vno}",
        "description": f"Flujo E2E: Alta → Mod → Reset → Baja\nVendor: {vend} | VNO: {vno} | OLT: {olt} | ont_id: {vid}",
        "item": items,
    }


def main():
    with open(COLLECTION_PATH, encoding="utf-8") as f:
        collection = json.load(f)

    new_folder = {
        "name": "09 — Flujo Completo E2E (Todas las Combinaciones VNO × OLT)",
        "description": (
            "Ciclo de vida completo para cada combinación VNO × Vendor (7 sub-flujos).\n"
            "Orden: Alta → Verificar → Consultar Acceso → Modificación → "
            "Verificar → Reset → Verificar → Baja → Verificar\n\n"
            "09a Nokia+DTV | 09b Huawei+DTV | 09c Nokia+CVTR | 09d Huawei+CVTR\n"
            "09e Nokia+ENTEL | 09f Huawei+ENTEL | 09g Nokia+TCH"
        ),
        "item": [make_subfolder(c) for c in COMBOS],
    }

    items = collection["item"]
    replaced = False
    for i, item in enumerate(items):
        if item.get("name", "").startswith("09"):
            items[i] = new_folder
            replaced = True
            break
    if not replaced:
        items.append(new_folder)

    with open(COLLECTION_PATH, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)

    total_requests = len(COMBOS) * 9
    print(f"Colección actualizada: {len(COMBOS)} sub-flujos × 9 pasos = {total_requests} requests E2E")


if __name__ == "__main__":
    main()
