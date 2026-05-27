"""
Tests de RBAC — RBAC-01 a RBAC-09
====================================
Fuente: docs/05_gaps_seguridad.md → sección "RBAC portal web"

Qué estamos probando:
    El portal web de Komands tiene 4 roles con permisos distintos.
    Cada endpoint solo puede ser usado por los roles autorizados.

Los 4 roles (docs/04_modelo_datos.md):
    ADMIN    → todo: usuarios, config, ejecución, consulta
    OPERATOR → ejecutar operaciones de red + consultar
    VIEWER   → solo lectura (transacciones y estado)
    AUDITOR  → solo audit_log

Diferencia con test_auth.py:
    Los tests SEC prueban el CANAL API (ServiceNow → Axway → Komands).
    Estos tests RBAC prueban el PORTAL WEB (usuarios humanos).
    Son dos sistemas de auth distintos — diferente token, diferente lógica.
"""

import pytest
from fastapi.testclient import TestClient

from tests.mocks.payloads import ACTIVATION_NOKIA_FTTH_VALID

PAYLOAD = ACTIVATION_NOKIA_FTTH_VALID
TXN_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


class TestRBAC:
    """
    Los 9 casos RBAC del documento de seguridad.

    Tabla de permisos resumida:
    ┌──────────┬────────────┬────────────────────┬───────────┬──────────────┐
    │ Rol      │ /activation│ /transaction/{id}  │ /audit-log│ /users       │
    ├──────────┼────────────┼────────────────────┼───────────┼──────────────┤
    │ ADMIN    │ ✅ 202     │ ✅ 200             │ ✅ 200    │ ✅ 201       │
    │ OPERATOR │ ✅ 202     │ ✅ 200             │ ❌ 403    │ ❌ 403       │
    │ VIEWER   │ ❌ 403     │ ✅ 200             │ ❌ 403    │ ❌ 403       │
    │ AUDITOR  │ ❌ 403     │ ❌ 403             │ ✅ 200    │ ❌ 403       │
    └──────────┴────────────┴────────────────────┴───────────┴──────────────┘
    """

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-01: ADMIN puede ejecutar activación
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac01_admin_puede_activar(
        self, test_client: TestClient, admin_token: str
    ):
        """
        ESCENARIO: Usuario con rol ADMIN intenta POST /activation.

        El ADMIN tiene todos los permisos — debe poder ejecutar
        cualquier operación de red.

        Resultado esperado: HTTP 202 Accepted
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {admin_token}"}

        # ACT
        response = test_client.post(
            "/api/v1/activation", json=PAYLOAD, headers=headers
        )

        # ASSERT
        assert response.status_code == 202, (
            f"ADMIN debería poder activar (202) pero recibió {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-02: OPERATOR puede ejecutar activación
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac02_operator_puede_activar(
        self, test_client: TestClient, operator_token: str
    ):
        """
        ESCENARIO: Usuario con rol OPERATOR intenta POST /activation.

        El OPERATOR existe precisamente para ejecutar operaciones de red.
        Es el rol del técnico de provisión.

        Resultado esperado: HTTP 202 Accepted
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {operator_token}"}

        # ACT
        response = test_client.post(
            "/api/v1/activation", json=PAYLOAD, headers=headers
        )

        # ASSERT
        assert response.status_code == 202, (
            f"OPERATOR debería poder activar (202) pero recibió {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-03: VIEWER NO puede ejecutar activación
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac03_viewer_no_puede_activar(
        self, test_client: TestClient, viewer_token: str
    ):
        """
        ESCENARIO: Usuario con rol VIEWER intenta POST /activation.

        El VIEWER es de solo lectura — puede VER el estado de los servicios
        pero no puede modificar la red. Si pudiera activar, un analista
        de monitoreo podría accidentalmente (o maliciosamente) afectar clientes.

        Resultado esperado: HTTP 403 Forbidden
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {viewer_token}"}

        # ACT
        response = test_client.post(
            "/api/v1/activation", json=PAYLOAD, headers=headers
        )

        # ASSERT
        assert response.status_code == 403, (
            f"VIEWER no debería poder activar (403) pero recibió {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-04: AUDITOR NO puede ejecutar activación
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac04_auditor_no_puede_activar(
        self, test_client: TestClient, auditor_token: str
    ):
        """
        ESCENARIO: Usuario con rol AUDITOR intenta POST /activation.

        El AUDITOR solo puede revisar logs de auditoría — existe para
        que el área de cumplimiento pueda revisar quién hizo qué,
        sin poder modificar nada.

        Resultado esperado: HTTP 403 Forbidden
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {auditor_token}"}

        # ACT
        response = test_client.post(
            "/api/v1/activation", json=PAYLOAD, headers=headers
        )

        # ASSERT
        assert response.status_code == 403, (
            f"AUDITOR no debería poder activar (403) pero recibió {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-05: VIEWER puede consultar estado de transacción
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac05_viewer_puede_consultar_transaccion(
        self, test_client: TestClient, viewer_token: str
    ):
        """
        ESCENARIO: Usuario con rol VIEWER consulta GET /transaction/{uuid}.

        Aunque el VIEWER no puede operar la red, sí puede ver el estado
        de las transacciones. Esto es útil para monitoreo y soporte.

        Resultado esperado: HTTP 200 OK
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {viewer_token}"}

        # ACT
        response = test_client.get(
            f"/api/v1/transaction/{TXN_ID}", headers=headers
        )

        # ASSERT
        assert response.status_code == 200, (
            f"VIEWER debería poder consultar transacciones (200) pero recibió {response.status_code}"
        )
        body = response.json()
        assert body["txn_id"] == TXN_ID

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-06: AUDITOR puede ver el audit_log
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac06_auditor_puede_ver_audit_log(
        self, test_client: TestClient, auditor_token: str
    ):
        """
        ESCENARIO: Usuario con rol AUDITOR consulta GET /audit-log.

        El audit_log registra todas las acciones de usuarios (quién hizo
        qué, cuándo, desde qué IP). El AUDITOR existe específicamente
        para revisar esto — requerimiento de ciberseguridad ON·NET.
        Retención: 365 días (docs/04_modelo_datos.md).

        Resultado esperado: HTTP 200 OK
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {auditor_token}"}

        # ACT
        response = test_client.get("/api/v1/audit-log", headers=headers)

        # ASSERT
        assert response.status_code == 200, (
            f"AUDITOR debería poder ver audit-log (200) pero recibió {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-07: VIEWER NO puede ver el audit_log
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac07_viewer_no_puede_ver_audit_log(
        self, test_client: TestClient, viewer_token: str
    ):
        """
        ESCENARIO: Usuario con rol VIEWER intenta GET /audit-log.

        El audit_log contiene datos sensibles (IPs, acciones de usuarios,
        intentos fallidos). El VIEWER no tiene acceso — solo el AUDITOR
        y el ADMIN pueden revisarlo.

        Resultado esperado: HTTP 403 Forbidden
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {viewer_token}"}

        # ACT
        response = test_client.get("/api/v1/audit-log", headers=headers)

        # ASSERT
        assert response.status_code == 403, (
            f"VIEWER no debería ver audit-log (403) pero recibió {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-08: ADMIN puede crear usuarios
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac08_admin_puede_crear_usuarios(
        self, test_client: TestClient, admin_token: str
    ):
        """
        ESCENARIO: Usuario con rol ADMIN hace POST /users para crear un nuevo usuario.

        La gestión de usuarios (crear, modificar, desactivar) es exclusiva
        del ADMIN. Esto previene escalación de privilegios — solo el ADMIN
        puede otorgar acceso a otros.

        Resultado esperado: HTTP 201 Created
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {admin_token}"}
        nuevo_usuario = {
            "email": "nuevo.operador@onnet.cl",
            "role": "OPERATOR",
        }

        # ACT
        response = test_client.post(
            "/api/v1/users", json=nuevo_usuario, headers=headers
        )

        # ASSERT
        assert response.status_code == 201, (
            f"ADMIN debería poder crear usuarios (201) pero recibió {response.status_code}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # RBAC-09: OPERATOR NO puede crear usuarios
    # ──────────────────────────────────────────────────────────────────────────

    def test_rbac09_operator_no_puede_crear_usuarios(
        self, test_client: TestClient, operator_token: str
    ):
        """
        ESCENARIO: Usuario con rol OPERATOR intenta POST /users.

        El OPERATOR opera la red pero no gestiona usuarios. Si pudiera
        crear usuarios, podría crear cuentas con más privilegios que los suyos
        (escalación de privilegios).

        Resultado esperado: HTTP 403 Forbidden
        """
        # ARRANGE
        headers = {"Authorization": f"Bearer {operator_token}"}
        nuevo_usuario = {
            "email": "intruso@onnet.cl",
            "role": "ADMIN",
        }

        # ACT
        response = test_client.post(
            "/api/v1/users", json=nuevo_usuario, headers=headers
        )

        # ASSERT
        assert response.status_code == 403, (
            f"OPERATOR no debería crear usuarios (403) pero recibió {response.status_code}"
        )
