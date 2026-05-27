"""Paridad funcional Nokia — Komands vs BluePlanet (PRIORIDAD #1).

Convención: test_parity_nokia_<producto>_<operacion>_<escenario>

Valida que los comandos CLI generados por Komands para Nokia ISAM 7360 FX
sean idénticos a los que generaba BluePlanet (Ciena).

Referencias:
- device_type Netmiko: "nokia_sros"
- QoS: Q0/P4 Internet, Q4/P5 VoIP, Q5/P6 IPTV
- SSAA Nokia v3.0 usa line-profile
"""
import pytest
