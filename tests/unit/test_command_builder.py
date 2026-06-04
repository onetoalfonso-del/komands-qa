"""Unit tests — Command Builder (Catálogo Técnico + Config Engine).

Convención: test_<operacion>_<vendor>_<producto>_<escenario>

Qué estamos probando:
    El Command Builder es el módulo que, dado un vendor/producto/operación
    y los parámetros del request (shelf, card, port, ont_id, services, etc.),
    produce la lista exacta de comandos CLI que el Adapter debe enviar a la OLT.

    No hay red, no hay BD, no hay SSH. Solo lógica pura.

Fuentes:
    - docs/02_arquitectura.md → Catálogo Técnico + Config Engine
    - docs/02_arquitectura.md → Diferencias Nokia vs Huawei
    - tests/mocks/nokia_responses.py → estructura CLI Nokia
    - tests/mocks/huawei_responses.py → estructura CLI Huawei + Riesgo R10
"""
import pytest

from komands.command_builder import (
    CommandBuilder,
    CommandBuilderError,
    parse_service_port_index,
)

# Parámetros base para deactivation/modification (sin services/groups)
NOKIA_DEACT_BASE = {
    "shelf": 1,
    "card": 2,
    "port": 3,
    "logic_pon": 1,
    "ont_id": 45,
}

HUAWEI_DEACT_BASE = {
    "shelf": 0,
    "card": 1,
    "port": 2,
    "logic_pon": 0,
    "ont_id": 10,
}

# ─── Parámetros base reutilizables ────────────────────────────────────────────

NOKIA_BASE = {
    "shelf": 1,
    "card": 2,
    "port": 3,
    "logic_pon": 1,
    "ont_id": 45,
    "ont_serial": "ALCLF1234567",
    "speed_profile": "100M_20M",
    "description": "Internet-DTV",
}

HUAWEI_BASE = {
    "shelf": 0,
    "card": 1,
    "port": 2,
    "logic_pon": 0,
    "ont_id": 10,
    "ont_serial": "485754C12345",
    "speed_profile": "100M_20M",
    "description": "Internet-DTV",
}


# ─── CB-01 a CB-05: Nokia FTTH — QoS por servicio ────────────────────────────

class TestNokiaFTTH:
    """
    Nokia ISAM 7360 FX — activación FTTH.

    Invariante clave: cada servicio tiene un par Queue/Priority fijo.
        INTERNET → Q0 / P4
        VoIP     → Q4 / P5
        IPTV     → Q5 / P6
    Fuente: docs/02_arquitectura.md → tabla Nokia vs Huawei.
    """

    def setup_method(self):
        self.builder = CommandBuilder(vendor="nokia", product="FTTH")

    # CB-01
    def test_nokia_ftth_activation_internet_contiene_interfaz_ont(self):
        """
        ESCENARIO: Activación Nokia FTTH solo INTERNET.

        El primer comando siempre configura la interfaz ONT con la ruta
        shelf/card/port/logic_pon/ont_id. Es el punto de entrada de toda
        activación Nokia — sin este comando los siguientes fallan.

        Resultado esperado: el CLI contiene la interfaz ONT correcta.
        """
        commands = self.builder.build_activation(
            **NOKIA_BASE, services=["INTERNET"]
        )

        ont_iface = "configure equipment ont interface 1/2/3/1/45"
        assert any(ont_iface in cmd for cmd in commands), (
            f"Comando de interfaz ONT no encontrado. Comandos generados:\n"
            + "\n".join(commands)
        )

    # CB-02
    def test_nokia_ftth_activation_internet_qos_q0_p4(self):
        """
        ESCENARIO: Activación Nokia FTTH solo INTERNET.

        Internet usa la cola Q0 con prioridad P4 en Nokia.
        Si se asigna una cola incorrecta, el tráfico del cliente
        no tendrá la prioridad correcta en la red.

        Resultado esperado: los comandos contienen Q0 y P4.
        """
        commands = self.builder.build_activation(
            **NOKIA_BASE, services=["INTERNET"]
        )

        all_cmds = " ".join(commands)
        assert "Q0" in all_cmds, "INTERNET debe usar cola Q0 en Nokia"
        assert "P4" in all_cmds, "INTERNET debe usar prioridad P4 en Nokia"

    # CB-03
    def test_nokia_ftth_activation_voip_qos_q4_p5(self):
        """
        ESCENARIO: Activación Nokia FTTH con servicio VoIP.

        VoIP usa Q4/P5 — mayor prioridad que Internet.
        Es crítico para la calidad de voz (latencia < 150ms).

        Resultado esperado: los comandos contienen Q4 y P5.
        """
        commands = self.builder.build_activation(
            **NOKIA_BASE, services=["INTERNET", "VOIP"]
        )

        all_cmds = " ".join(commands)
        assert "Q4" in all_cmds, "VoIP debe usar cola Q4 en Nokia"
        assert "P5" in all_cmds, "VoIP debe usar prioridad P5 en Nokia"

    # CB-04
    def test_nokia_ftth_activation_iptv_qos_q5_p6(self):
        """
        ESCENARIO: Activación Nokia FTTH con INTERNET + VoIP + IPTV.

        IPTV usa Q5/P6 — la más alta prioridad.
        Sin esto el streaming de video sufre buffering.

        Resultado esperado: los comandos contienen Q5 y P6.
        """
        commands = self.builder.build_activation(
            **NOKIA_BASE, services=["INTERNET", "VOIP", "IPTV"]
        )

        all_cmds = " ".join(commands)
        assert "Q5" in all_cmds, "IPTV debe usar cola Q5 en Nokia"
        assert "P6" in all_cmds, "IPTV debe usar prioridad P6 en Nokia"

    # CB-05
    def test_nokia_ftth_activation_tres_servicios_genera_tres_bloques_qos(self):
        """
        ESCENARIO: Activación con INTERNET + VoIP + IPTV.

        Cada servicio requiere su propio bloque de configuración QoS.
        Si solo se genera un bloque, dos servicios quedarán sin configurar.

        Resultado esperado: al menos 3 comandos de QoS (uno por servicio).
        """
        commands = self.builder.build_activation(
            **NOKIA_BASE, services=["INTERNET", "VOIP", "IPTV"]
        )

        qos_cmds = [c for c in commands if any(q in c for q in ["Q0", "Q4", "Q5"])]
        assert len(qos_cmds) >= 3, (
            f"Se esperaban al menos 3 comandos QoS, se generaron {len(qos_cmds)}"
        )


