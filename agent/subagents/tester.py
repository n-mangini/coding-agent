"""Tester: subagente que ejecuta checks acotados y registra resultados.

El Tester valida el artefacto/repo con comandos seguros y predefinidos. Su
`tool_map` expone `execute_command` para respetar el rol de la issue, pero el
callable está envuelto: solo permite comandos de `ALLOWED_TEST_COMMANDS`. Así el
LLM no puede convertir el Tester en un shell general.
"""

from .. import tools as tools_module
from ..harness import Harness
from ..llm import schemas_for
from .base import Subagent

TESTER_TOOLS = ["execute_command"]

DEFAULT_TEST_COMMAND = (
    "python3 -m compileall agent rag analyze.py main.py run_tests.py repo.py"
)
ALLOWED_TEST_COMMANDS = (DEFAULT_TEST_COMMAND,)

TESTER_SYSTEM_MESSAGE = (
    "Sos el subagente TESTER de un sistema de análisis de repositorios. "
    "Tu tarea es ejecutar checks reales y acotados para validar que el código "
    "siga cargando después del análisis. Tu única herramienta es execute_command, "
    "pero solo podés usar exactamente el comando permitido que te pasa el "
    "orquestador. No inventes comandos, no borres archivos, no instales "
    "dependencias y no ejecutes scripts que hagan llamadas LLM. "
    "Ejecutá el check una sola vez. Si falla, no rompas el pipeline: explicá el "
    "fallo con stdout/stderr y una observación breve. Si pasa, reportá que pasó "
    "y resumí la salida relevante."
)


class TesterSubagent(Subagent):
    """Subagente Tester con estado explícito del último check."""

    def __init__(self, harness):
        super().__init__(
            name="tester",
            description="Ejecuta checks acotados y reporta su resultado.",
            harness=harness,
        )
        self.last_check = None

    def run(self, task, state):
        """Ejecuta el check y registra eventos de loop en el estado."""
        state.record_progress(f"Delegando en '{self.name}'.")
        self.last_check = None
        history = self.harness.new_conversation()
        result, _ = self.harness.run_conversation(task, history)
        state.record_result(self.name, result)
        for event in self.harness.loop_events:
            state.record_observation(f"{self.name}: {event}")
        return result


def build_tester(client, policies=None):
    """Construye el Tester con `execute_command` acotado por allowlist."""

    tester = None

    def execute_test_command(command):
        if command not in ALLOWED_TEST_COMMANDS:
            return (
                "Error: el Tester solo puede ejecutar comandos permitidos. "
                f"Permitidos: {', '.join(ALLOWED_TEST_COMMANDS)}"
            )
        output = tools_module.execute_command(command)
        if tester is not None:
            tester.last_check = {"command": command, "output": output}
        return output

    tool_map = {"execute_command": execute_test_command}
    harness = Harness(
        client,
        tool_map,
        schemas_for(TESTER_TOOLS),
        system_message=TESTER_SYSTEM_MESSAGE,
        policies=policies,
    )
    tester = TesterSubagent(harness)
    return tester
