# Proyecto: Sunset BluePlanet / Plataforma Komands

## ¿Qué es este proyecto?
Reemplazar la plataforma **BluePlanet (Ciena)** por una plataforma propia llamada **Komands**.
BluePlanet gestionaba la activación de servicios de fibra óptica en equipos de red (OLTs).
Fallaba constantemente, generando intervenciones manuales y pérdida de ventas.

## Empresa cliente
**ON·NET Fibra** — empresa mayorista de fibra óptica en Chile. Atiende a ~2.000.000 clientes finales a través de 4 operadores virtuales (VNOs).

## Empresa proveedora
**MOS-iT** — construye Komands. 20 sprints, marzo–diciembre 2026.

## VNOs (clientes de ON·NET)
| Código | Nombre comercial | Orden de migración |
|--------|------------------|--------------------|
| DTV    | DirecTV          | Semana 22–23 (piloto) |
| ClaroVTR | ClaroVTR       | Semana 24–25 |
| Entel  | Entel            | Semana 25 |
| TCH    | Movistar         | Semana 26 (última, mayor volumen) |

## Productos soportados
### FTTH (residencial masivo)
- Internet, VoIP, IPTV
- Tecnología: GPON / XGSPON
- Vendors: Nokia + Huawei

### SSAA (empresas B2B)
- 7 grupos comerciales:
  - **A** — Internet Dedicado (100% garantizado)
  - **B** — BW Asegurado 10%
  - **C** — TrunkIP Telefonía (baja latencia)
  - **D** — Internet Business (best effort)
  - **E** — Best Effort nuevo (Nokia v3.0)
  - **BX** — XGSPON Asegurado (30%)
  - **DX** — XGSPON Best Effort
- Los grupos se pueden combinar: A+C, C+D, A+C+D, etc.

## Equipamiento de red (OLTs)
| Vendor | Modelo | Software | Tecnologías |
|--------|--------|----------|-------------|
| Nokia  | ISAM 7360 FX | Rel. 6.2 | GPON / XGSPON |
| Huawei | MA5600T | V800R018 | GPON |
| Huawei | MA5800  | V100R020 | GPON / XGSPON |

Total OLTs activas: ~618. Conexión vía SSH/CLI con librería **Netmiko**.

## Principios de diseño (NO negociables)
1. **Paridad funcional (TDD)** — Komands produce exactamente los mismos resultados que BluePlanet. Tests ANTES del código. Cobertura objetivo > 80%.
2. **Transparencia para VNOs** — Las 4 VNOs no perciben ningún cambio en interfaces ni comportamiento.
3. **Feature Flags** — Control por VNO/tecnología/producto/operación. Rollback < 5 min sin deploy.
4. **Contingencia 0** — Operación directa a la red sin sistemas intermedios.

## Componentes que se ELIMINAN
- BluePlanet BPI (inventario)
- BluePlanet BPO (orquestación)
- BluePlanet RA (ejecución SSH)
- Neo4j (base de datos de grafo)

## Componentes que se MANTIENEN
- ServiceNow SOM (orquestador exclusivo — se modifica para apuntar a Komands)
- BluePlanet UAA (monitoreo alarmas — sin cambios)
- WSO2 APIM (gateway VNOs — sin cambios)
- Axway APIM (nuevo gateway ServiceNow ↔ Komands)
- OSP/CPQD (inventario planta externa — sin cambios)

## Glosario clave
| Término | Significado |
|---------|-------------|
| OLT | Optical Line Terminal — equipo físico de red en central |
| ONT | Optical Network Terminal — equipo en casa del cliente |
| VNO | Virtual Network Operator — cliente de ON·NET |
| FTTH | Fiber To The Home — internet residencial |
| SSAA | Servicios Avanzados — servicios B2B empresas |
| GPON | Tecnología PON hasta 2.5 Gbps |
| XGSPON | Tecnología PON simétrica hasta 10 Gbps |
| SOM | Service Order Management (módulo de ServiceNow) |
| APIM | API Management |
| CLI | Command Line Interface — comandos de terminal a OLT |
| TDD | Test-Driven Development — tests antes que código |
| ADC | Nombre anterior de Komands (Administrador de Comandos) |
| CMDB | Configuration Management Database (en ServiceNow) |
| callback | Notificación que Komands envía a ServiceNow al terminar |
| txn_id | UUID único que identifica cada transacción |
| rollback | Deshacer pasos ejecutados cuando algo falla |
| feature flag | Interruptor para activar/desactivar Komands por VNO |
