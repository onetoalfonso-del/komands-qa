"""Payloads JSON para todos los endpoints de Komands API v2.2.3.

Convención de nombres: <operacion>_<vendor>_<producto>_<escenario>
Ejemplo: ACTIVATION_NOKIA_FTTH_VALID

Fuente de verdad: docs/openapi.json — KOMANDs Provisioning API v2.2.3
Formato: cuerpo jerárquico con familias u_routing, u_identification, etc.
"""

_CB = "https://api.onnetfibra.cl/sn/komands/callback"

# ─── POST /api/Komands/v1/service-activation ─────────────────────────────────

ACTIVATION_NOKIA_FTTH_VALID = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
    "u_action": {
        "u_iptv": "T",
        "u_voz": "T",
        "u_gestion": "F",
    },
    "u_product": {
        "u_speed_plan": "100M/20M",
    },
}

ACTIVATION_NOKIA_FTTH_INTERNET_ONLY = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "46",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF0000001",
        "u_slid": "SLID-002",
    },
    "u_action": {
        "u_iptv": "F",
        "u_voz": "F",
        "u_gestion": "F",
    },
    "u_product": {
        "u_speed_plan": "100M/20M",
    },
}

ACTIVATION_NOKIA_SSAA_GROUP_A = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "ENTEL",
        "u_olt": "OLT-SCL-010",
        "u_slot": "1",
        "u_pon": "0",
        "u_ontid": "5",
        "u_product": "SSAA",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF9999999",
        "u_slid": "SLID-SCL-001",
    },
    "u_product": {
        "u_speed_plan": "200M/200M",
    },
    "u_services_port": [
        {"u_index": "1", "u_service": "A", "u_cvlan": "200", "u_svlan": "100"},
    ],
}

ACTIVATION_NOKIA_SSAA_GROUP_AC = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "ENTEL",
        "u_olt": "OLT-SCL-010",
        "u_slot": "1",
        "u_pon": "0",
        "u_ontid": "5",
        "u_product": "SSAA",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF9999999",
        "u_slid": "SLID-SCL-001",
    },
    "u_product": {
        "u_speed_plan": "200M/200M",
    },
    "u_services_port": [
        {"u_index": "1", "u_service": "A", "u_cvlan": "200", "u_svlan": "100"},
        {"u_index": "2", "u_service": "C", "u_cvlan": "202", "u_svlan": "100"},
    ],
}

ACTIVATION_NOKIA_SSAA_GROUP_ACD = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "ENTEL",
        "u_olt": "OLT-SCL-010",
        "u_slot": "1",
        "u_pon": "0",
        "u_ontid": "5",
        "u_product": "SSAA",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF9999999",
        "u_slid": "SLID-SCL-001",
    },
    "u_product": {
        "u_speed_plan": "200M/200M",
    },
    "u_services_port": [
        {"u_index": "1", "u_service": "A", "u_cvlan": "200", "u_svlan": "100"},
        {"u_index": "2", "u_service": "C", "u_cvlan": "202", "u_svlan": "100"},
        {"u_index": "3", "u_service": "D", "u_cvlan": "203", "u_svlan": "100"},
    ],
}

ACTIVATION_NOKIA_SSAA_GROUP_BX = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "ENTEL",
        "u_olt": "OLT-SCL-010",
        "u_slot": "1",
        "u_pon": "0",
        "u_ontid": "5",
        "u_product": "SSAA",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF9999999",
        "u_slid": "SLID-SCL-001",
    },
    "u_product": {
        "u_speed_plan": "1G/500M",
    },
    "u_services_port": [
        {"u_index": "1", "u_service": "BX", "u_cvlan": "200", "u_svlan": "100"},
    ],
}

ACTIVATION_HUAWEI_FTTH_VALID = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-H-001",
    },
    "u_action": {
        "u_iptv": "F",
        "u_voz": "T",
        "u_gestion": "F",
    },
    "u_product": {
        "u_speed_plan": "100M/20M",
    },
}

ACTIVATION_HUAWEI_FTTH_WITH_IPTV = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C99999",
        "u_slid": "SLID-H-002",
    },
    "u_action": {
        "u_iptv": "T",
        "u_voz": "T",
        "u_gestion": "F",
    },
    "u_product": {
        "u_speed_plan": "100M/20M",
    },
}

ACTIVATION_HUAWEI_SSAA_GROUP_A = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "CVTR",
        "u_olt": "OLT-VAL-003",
        "u_slot": "1",
        "u_pon": "2",
        "u_ontid": "12",
        "u_product": "SSAA",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-VAL-001",
    },
    "u_product": {
        "u_speed_plan": "200M/200M",
    },
    "u_services_port": [
        {"u_index": "1", "u_service": "A", "u_cvlan": "200", "u_svlan": "100"},
    ],
}

