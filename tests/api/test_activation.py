"""API tests — POST /api/v1/activation.

Convención: test_activation_<vendor>_<producto>_<escenario>

Cubre:
- FTTH Nokia: INTERNET, VOIP, IPTV (servicios individuales y combinados)
- FTTH Huawei: INTERNET, VOIP, IPTV
- SSAA Nokia: grupos A, B, C, D, E, BX, DX y combinaciones
- SSAA Huawei: grupos A, B, C, D
- Respuesta 202 + txn_id en todos los casos válidos
- Validaciones 400/422 por campos faltantes o inválidos
- Idempotencia: mismo txn_id → 409 o resultado idéntico sin re-ejecución
"""
import pytest
