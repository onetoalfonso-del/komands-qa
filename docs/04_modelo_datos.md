# Modelo de Datos — Komands

## Motor de BD
PostgreSQL 15+ con dos schemas:
- `komands` — tablas nuevas (25 tablas)
- `public` — tablas legacy ADC (8 tablas, compatibilidad)

## Campos de auditoría estándar (en TODAS las tablas)
```sql
created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
created_by  VARCHAR(100) NOT NULL DEFAULT 'system'
updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
updated_by  VARCHAR(100) NOT NULL DEFAULT 'system'
```

---

## SCHEMA KOMANDS — 7 dominios

### Dominio 1: Infraestructura de Red (6 tablas)

**olt_vendor** — fabricantes
```sql
vendor_id   SERIAL PK
name        VARCHAR(50)  -- 'nokia', 'huawei'
```

**olt_model** — modelos de equipo
```sql
model_id    SERIAL PK
vendor_id   FK → olt_vendor
name        VARCHAR(100) -- 'ISAM 7360 FX', 'MA5800'
technology  VARCHAR(20)  -- 'GPON', 'XGSPON', 'GPON/XGSPON'
```

**olt** — equipos de red activos
```sql
olt_id      SERIAL PK
name        VARCHAR(100) UNIQUE  -- 'OLT-SAN-001'
model_id    FK → olt_model
ip_address  INET
location    VARCHAR(200)
status      VARCHAR(20)  -- 'ACTIVE', 'MAINTENANCE', 'INACTIVE'
```

**olt_shelf, olt_card, olt_port** — jerarquía física dentro de la OLT

---

### Dominio 2: Catálogo de Comandos (6 tablas)

**command_template** — templates CLI parametrizados
```sql
template_id   SERIAL PK
vendor_id     FK → olt_vendor
operation     VARCHAR(50)   -- 'activation', 'deactivation', 'modification'
product       VARCHAR(20)   -- 'FTTH', 'SSAA'
technology    VARCHAR(20)   -- 'GPON', 'XGSPON'
step_number   INTEGER       -- orden de ejecución
step_name     VARCHAR(100)  -- 'create_ont', 'configure_service_port'
template_text TEXT          -- el comando con placeholders {param}
rollback_template TEXT      -- comando para deshacer este paso
```

**template_variable** — variables de cada template
```sql
variable_id   SERIAL PK
template_id   FK → command_template
var_name      VARCHAR(50)
var_type      VARCHAR(20)   -- 'string', 'integer', 'enum'
required      BOOLEAN
```

**speed_profile** — perfiles de velocidad por VNO
```sql
profile_id    SERIAL PK
vno_id        FK → vno
name          VARCHAR(50)   -- '100M_20M', '200M_50M'
download_mbps INTEGER
upload_mbps   INTEGER
```

**vlan_assignment** — VLANs por servicio y VNO
**service_type** — tipos de servicio (INTERNET, VOIP, IPTV)
**operation_type** — tipos de operación

---

### Dominio 3: Transacciones (4 tablas)

**transaction** — registro de cada operación
```sql
txn_id         UUID PK
vno_id         FK → vno
operation      VARCHAR(50)
status         VARCHAR(20)  -- PENDING, IN_PROGRESS, COMPLETED, FAILED, ROLLBACK, ROLLBACK_FAILED
olt_id         FK → olt
request_payload JSONB       -- payload original recibido
created_at     TIMESTAMPTZ
completed_at   TIMESTAMPTZ
callback_url   TEXT
```

**transaction_step** — cada paso ejecutado
```sql
step_id        SERIAL PK
txn_id         FK → transaction
step_number    INTEGER
step_name      VARCHAR(100)
status         VARCHAR(20)  -- OK, FAILED, SKIPPED, ROLLED_BACK
command_sent   TEXT         -- comando CLI exacto enviado a la OLT
olt_response   TEXT         -- respuesta exacta de la OLT
duration_ms    INTEGER
executed_at    TIMESTAMPTZ
```

**transaction_error** — detalle de errores
```sql
error_id       SERIAL PK
txn_id         FK → transaction
step_id        FK → transaction_step
error_code     VARCHAR(20)  -- KMD-xxxx
error_message  TEXT
stack_trace    TEXT
```