# ─── VNOs descubiertos en portal real (2026-06-17) — GTD, WOM, Claro, Genérico ─
# Estos VNOs NO estaban en el spec original. Verificados en onf-komands.cl:9010.

ACTIVATION_NOKIA_GTD = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "GTD",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "47",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234568",
        "u_slid": "SLID-GTD-001",
    },
    "u_action": {"u_iptv": "F", "u_voz": "T", "u_gestion": "F"},
    "u_product": {"u_speed_plan": "100M/20M"},
}

ACTIVATION_NOKIA_WOM = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "WOM",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "4",
        "u_ontid": "48",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234569",
        "u_slid": "SLID-WOM-001",
    },
    "u_action": {"u_iptv": "F", "u_voz": "T", "u_gestion": "F"},
    "u_product": {"u_speed_plan": "100M/20M"},
}

ACTIVATION_NOKIA_CLARO = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "Claro",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "5",
        "u_ontid": "49",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234570",
        "u_slid": "SLID-CLR-001",
    },
    "u_action": {"u_iptv": "T", "u_voz": "T", "u_gestion": "F"},
    "u_product": {"u_speed_plan": "100M/20M"},
}

ACTIVATION_NOKIA_GENERICO = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "Genérico",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "6",
        "u_ontid": "50",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234571",
        "u_slid": "SLID-GEN-001",
    },
    "u_action": {"u_iptv": "F", "u_voz": "F", "u_gestion": "F"},
    "u_product": {"u_speed_plan": "100M/20M"},
}

ACTIVATION_HUAWEI_GTD = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "GTD",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "3",
        "u_ontid": "11",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C55555",
        "u_slid": "SLID-H-GTD-001",
    },
    "u_action": {"u_iptv": "F", "u_voz": "T", "u_gestion": "F"},
    "u_product": {"u_speed_plan": "100M/20M"},
}

ACTIVATION_HUAWEI_WOM = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "WOM",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "4",
        "u_ontid": "13",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C66666",
        "u_slid": "SLID-H-WOM-001",
    },
    "u_action": {"u_iptv": "F", "u_voz": "T", "u_gestion": "F"},
    "u_product": {"u_speed_plan": "100M/20M"},
}

ACTIVATION_WITH_TXN_ID = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
}

ACTIVATION_MISSING_REQUIRED_FIELDS = {
    "u_routing": {
        "u_id_vno": "DTV",
        "u_product": "FTTH",
    },
}

ACTIVATION_INVALID_VNO = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "FAKE_VNO",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {"u_serialnumber": "ALCLF1234567"},
}

ACTIVATION_INVALID_VENDOR = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-ERICSSON-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {"u_serialnumber": "ALCLF1234567"},
}

# ─── POST /api/Komands/v1/unsubscription ─────────────────────────────────────

DEACTIVATION_NOKIA_VALID = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
}

DEACTIVATION_NOKIA_CVTR = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "CVTR",
        "u_olt": "OLT-VAL-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-VAL-001",
    },
}

DEACTIVATION_NOKIA_TCH = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "TCH",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-TCH-001",
    },
    "u_vlan": {
        "u_delete_vlan_on_terminate": "T",
        "u_svlan": "300",
    },
}

DEACTIVATION_HUAWEI_VALID = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-H-001",
    },
}

# ─── POST /api/Komands/v1/reset-ont (mock-only) ───────────────────────────────

RESET_ONT_NOKIA_VALID = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
    },
}

RESET_ONT_HUAWEI_VALID = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
    },
}

# ─── POST /api/Komands/v1/device-modification ────────────────────────────────

DEVICE_MOD_NOKIA_VALID = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
        "u_new_serialnumber": "ALCLF7654321",
    },
}

DEVICE_MOD_HUAWEI_VALID = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-H-001",
        "u_new_serialnumber": "485754C99999",
    },
}

# ─── POST /api/Komands/v1/service-modification ───────────────────────────────

MODIFICATION_SPEED_CHANGE_NOKIA = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
    "u_action": {
        "u_type": "SPEED_CHANGE",
    },
    "u_product": {
        "u_speed_plan": "200M/50M",
    },
}

MODIFICATION_BLOCK_NOKIA = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
    "u_action": {
        "u_type": "BLOCK",
    },
}

MODIFICATION_UNBLOCK_NOKIA = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
    "u_action": {
        "u_type": "UNBLOCK",
    },
}

