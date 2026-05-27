# Arquitectura — Plataforma Komands

## Stack tecnológico
- **Lenguaje:** Python 3.13+
- **Framework:** FastAPI + Uvicorn (ASGI, asíncrono)
- **Base de datos:** PostgreSQL 15+
- **Driver BD:** asyncpg (asíncrono)
- **SSH a OLTs:** Netmiko
- **Cola de trabajos:** Redis (Sentinel HA en producción)
- **Autenticación:** JWT (RS256 en TO-BE) + OAuth 2.0 vía Axway
- **Deploy:** Kubernetes en datacenter IFX
- **Migraciones BD:** Alembic

## Flujo completo de una operación (ejemplo: activación)

```
VNO → WSO2 APIM → ServiceNow SOM → Axway APIM → [Komands] → OLT Nokia/Huawei
                                                      ↑
                                              callback al terminar
```

### Paso a paso dentro de Komands:
1. **Axway** valida token OAuth2/JWT y reenvía a API Gateway
2. **API Gateway** valida payload, genera `txn_id` (UUID v4), encola en Redis
3. Responde HTTP 202 + `txn_id` a ServiceNow (inmediato, sin esperar la red)
4. **Orchestrator** toma el trabajo de Redis, consulta el **Catálogo Técnico**
5. **Catálogo** devuelve los templates CLI para esa operación/vendor/producto
6. **Config Engine** resuelve parámetros: VLANs, velocidades, configuración VNO
7. **Nokia Adapter** o **Huawei Adapter** ejecuta los comandos via SSH (Netmiko)
8. Cada paso se registra en PostgreSQL (`transaction_step`)
9. Al completar, **Orchestrator** envía callback a ServiceNow vía Axway
10. **Service Listener** gestiona eventos entrantes (cancelaciones, etc.)

## Los 7 microservicios

### 1. API Gateway
- Punto de entrada REST de todo Komands
- Valida JWT, extrae claims (vno_id, scope)
- Genera UUID (`txn_id`) por cada request
- Encola en Redis para procesamiento asíncrono
- Responde 202 inmediato en operaciones async, 200 directo en consultas sync
- Puerto: configurable por ambiente

### 2. Orchestrator
- Motor de ejecución de transacciones
- Ejecuta pasos en orden secuencial
- Si un paso falla → ejecuta rollback de los pasos anteriores en orden inverso
- Persiste estado en PostgreSQL (tabla `transaction` y `transaction_step`)
- Llama al Catálogo para obtener los comandos
- Envía callback a ServiceNow al completar (COMPLETED, FAILED, ROLLBACK)

### 3. Catálogo Técnico
- Almacena templates CLI parametrizados por vendor/producto/operación
- Tablas: `command_template`, `template_variable`
- Ejemplo template Nokia activación FTTH:
  ```
  configure equipment ont interface {shelf}/{card}/{port}/{logic_pon}/{ont_id}
  desc {description}
  sw-ver-pland {sw_version}
  ...
  ```
- Templates son distintos para Nokia vs Huawei (no son intercambiables)

### 4. Config Engine
- Resuelve configuración dinámica por VNO y operación
- Tablas: `vno_service_config`, `speed_profile`, `vlan_assignment`, `feature_flag`
- Gestiona los Feature Flags de migración por VNO
- Provee VLANs correctas (SVLAN, CVLAN) según el grupo SSAA

### 5. Nokia Adapter
- Conectividad SSH a OLTs Nokia ISAM 7360 FX (Rel. 6.2)
- Usa Netmiko con `device_type = "nokia_sros"`
- Comandos CLI propios de Nokia (distintos a Huawei)
- Maneja validaciones pre-ejecución específicas de Nokia
- Parsea respuestas Nokia para detectar éxito/error

### 6. Huawei Adapter
- Conectividad SSH a OLTs Huawei MA5800 / MA5600T
- Usa Netmiko con `device_type = "huawei_vrp"`
- Riesgo conocido: **service-port INDEX dinámico** (R10) — el índice del service-port lo asigna el equipo dinámicamente, hay que leerlo después de crearlo
- Parsea respuestas Huawei (formato distinto a Nokia)

### 7. Service Listener
- Escucha eventos entrantes del ecosistema
- Gestiona cancelaciones de órdenes en vuelo
- Recibe notificaciones de ServiceNow

## Patrones de comunicación

### Asíncrono (operaciones de red)
```
Request → 202 Accepted + txn_id
...procesamiento en background...
→ callback POST a ServiceNow con resultado
```
Endpoints: /activation, /deactivation, /device-modification, /fiber-modification, /modification

### Síncrono (consultas)
```
Request → procesamiento directo → 200 OK + resultado
```
Endpoints: GET /access/{id}, POST /query/pon-info, GET /port-occupancy, GET /transaction/{uuid}

## Rollback automático
- Si el paso N falla, el Orchestrator deshace los pasos 1..N-1 en orden inverso
- Cada paso tiene su comando de rollback definido en el Catálogo
- Estado final en callback: `ROLLBACK` (rollback exitoso) o `ROLLBACK_FAILED`
- Si rollback falla, se genera alerta y requiere intervención manual

## Idempotencia
- Mismo `txn_id` enviado dos veces → segunda vez devuelve el mismo resultado sin re-ejecutar
- Controlado en API Gateway consultando tabla `transaction` en PostgreSQL

## Diferencias clave Nokia vs Huawei

| Aspecto | Nokia ISAM 7360 | Huawei MA5800/MA5600T |
|---------|-----------------|----------------------|
| Sintaxis CLI | Propia Nokia SROS | Propia Huawei VRP |
| Service ports | Bridge-port + Queue | Service-port + Gemport |
| Gemports fijos FTTH | No aplica | Internet=2, VoIP=6, IPTV=7 |
| INDEX service-port | Estático | **Dinámico** (riesgo R10) |
| SSAA | Line-profile (Nokia v3.0) | Service-ports múltiples |
| Prioridad QoS Nokia | Q0/P4 Internet, Q4/P5 VoIP, Q5/P6 IPTV | N/A |

## Infraestructura
- Datacenter: IFX (privado, Chile)
- Deploy: Kubernetes
- BD: PostgreSQL 15+ con Patroni (HA activo-activo)
- Redis: Sentinel HA
- SLA: 99.9% uptime interno / 99.95% hacia VNOs
- Latencia APIs: P95 < 500ms
- Throughput: 20.000 transacciones/hora
- RPO < 1 hora, RTO < 4 horas

## Ambientes
- DEV — desarrollo local
- QA — pruebas integración
- PROD — producción (administrado por ON·NET)
