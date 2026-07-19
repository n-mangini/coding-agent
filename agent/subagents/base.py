"""Subagente: un `Harness` especializado que el orquestador invoca como una tool.

La idea central del diseño (sin frameworks de orquestación) es que cada subagente
es el mismo motor `Harness` con su propio system prompt y su `tool_map` acotado.
El orquestador los usa como si fueran tools: les pasa una tarea y el `TaskState`
compartido, y recibe de vuelta el resultado.
"""

from dataclasses import dataclass

from ..harness import Harness


@dataclass
class Subagent:
    """Envoltorio fino sobre un `Harness` con identidad y permisos propios.

    Attributes:
        name: identificador corto (clave en `TaskState.subagent_results`).
        description: para qué sirve; el orquestador la usa para decidir a quién
            delegar (hoy trivial, con un solo subagente).
        harness: el motor especializado (prompt + tool_map acotado).
    """

    name: str
    description: str
    harness: Harness

    def run(self, task, state):
        """Ejecuta una tarea en una conversación nueva y registra el resultado.

        Args:
            task (str): instrucción concreta para este subagente.
            state (TaskState): estado compartido donde deja su resultado.

        Returns:
            str: el texto final producido por el subagente.
        """
        state.record_progress(f"Delegando en '{self.name}'.")
        history = self.harness.new_conversation()
        result, _ = self.harness.run_conversation(task, history)
        state.record_result(self.name, result)
        return result
