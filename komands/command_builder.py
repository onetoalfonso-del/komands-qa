"""Config Engine — generación de comandos CLI para Nokia y Huawei.

Reglas fijas por vendor (fuente: LLD REF-09, REF-10):
  Nokia FTTH   → configure equipment ont interface shelf/card/port/logic_pon/ont_id
                 QoS por servicio: INTERNET Q0/P4 · VoIP Q4/P5 · IPTV Q5/P6
  Nokia SSAA   → configure equipment ont interface + line-profile + bridge-port por grupo
                 Grupos A/B/C/D/E/BX/DX con svlan/cvlan del payload
  Huawei FTTH  → interface gpon + ont add + service-port por gemport fijo
                 gemports: INTERNET=2 · VoIP=6 · IPTV=7
  Huawei SSAA  → interface gpon + ont add + service-port con svlan/cvlan del payload
  Riesgo R10   → INDEX service-port Huawei es dinámico; parse_service_port_index()
                 lo extrae de la respuesta SSH para pasos posteriores.
"""
import re

# ── Tablas de constantes por vendor ──────────────────────────────────────────

_NOKIA_SERVICE_QOS: dict[str, tuple[str, str]] = {
    "INTERNET": ("Q0", "P4"),
    "VOIP":     ("Q4", "P5"),
    "IPTV":     ("Q5", "P6"),
}

_HUAWEI_SERVICE_GEMPORT: dict[str, int] = {
    "INTERNET": 2,
    "VOIP":     6,
    "IPTV":     7,
}

_SERVICE_PORT_INDEX_RE = re.compile(r"Service Virtual Port\(index\)\s*:\s*(\d+)")

# SSAA Nokia: cada grupo usa un CVLAN distinto según su función de negocio
_NOKIA_SSAA_GROUP_CVLAN_KEY: dict[str, str] = {
    "A":  "cvlan_dato",
    "B":  "cvlan_dato",
    "C":  "cvlan_gestion",
    "D":  "cvlan_dato",
    "E":  "cvlan_internet",
    "BX": "cvlan_dato",
    "DX": "cvlan_dato",
}


# ── Excepción pública ─────────────────────────────────────────────────────────

class CommandBuilderError(Exception):
    pass


# ── Función auxiliar (Riesgo R10) ─────────────────────────────────────────────

def parse_service_port_index(olt_response: str) -> int:
    """Extrae el INDEX dinámico de service-port de una respuesta Huawei SSH.

    Busca la línea:
        Service Virtual Port(index) : <N>

    Raises CommandBuilderError si la línea no aparece en la respuesta.
    """
    match = _SERVICE_PORT_INDEX_RE.search(olt_response)
    if not match:
        raise CommandBuilderError(
            "service-port index no encontrado en la respuesta de la OLT"
        )
    return int(match.group(1))


# ── Clase principal ───────────────────────────────────────────────────────────