# ─── CB-06 a CB-09: Huawei FTTH — Gemports fijos ────────────────────────────

class TestHuaweiFTTH:
    """
    Huawei MA5800/MA5600T — activación FTTH.

    Invariante clave: los gemports son FIJOS (no parametrizables).
        INTERNET → gemport 2
        VoIP     → gemport 6
        IPTV     → gemport 7
    Fuente: docs/02_arquitectura.md + tests/mocks/huawei_responses.py.
    """

    def setup_method(self):
        self.builder = CommandBuilder(vendor="huawei", product="FTTH")

    # CB-06
    def test_huawei_ftth_activation_contiene_comando_ont_add(self):
        """
        ESCENARIO: Activación Huawei FTTH.

        El comando principal de Huawei para agregar ONT es 'ont add',
        a diferencia de Nokia que usa 'configure equipment ont interface'.
        Si se mezclan los templates, la OLT rechaza el comando.

        Resultado esperado: los comandos contienen 'ont add'.
        """
        commands = self.builder.build_activation(
            **HUAWEI_BASE, services=["INTERNET"]
        )

        assert any("ont add" in cmd for cmd in commands), (
            "Huawei debe usar 'ont add' — no el template de Nokia"
        )

    # CB-07
    def test_huawei_ftth_activation_internet_usa_gemport_2(self):
        """
        ESCENARIO: Activación Huawei FTTH con INTERNET.

        El gemport para Internet en Huawei es siempre 2.
        Es un valor fijo del hardware — no viene del payload del request.

        Resultado esperado: los comandos contienen 'gemport 2'.
        """
        commands = self.builder.build_activation(
            **HUAWEI_BASE, services=["INTERNET"]
        )

        assert any("gemport 2" in cmd for cmd in commands), (
            "INTERNET en Huawei debe usar gemport 2"
        )

    # CB-08
    def test_huawei_ftth_activation_voip_usa_gemport_6(self):
        """
        ESCENARIO: Activación Huawei FTTH con VoIP.

        El gemport para VoIP en Huawei es siempre 6.

        Resultado esperado: los comandos contienen 'gemport 6'.
        """
        commands = self.builder.build_activation(
            **HUAWEI_BASE, services=["INTERNET", "VOIP"]
        )

        assert any("gemport 6" in cmd for cmd in commands), (
            "VoIP en Huawei debe usar gemport 6"
        )

    # CB-09
    def test_huawei_ftth_activation_iptv_usa_gemport_7(self):
        """
        ESCENARIO: Activación Huawei FTTH con IPTV.

        El gemport para IPTV en Huawei es siempre 7.

        Resultado esperado: los comandos contienen 'gemport 7'.
        """
        commands = self.builder.build_activation(
            **HUAWEI_BASE, services=["INTERNET", "VOIP", "IPTV"]
        )

        assert any("gemport 7" in cmd for cmd in commands), (
            "IPTV en Huawei debe usar gemport 7"
        )


