"""Orquestador: agente principal que coordina subagentes y mantiene el TaskState.

En este walking skeleton el pipeline es de un solo paso (delega en el Explorer),
pero la forma ya es la definitiva: el orquestador crea el estado compartido,
delega en subagentes como si fueran tools y arma el reporte a partir del estado.
Los próximos subagentes (Implementer, Reviewer, Tester, Researcher) se enchufan
agregando pasos a `run`, sin cambiar esta estructura.
"""

from .state import TaskState


class Orchestrator:
    """Coordina a los subagentes y sostiene el estado de la tarea.

    Args:
        explorer (Subagent): subagente de exploración (único en el skeleton).
    """

    def __init__(self, explorer):
        self.explorer = explorer

    def run(self, request):
        """Ejecuta el caso de uso end-to-end y devuelve (reporte, estado).

        Args:
            request (str): pedido del usuario (p. ej. "analizá este repo").

        Returns:
            tuple[str, TaskState]: el mini-reporte y el estado compartido final.
        """
        state = TaskState(request=request)

        task = (
            "Analizá el repositorio del directorio actual y describí su "
            "estructura, sus dependencias y sus convenciones.\n\n"
            f"Pedido del usuario: {request}"
        )
        self.explorer.run(task, state)

        return self._render_report(state), state

    def _render_report(self, state):
        """Arma el mini-reporte a partir de lo que dejaron los subagentes."""
        explorer_result = state.subagent_results.get(
            "explorer", "(el Explorer no produjo resultado)"
        )
        lines = [
            "# Mini-reporte de análisis del repositorio",
            "",
            f"**Pedido:** {state.request}",
            "",
            "## Exploración (Explorer)",
            "",
            explorer_result,
        ]
        if state.observations:
            lines += ["", "## Observaciones", ""]
            lines += [f"- {obs}" for obs in state.observations]
        return "\n".join(lines)
