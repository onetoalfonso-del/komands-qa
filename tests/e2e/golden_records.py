"""
Golden Records para todos los flujos E2E FTTH.
Cubre: Nokia (OLT-SAN-001) × 10 VNOs  +  Huawei (OLT-SAN-002) × 10 VNOs

Cada combinación tiene ONT ID y serial únicos para evitar conflictos.
Rango reservado QA: ONT IDs 81-90 en slot/pon de prueba.
"""
from dataclasses import dataclass
from typing import List

# (vno_real_en_payload, label_ascii_para_test_id)
_VNOS = [
    ("DTV",       "DTV"),
    ("VTR",       "VTR"),
    ("Entel",     "Entel"),
    ("ENTEL",     "ENTEL"),
    ("TCH",       "TCH"),
    ("Claro",     "Claro"),
    ("Genérico",  "Generico"),
    ("GTD",       "GTD"),
    ("WOM",       "WOM"),
    ("CVTR",      "CVTR"),
]


@dataclass
class GoldenRecord:
    vno: str            # valor real que va en el payload (ej: "Genérico")
    vno_label: str      # label ASCII para el test ID (ej: "Generico")
    vendor: str         # "Nokia" | "Huawei"
    olt: str
    slot: str
    pon: str
    ont_id: str
    serial: str
    serial_nuevo: str

    @property
    def label(self) -> str:
        return f"{self.vendor}-{self.vno_label}"

    # ── Payloads ──────────────────────────────────────────────────────────────

    def payload_alta(self) -> dict:
        return {
            "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
            "u_routing": {
                "u_id_vno":     self.vno,
                "u_olt":        self.olt,
                "u_slot":       self.slot,
                "u_pon":        self.pon,
                "u_ontid":      self.ont_id,
                "u_product":    "FTTH",
                "u_technology": "GPON",
            },
            "u_identification": {"u_serialnumber": self.serial},
            "u_action":  {"u_iptv": "F", "u_voz": "T", "u_gestion": "F"},
            "u_product": {"u_speed_plan": "100M/20M"},
        }

    def payload_modificacion(self) -> dict:
        return {
            "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
            "u_routing": {
                "u_id_vno":     self.vno,
                "u_olt":        self.olt,
                "u_slot":       self.slot,
                "u_pon":        self.pon,
                "u_ontid":      self.ont_id,
                "u_product":    "FTTH",
                "u_technology": "GPON",
            },
            "u_identification": {"u_serialnumber": self.serial},
            "u_action":  {"u_action": "speed_change"},
            "u_product": {"u_speed_plan": "200M/50M"},
        }

    def payload_cambio_dispositivo(self) -> dict:
        return {
            "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
            "u_routing": {
                "u_id_vno":     self.vno,
                "u_olt":        self.olt,
                "u_slot":       self.slot,
                "u_pon":        self.pon,
                "u_ontid":      self.ont_id,
                "u_product":    "FTTH",
                "u_technology": "GPON",
            },
            "u_identification": {
                "u_serialnumber":     self.serial,
                "u_new_serialnumber": self.serial_nuevo,
            },
        }

    def payload_baja(self) -> dict:
        return {
            "u_callback_url": "https://api.onnetfibra.cl/sn/komands/callback",
            "u_routing": {
                "u_id_vno":     self.vno,
                "u_olt":        self.olt,
                "u_slot":       self.slot,
                "u_pon":        self.pon,
                "u_ontid":      self.ont_id,
                "u_product":    "FTTH",
                "u_technology": "GPON",
            },
            "u_identification": {"u_serialnumber": self.serial_nuevo},
        }


def _build_nokia() -> List[GoldenRecord]:
    """Nokia OLT-SAN-001 × todos los VNOs. ONT IDs 81-90, slot=1 pon=0."""
    records = []
    for i, (vno, label) in enumerate(_VNOS, start=1):
        records.append(GoldenRecord(
            vno=vno,
            vno_label=label,
            vendor="Nokia",
            olt="OLT-SAN-001",
            slot="1",
            pon="0",
            ont_id=str(80 + i),
            serial=f"ALCL00QA{i:02d}01",
            serial_nuevo=f"ALCL00QA{i:02d}02",
        ))
    return records


def _build_huawei() -> List[GoldenRecord]:
    """Huawei OLT-SAN-002 × todos los VNOs. ONT IDs 81-90, slot=0 pon=0."""
    records = []
    for i, (vno, label) in enumerate(_VNOS, start=1):
        records.append(GoldenRecord(
            vno=vno,
            vno_label=label,
            vendor="Huawei",
            olt="OLT-SAN-002",
            slot="0",
            pon="0",
            ont_id=str(80 + i),
            serial=f"485754CQ{i:02d}01",
            serial_nuevo=f"485754CQ{i:02d}02",
        ))
    return records


NOKIA_FTTH  = _build_nokia()
HUAWEI_FTTH = _build_huawei()
ALL_FTTH    = NOKIA_FTTH + HUAWEI_FTTH
