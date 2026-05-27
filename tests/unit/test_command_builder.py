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
