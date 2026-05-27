"""Respuestas SSH simuladas para Nokia ISAM 7360 FX (Rel. 6.2) — device_type: nokia_sros."""


# ─── Respuestas de creación de ONT ────────────────────────────────────────────

ONT_CREATE_OK = """\
*A:OLT-SAN-001# configure equipment ont interface 1/2/3/1/45
*A:OLT-SAN-001(config-ont-1/2/3/1/45)# exit
"""

ONT_CREATE_ALREADY_EXISTS = """\
MINOR: MDAL #1503 Object already exists.
"""

ONT_CREATE_TIMEOUT = """\
Error: command timed out
"""

# ─── Respuestas de service-port / bridge-port ─────────────────────────────────

SERVICE_PORT_INTERNET_OK = """\
*A:OLT-SAN-001(config-service)# exit
"""

SERVICE_PORT_VOIP_OK = """\
*A:OLT-SAN-001(config-service)# exit
"""

SERVICE_PORT_IPTV_OK = """\
*A:OLT-SAN-001(config-service)# exit
"""

SERVICE_PORT_ERROR_VLAN = """\
MINOR: MDAL #1402 Invalid VLAN ID specified.
"""

# ─── Respuestas de QoS (Queue / Priority) ─────────────────────────────────────
# Nokia: Q0/P4 Internet, Q4/P5 VoIP, Q5/P6 IPTV

QUEUE_INTERNET_OK = "Queue Q0/P4 configured successfully."
QUEUE_VOIP_OK = "Queue Q4/P5 configured successfully."
QUEUE_IPTV_OK = "Queue Q5/P6 configured successfully."

# ─── Respuestas de baja (deactivation) ────────────────────────────────────────

ONT_DELETE_OK = """\
*A:OLT-SAN-001# no equipment ont interface 1/2/3/1/45
*A:OLT-SAN-001# exit
"""

ONT_DELETE_NOT_FOUND = """\
MINOR: MDAL #1501 Object does not exist.
"""

# ─── Respuestas de consulta PON ───────────────────────────────────────────────

PON_INFO_OK = """\
ONT-ID  Serial        Status    Rx-Power  Description
------  ----------    ------    --------  -----------
45      ALCLF1234567  ACTIVE    -18.2 dBm Internet-DTV
"""

PON_INFO_EMPTY = """\
No ONT entries found on this PON port.
"""

PORT_OCCUPANCY_OK = """\
Port 1/2/3: ONTs configured: 87 / 128
"""

# ─── Respuestas de modificación de velocidad (SSAA line-profile) ──────────────

SPEED_CHANGE_OK = """\
*A:OLT-SAN-001(config-ont-1/2/3/1/45)# line-profile 200M_200M
*A:OLT-SAN-001(config-ont-1/2/3/1/45)# exit
"""

SPEED_CHANGE_PROFILE_NOT_FOUND = """\
MINOR: MDAL #2200 Line profile not found: 200M_200M
"""