# ─── CB-10: Riesgo R10 — Parseo de service-port INDEX dinámico ───────────────

class TestHuaweiServicePortIndex:
    """
    Riesgo R10 — El INDEX del service-port en Huawei es asignado
    dinámicamente por el equipo. Hay que leerlo de la respuesta SSH
    para usarlo en pasos posteriores (modificación, baja).

    Si no se parsea correctamente, los pasos siguientes fallan porque
    referencian un INDEX incorrecto.

    Fuente: docs/02_arquitectura.md + tests/mocks/huawei_responses.py.
    """

    # CB-10
    def test_parse_service_port_index_extrae_numero_correcto(self):
        """
        ESCENARIO: La OLT Huawei responde con el INDEX asignado al service-port.

        La respuesta contiene la línea:
            "Service Virtual Port(index) : 1025"

        El parser debe extraer el número 1025.

        Resultado esperado: parse_service_port_index() retorna 1025.
        """
        respuesta_olt = (
            "{ <cr>||<K> }:\n"
            "Command:\n"
            "        service-port vlan 100 gpon 0/1/2 ont 10 gemport 2\n"
            " Failure: The operation failed.\n"
            "Reconfig port:\n"
            "NOTICE: This operation will take a few minutes, please wait...\n"
            "Service Virtual Port(index) : 1025\n"
        )

        index = parse_service_port_index(respuesta_olt)

        assert index == 1025, (
            f"Se esperaba INDEX=1025, se obtuvo {index}"
        )

    # CB-11
    def test_parse_service_port_index_sin_index_lanza_error(self):
        """
        ESCENARIO: La respuesta de la OLT no contiene la línea del INDEX.

        Puede ocurrir si el comando falló antes de asignar el port.
        En este caso el parser debe lanzar un error — no retornar None
        o un valor falso, porque eso causaría errores silenciosos.

        Resultado esperado: CommandBuilderError.
        """
        respuesta_sin_index = "Failure: The VLAN has been used.\n"

        with pytest.raises(CommandBuilderError, match="service-port index"):
            parse_service_port_index(respuesta_sin_index)


# ─── CB-12 a CB-13: Validación de parámetros obligatorios ───────────────────

class TestValidacionParametros:
    """
    El Command Builder debe rechazar requests con parámetros faltantes
    antes de intentar generar comandos. Mejor fallar rápido con un error
    claro que enviar un comando incompleto a la OLT.
    """

    # CB-12
    def test_nokia_activation_sin_ont_serial_lanza_error(self):
        """
        ESCENARIO: Se intenta activar sin ont_serial.

        El ont_serial identifica el ONT físico — sin él Nokia no puede
        verificar que el equipo conectado es el correcto.

        Resultado esperado: CommandBuilderError con mención de 'ont_serial'.
        """
        builder = CommandBuilder(vendor="nokia", product="FTTH")
        params = {k: v for k, v in NOKIA_BASE.items() if k != "ont_serial"}

        with pytest.raises(CommandBuilderError, match="ont_serial"):
            builder.build_activation(**params, services=["INTERNET"])

    # CB-13
    def test_nokia_activation_sin_services_lanza_error(self):
        """
        ESCENARIO: Se intenta activar sin especificar ningún servicio.

        Sin servicios no hay nada que configurar — es un request inválido.

        Resultado esperado: CommandBuilderError con mención de 'services'.
        """
        builder = CommandBuilder(vendor="nokia", product="FTTH")

        with pytest.raises(CommandBuilderError, match="services"):
            builder.build_activation(**NOKIA_BASE, services=[])


# ─── CB-14: Templates Nokia y Huawei NO son intercambiables ─────────────────