MODIFICATION_SPEED_CHANGE_HUAWEI = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-H-001",
    },
    "u_action": {
        "u_type": "SPEED_CHANGE",
    },
    "u_product": {
        "u_speed_plan": "200M/50M",
    },
}

MODIFICATION_BLOCK_HUAWEI = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "u_action": {"u_type": "BLOCK"},
}

MODIFICATION_UNBLOCK_HUAWEI = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "u_action": {"u_type": "UNBLOCK"},
}

MODIFICATION_SERVICE_ADD_IPTV = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
    "u_action": {
        "u_type": "ADD_SERVICE",
        "u_iptv": "T",
    },
}

MODIFICATION_SERVICE_REMOVE_VOIP = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
    "u_action": {
        "u_type": "REMOVE_SERVICE",
        "u_voz": "F",
    },
}

# ─── Centinelas — errores de negocio en modificación ──────────────────────────
#
# u_routing.u_ontid="8888" → ONT no encontrado                        (MOD-18/19)
# u_routing.u_ontid="7777" → timeout SSH                              (MOD-20/21)
# u_action.u_type="REMOVE_SERVICE" + OLT Nokia → 422 KMD-4001         (MOD-22)
# u_product.u_speed_plan="PERFIL_INVALIDO" → 422 KMD-2004             (MOD-23)

MODIFICATION_NOKIA_ONT_NOT_FOUND = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "u_routing": {**MODIFICATION_SPEED_CHANGE_NOKIA["u_routing"], "u_ontid": "8888"},
}

MODIFICATION_HUAWEI_ONT_NOT_FOUND = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "u_routing": {**MODIFICATION_SPEED_CHANGE_HUAWEI["u_routing"], "u_ontid": "8888"},
}

MODIFICATION_NOKIA_SSH_TIMEOUT = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "u_routing": {**MODIFICATION_SPEED_CHANGE_NOKIA["u_routing"], "u_ontid": "7777"},
}

MODIFICATION_HUAWEI_SSH_TIMEOUT = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "u_routing": {**MODIFICATION_SPEED_CHANGE_HUAWEI["u_routing"], "u_ontid": "7777"},
}

# remove_service en Nokia → 422 (no soportado)
MODIFICATION_SERVICE_REMOVE_NOKIA = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
    "u_action": {
        "u_type": "REMOVE_SERVICE",
        "u_voz": "F",
    },
}

# Perfil de velocidad inválido → 422 (KMD-2004)
MODIFICATION_INVALID_SPEED_PROFILE = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "u_product": {"u_speed_plan": "PERFIL_INVALIDO"},
}

# ─── Centinelas — errores de negocio en baja (unsubscription) ────────────────
#
# u_routing.u_ontid="9999" → Huawei INDEX dinámico no resuelto        (BAJ-16)
# u_routing.u_ontid="9998" → Huawei INDEX parcial                     (BAJ-17)
# u_routing.u_ontid="8888" → ONT no encontrado                        (BAJ-18/19)
# u_routing.u_ontid="7777" → timeout SSH                              (BAJ-20/21)

DEACTIVATION_HUAWEI_INDEX_FAIL = {
    **DEACTIVATION_HUAWEI_VALID,
    "u_routing": {**DEACTIVATION_HUAWEI_VALID["u_routing"], "u_ontid": "9999"},
}

DEACTIVATION_HUAWEI_PARTIAL_INDEX = {
    **DEACTIVATION_HUAWEI_VALID,
    "u_routing": {**DEACTIVATION_HUAWEI_VALID["u_routing"], "u_ontid": "9998"},
}

DEACTIVATION_NOKIA_ONT_NOT_FOUND = {
    **DEACTIVATION_NOKIA_VALID,
    "u_routing": {**DEACTIVATION_NOKIA_VALID["u_routing"], "u_ontid": "8888"},
}

DEACTIVATION_HUAWEI_ONT_NOT_FOUND = {
    **DEACTIVATION_HUAWEI_VALID,
    "u_routing": {**DEACTIVATION_HUAWEI_VALID["u_routing"], "u_ontid": "8888"},
}

DEACTIVATION_NOKIA_SSH_TIMEOUT = {
    **DEACTIVATION_NOKIA_VALID,
    "u_routing": {**DEACTIVATION_NOKIA_VALID["u_routing"], "u_ontid": "7777"},
}

DEACTIVATION_HUAWEI_SSH_TIMEOUT = {
    **DEACTIVATION_HUAWEI_VALID,
    "u_routing": {**DEACTIVATION_HUAWEI_VALID["u_routing"], "u_ontid": "7777"},
}