**transaction_listener** — callbacks pendientes de enviar
```sql
listener_id    SERIAL PK
txn_id         FK → transaction
callback_url   TEXT
attempts       INTEGER DEFAULT 0
last_attempt   TIMESTAMPTZ
next_attempt   TIMESTAMPTZ
status         VARCHAR(20)  -- PENDING, SENT, FAILED
```

---

### Dominio 4: Administración Web (3 tablas)

**app_user** — usuarios del portal web
```sql
user_id        SERIAL PK
email          VARCHAR(200) UNIQUE
password_hash  VARCHAR(200)  -- bcrypt
role_id        FK → app_role
totp_secret    VARCHAR(100)  -- 2FA (puede ser NULL si no activado)
totp_enabled   BOOLEAN DEFAULT false
last_login     TIMESTAMPTZ
```

**app_role** — roles RBAC
```sql
role_id   SERIAL PK
name      VARCHAR(50)  -- 'ADMIN', 'OPERATOR', 'VIEWER', 'AUDITOR'
```

**audit_log** — registro de acciones de usuarios
```sql
log_id       SERIAL PK
user_id      FK → app_user
action       VARCHAR(100)
resource     VARCHAR(200)
ip_address   INET
user_agent   TEXT
result       VARCHAR(20)   -- 'SUCCESS', 'DENIED'
logged_at    TIMESTAMPTZ
```

---

### Dominio 5: VNO / Multi-Tenancy (2 tablas)

**vno** — operadores virtuales
```sql
vno_id         SERIAL PK
code           VARCHAR(20) UNIQUE  -- 'DTV', 'ClaroVTR', 'Entel', 'TCH'
name           VARCHAR(100)
status         VARCHAR(20)  -- 'ACTIVE', 'INACTIVE'
```

**vno_service_config** — configuración específica por VNO
```sql
config_id      SERIAL PK
vno_id         FK → vno
product        VARCHAR(20)
technology     VARCHAR(20)
svlan_base     INTEGER
cvlan_range    VARCHAR(50)
```

---

### Dominio 6: Configuración y Seguridad (4 tablas)

**ssh_credential** — credenciales SSH para OLTs
```sql
credential_id   SERIAL PK
olt_id          FK → olt
username        VARCHAR(100)
password_enc    TEXT         -- cifrado AES-256/Fernet (TO-BE; en AS-IS aún sin cifrar — GAP)
key_path        TEXT         -- ruta a llave SSH si aplica
```

**feature_flag** — interruptores de migración
```sql
flag_id     SERIAL PK
vno_id      FK → vno
product     VARCHAR(20)      -- NULL = todos
technology  VARCHAR(20)      -- NULL = todas
operation   VARCHAR(50)      -- NULL = todas
enabled     BOOLEAN DEFAULT false
updated_by  VARCHAR(100)
```

**system_config** — configuración global
```sql
config_key   VARCHAR(100) PK  -- natural key
config_value TEXT
description  TEXT
```

**retention_policy** — política de retención por dominio
```sql
domain        VARCHAR(50) PK
retention_days INTEGER
```

---

### Dominio 7: Legacy / Schema public (8 tablas)
Tablas existentes de la versión ADC. Se mantienen por compatibilidad.
Prefijo: `kmd_` (kmd_roles, kmd_permisos, kmd_rol_permisos, kmd_usuarios, kmd_olt_ip, etc.)
Se están migrando al schema komands mediante scripts ALTER TABLE + Alembic.

---

## ROLES RBAC

| Rol | Permisos principales |
|-----|----------------------|
| ADMIN | Todo: gestión usuarios, config, ejecución, consulta |
| OPERATOR | Ejecutar operaciones de red, consultar, ver logs |
| VIEWER | Solo lectura: consultar transacciones y estado |
| AUDITOR | Solo audit_log: ver registros de auditoría |

Total: 4 roles, 22 permisos granulares.

## Retención de datos
| Dominio | Retención |
|---------|-----------|
| transaction / transaction_step | 365 días |
| audit_log | 365 días (requerimiento ciberseguridad) |
| transaction_error | 180 días |
| system_config | Permanente |

Limpieza automática: función `fn_cleanup_old_records()` ejecutada por `pg_cron`.