class TestTemplatesNoIntercambiables:
    """
    Un comando Nokia enviado a una OLT Huawei (o viceversa) es rechazado
    por el equipo con error de sintaxis. El Command Builder debe garantizar
    que nunca mezcle templates de vendors distintos.
    """

    # CB-14
    def test_nokia_y_huawei_generan_comandos_distintos(self):
        """
        ESCENARIO: Mismos parámetros, vendors distintos.

        Los comandos Nokia y Huawei no deben tener ningún comando en común
        (salvo quizás comentarios o metadatos, que no aplica aquí).

        Resultado esperado: los conjuntos de comandos son distintos.
        """
        params = {
            "shelf": 1, "card": 2, "port": 3, "logic_pon": 1, "ont_id": 45,
            "ont_serial": "TEST1234567", "speed_profile": "100M_20M",
            "description": "Test",
        }

        nokia_cmds = CommandBuilder(vendor="nokia", product="FTTH").build_activation(
            **params, services=["INTERNET"]
        )
        huawei_cmds = CommandBuilder(vendor="huawei", product="FTTH").build_activation(
            **params, services=["INTERNET"]
        )

        assert set(nokia_cmds) != set(huawei_cmds), (
            "Nokia y Huawei no pueden generar los mismos comandos — "
            "los templates son distintos por diseño"
        )


# ─── Parámetros base SSAA ─────────────────────────────────────────────────────

NOKIA_SSAA_BASE = {
    "shelf": 1,
    "card": 1,
    "port": 0,
    "logic_pon": 1,
    "ont_id": 5,
    "ont_serial": "ALCLF9999999",
    "speed_profile": "200M_200M",
    "description": "SSAA-Entel",
    "svlan": 100,
    "cvlan_dato": 200,
    "cvlan_internet": 201,
    "cvlan_gestion": 202,
}

HUAWEI_SSAA_BASE = {
    "shelf": 1,
    "card": 1,
    "port": 2,
    "logic_pon": 1,
    "ont_id": 12,
    "ont_serial": "485754C12345",
    "speed_profile": "200M_200M",
    "description": "SSAA-ClaroVTR",
    "svlan": 100,
    "cvlan_dato": 200,
    "cvlan_internet": 201,
    "cvlan_gestion": 202,
}


# ─── CB-15 a CB-20: Nokia SSAA ────────────────────────────────────────────────