# ─── Centinelas — errores de negocio en swap (device-modification) ───────────
#
# u_identification.u_new_serialnumber="FAIL00000000" → swap asimétrico (ONT-16)
# u_identification.u_new_serialnumber="VLAN00000000" → VLAN_CONFLICT   (ONT-17/18)
# u_routing.u_ontid="8888" → ONT no encontrado al iniciar swap         (ONT-19)
# u_identification.u_new_serialnumber="DUPL00000000" → serial duplicado(ONT-20)

DEVICE_MOD_ASYMMETRIC_FAIL = {
    **DEVICE_MOD_NOKIA_VALID,
    "u_identification": {
        **DEVICE_MOD_NOKIA_VALID["u_identification"],
        "u_new_serialnumber": "FAIL00000000",
    },
}

DEVICE_MOD_VLAN_CONFLICT = {
    **DEVICE_MOD_NOKIA_VALID,
    "u_identification": {
        **DEVICE_MOD_NOKIA_VALID["u_identification"],
        "u_new_serialnumber": "VLAN00000000",
    },
}

DEVICE_MOD_NOKIA_ONT_NOT_FOUND = {
    **DEVICE_MOD_NOKIA_VALID,
    "u_routing": {**DEVICE_MOD_NOKIA_VALID["u_routing"], "u_ontid": "8888"},
}

DEVICE_MOD_SERIAL_DUPLICATE = {
    **DEVICE_MOD_NOKIA_VALID,
    "u_identification": {
        **DEVICE_MOD_NOKIA_VALID["u_identification"],
        "u_new_serialnumber": "DUPL00000000",
    },
}

# ─── POST /api/Komands/v1/fiber-change ───────────────────────────────────────
#
# u_routing_new.u_ontid="9000" → posición destino ocupada              (FIB-07)

FIBER_CHANGE_DEST_PORT_OCCUPIED = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "3",
        "u_ontid": "45",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF1234567",
        "u_slid": "SLID-001",
    },
    "u_routing_new": {
        "u_olt": "OLT-SAN-001",
        "u_slot": "1",
        "u_pon": "5",
        "u_ontid": "9000",
        "u_technology": "GPON",
    },
}

# ─── Centinelas — reset con ONT offline ──────────────────────────────────────
#
# u_routing.u_ontid="6666" → ONT sin señal óptica (KMD-2003)

RESET_ONT_NOKIA_OFFLINE = {
    **RESET_ONT_NOKIA_VALID,
    "u_routing": {**RESET_ONT_NOKIA_VALID["u_routing"], "u_ontid": "6666"},
}

RESET_ONT_HUAWEI_OFFLINE = {
    **RESET_ONT_HUAWEI_VALID,
    "u_routing": {**RESET_ONT_HUAWEI_VALID["u_routing"], "u_ontid": "6666"},
}

RESET_ONT_NOKIA_ONT_NOT_FOUND = {
    **RESET_ONT_NOKIA_VALID,
    "u_routing": {**RESET_ONT_NOKIA_VALID["u_routing"], "u_ontid": "8888"},
}

RESET_ONT_HUAWEI_ONT_NOT_FOUND = {
    **RESET_ONT_HUAWEI_VALID,
    "u_routing": {**RESET_ONT_HUAWEI_VALID["u_routing"], "u_ontid": "8888"},
}

RESET_ONT_NOKIA_SSH_TIMEOUT = {
    **RESET_ONT_NOKIA_VALID,
    "u_routing": {**RESET_ONT_NOKIA_VALID["u_routing"], "u_ontid": "7777"},
}

RESET_ONT_HUAWEI_SSH_TIMEOUT = {
    **RESET_ONT_HUAWEI_VALID,
    "u_routing": {**RESET_ONT_HUAWEI_VALID["u_routing"], "u_ontid": "7777"},
}

# ─── Callbacks esperados (contratos de respuesta) ─────────────────────────────

CALLBACK_COMPLETED = {
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "correlation_id": "corr-test-001",
    "external_order_id": "ORD-SN-TEST-001",
    "status": "COMPLETED",
    "operation": "activation",
    "vno_code": "DTV",
    "olt_name": "OLT-SAN-001",
    "started_at": "2026-06-16T10:00:00Z",
    "completed_at": "2026-06-16T10:00:45Z",
    "duration_ms": 1250,
    "steps": [
        {"step": 1, "name": "create_ont", "status": "OK", "duration_ms": 850},
        {"step": 2, "name": "configure_service_port", "status": "OK", "duration_ms": 1200},
    ],
}

