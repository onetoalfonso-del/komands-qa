"""Payloads JSON de ejemplo para todos los endpoints de Komands API v1.

Convención de nombres: <operacion>_<vendor>_<producto>_<escenario>
Ejemplo: ACTIVATION_NOKIA_FTTH_VALID
"""
import uuid

CALLBACK_URL = "https://servicenow.onnet.cl/api/komands/callback"

# ─── POST /api/v1/activation ──────────────────────────────────────────────────

ACTIVATION_NOKIA_FTTH_VALID = {
    "vno_id": "DTV",
    "product": "FTTH",
    "technology": "GPON",
    "olt_name": "OLT-SAN-001",
    "olt_vendor": "nokia",
    "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
    "ont_serial": "ALCLF1234567",
    "services": ["INTERNET", "VOIP", "IPTV"],
    "speed_profile": "100M_20M",
    "callback_url": CALLBACK_URL,
}

ACTIVATION_NOKIA_FTTH_INTERNET_ONLY = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "services": ["INTERNET"],
    "ont_serial": "ALCLF0000001",
}

ACTIVATION_NOKIA_SSAA_GROUP_A = {
    "vno_id": "Entel",
    "product": "SSAA",
    "technology": "GPON",
    "olt_name": "OLT-SCL-010",
    "olt_vendor": "nokia",
    "shelf": 1, "card": 1, "port": 0, "logic_pon": 1, "ont_id": 5,
    "ont_serial": "ALCLF9999999",
    "groups": ["A"],
    "svlan": 100,
    "cvlan_dato": 200,
    "cvlan_internet": 201,
    "cvlan_gestion": 202,
    "speed_profile": "200M_200M",
    "callback_url": CALLBACK_URL,
}

ACTIVATION_NOKIA_SSAA_GROUP_AC = {
    **ACTIVATION_NOKIA_SSAA_GROUP_A,
    "groups": ["A", "C"],
}

ACTIVATION_NOKIA_SSAA_GROUP_ACD = {
    **ACTIVATION_NOKIA_SSAA_GROUP_A,
    "groups": ["A", "C", "D"],
}

ACTIVATION_NOKIA_SSAA_GROUP_BX = {
    **ACTIVATION_NOKIA_SSAA_GROUP_A,
    "technology": "XGSPON",
    "groups": ["BX"],
    "speed_profile": "1G_500M",
}

ACTIVATION_HUAWEI_FTTH_VALID = {
    "vno_id": "DTV",
    "product": "FTTH",
    "technology": "GPON",
    "olt_name": "OLT-SAN-002",
    "olt_vendor": "huawei",
    "shelf": 0, "card": 1, "port": 2, "logic_pon": 0, "ont_id": 10,
    "ont_serial": "485754C12345",
    "services": ["INTERNET", "VOIP"],
    "speed_profile": "100M_20M",
    "callback_url": CALLBACK_URL,
}

ACTIVATION_HUAWEI_FTTH_WITH_IPTV = {
    **ACTIVATION_HUAWEI_FTTH_VALID,
    "services": ["INTERNET", "VOIP", "IPTV"],
    "ont_serial": "485754C99999",
}

ACTIVATION_HUAWEI_SSAA_GROUP_A = {
    "vno_id": "ClaroVTR",
    "product": "SSAA",
    "technology": "GPON",
    "olt_name": "OLT-VAL-003",
    "olt_vendor": "huawei",
    "shelf": 1, "card": 1, "port": 2, "logic_pon": 1, "ont_id": 12,
    "ont_serial": "485754C12345",
    "groups": ["A"],
    "svlan": 100,
    "cvlan_dato": 200,
    "cvlan_internet": 201,
    "cvlan_gestion": 202,
    "speed_profile": "200M_200M",
    "callback_url": CALLBACK_URL,
}

# Payload con txn_id fijo (para tests de idempotencia)
ACTIVATION_WITH_TXN_ID = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
}

# Payloads inválidos
ACTIVATION_MISSING_REQUIRED_FIELDS = {
    "vno_id": "DTV",
    "product": "FTTH",
    # Faltan: olt_name, olt_vendor, shelf, card, port, ont_serial, services, callback_url
}

ACTIVATION_INVALID_VNO = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "vno_id": "FAKE_VNO",
}

ACTIVATION_INVALID_VENDOR = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "olt_vendor": "ericsson",
}

# ─── POST /api/v1/unsuscription ───────────────────────────────────────────────

DEACTIVATION_NOKIA_VALID = {
    "vno_id": "DTV",
    "olt_name": "OLT-SAN-001",
    "olt_vendor": "nokia",
    "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
    "callback_url": CALLBACK_URL,
}

DEACTIVATION_NOKIA_CVTR = {
    **DEACTIVATION_NOKIA_VALID,
    "vno_id": "ClaroVTR",
    "olt_name": "OLT-VAL-001",
}