class TestNokiaSSAA:
    """
    Nokia ISAM 7360 FX — activación SSAA (producto empresarial B2B).

    Diferencias clave respecto a FTTH:
      - Usa 'line-profile' para velocidad (no QoS Q0/Q4/Q5)
      - Usa VLANs (svlan/cvlan) en vez de servicios (INTERNET/VOIP/IPTV)
      - Cada grupo genera su propio bridge-port

    Grupos soportados: A, B, C, D, E, BX, DX
    Fuente: LLD v2.2 → Nokia SSAA v3.0.
    """

    def setup_method(self):
        self.builder = CommandBuilder(vendor="nokia", product="SSAA")

    # CB-15
    def test_nokia_ssaa_contiene_line_profile(self):
        """
        ESCENARIO: Activación Nokia SSAA grupo A.

        SSAA usa line-profile para configurar velocidad, a diferencia de
        FTTH que usa QoS por servicio (Q0/P4, Q4/P5, Q5/P6).
        Si se usa el template FTTH, el equipo queda con QoS incorrecto.

        Resultado esperado: los comandos contienen 'line-profile'.
        """
        cmds = self.builder.build_activation(**NOKIA_SSAA_BASE, groups=["A"])

        assert any("line-profile" in c for c in cmds), (
            "Nokia SSAA debe usar line-profile — no QoS de FTTH"
        )

    # CB-16
    def test_nokia_ssaa_no_usa_qos_ftth(self):
        """
        ESCENARIO: Activación Nokia SSAA — verificar que NO usa QoS FTTH.

        Los tokens Q0/Q4/Q5 del template FTTH no deben aparecer en SSAA.
        Si aparecen, el sistema está mezclando templates.

        Resultado esperado: ningún comando contiene Q0, Q4 ni Q5.
        """
        cmds = self.builder.build_activation(**NOKIA_SSAA_BASE, groups=["A"])
        all_cmds = " ".join(cmds)

        for token in ["Q0", "Q4", "Q5"]:
            assert token not in all_cmds, (
                f"SSAA no debe contener '{token}' — ese token es de FTTH"
            )

    # CB-17
    def test_nokia_ssaa_grupo_a_usa_cvlan_dato(self):
        """
        ESCENARIO: Activación Nokia SSAA grupo A.

        El grupo A corresponde al servicio de datos — usa cvlan_dato (200).
        Si se asigna un CVLAN incorrecto, el tráfico va por la VLAN equivocada.

        Resultado esperado: los comandos contienen el valor de cvlan_dato.
        """
        cmds = self.builder.build_activation(**NOKIA_SSAA_BASE, groups=["A"])
        all_cmds = " ".join(cmds)

        assert "200" in all_cmds, (
            "Grupo A debe usar cvlan_dato=200"
        )

    # CB-18
    def test_nokia_ssaa_grupo_c_usa_cvlan_gestion(self):
        """
        ESCENARIO: Activación Nokia SSAA grupo C.

        El grupo C corresponde a gestión — usa cvlan_gestion (202).

        Resultado esperado: los comandos contienen el valor de cvlan_gestion.
        """
        cmds = self.builder.build_activation(**NOKIA_SSAA_BASE, groups=["C"])
        all_cmds = " ".join(cmds)

        assert "202" in all_cmds, (
            "Grupo C debe usar cvlan_gestion=202"
        )

    # CB-19
    def test_nokia_ssaa_dos_grupos_genera_dos_bridge_ports(self):
        """
        ESCENARIO: Activación Nokia SSAA con grupos A y C.

        Cada grupo requiere su propio bridge-port en Nokia.
        Si se genera uno solo, el segundo servicio queda sin configurar.

        Resultado esperado: al menos 2 comandos de bridge-port.
        """
        cmds = self.builder.build_activation(**NOKIA_SSAA_BASE, groups=["A", "C"])

        bridge_ports = [c for c in cmds if "bridge-port" in c]
        assert len(bridge_ports) >= 2, (
            f"Grupos A+C deben generar al menos 2 bridge-ports, "
            f"se generaron {len(bridge_ports)}"
        )

    # CB-20
    def test_nokia_ssaa_grupo_bx_genera_comandos_validos(self):
        """
        ESCENARIO: Activación Nokia SSAA grupo BX (tecnología XGSPON).

        BX es el grupo para clientes XGSPON de alta velocidad.
        Debe generar comandos válidos como cualquier otro grupo.

        Resultado esperado: HTTP 202, al menos un bridge-port.
        """
        cmds = self.builder.build_activation(**NOKIA_SSAA_BASE, groups=["BX"])

        assert any("bridge-port" in c for c in cmds), (
            "Grupo BX debe generar al menos un bridge-port"
        )

    # CB-21
    def test_nokia_ssaa_sin_groups_lanza_error(self):
        """
        ESCENARIO: Se intenta activar SSAA sin especificar grupos.

        Sin grupos no hay servicios que configurar — es un request inválido.

        Resultado esperado: CommandBuilderError con mención de 'groups'.
        """
        with pytest.raises(CommandBuilderError, match="groups"):
            self.builder.build_activation(**NOKIA_SSAA_BASE, groups=[])


# ─── CB-22 a CB-25: Huawei SSAA ──────────────────────────────────────────────

