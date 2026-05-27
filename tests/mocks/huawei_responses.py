"""Respuestas SSH simuladas para Huawei MA5800/MA5600T — device_type: huawei_vrp.

Riesgo R10: el service-port INDEX es dinámico. Después de crearlo, hay que
leerlo del equipo para usarlo en pasos posteriores.
"""


# ─── Respuestas de creación de ONT ────────────────────────────────────────────

ONT_ADD_OK = """\
{ <cr>||<K> }:
Command:
        ont add 0 2 0 10 sn-auth 485754C12345 snmp ont-lineprofile-id 1 ont-srvprofile-id 1
ONTID :10
OMCC channel :GEM port 2048
"""

ONT_ADD_ALREADY_EXISTS = """\
Failure: The ONT SN already exists.
"""

# ─── Gemports fijos FTTH Huawei ───────────────────────────────────────────────
# Internet=2, VoIP=6, IPTV=7 (valores fijos, no parametrizables)

GEMPORT_INTERNET_ADD_OK = "GEM port 2 (Internet) configured."
GEMPORT_VOIP_ADD_OK = "GEM port 6 (VoIP) configured."
GEMPORT_IPTV_ADD_OK = "GEM port 7 (IPTV) configured."

# ─── Respuestas de service-port (INDEX DINÁMICO — Riesgo R10) ─────────────────

SERVICE_PORT_ADD_OK = """\
{ <cr>||<K> }:
Command:
        service-port vlan 100 gpon 0/1/2 ont 10 gemport 2 multi-service user-vlan 200 rx-cttr 6 tx-cttr 6
 Failure: The operation failed.
Reconfig port:
NOTICE: This operation will take a few minutes, please wait...
Service Virtual Port(index) : 1025
"""

# INDEX dinámico: hay que parsear "Service Virtual Port(index) : <N>" de la respuesta
SERVICE_PORT_ADD_OK_INDEX = 1025

SERVICE_PORT_ADD_VLAN_CONFLICT = """\
Failure: The VLAN has been used.
"""

SERVICE_PORT_QUERY_OK = """\
{ <cr>||<K> }:
------------------------------------------------------------------------------------------
NO.  ONT-ID   DESCRIPTION     TYPE    GEMPORT  INBOUND-TRAFFIC-TABLE  OUTBOUND-TRAFFIC-TABLE
------------------------------------------------------------------------------------------
0    10       Internet-DTV    eth     2        6                      6
"""

# ─── Respuestas de baja (deactivation) ────────────────────────────────────────

ONT_DELETE_OK = """\
Undo ont: ont-id 10, port: 0/1/2
NOTICE: Deleting the ONT will cause service interruption. Continue? [Y/N]:Y
"""

SERVICE_PORT_DELETE_OK = """\
Deleting service-port 1025...
"""

ONT_DELETE_NOT_FOUND = """\
Failure: The ONT does not exist.
"""

# ─── Respuestas de consulta PON ───────────────────────────────────────────────

PON_INFO_OK = """\
F/S/P   ONT-ID  SN            Control-flag  Run-state   Config-state  Match-state
---------------------------------------------------------------------------
0/1/ 2  10      485754C12345  active        online      normal        match
"""

PON_INFO_EMPTY = """\
Failure: The ONT does not exist.
"""

PORT_OCCUPANCY_OK = """\
F/S/P   Total  Online  Offline  Config
0/1/2   128    87      0        87
"""

# ─── Respuestas de modificación de velocidad ──────────────────────────────────

SPEED_CHANGE_OK = """\
NOTICE: The traffic table referenced by service port exists. This operation resets the traffic table.
"""

SPEED_CHANGE_PROFILE_NOT_FOUND = """\
Failure: The traffic table does not exist.
"""

# ─── Respuestas de error SSH ──────────────────────────────────────────────────

SSH_AUTH_FAILED = "Authentication failed."
SSH_TIMEOUT = "SSH connection timed out after 30 seconds."
SSH_HOST_UNREACHABLE = "No route to host."
