"""Paridad funcional Huawei — Komands vs BluePlanet (PRIORIDAD #1).

Convención: test_parity_huawei_<producto>_<operacion>_<escenario>

Valida que los comandos CLI generados por Komands para Huawei MA5800/MA5600T
sean idénticos a los que generaba BluePlanet (Ciena).

Referencias:
- device_type Netmiko: "huawei_vrp"
- Gemports fijos FTTH: Internet=2, VoIP=6, IPTV=7
- Riesgo R10: service-port INDEX dinámico — parsear respuesta del equipo
"""
import pytest