class TestHuaweiSSAA:
    """
    Huawei MA5800/MA5600T — activación SSAA.

    Diferencias clave respecto a FTTH:
      - Usa svlan/cvlan del payload (no VLAN hardcodeada 100)
      - gemport 1 para SSAA (vs gemport 2/6/7 fijos para FTTH)
      - Cada grupo genera su propio service-port con las VLANs correctas
    """

    def setup_method(self):
        self.builder = CommandBuilder(vendor="huawei", product="SSAA")

    # CB-22
    def test_huawei_ssaa_contiene_ont_add(self):
        """
        ESCENARIO: Activación Huawei SSAA grupo A.

        El primer paso siempre es registrar el ONT con 'ont add',
        igual que en FTTH. La diferencia está en el service-port.

        Resultado esperado: los comandos contienen 'ont add'.
        """
        cmds = self.builder.build_activation(**HUAWEI_SSAA_BASE, groups=["A"])

        assert any("ont add" in c for c in cmds), (
            "Huawei SSAA debe comenzar con 'ont add'"
        )

    # CB-23
    def test_huawei_ssaa_usa_svlan_en_service_port(self):
        """
        ESCENARIO: Activación Huawei SSAA grupo A con svlan=100.

        A diferencia de FTTH que usa vlan 100 hardcodeada, SSAA debe
        usar el svlan del payload (puede ser cualquier valor).

        Resultado esperado: los comandos contienen 'vlan 100' (svlan).
        """
        cmds = self.builder.build_activation(**HUAWEI_SSAA_BASE, groups=["A"])

        assert any("vlan 100" in c for c in cmds), (
            "Huawei SSAA debe usar el svlan=100 del payload"
        )

    # CB-24
    def test_huawei_ssaa_dos_grupos_genera_dos_service_ports(self):
        """
        ESCENARIO: Activación Huawei SSAA con grupos A y C.

        Cada grupo necesita su propio service-port.

        Resultado esperado: al menos 2 comandos service-port.
        """
        cmds = self.builder.build_activation(**HUAWEI_SSAA_BASE, groups=["A", "C"])

        sp_cmds = [c for c in cmds if "service-port" in c]
        assert len(sp_cmds) >= 2, (
            f"Grupos A+C deben generar al menos 2 service-ports, "
            f"se generaron {len(sp_cmds)}"
        )

    # CB-25 (note: name kept for historical reference)
    def test_nokia_ssaa_y_ftth_generan_comandos_distintos(self):
        """
        ESCENARIO: Mismo vendor Nokia, mismo ONT, pero producto distinto.

        SSAA y FTTH usan templates completamente distintos.
        Si se confunden, un cliente empresarial (SSAA) recibiría la
        configuración de un cliente residencial (FTTH) y viceversa.

        Resultado esperado: los conjuntos de comandos son distintos.
        """
        params = {
            "shelf": 1, "card": 1, "port": 0, "logic_pon": 1, "ont_id": 5,
            "ont_serial": "ALCLF9999999", "speed_profile": "200M_200M",
            "description": "Test",
            "svlan": 100, "cvlan_dato": 200, "cvlan_internet": 201,
            "cvlan_gestion": 202,
        }

        ftth_cmds = CommandBuilder(vendor="nokia", product="FTTH").build_activation(
            **params, services=["INTERNET"]
        )
        ssaa_cmds = CommandBuilder(vendor="nokia", product="SSAA").build_activation(
            **params, groups=["A"]
        )

        assert set(ftth_cmds) != set(ssaa_cmds), (
            "Nokia SSAA y FTTH no pueden generar los mismos comandos"
        )


# ─── CB-26 a CB-31: Baja Nokia y Huawei FTTH ─────────────────────────────────

@pytest.mark.postventa
class TestNokiaFTTHDeactivation:
    """
    Nokia ISAM 7360 FX — baja FTTH (POST /unsuscription).

    Secuencia correcta:
        1. configure equipment ont interface {iface} → admin-state down
        2. no equipment ont interface {iface}          → eliminar ONT
        3. (solo TCH) no vlan {svlan}                  → delete_vlan_on_terminate

    Fuente: LLD REF-09 + Plan v3 PV-BAJ → "delete_vlan_on_terminate exclusivo TCH".
    """

    def setup_method(self):
        self.builder = CommandBuilder(vendor="nokia", product="FTTH")

    # CB-26
    def test_nokia_baja_contiene_no_equipment_ont_interface(self):
        """
        ESCENARIO: Baja Nokia FTTH — el comando de eliminación es obligatorio.

        'no equipment ont interface' elimina el ONT de la configuración.
        Sin él el ONT queda registrado aunque el cliente ya no esté.

        Resultado esperado: los comandos contienen 'no equipment ont interface'.
        """
        cmds = self.builder.build_deactivation(**NOKIA_DEACT_BASE)

        assert any("no equipment ont interface" in c for c in cmds), (
            "Nokia baja debe usar 'no equipment ont interface'"
        )

    # CB-27
    def test_nokia_baja_contiene_admin_state_down(self):
        """
        ESCENARIO: Baja Nokia FTTH — el ONT debe bajar primero de admin-state.

        Antes de eliminar el ONT se debe poner en admin-state down.
        Si se salta este paso la OLT puede rechazar el 'no equipment' con error.

        Resultado esperado: los comandos contienen 'admin-state down'.
        """
        cmds = self.builder.build_deactivation(**NOKIA_DEACT_BASE)

        assert any("admin-state down" in c for c in cmds), (
            "Nokia baja debe bajar admin-state antes de eliminar el ONT"
        )

    # CB-28
    def test_nokia_baja_tch_agrega_no_vlan(self):
        """
        ESCENARIO: Baja Nokia TCH con delete_vlan_on_terminate=True.

        Movistar (TCH) tiene una regla de negocio especial: al dar de baja
        también hay que eliminar la VLAN del cliente en la OLT.
        Los otros 3 VNOs no tienen este paso.

        Resultado esperado: los comandos contienen 'no vlan 300'.
        """
        cmds = self.builder.build_deactivation(
            **NOKIA_DEACT_BASE,
            delete_vlan_on_terminate=True,
            svlan=300,
        )

        assert any("no vlan 300" in c for c in cmds), (
            "TCH con delete_vlan_on_terminate=True debe agregar 'no vlan {svlan}'"
        )

    # CB-29
    def test_nokia_baja_sin_delete_vlan_no_agrega_no_vlan(self):
        """
        ESCENARIO: Baja Nokia DTV (sin delete_vlan_on_terminate).

        Para los VNOs DTV, ClaroVTR y Entel NO se elimina la VLAN.
        El comando 'no vlan' solo aparece cuando el flag está activo.

        Resultado esperado: los comandos NO contienen 'no vlan'.
        """
        cmds = self.builder.build_deactivation(**NOKIA_DEACT_BASE)
        all_cmds = " ".join(cmds)

        assert "no vlan" not in all_cmds, (
            "Sin delete_vlan_on_terminate no debe aparecer 'no vlan'"
        )


