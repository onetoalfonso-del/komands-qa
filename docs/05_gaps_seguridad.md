# Seguridad — Gaps AS-IS vs TO-BE y Casos de Prueba

## Estado actual (AS-IS) vs objetivo (TO-BE)

| Gap | AS-IS (hoy) | TO-BE (antes de Go-Live) | Sprint |
|-----|-------------|--------------------------|--------|
| JWT algoritmo | HS256 (portal) | RS256 (integración Axway) | Sprint 1 |
| 2FA/TOTP | Ausente (campos en BD listos) | Obligatorio por rol ADMIN y OPERATOR | Sprint 1 |
| Passwords | Schema legacy `public.usuarios` sin bcrypt | bcrypt en `komands.app_user` | Sprint 1 |
| SSH credentials | Sin cifrado en BD | AES-256/Fernet en `ssh_credential.password_enc` | Sprint 1 — ESCALADO a CISO |
| Redis | Ausente | Cola + cache + sesiones + Sentinel HA | Pre Sprint 1 |
| RBAC | 3 roles + 22 permisos | 4 roles: ADMIN, OPERATOR, VIEWER, AUDITOR | Sprint 1 |
| Cookie portal | Sin `secure=True` | `secure=True` en PROD/QA | Sprint 1 |

**Todos estos gaps son BLOQUEANTES para Go-Live.** El CISO debe aprobar antes del despliegue en PROD.

---

## Arquitectura de seguridad TO-BE

### Autenticación APIs (Axway → Komands)
```
ServiceNow → Axway APIM → (valida JWT RS256) → Komands API Gateway
```
- OAuth 2.0 client_credentials
- JWT firmado con RS256 (clave pública/privada)
- Claims requeridos: sub, vno_id, scope, exp
- Expiración: 1 hora (configurable)

### Autenticación portal web (usuarios humanos)
```
Usuario → POST /api/login → JWT HS256 (AS-IS) / RS256 (TO-BE) → Cookie httponly
→ En cada request: TokenRefreshMiddleware verifica token_version
```
- bcrypt para passwords
- TOTP obligatorio para ADMIN y OPERATOR
- Cookie: httponly=True, samesite=lax, secure=True (PROD/QA)

### Cifrado en tránsito
- TLS 1.2+ obligatorio en todas las comunicaciones entre componentes
- SSH nativo hacia OLTs

### Cifrado en reposo
- Passwords: bcrypt
- SSH credentials: AES-256/Fernet en campo `password_enc`
- Secrets y variables de entorno: gestor de secretos K8s (Sealed Secrets o Vault)

### Logging y auditoría
- Tabla `audit_log`: retención 365 días (requerimiento legal Chile)
- Logs estructurados JSON con: timestamp, user_id, action, resource, ip, result
- Trazabilidad UUID end-to-end en toda la cadena

---

## Casos de prueba de seguridad

### Autenticación APIs

| ID | Caso | Input | Resultado esperado |
|----|------|-------|--------------------|
| SEC-01 | Sin token | POST /activation sin Authorization header | HTTP 401 |
| SEC-02 | Token malformado | Authorization: Bearer "abc123" | HTTP 401 |
| SEC-03 | Token expirado | JWT con exp en el pasado | HTTP 401 |
| SEC-04 | Token válido | JWT válido con claims correctos | HTTP 202 |
| SEC-05 | VNO no autorizada | JWT válido pero vno_id = "FAKE" | HTTP 403 |
| SEC-06 | Scope insuficiente | JWT con scope solo "komands:read" intentando POST | HTTP 403 |

### RBAC portal web

| ID | Caso | Rol | Acción | Resultado esperado |
|----|------|-----|--------|--------------------|
| RBAC-01 | ADMIN puede ejecutar activación | ADMIN | POST /activation | HTTP 202 |
| RBAC-02 | OPERATOR puede ejecutar activación | OPERATOR | POST /activation | HTTP 202 |
| RBAC-03 | VIEWER NO puede ejecutar activación | VIEWER | POST /activation | HTTP 403 |
| RBAC-04 | AUDITOR NO puede ejecutar activación | AUDITOR | POST /activation | HTTP 403 |
| RBAC-05 | VIEWER puede consultar transacción | VIEWER | GET /transaction/{id} | HTTP 200 |
| RBAC-06 | AUDITOR puede ver audit_log | AUDITOR | GET /audit-log | HTTP 200 |
| RBAC-07 | VIEWER NO puede ver audit_log | VIEWER | GET /audit-log | HTTP 403 |
| RBAC-08 | ADMIN puede crear usuarios | ADMIN | POST /users | HTTP 201 |
| RBAC-09 | OPERATOR NO puede crear usuarios | OPERATOR | POST /users | HTTP 403 |

### Credenciales SSH cifradas

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| CRYPT-01 | Campo password_enc en BD no es texto plano | El valor inicia con prefijo Fernet ($2...) o está cifrado |
| CRYPT-02 | El adapter puede descifrar y conectarse | Conexión SSH exitosa usando credencial de BD |
| CRYPT-03 | Si la llave de cifrado es incorrecta | Error descriptivo, NO expone password |

### Idempotencia (también seguridad)

| ID | Caso | Resultado esperado |
|----|------|--------------------|
| IDEM-01 | Mismo txn_id enviado dos veces | Segunda vez: HTTP 409 o devuelve mismo resultado sin re-ejecutar |
| IDEM-02 | Mismo txn_id con distinto payload | HTTP 409 Conflict |

---

## Casos de prueba de Feature Flags

| ID | Caso | Estado flag | Resultado esperado |
|----|------|-------------|--------------------|
| FF-01 | Flag DTV desactivado | DTV disabled | HTTP 200 pero KMD-4001 en response o tráfico va a BluePlanet |
| FF-02 | Flag DTV activado | DTV enabled | Operación procesada por Komands normalmente |
| FF-03 | Flag solo para FTTH activado | DTV FTTH=enabled, SSAA=disabled | FTTH va a Komands, SSAA va a BluePlanet |
| FF-04 | Rollback de flag (apagar en < 5 min) | Cambiar enabled=false | Próximas operaciones van a BluePlanet |

---

## Checklist Go-Live (criterios bloqueantes)
- [ ] JWT RS256 implementado y validado
- [ ] 2FA/TOTP activo para roles ADMIN y OPERATOR
- [ ] Passwords migrados a bcrypt en schema komands
- [ ] SSH credentials cifrados con AES-256/Fernet
- [ ] Redis operativo con Sentinel HA
- [ ] Cookie secure=True en ambientes PROD y QA
- [ ] RBAC 4 roles migrados (ADMIN, OPERATOR, VIEWER, AUDITOR)
- [ ] Aprobación formal CISO ON·NET
- [ ] Escaneo de vulnerabilidades sin críticos
- [ ] Audit log funcionando con retención 365 días
- [ ] TLS 1.2+ en todas las comunicaciones internas