DEACTIVATION_NOKIA_TCH = {
    **DEACTIVATION_NOKIA_VALID,
    "vno_id": "TCH",
    "delete_vlan_on_terminate": True,
    "svlan": 300,
}

DEACTIVATION_HUAWEI_VALID = {
    "vno_id": "DTV",
    "olt_name": "OLT-SAN-002",
    "olt_vendor": "huawei",
    "shelf": 0, "card": 1, "port": 2, "logic_pon": 0, "ont_id": 10,
    "callback_url": CALLBACK_URL,
}

# ─── POST /api/v1/reset-ont ──────────────────────────────────────────────────

RESET_ONT_NOKIA_VALID = {
    "vno_id": "DTV",
    "olt_name": "OLT-SAN-001",
    "olt_vendor": "nokia",
    "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
    "callback_url": CALLBACK_URL,
}

RESET_ONT_HUAWEI_VALID = {
    "vno_id": "DTV",
    "olt_name": "OLT-SAN-002",
    "olt_vendor": "huawei",
    "shelf": 0, "card": 1, "port": 2, "logic_pon": 0, "ont_id": 10,
    "callback_url": CALLBACK_URL,
}

# ─── POST /api/v1/device-modification (swap ONT) ─────────────────────────────

DEVICE_MOD_NOKIA_VALID = {
    "vno_id": "DTV",
    "olt_name": "OLT-SAN-001",
    "olt_vendor": "nokia",
    "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
    "old_ont_serial": "ALCLF1234567",
    "new_ont_serial": "ALCLF7654321",
    "callback_url": CALLBACK_URL,
}

DEVICE_MOD_HUAWEI_VALID = {
    "vno_id": "DTV",
    "olt_name": "OLT-SAN-002",
    "olt_vendor": "huawei",
    "shelf": 0, "card": 1, "port": 2, "logic_pon": 0, "ont_id": 10,
    "old_ont_serial": "485754C12345",
    "new_ont_serial": "485754C99999",
    "callback_url": CALLBACK_URL,
}

# ─── POST /api/v1/fiber-modification (cambio de pelo) ────────────────────────

FIBER_MOD_NOKIA_VALID = {
    "vno_id": "DTV",
    "olt_vendor": "nokia",
    "source_olt": "OLT-SAN-001",
    "source_shelf": 1, "source_card": 2, "source_port": 3,
    "source_logic_pon": 1, "source_ont_id": 45,
    "target_olt": "OLT-SAN-001",
    "target_shelf": 1, "target_card": 2, "target_port": 4,
    "target_logic_pon": 1,
    "callback_url": CALLBACK_URL,
}

# ─── POST /api/v1/modification ────────────────────────────────────────────────

MODIFICATION_SPEED_CHANGE_NOKIA = {
    "vno_id": "DTV",
    "operation_type": "SPEED_CHANGE",
    "olt_vendor": "nokia",
    "olt_name": "OLT-SAN-001",
    "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
    "new_speed_profile": "200M_50M",
    "callback_url": CALLBACK_URL,
}

MODIFICATION_BLOCK_NOKIA = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "operation_type": "BLOCK",
}

MODIFICATION_UNBLOCK_NOKIA = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "operation_type": "UNBLOCK",
}

MODIFICATION_SPEED_CHANGE_HUAWEI = {
    "vno_id": "DTV",
    "operation_type": "SPEED_CHANGE",
    "olt_vendor": "huawei",
    "olt_name": "OLT-SAN-002",
    "shelf": 0, "card": 1, "port": 2, "logic_pon": 0, "ont_id": 10,
    "new_speed_profile": "200M_50M",
    "callback_url": CALLBACK_URL,
}

MODIFICATION_BLOCK_HUAWEI = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "operation_type": "BLOCK",
}

MODIFICATION_UNBLOCK_HUAWEI = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "operation_type": "UNBLOCK",
}

MODIFICATION_SERVICE_ADD_IPTV = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "operation_type": "SERVICE_ADD",
    "service": "IPTV",
}

MODIFICATION_SERVICE_REMOVE_VOIP = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "operation_type": "SERVICE_REMOVE",
    "service": "VOIP",
}

# ─── Callbacks esperados (contratos de respuesta) ─────────────────────────────

CALLBACK_COMPLETED = {
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "COMPLETED",
    "operation": "activation",
    "vno_id": "DTV",
    "completed_at": "2026-04-13T15:30:45Z",
    "steps": [
        {"step": 1, "name": "create_ont", "status": "OK", "duration_ms": 850},
        {"step": 2, "name": "configure_service_port", "status": "OK", "duration_ms": 1200},
    ],
}

CALLBACK_ROLLBACK = {
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "ROLLBACK",
    "failed_step": 3,
    "error_code": "KMD-2003",
    "error_message": "Timeout ejecutando comando en OLT",
    "steps": [],
}
