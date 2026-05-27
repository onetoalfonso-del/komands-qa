"""Unit tests — Command Builder (Catálogo Técnico + Config Engine).

Convención: test_<operacion>_<vendor>_<producto>_<escenario>

Cubre:
- Resolución de templates CLI por vendor/producto/operación
- Sustitución de variables en templates
- Validación de parámetros obligatorios
- Nokia vs Huawei: templates no intercambiables
"""
import pytest