@pytest.mark.postventa
class TestHuaweiFTTHDeactivation:
    """
    Huawei MA5800/MA5600T — baja FTTH.

    Secuencia correcta (Riesgo R10):
        1. interface gpon {shelf}/{card}
        2. undo service-port {service_port_index}  ← INDEX dinámico
        3. ont delete {port} {ont_id}
        4. quit

    El service_port_index debe venir del paso previo de parseo SSH.
    """

    def setup_method(self):
        self.builder = CommandBuilder(vendor="huawei", product="FTTH")

    # CB-30
    def test_huawei_baja_contiene_undo_service_port_con_index(self):
        """
        ESCENARIO: Baja Huawei FTTH con service_port_index=1025.

        El INDEX es el que devuelve parse_service_port_index() sobre la
        respuesta SSH anterior. Usar un INDEX equivocado borra el servicio
        de otro cliente.

        Resultado esperado: los comandos contienen 'undo service-port 1025'.
        """
        cmds = self.builder.build_deactivation(
            **HUAWEI_DEACT_BASE,
            service_port_index=1025,
        )

        assert any("undo service-port 1025" in c for c in cmds), (
            "Huawei baja debe usar 'undo service-port {index}' con el INDEX correcto"
        )

    # CB-31
    def test_huawei_baja_contiene_ont_delete(self):
        """
        ESCENARIO: Baja Huawei FTTH — eliminación del ONT.

        Después de borrar el service-port se elimina el ONT con 'ont delete'.

        Resultado esperado: los comandos contienen 'ont delete'.
        """
        cmds = self.builder.build_deactivation(
            **HUAWEI_DEACT_BASE,
            service_port_index=1025,
        )

        assert any("ont delete" in c for c in cmds), (
            "Huawei baja debe terminar con 'ont delete {port} {ont_id}'"
        )

    # CB-32
    def test_huawei_baja_sin_service_port_index_lanza_error(self):
        """
        ESCENARIO: Se intenta dar de baja en Huawei sin el INDEX del service-port.

        Esto significa que el paso de parseo SSH (R10) no se ejecutó o falló.
        El Command Builder debe rechazarlo — no asumir un INDEX por defecto.

        Resultado esperado: CommandBuilderError con mención de 'service_port_index'.
        """
        with pytest.raises(CommandBuilderError, match="service_port_index"):
            self.builder.build_deactivation(**HUAWEI_DEACT_BASE)


# ─── CB-33 a CB-36: Modificación Nokia y Huawei FTTH ─────────────────────────

