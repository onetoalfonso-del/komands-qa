"""API tests — POST /api/v1/device-modification (swap de ONT).

Convención: test_device_modification_<vendor>_<escenario>

Cubre:
- Swap Nokia: baja ONT anterior + alta ONT nueva con misma configuración
- Swap Huawei: ídem (con manejo de service-port INDEX dinámico R10)
- Serial nuevo ya existe en OLT → KMD-1002
- Rollback si falla el alta de la nueva ONT
"""
import pytest
