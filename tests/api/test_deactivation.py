"""API tests — POST /api/v1/deactivation.

Convención: test_deactivation_<vendor>_<producto>_<escenario>

Cubre:
- Baja de acceso Nokia FTTH y SSAA
- Baja de acceso Huawei FTTH y SSAA
- Rollback automático si falla algún paso
- ONT inexistente → error descriptivo KMD-1002
- OLT inalcanzable → KMD-2001 / 503
"""
import pytest
