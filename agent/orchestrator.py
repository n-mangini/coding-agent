"""Orquestador: agente principal que coordina subagentes y mantiene el TaskState.

En este walking skeleton el pipeline es de un solo paso (delega en el Explorer),
pero la forma ya es la definitiva: el orquestador crea el estado compartido,
delega en subagentes como si fueran tools y arma el reporte a partir del estado.
Los próximos subagentes (Implementer, Reviewer, Tester, Researcher) se enchufan
agregando pasos a `run`, sin cambiar esta estructura.
"""

from .observability import observed_run
from .state import TaskState
from .subagents import extract_sources


class Orchestrator:
    """Coordina a los subagentes y sostiene el estado de la tarea.

    Args:
        explorer (Subagent): subagente de exploración.
        researcher (Subagent): subagente que busca en la web ante falta de evidencia.
    """

    def __init__(self, explorer, researcher):
        self.explorer = explorer
        self.researcher = researcher

    def run(self, request):
        """Ejecuta el caso de uso end-to-end y devuelve (reporte, estado).

        Args:
            request (str): pedido del usuario (p. ej. "analizá este repo").

        Returns:
            tuple[str, TaskState]: el mini-reporte y el estado compartido final.
        """
        state = TaskState(request=request)
        # Traza raíz del caso de uso: las generations (turnos LLM) y los spans
        # (tools) de todos los subagentes anidan dentro de una única traza.
        with observed_run("analyze-repo", request):
            self._explore(state)
            self._research(state)
        return self._render_report(state), state

    def _explore(self, state):
        """Paso 1: el Explorer describe estructura, dependencias y convenciones."""
        task = (
            "Analizá el repositorio del directorio actual y describí su "
            "estructura, sus dependencias y sus convenciones.\n\n"
            f"Pedido del usuario: {state.request}"
        )
        self.explorer.run(task, state)

    def _research(self, state):
        """Paso 2: el Researcher busca en la web lo que la exploración no cubre.

        Registra las fuentes recuperadas (con su origen) en el estado. Si no se
        recuperó ninguna fuente web, lo anota como falta de evidencia — cubre el
        caso del stub sin TAVILY_API_KEY sin tratamiento especial.
        """
        explorer_result = state.subagent_results.get("explorer", "")
        task = (
            "A partir del pedido del usuario y de lo que ya se sabe del repo, "
            "identificá qué falta de evidencia queda y buscá en la web para "
            "cubrirla. Citá fuentes y marcá su origen (web / inferencia).\n\n"
            f"Pedido del usuario: {state.request}\n\n"
            f"Lo que ya se sabe del repo (Explorer):\n{explorer_result}"
        )
        result = self.researcher.run(task, state)

        sources = extract_sources(result)
        for origin, reference in sources:
            state.record_source(f"{reference} (origen: {origin})")
        if not any(origin == "web" for origin, _ in sources):
            state.record_missing_evidence(
                "El Researcher no recuperó evidencia web "
                "(posible stub sin TAVILY_API_KEY): la respuesta se apoya en inferencia."
            )

    def _render_report(self, state):
        """Arma el mini-reporte a partir de lo que dejaron los subagentes."""
        explorer_result = state.subagent_results.get(
            "explorer", "(el Explorer no produjo resultado)"
        )
        researcher_result = state.subagent_results.get(
            "researcher", "(el Researcher no produjo resultado)"
        )
        lines = [
            "# Mini-reporte de análisis del repositorio",
            "",
            f"**Pedido:** {state.request}",
            "",
            "## Exploración (Explorer)",
            "",
            explorer_result,
            "",
            "## Investigación (Researcher)",
            "",
            researcher_result,
        ]
        if state.sources:
            lines += ["", "## Fuentes", ""]
            lines += [f"- {source}" for source in state.sources]
        if state.observations:
            lines += ["", "## Observaciones", ""]
            lines += [f"- {obs}" for obs in state.observations]
        if state.missing_evidence:
            lines += ["", "## Falta de evidencia", ""]
            lines += [f"- {gap}" for gap in state.missing_evidence]
        return "\n".join(lines)
