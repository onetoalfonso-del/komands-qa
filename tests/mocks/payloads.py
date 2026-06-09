"""Payloads JSON de ejemplo para todos los endpoints de Komands API v1.

Convención de nombres: <operacion>_<vendor>_<producto>_<escenario>
Ejemplo: ACTIVATION_NOKIA_FTTH_VALID

Fuente de verdad: AnexoH_Especificacion_APIs_v2_2_FINAL.docx
"""

# ─── POST /api/v1/activation ──────────────────────────────────────────────────

ACTIVATION_NOKIA_FTTH_VALID = {
    "vno_code": "DTV",
    "external_order_id": "SO-ACT-001",
    "service_type": "FTTH",
    "olt_name": "OLT-SAN-001",
    "slot": 1,
    "port": 3,
    "ont_id": 45,
    "serial_ont": "ALCLF1234567",
    "internet": True,
    "voip": True,
    "iptv": True,
    "speed_profile": "100M_20M",
}

ACTIVATION_NOKIA_FTTH_INTERNET_ONLY = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "external_order_id": "SO-ACT-002",
    "voip": False,
    "iptv": False,
    "serial_ont": "ALCLF0000001",
}

ACTIVATION_NOKIA_SSAA_GROUP_A = {
    "vno_code": "ENTEL",
    "external_order_id": "SO-ACT-003",
    "service_type": "SSAA",
    "olt_name": "OLT-SCL-010",
    "slot": 1,
    "port": 0,
    "ont_id": 5,
    "serial_ont": "ALCLF9999999",
    "services": [
        {"code": "A", "svlan": 100, "cvlan": 200},
    ],
    "speed_profile": "200M_200M",
}

ACTIVATION_NOKIA_SSAA_GROUP_AC = {
    **ACTIVATION_NOKIA_SSAA_GROUP_A,
    "external_order_id": "SO-ACT-004",
    "services": [
        {"code": "A", "svlan": 100, "cvlan": 200},
        {"code": "C", "svlan": 100, "cvlan": 202},
    ],
}

ACTIVATION_NOKIA_SSAA_GROUP_ACD = {
    **ACTIVATION_NOKIA_SSAA_GROUP_A,
    "external_order_id": "SO-ACT-005",
    "services": [
        {"code": "A", "svlan": 100, "cvlan": 200},
        {"code": "C", "svlan": 100, "cvlan": 202},
        {"code": "D", "svlan": 100, "cvlan": 203},
    ],
}

ACTIVATION_NOKIA_SSAA_GROUP_BX = {
    **ACTIVATION_NOKIA_SSAA_GROUP_A,
    "external_order_id": "SO-ACT-006",
    "services": [{"code": "BX", "svlan": 100, "cvlan": 200}],
    "speed_profile": "1G_500M",
}

ACTIVATION_HUAWEI_FTTH_VALID = {
    "vno_code": "DTV",
    "external_order_id": "SO-ACT-007",
    "service_type": "FTTH",
    "olt_name": "OLT-SAN-002",
    "slot": 0,
    "port": 2,
    "ont_id": 10,
    "serial_ont": "485754C12345",
    "internet": True,
    "voip": True,
    "iptv": False,
    "speed_profile": "100M_20M",
}

ACTIVATION_HUAWEI_FTTH_WITH_IPTV = {
    **ACTIVATION_HUAWEI_FTTH_VALID,
    "external_order_id": "SO-ACT-008",
    "iptv": True,
    "serial_ont": "485754C99999",
}

ACTIVATION_HUAWEI_SSAA_GROUP_A = {
    "vno_code": "CVTR",
    "external_order_id": "SO-ACT-009",
    "service_type": "SSAA",
    "olt_name": "OLT-VAL-003",
    "slot": 1,
    "port": 2,
    "ont_id": 12,
    "serial_ont": "485754C12345",
    "services": [
        {"code": "A", "svlan": 100, "cvlan": 200},
    ],
    "speed_profile": "200M_200M",
}

# Payload con txn_id fijo (para tests de idempotencia)
ACTIVATION_WITH_TXN_ID = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
}

# Payloads inválidos
ACTIVATION_MISSING_REQUIRED_FIELDS = {
    "vno_code": "DTV",
    "service_type": "FTTH",
    # Faltan: olt_name, slot, port, serial_ont, internet/voip/iptv
}

ACTIVATION_INVALID_VNO = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "vno_code": "FAKE_VNO",
}

ACTIVATION_INVALID_VENDOR = {
    **ACTIVATION_NOKIA_FTTH_VALID,
    "olt_name": "OLT-ERICSSON-001",
}

# ─── POST /api/v1/unsuscription ───────────────────────────────────────────────

DEACTIVATION_NOKIA_VALID = {
    "vno_code": "DTV",
    "external_order_id": "SO-BAJ-001",
    "olt_name": "OLT-SAN-001",
    "slot": 1,
    "port": 3,
    "ont_id": 45,
}