CALLBACK_ROLLBACK = {
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "correlation_id": "corr-test-002",
    "external_order_id": "ORD-SN-TEST-002",
    "status": "ROLLED_BACK",
    "operation": "unsubscription",
    "vno_code": "DTV",
    "olt_name": "OLT-SAN-002",
    "started_at": "2026-06-16T10:00:00Z",
    "completed_at": "2026-06-16T10:00:10Z",
    "duration_ms": 10000,
    "steps": [],
    "error": {
        "code": "KMD-5020",
        "category": "CLI_ERROR",
        "message": "Timeout esperando respuesta de la OLT",
        "retryable": True,
    },
}

# ─── Bajas SSAA ───────────────────────────────────────────────────────────────

DEACTIVATION_NOKIA_SSAA_ENTEL = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "ENTEL",
        "u_olt": "OLT-SCL-010",
        "u_slot": "1",
        "u_pon": "0",
        "u_ontid": "5",
        "u_product": "SSAA",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF9999999",
        "u_slid": "SLID-SCL-001",
    },
}

DEACTIVATION_HUAWEI_SSAA_MULTI_SERVICE = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "CVTR",
        "u_olt": "OLT-VAL-003",
        "u_slot": "1",
        "u_pon": "2",
        "u_ontid": "12",
        "u_product": "SSAA",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-VAL-001",
    },
    "u_services_port": [
        {"u_index": str(i), "u_service": s}
        for i, s in enumerate(["A", "B", "C", "D", "E"], 1)
    ],
}

DEACTIVATION_HUAWEI_PARTIAL_VOIP = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-H-001",
    },
    "u_action": {
        "u_voz": "F",
    },
}

# ─── Modificación — tipos adicionales ────────────────────────────────────────

MODIFICATION_ADD_SERVICE_VOIP_HUAWEI = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-H-001",
    },
    "u_action": {
        "u_type": "ADD_SERVICE",
        "u_voz": "T",
    },
}

MODIFICATION_REMOVE_SERVICE_HUAWEI = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "10",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-H-001",
    },
    "u_action": {
        "u_type": "REMOVE_SERVICE",
        "u_voz": "F",
    },
}

MODIFICATION_MIGRATE_FTTH_SSAA = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "ENTEL",
        "u_olt": "OLT-SCL-010",
        "u_slot": "1",
        "u_pon": "0",
        "u_ontid": "5",
        "u_product": "SSAA",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "ALCLF9999999",
        "u_slid": "SLID-SCL-001",
    },
    "u_action": {
        "u_type": "MIGRATE_FTTH_SSAA",
    },
    "u_services_port": [
        {"u_index": "1", "u_service": "A", "u_cvlan": "200", "u_svlan": "100"},
    ],
}

# ─── Payloads PV-RBK Rollback automático ─────────────────────────────────────
#
# u_routing.u_ontid="6661" → Nokia paso crítico falla → ROLLED_BACK    (RBK-001)
# u_routing.u_ontid="6662" → Huawei paso crítico falla → ROLLED_BACK   (RBK-002)
# u_routing.u_ontid="6663" → rollback también falla → ROLLBACK_FAILED  (RBK-003)
# u_routing.u_ontid="6664" → paso NO crítico falla → COMPLETED          (RBK-004)

ACTIVATION_NOKIA_ROLLBACK = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "u_routing": {**ACTIVATION_NOKIA_FTTH_VALID["u_routing"], "u_ontid": "6661"},
}

ACTIVATION_HUAWEI_ROLLBACK = {
    "u_callback_url": _CB,
    "u_routing": {
        "u_id_vno": "DTV",
        "u_olt": "OLT-SAN-002",
        "u_slot": "0",
        "u_pon": "2",
        "u_ontid": "6662",
        "u_product": "FTTH",
        "u_technology": "GPON",
    },
    "u_identification": {
        "u_serialnumber": "485754C12345",
        "u_slid": "SLID-H-001",
    },
    "u_action": {"u_iptv": "F", "u_voz": "T", "u_gestion": "F"},
    "u_product": {"u_speed_plan": "100M/20M"},
}

ACTIVATION_ROLLBACK_FAILED = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "u_routing": {**ACTIVATION_NOKIA_FTTH_VALID["u_routing"], "u_ontid": "6663"},
}

ACTIVATION_NON_CRITICAL_FAIL = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "u_routing": {**ACTIVATION_NOKIA_FTTH_VALID["u_routing"], "u_ontid": "6664"},
}

# ─── Payloads PV-IDP Idempotencia ─────────────────────────────────────────────

ACTIVATION_IDEMPOTENCY = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "u_routing": {**ACTIVATION_NOKIA_FTTH_VALID["u_routing"], "u_ontid": "46"},
}
