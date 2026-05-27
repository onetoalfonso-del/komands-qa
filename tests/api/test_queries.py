"""API tests — Consultas síncronas (200 directo, sin encolar en Redis).

Endpoints cubiertos:
- GET  /api/v1/access/{id}
- POST /api/v1/query/pon-info
- GET  /api/v1/port-occupancy
- GET  /api/v1/transaction/{uuid}
"""
import pytest