DEACTIVATION_NOKIA_CVTR = {
    **DEACTIVATION_NOKIA_VALID,
    "vno_code": "CVTR",
    "external_order_id": "SO-BAJ-002",
    "olt_name": "OLT-VAL-001",
}

DEACTIVATION_NOKIA_TCH = {
    **DEACTIVATION_NOKIA_VALID,
    "vno_code": "TCH",
    "external_order_id": "SO-BAJ-003",
    "delete_vlan_on_terminate": True,
    "svlan": 300,
}

DEACTIVATION_HUAWEI_VALID = {
    "vno_code": "DTV",
    "external_order_id": "SO-BAJ-004",
    "olt_name": "OLT-SAN-002",
    "slot": 0,
    "port": 2,
    "ont_id": 10,
}

# ─── POST /api/v1/reset-ont ──────────────────────────────────────────────────

RESET_ONT_NOKIA_VALID = {
    "vno_code": "DTV",
    "external_order_id": "SO-RST-001",
    "olt_name": "OLT-SAN-001",
    "slot": 1,
    "port": 3,
    "ont_id": 45,
}

RESET_ONT_HUAWEI_VALID = {
    "vno_code": "DTV",
    "external_order_id": "SO-RST-002",
    "olt_name": "OLT-SAN-002",
    "slot": 0,
    "port": 2,
    "ont_id": 10,
}

# ─── POST /api/v1/device-modification (swap ONT) ─────────────────────────────

DEVICE_MOD_NOKIA_VALID = {
    "vno_code": "DTV",
    "external_order_id": "SO-ONT-001",
    "olt_name": "OLT-SAN-001",
    "slot": 1,
    "port": 3,
    "ont_id": 45,
    "new_serial_ont": "ALCLF7654321",
}

DEVICE_MOD_HUAWEI_VALID = {
    "vno_code": "DTV",
    "external_order_id": "SO-ONT-002",
    "olt_name": "OLT-SAN-002",
    "slot": 0,
    "port": 2,
    "ont_id": 10,
    "new_serial_ont": "485754C99999",
}

# ─── Payloads centinela — errores de negocio en reset ────────────────────────
#
# Valores reservados de ont_id:
#   8888 → ONT no encontrado en la OLT                              (RST-16/17)
#   7777 → timeout SSH, la OLT no respondió                         (RST-18/19)

RESET_ONT_NOKIA_ONT_NOT_FOUND = {
    **RESET_ONT_NOKIA_VALID,
    "ont_id": 8888,
}

RESET_ONT_HUAWEI_ONT_NOT_FOUND = {
    **RESET_ONT_HUAWEI_VALID,
    "ont_id": 8888,
}

RESET_ONT_NOKIA_SSH_TIMEOUT = {
    **RESET_ONT_NOKIA_VALID,
    "ont_id": 7777,
}

RESET_ONT_HUAWEI_SSH_TIMEOUT = {
    **RESET_ONT_HUAWEI_VALID,
    "ont_id": 7777,
}

# ─── POST /api/v1/modification ────────────────────────────────────────────────
#
# modification_type usa valores en minúscula per AnexoH v2.2 tabla 58:
#   speed_change, block, unblock, add_service, remove_service, migrate_ftth_ssaa

MODIFICATION_SPEED_CHANGE_NOKIA = {
    "vno_code": "DTV",
    "external_order_id": "SO-MOD-001",
    "modification_type": "speed_change",
    "olt_name": "OLT-SAN-001",
    "slot": 1,
    "port": 3,
    "ont_id": 45,
    "new_speed_profile": "200M_50M",
}

MODIFICATION_BLOCK_NOKIA = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "external_order_id": "SO-MOD-002",
    "modification_type": "block",
}

MODIFICATION_UNBLOCK_NOKIA = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "external_order_id": "SO-MOD-003",
    "modification_type": "unblock",
}

MODIFICATION_SPEED_CHANGE_HUAWEI = {
    "vno_code": "DTV",
    "external_order_id": "SO-MOD-004",
    "modification_type": "speed_change",
    "olt_name": "OLT-SAN-002",
    "slot": 0,
    "port": 2,
    "ont_id": 10,
    "new_speed_profile": "200M_50M",
}

MODIFICATION_BLOCK_HUAWEI = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "external_order_id": "SO-MOD-005",
    "modification_type": "block",
}

MODIFICATION_UNBLOCK_HUAWEI = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "external_order_id": "SO-MOD-006",
    "modification_type": "unblock",
}

MODIFICATION_SERVICE_ADD_IPTV = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "external_order_id": "SO-MOD-007",
    "modification_type": "add_service",
    "service_code": "IPTV",
}

MODIFICATION_SERVICE_REMOVE_VOIP = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "external_order_id": "SO-MOD-008",
    "modification_type": "remove_service",
    "service_code": "VOIP",
}

# ─── Payloads centinela — errores de negocio en modificación ──────────────────
#
# Valores de ont_id reservados:
#   8888 → ONT no encontrado en la OLT                              (MOD-18/19)
#   7777 → timeout SSH, la OLT no respondió                         (MOD-20/21)
#
# Centinelas de payload:
#   modification_type = "remove_service" → Nokia no lo soporta (KMD-4001)   (MOD-22)
#   new_speed_profile = "PERFIL_INVALIDO" → perfil no existe en la OLT      (MOD-23)

