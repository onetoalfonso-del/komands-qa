"""API tests — POST /api/Komands/v1/fiber-modification (cambio de pelo/puerto PON).

Convención: test_fiber_modification_<vendor>_<escenario>

Cubre:
- Cambio de puerto PON Nokia (solo GPON)
- Cambio de puerto PON Huawei (solo GPON)
- Puerto destino sin capacidad → KMD-1003
- Rollback si falla algún paso del traslado
"""
import pytest
