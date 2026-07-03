"""Tests de seguridad que requieren infraestructura real (BLOQUEADOS).

PV-SEC-004: Rate limiting — requiere API Gateway (Axway APIM / Kong).
PV-SEC-005: Audit log PostgreSQL — requiere PostgreSQL DEV con schema.
PV-SEC-006: TLS 1.2+ hacia OLT SSH — requiere OLT real en ambiente QA.

Estos tests no corren en T1 (mock). Pertenecen a:
  PV-SEC-004 → T7 (seguridad OWASP, cuando API GW esté configurado)
  PV-SEC-005 → T5 (PostgreSQL DEV desplegado)
  PV-SEC-006 → T4 (OLTs reales en QA)
"""
import pytest


@pytest.mark.skip(reason="PV-SEC-004: Requiere API Gateway con rate limiting configurado")
def test_sec_pv004_rate_limit_60rpm_retorna_429():
    """
    PV-SEC-004: Rate limit 60 req/min por token — solicitud 61 retorna 429.

    El API Gateway debe rechazar con HTTP 429 Too Many Requests cuando un
    token supera el límite de 60 solicitudes por minuto.
    Requiere configuración de throttling en Axway APIM o Kong.
    """
    pass


@pytest.mark.skip(reason="PV-SEC-005: Requiere PostgreSQL DEV + audit_log con trigger de inmutabilidad")
def test_sec_pv005_operacion_exitosa_registra_audit_log():
    """
    PV-SEC-005: Toda operación exitosa genera registro en audit_log PostgreSQL.

    audit_log debe contener: txn_id, action, vno_code, olt_name, actor,
    timestamp. El trigger de inmutabilidad impide UPDATE/DELETE posterior.
    Requiere PostgreSQL DEV con schema Komands desplegado.
    """
    pass


@pytest.mark.skip(reason="PV-SEC-006: Requiere OLT real en QA — verifica TLS 1.2+ hacia OLT SSH")
def test_sec_pv006_conexion_sin_cert_tls_rechazada():
    """
    PV-SEC-006: Conexión SSH a OLT sin certificado TLS válido es rechazada.

    Komands debe usar TLS 1.2 mínimo en todas las conexiones salientes.
    Un intento de conexión sin cert o con cert expirado debe devolver
    error de handshake (KMD-5020 o similar), no conectar sin verificar.
    Requiere OLT física en ambiente QA.
    """
    pass