MODIFICATION_NOKIA_ONT_NOT_FOUND = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "ont_id": 8888,
}

MODIFICATION_HUAWEI_ONT_NOT_FOUND = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "ont_id": 8888,
}

MODIFICATION_NOKIA_SSH_TIMEOUT = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "ont_id": 7777,
}

MODIFICATION_HUAWEI_SSH_TIMEOUT = {
    **MODIFICATION_SPEED_CHANGE_HUAWEI,
    "ont_id": 7777,
}

# remove_service Nokia — la OLT Nokia ISAM 7360 no tiene comando de remove-service
# en FTTH. Komands debe rechazarlo con 422 (KMD-4001) antes de enviar nada a la red.
MODIFICATION_SERVICE_REMOVE_NOKIA = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "modification_type": "remove_service",
    "service_code": "VOIP",
}

# Perfil de velocidad que no existe en el catálogo configurado en la OLT
MODIFICATION_INVALID_SPEED_PROFILE = {
    **MODIFICATION_SPEED_CHANGE_NOKIA,
    "new_speed_profile": "PERFIL_INVALIDO",
}

# ─── Payloads centinela — errores de negocio en baja (unsuscription) ─────────
#
# Tabla de valores reservados (ont_id):
#   9999 → Huawei: _resolve_dynamic_ids() no pudo obtener el INDEX   (BAJ-16)
#   9998 → Huawei: INDEX parcial, 2 de 3 service-ports resueltos     (BAJ-17)
#   8888 → Nokia/Huawei: ONT ID no existe en la OLT                  (BAJ-18/19)
#   7777 → Nokia/Huawei: timeout SSH, la OLT no respondió            (BAJ-20/21)

# Centinela Huawei — INDEX dinámico no resuelto
DEACTIVATION_HUAWEI_INDEX_FAIL = {
    **DEACTIVATION_HUAWEI_VALID,
    "ont_id": 9999,
}

# Centinela Huawei — INDEX parcial
DEACTIVATION_HUAWEI_PARTIAL_INDEX = {
    **DEACTIVATION_HUAWEI_VALID,
    "ont_id": 9998,
}

# Centinela Nokia/Huawei — ONT no encontrado en la OLT
DEACTIVATION_NOKIA_ONT_NOT_FOUND = {
    **DEACTIVATION_NOKIA_VALID,
    "ont_id": 8888,
}

DEACTIVATION_HUAWEI_ONT_NOT_FOUND = {
    **DEACTIVATION_HUAWEI_VALID,
    "ont_id": 8888,
}

# Centinela Nokia/Huawei — timeout SSH a la OLT
DEACTIVATION_NOKIA_SSH_TIMEOUT = {
    **DEACTIVATION_NOKIA_VALID,
    "ont_id": 7777,
}

DEACTIVATION_HUAWEI_SSH_TIMEOUT = {
    **DEACTIVATION_HUAWEI_VALID,
    "ont_id": 7777,
}

# ─── Payloads centinela — errores de negocio en swap (device-modification) ───

# Centinela swap asimétrico — baja del ONT viejo OK, pero alta del nuevo falla.
# El ONT viejo ya fue retirado de la OLT y no puede recuperarse automáticamente.
DEVICE_MOD_ASYMMETRIC_FAIL = {
    **DEVICE_MOD_NOKIA_VALID,
    "new_serial_ont": "FAIL00000000",
}

# Centinela VLAN_CONFLICT — conflicto de VLAN al dar de alta el ONT nuevo.
# Komands deshace lo ejecutado y reporta ROLLED_BACK con KMD-3001.
DEVICE_MOD_VLAN_CONFLICT = {
    **DEVICE_MOD_NOKIA_VALID,
    "new_serial_ont": "VLAN00000000",
}

# ─── Callbacks esperados (contratos de respuesta) ─────────────────────────────
#
# Contrato completo per AnexoH v2.2: vno_code (no vno_id), objeto error con retryable.

CALLBACK_COMPLETED = {
    "txn_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "correlation_id": "corr-test-001",
    "external_order_id": "ORD-SN-TEST-001",
    "status": "COMPLETED",
    "operation": "activation",
    "vno_code": "DTV",
    "olt_name": "OLT-SAN-001",
    "started_at": "2026-06-09T10:00:00Z",
    "completed_at": "2026-06-09T10:00:45Z",
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
    "operation": "unsuscription",
    "vno_code": "DTV",
    "olt_name": "OLT-SAN-002",
    "started_at": "2026-06-09T10:00:00Z",
    "completed_at": "2026-06-09T10:00:10Z",
    "duration_ms": 10000,
    "steps": [],
    "error": {
        "code": "KMD-5020",
        "category": "CLI_ERROR",
        "message": "Timeout esperando respuesta de la OLT",
        "retryable": True,
    },
}
