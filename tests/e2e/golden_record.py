"""
Dato de prueba fijo (Golden Record) reservado exclusivamente para E2E QA.

Este ONT NO existe en clientes reales.
Slot 1 / PON 0 / ONT ID 99 en OLT-SAN-001 está reservado para automatización.

Si se corre contra el servidor real (KOMANDS_E2E_URL), el Komands acepta el HTTP 202
y encola la operación. Si la OLT no tiene ese ONT físico, el worker falla de forma
asíncrona — pero la capa HTTP que testeamos responde correctamente.
"""

# ── Identificación del ONT de prueba ──────────────────────────────────────────
VNO          = "DTV"
OLT          = "OLT-SAN-001"   # Nokia ISAM 7360 FX
SLOT         = "1"
PON          = "0"
ONT_ID       = "99"             # ID reservado QA — no asignar a clientes
SERIAL       = "ALCL00QA0001"  # Serial ficticio QA
SERIAL_NUEVO = "ALCL00QA0002"  # Serial de reemplazo para Cambio Dispositivo
SPEED_PLAN   = "100M/20M"
SPEED_NUEVO  = "200M/50M"      # Para demo de Cambio Plan Comercial

# ── Payloads completos por operación ─────────────────────────────────────────

ALTA = {
    "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
    "u_routing": {
        "u_id_vno":     VNO,
        "u_olt":        OLT,
        "u_slot":       SLOT,
        "u_pon":        PON,
        "u_ontid":      ONT_ID,
        "u_product":    "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": SERIAL,
    },
    "u_action": {
        "u_iptv":    "F",
        "u_voz":     "T",
        "u_gestion": "F",
    },
    "u_product": {
        "u_speed_plan": SPEED_PLAN,
    },
}

MODIFICACION_VELOCIDAD = {
    "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
    "u_routing": {
        "u_id_vno":     VNO,
        "u_olt":        OLT,
        "u_slot":       SLOT,
        "u_pon":        PON,
        "u_ontid":      ONT_ID,
        "u_product":    "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": SERIAL,
    },
    "u_action": {
        "u_action": "speed_change",
    },
    "u_product": {
        "u_speed_plan": SPEED_NUEVO,
    },
}

CAMBIO_DISPOSITIVO = {
    "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
    "u_routing": {
        "u_id_vno":     VNO,
        "u_olt":        OLT,
        "u_slot":       SLOT,
        "u_pon":        PON,
        "u_ontid":      ONT_ID,
        "u_product":    "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber":     SERIAL,
        "u_new_serialnumber": SERIAL_NUEVO,
    },
}

BAJA = {
    "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
    "u_routing": {
        "u_id_vno":     VNO,
        "u_olt":        OLT,
        "u_slot":       SLOT,
        "u_pon":        PON,
        "u_ontid":      ONT_ID,
        "u_product":    "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": SERIAL_NUEVO,
    },
}