class CommandBuilder:
    """Genera la secuencia de comandos CLI para una operación sobre una OLT.

    vendor: "nokia" | "huawei"
    product: "FTTH" | "SSAA"
    """

    def __init__(self, vendor: str, product: str) -> None:
        self.vendor = vendor.lower()
        self.product = product.upper()

    def build_activation(
        self,
        *,
        services: list[str] | None = None,
        groups: list[str] | None = None,
        **params,
    ) -> list[str]:
        """Retorna la lista ordenada de comandos CLI para activar un ONT."""
        if not params.get("ont_serial"):
            raise CommandBuilderError("ont_serial es obligatorio para la activación")

        if self.product == "FTTH":
            if not services:
                raise CommandBuilderError("services no puede estar vacío")
            if self.vendor == "nokia":
                return self._nokia_ftth_activation(services=services, **params)
            if self.vendor == "huawei":
                return self._huawei_ftth_activation(services=services, **params)
            raise CommandBuilderError(f"Vendor no soportado: {self.vendor}")

        if self.product == "SSAA":
            if not groups:
                raise CommandBuilderError("groups no puede estar vacío para SSAA")
            if self.vendor == "nokia":
                return self._nokia_ssaa_activation(groups=groups, **params)
            if self.vendor == "huawei":
                return self._huawei_ssaa_activation(groups=groups, **params)
            raise CommandBuilderError(f"Vendor no soportado: {self.vendor}")

        raise CommandBuilderError(f"Producto no soportado: {self.product}")

    # ── Nokia FTTH ────────────────────────────────────────────────────────────

    def _nokia_ftth_activation(
        self,
        *,
        shelf: int,
        card: int,
        port: int,
        logic_pon: int,
        ont_id: int,
        ont_serial: str,
        speed_profile: str,
        description: str = "",
        services: list[str],
        **_,
    ) -> list[str]:
        iface = f"{shelf}/{card}/{port}/{logic_pon}/{ont_id}"
        cmds = [
            f"configure equipment ont interface {iface}",
            f"  sernum {ont_serial}",
            f"  sw-ver-pref auto",
            f"  admin-state up",
            "exit",
        ]
        for svc in services:
            queue, prio = _NOKIA_SERVICE_QOS.get(svc, ("Q0", "P4"))
            cmds.append(
                f"configure qos ont interface {iface}"
                f" service {svc} queue {queue} priority {prio}"
                f" profile {speed_profile}"
            )
        return cmds

    # ── Nokia SSAA ────────────────────────────────────────────────────────────

    def _nokia_ssaa_activation(
        self,
        *,
        shelf: int,
        card: int,
        port: int,
        logic_pon: int,
        ont_id: int,
        ont_serial: str,
        speed_profile: str,
        svlan: int,
        cvlan_dato: int,
        cvlan_internet: int | None = None,
        cvlan_gestion: int | None = None,
        description: str = "",
        groups: list[str],
        **_,
    ) -> list[str]:
        iface = f"{shelf}/{card}/{port}/{logic_pon}/{ont_id}"
        cvlan_map = {
            "cvlan_dato":     cvlan_dato,
            "cvlan_internet": cvlan_internet if cvlan_internet is not None else cvlan_dato,
            "cvlan_gestion":  cvlan_gestion  if cvlan_gestion  is not None else cvlan_dato,
        }
        cmds = [
            f"configure equipment ont interface {iface}",
            f"  sernum {ont_serial}",
            f"  sw-ver-pref auto",
            f"  admin-state up",
            "exit",
            f"configure qos ont interface {iface} line-profile {speed_profile}",
        ]
        for group in groups:
            cvlan_key = _NOKIA_SSAA_GROUP_CVLAN_KEY.get(group, "cvlan_dato")
            cvlan = cvlan_map[cvlan_key]
            cmds.append(
                f"configure bridge bridge-port {iface}:{cvlan}"
                f" svlan {svlan} group {group}"
            )
        return cmds

    # ── Huawei FTTH ───────────────────────────────────────────────────────────

    def _huawei_ftth_activation(
        self,
        *,
        shelf: int,
        card: int,
        port: int,
        logic_pon: int,
        ont_id: int,
        ont_serial: str,
        speed_profile: str,
        description: str = "",
        services: list[str],
        **_,
    ) -> list[str]:
        cmds = [
            f"interface gpon {shelf}/{card}",
            f'ont add {port} {ont_id} sn-auth {ont_serial} omci'
            f' ont-lineprofile-id 10 ont-srvprofile-id 10 desc "{description}"',
            "quit",
        ]
        for svc in services:
            gemport = _HUAWEI_SERVICE_GEMPORT.get(svc, 2)
            cmds.append(
                f"service-port vlan 100 gpon {shelf}/{card}/{port}"
                f" ont {ont_id} gemport {gemport}"
                f" multi-service user-vlan 100 rx-cttr 6 tx-cttr 6"
            )
        return cmds

    # ── Huawei SSAA ───────────────────────────────────────────────────────────

    def _huawei_ssaa_activation(
        self,
        *,
        shelf: int,
        card: int,
        port: int,
        logic_pon: int,
        ont_id: int,
        ont_serial: str,
        speed_profile: str,
        svlan: int,
        cvlan_dato: int,
        description: str = "",
        groups: list[str],
        **_,
    ) -> list[str]:
        cmds = [
            f"interface gpon {shelf}/{card}",
            f'ont add {port} {ont_id} sn-auth {ont_serial} omci'
            f' ont-lineprofile-id 10 ont-srvprofile-id 10 desc "{description}"',
            "quit",
        ]
        for group in groups:
            cmds.append(
                f"service-port vlan {svlan} gpon {shelf}/{card}/{port}"
                f" ont {ont_id} gemport 1"
                f" multi-service user-vlan {cvlan_dato} rx-cttr 6 tx-cttr 6"
            )
        return cmds

    # ── Baja (deactivation) — FTTH ────────────────────────────────────────────

    def build_deactivation(
        self,
        *,
        service_port_index: int | None = None,
        delete_vlan_on_terminate: bool = False,
        svlan: int | None = None,
        **params,
    ) -> list[str]:
        """Retorna la lista de comandos CLI para dar de baja un ONT FTTH."""
        if self.product == "FTTH":
            if self.vendor == "nokia":
                return self._nokia_ftth_deactivation(
                    delete_vlan_on_terminate=delete_vlan_on_terminate,
                    svlan=svlan,
                    **params,
                )
            if self.vendor == "huawei":
                if service_port_index is None:
                    raise CommandBuilderError(
                        "service_port_index es obligatorio para Huawei (Riesgo R10)"
                    )
                return self._huawei_ftth_deactivation(
                    service_port_index=service_port_index, **params
                )
            raise CommandBuilderError(f"Vendor no soportado: {self.vendor}")
        raise CommandBuilderError(f"Producto {self.product} no soportado para baja")

    def _nokia_ftth_deactivation(
        self,
        *,
        shelf: int,
        card: int,
        port: int,
        logic_pon: int,
        ont_id: int,
        delete_vlan_on_terminate: bool = False,
        svlan: int | None = None,
        **_,
    ) -> list[str]:
        iface = f"{shelf}/{card}/{port}/{logic_pon}/{ont_id}"
        cmds = [
            f"configure equipment ont interface {iface}",
            f"  admin-state down",
            "exit",
            f"no equipment ont interface {iface}",
        ]
        if delete_vlan_on_terminate and svlan is not None:
            cmds.append(f"no vlan {svlan}")
        return cmds

    def _huawei_ftth_deactivation(
        self,
        *,
        shelf: int,
        card: int,
        port: int,
        logic_pon: int,
        ont_id: int,
        service_port_index: int,
        **_,
    ) -> list[str]:
        return [
            f"interface gpon {shelf}/{card}",
            f"undo service-port {service_port_index}",
            f"ont delete {port} {ont_id}",
            "quit",
        ]

    # ── Modificación — FTTH ───────────────────────────────────────────────────

    def build_modification(
        self,
        *,
        operation_type: str,
        **params,
    ) -> list[str]:
        """Retorna la lista de comandos CLI para modificar un ONT FTTH.

        operation_type: SPEED_CHANGE | BLOCK | UNBLOCK
        """
        if not operation_type:
            raise CommandBuilderError("operation_type es obligatorio")
        if self.product == "FTTH":
            if self.vendor == "nokia":
                return self._nokia_ftth_modification(
                    operation_type=operation_type, **params
                )
            if self.vendor == "huawei":
                return self._huawei_ftth_modification(
                    operation_type=operation_type, **params
                )
            raise CommandBuilderError(f"Vendor no soportado: {self.vendor}")
        raise CommandBuilderError(
            f"Producto {self.product} no soportado para modificación"
        )

    def _nokia_ftth_modification(
        self,
        *,
        shelf: int,
        card: int,
        port: int,
        logic_pon: int,
        ont_id: int,
        operation_type: str,
        new_speed_profile: str | None = None,
        **_,
    ) -> list[str]:
        iface = f"{shelf}/{card}/{port}/{logic_pon}/{ont_id}"
        if operation_type == "SPEED_CHANGE":
            if not new_speed_profile:
                raise CommandBuilderError(
                    "new_speed_profile es obligatorio para SPEED_CHANGE"
                )
            return [f"configure qos ont interface {iface} line-profile {new_speed_profile}"]
        if operation_type == "BLOCK":
            return [
                f"configure equipment ont interface {iface}",
                f"  admin-state down",
                "exit",
            ]
        if operation_type == "UNBLOCK":
            return [
                f"configure equipment ont interface {iface}",
                f"  admin-state up",
                "exit",
            ]
        raise CommandBuilderError(f"operation_type no soportado: {operation_type}")

    def _huawei_ftth_modification(
        self,
        *,
        shelf: int,
        card: int,
        port: int,
        logic_pon: int,
        ont_id: int,
        operation_type: str,
        new_speed_profile: str | None = None,
        **_,
    ) -> list[str]:
        if operation_type == "SPEED_CHANGE":
            if not new_speed_profile:
                raise CommandBuilderError(
                    "new_speed_profile es obligatorio para SPEED_CHANGE"
                )
            return [
                f"interface gpon {shelf}/{card}",
                f"ont modify {port} {ont_id} traffic-profile {new_speed_profile}",
                "quit",
            ]
        if operation_type == "BLOCK":
            return [
                f"interface gpon {shelf}/{card}",
                f"ont deactivate {port} {ont_id}",
                "quit",
            ]
        if operation_type == "UNBLOCK":
            return [
                f"interface gpon {shelf}/{card}",
                f"ont activate {port} {ont_id}",
                "quit",
            ]
        raise CommandBuilderError(f"operation_type no soportado: {operation_type}")

    # ── Reset ONT — FTTH ──────────────────────────────────────────────────────

    def build_reset(self, **params) -> list[str]:
        """Retorna la lista de comandos CLI para resetear un ONT FTTH."""
        if self.product == "FTTH":
            if self.vendor == "nokia":
                return self._nokia_reset(**params)
            if self.vendor == "huawei":
                return self._huawei_reset(**params)
            raise CommandBuilderError(f"Vendor no soportado: {self.vendor}")
        raise CommandBuilderError(f"Producto {self.product} no soportado para reset")

    def _nokia_reset(
        self, *, shelf: int, card: int, port: int, logic_pon: int, ont_id: int, **_
    ) -> list[str]:
        iface = f"{shelf}/{card}/{port}/{logic_pon}/{ont_id}"
        return [
            f"configure equipment ont interface {iface}",
            f"  reset",
            "exit",
        ]

    def _huawei_reset(
        self, *, shelf: int, card: int, port: int, logic_pon: int, ont_id: int, **_
    ) -> list[str]:
        return [
            f"interface gpon {shelf}/{card}",
            f"ont reset {port} {ont_id}",
            "quit",
        ]

    # ── Cambio de ONT (device-modification) — FTTH ───────────────────────────

    def build_device_modification(
        self,
        *,
        old_ont_serial: str,
        new_ont_serial: str,
        service_port_index: int | None = None,
        services: list[str] | None = None,
        speed_profile: str | None = None,
        **params,
    ) -> list[str]:
        """Retorna la lista de comandos CLI para el swap de ONT FTTH."""
        if self.product == "FTTH":
            if self.vendor == "nokia":
                return self._nokia_device_modification(
                    old_ont_serial=old_ont_serial,
                    new_ont_serial=new_ont_serial,
                    services=services,
                    speed_profile=speed_profile,
                    **params,
                )
            if self.vendor == "huawei":
                if service_port_index is None:
                    raise CommandBuilderError(
                        "service_port_index es obligatorio para Huawei (Riesgo R10)"
                    )
                return self._huawei_device_modification(
                    old_ont_serial=old_ont_serial,
                    new_ont_serial=new_ont_serial,
                    service_port_index=service_port_index,
                    services=services,
                    **params,
                )
            raise CommandBuilderError(f"Vendor no soportado: {self.vendor}")
        raise CommandBuilderError(
            f"Producto {self.product} no soportado para device-modification"
        )

    def _nokia_device_modification(
        self,
        *,
        shelf: int, card: int, port: int, logic_pon: int, ont_id: int,
        old_ont_serial: str,
        new_ont_serial: str,
        speed_profile: str | None = None,
        services: list[str] | None = None,
        description: str = "",
        **_,
    ) -> list[str]:
        iface = f"{shelf}/{card}/{port}/{logic_pon}/{ont_id}"
        cmds = [
            f"configure equipment ont interface {iface}",
            f"  admin-state down",
            "exit",
            f"no equipment ont interface {iface}",
            f"configure equipment ont interface {iface}",
            f"  sernum {new_ont_serial}",
            f"  sw-ver-pref auto",
            f"  admin-state up",
            "exit",
        ]
        if services and speed_profile:
            for svc in services:
                queue, prio = _NOKIA_SERVICE_QOS.get(svc, ("Q0", "P4"))
                cmds.append(
                    f"configure qos ont interface {iface}"
                    f" service {svc} queue {queue} priority {prio}"
                    f" profile {speed_profile}"
                )
        return cmds

    def _huawei_device_modification(
        self,
        *,
        shelf: int, card: int, port: int, logic_pon: int, ont_id: int,
        old_ont_serial: str,
        new_ont_serial: str,
        service_port_index: int,
        services: list[str] | None = None,
        description: str = "",
        **_,
    ) -> list[str]:
        cmds = [
            f"interface gpon {shelf}/{card}",
            f"undo service-port {service_port_index}",
            f"ont delete {port} {ont_id}",
            "quit",
            f"interface gpon {shelf}/{card}",
            f'ont add {port} {ont_id} sn-auth {new_ont_serial} omci'
            f' ont-lineprofile-id 10 ont-srvprofile-id 10 desc "{description}"',
            "quit",
        ]
        if services:
            for svc in services:
                gemport = _HUAWEI_SERVICE_GEMPORT.get(svc, 2)
                cmds.append(
                    f"service-port vlan 100 gpon {shelf}/{card}/{port}"
                    f" ont {ont_id} gemport {gemport}"
                    f" multi-service user-vlan 100 rx-cttr 6 tx-cttr 6"
                )
        return cmds
