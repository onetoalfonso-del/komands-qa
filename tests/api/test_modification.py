"""API tests — POST /api/v1/modification.

Convención: test_modification_<vendor>_<operation_type>_<escenario>

operation_type soportados:
- SPEED_CHANGE
- BLOCK
- UNBLOCK
- SERVICE_ADD
- SERVICE_REMOVE
- FTTH_TO_SSAA
"""
import pytest