@pytest.mark.postventa
class TestNokiaFTTHModification:
    """
    Nokia ISAM 7360 FX — modificación FTTH.

    Operaciones soportadas:
      SPEED_CHANGE → configure qos ont interface {iface} line-profile {new_profile}
      BLOCK        → admin-state down
      UNBLOCK      → admin-state up
    """

    def setup_method(self):
        self.builder = CommandBuilder(vendor="nokia", product="FTTH")

    # CB-33
    def test_nokia_mod_speed_change_contiene_line_profile_nuevo(self):
        """
        ESCENARIO: Cambio de velocidad Nokia FTTH → nuevo perfil 200M_50M.

        La modificación de velocidad en Nokia usa 'line-profile' con el
        nombre del nuevo perfil. Si se usa el perfil anterior, no cambia nada.

        Resultado esperado: los comandos contienen 'line-profile 200M_50M'.
        """
        cmds = self.builder.build_modification(
            **NOKIA_DEACT_BASE,
            operation_type="SPEED_CHANGE",
            new_speed_profile="200M_50M",
        )

        assert any("line-profile 200M_50M" in c for c in cmds), (
            "SPEED_CHANGE Nokia debe aplicar el nuevo perfil de velocidad"
        )

    # CB-34
    def test_nokia_mod_block_contiene_admin_state_down(self):
        """
        ESCENARIO: Bloqueo de servicio Nokia FTTH.

        BLOCK pone el ONT en admin-state down — corta el servicio sin borrar
        la configuración. Permite un UNBLOCK posterior sin reconfigurar.

        Resultado esperado: los comandos contienen 'admin-state down'.
        """
        cmds = self.builder.build_modification(
            **NOKIA_DEACT_BASE,
            operation_type="BLOCK",
        )

        assert any("admin-state down" in c for c in cmds), (
            "BLOCK Nokia debe poner admin-state down"
        )

    # CB-35
    def test_nokia_mod_unblock_contiene_admin_state_up(self):
        """
        ESCENARIO: Desbloqueo de servicio Nokia FTTH.

        UNBLOCK reactiva el ONT con admin-state up — es el reverso de BLOCK.

        Resultado esperado: los comandos contienen 'admin-state up'.
        """
        cmds = self.builder.build_modification(
            **NOKIA_DEACT_BASE,
            operation_type="UNBLOCK",
        )

        assert any("admin-state up" in c for c in cmds), (
            "UNBLOCK Nokia debe poner admin-state up"
        )


@pytest.mark.postventa
class TestHuaweiFTTHModification:
    """
    Huawei MA5800/MA5600T — modificación FTTH.

    Operaciones soportadas:
      SPEED_CHANGE → ont modify {port} {ont_id} traffic-profile {new_profile}
      BLOCK        → ont deactivate {port} {ont_id}
      UNBLOCK      → ont activate {port} {ont_id}
    """

    def setup_method(self):
        self.builder = CommandBuilder(vendor="huawei", product="FTTH")

    # CB-36
    def test_huawei_mod_speed_change_contiene_traffic_profile(self):
        """
        ESCENARIO: Cambio de velocidad Huawei FTTH → nuevo perfil 200M_50M.

        Huawei usa 'traffic-profile' en el comando 'ont modify'.
        A diferencia de Nokia que usa 'line-profile'.

        Resultado esperado: los comandos contienen 'traffic-profile 200M_50M'.
        """
        cmds = self.builder.build_modification(
            **HUAWEI_DEACT_BASE,
            operation_type="SPEED_CHANGE",
            new_speed_profile="200M_50M",
        )

        assert any("traffic-profile 200M_50M" in c for c in cmds), (
            "SPEED_CHANGE Huawei debe usar 'traffic-profile' con el nuevo perfil"
        )

    # CB-37
    def test_nokia_y_huawei_mod_speed_change_generan_comandos_distintos(self):
        """
        ESCENARIO: SPEED_CHANGE con mismos parámetros pero vendors distintos.

        Nokia usa 'configure qos ... line-profile'; Huawei usa 'ont modify ...
        traffic-profile'. Confirma que los templates no se mezclan.

        Resultado esperado: los conjuntos de comandos son distintos.
        """
        params = {**NOKIA_DEACT_BASE, "operation_type": "SPEED_CHANGE", "new_speed_profile": "200M_50M"}

        nokia_cmds = CommandBuilder(vendor="nokia", product="FTTH").build_modification(**params)
        huawei_cmds = CommandBuilder(vendor="huawei", product="FTTH").build_modification(
            **{**HUAWEI_DEACT_BASE, "operation_type": "SPEED_CHANGE", "new_speed_profile": "200M_50M"}
        )

        assert set(nokia_cmds) != set(huawei_cmds), (
            "Nokia y Huawei SPEED_CHANGE no pueden generar los mismos comandos"
        )
