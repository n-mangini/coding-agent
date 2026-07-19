"""Orquestador: agente principal que coordina subagentes y mantiene el TaskState.

El pipeline cierra el ciclo analizar→generar→validar→revisar: el Explorer y el
Researcher juntan material, el Implementer redacta y persiste el reporte, el
Tester corre checks acotados y el Reviewer valida que el resultado responda al
pedido. La forma es la definitiva: el orquestador crea el estado compartido,
delega en subagentes como si fueran tools y arma el reporte a partir del estado.
"""

from .observability import observed_run
from .state import TaskState
from .subagents import (
    DEFAULT_TEST_COMMAND,
    REPORT_FILENAME,
    extract_observations,
    extract_sources,
)


class Orchestrator:
    """Coordina a los subagentes y sostiene el estado de la tarea.

    Args:
        explorer (Subagent): subagente de exploración (solo lectura).
        researcher (Subagent): subagente que busca en la web ante falta de evidencia.
        implementer (Subagent): subagente que redacta y persiste el reporte.
        tester (Subagent): subagente que ejecuta checks acotados.
        reviewer (Subagent): subagente que valida el reporte vs. el pedido.
    """

    def __init__(self, explorer, researcher, implementer, tester, reviewer):
        self.explorer = explorer
        self.researcher = researcher
        self.implementer = implementer
        self.tester = tester
        self.reviewer = reviewer

    def run(self, request):
        """Ejecuta el caso de uso end-to-end y devuelve (reporte, estado).

        Args:
            request (str): pedido del usuario (p. ej. "analizá este repo").

        Returns:
            tuple[str, TaskState]: el reporte final y el estado compartido.
        """
        state = TaskState(request=request)
        # Traza raíz del caso de uso: las generations (turnos LLM) y los spans
        # (tools) de todos los subagentes anidan dentro de una única traza.
        with observed_run("analyze-repo", request):
            self._explore(state)
            self._research(state)
            self._implement(state)
            self._test(state)
            self._review(state)
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
        """Paso 2: el Researcher cubre la falta de evidencia (RAG primero, web después).

        Registra las fuentes recuperadas (con su origen) en el estado. Si no se
        recuperó evidencia externa (ni RAG ni web), lo anota como falta de
        evidencia — cubre el caso del índice vacío o del stub sin TAVILY_API_KEY
        sin tratamiento especial.
        """
        explorer_result = state.subagent_results.get("explorer", "")
        task = (
            "A partir del pedido del usuario y de lo que ya se sabe del repo, "
            "identificá qué falta de evidencia queda. Consultá PRIMERO el índice "
            "RAG con retrieve y solo caé a web_search si el RAG no alcanza. Citá "
            "fuentes y marcá su origen (repo / memoria / rag / web / inferencia).\n\n"
            f"Pedido del usuario: {state.request}\n\n"
            f"Lo que ya se sabe del repo (Explorer):\n{explorer_result}"
        )
        result = self.researcher.run(task, state)

        sources = extract_sources(self.researcher)
        for origin, reference in sources:
            state.record_source(f"{reference} (origen: {origin})")
        external_origins = {"rag", "web"}
        if not any(origin in external_origins for origin, _ in sources):
            state.record_missing_evidence(
                "El Researcher no recuperó evidencia externa (RAG vacío/sin chromadb "
                "y/o web_search stub sin TAVILY_API_KEY): la respuesta se apoya en inferencia."
            )

    def _implement(self, state):
        """Paso 3: el Implementer redacta el reporte desde el estado y lo persiste.

        Le pasa el material crudo (Explorer + Researcher + fuentes) y el pedido
        original. El Implementer escribe el reporte en `REPORT_FILENAME`; el
        orquestador registra ese archivo como modificado.
        """
        explorer_result = state.subagent_results.get("explorer", "")
        researcher_result = state.subagent_results.get("researcher", "")
        sources = "\n".join(f"- {s}" for s in state.sources) or "(sin fuentes)"
        task = (
            "Redactá el reporte final de análisis del repo a partir del material "
            f"provisto y guardalo en '{REPORT_FILENAME}'. El reporte tiene que "
            "responder al pedido original del usuario.\n\n"
            f"Pedido del usuario: {state.request}\n\n"
            f"Exploración (Explorer):\n{explorer_result}\n\n"
            f"Investigación (Researcher):\n{researcher_result}\n\n"
            f"Fuentes:\n{sources}"
        )
        self.implementer.run(task, state)
        state.record_modified_file(REPORT_FILENAME)

    def _test(self, state):
        """Paso 4: el Tester ejecuta un check real y registra el resultado.

        El comando permitido compila los módulos Python para detectar errores de
        sintaxis/import básicos. Si falla, no corta el pipeline: deja una
        observación para que el Reviewer la considere.
        """
        task = (
            "Ejecutá el check real permitido para validar el repo y el reporte. "
            "Usá exactamente este comando con execute_command, sin modificarlo:\n\n"
            f"{DEFAULT_TEST_COMMAND}\n\n"
            "Reportá si pasó o falló y resumí stdout/stderr relevante."
        )
        result = self.tester.run(task, state)
        if _check_failed(result):
            state.record_observation(f"Tester: check fallido. {result}")

    def _review(self, state):
        """Paso 5: el Reviewer valida el reporte contra el pedido original.

        Lee el archivo que dejó el Implementer y emite observaciones en su pie
        parseable; el orquestador las registra en el estado.
        """
        task = (
            "Validá que el reporte responda al pedido original del usuario. Leé "
            f"el archivo '{REPORT_FILENAME}' (y, si hace falta, contrastá con el "
            "repo) y dejá tus observaciones. Considerá también el resultado del "
            "Tester.\n\n"
            f"Pedido del usuario: {state.request}\n\n"
            f"Resultado del Tester:\n{state.subagent_results.get('tester', '')}"
        )
        self.reviewer.run(task, state)

        observations = extract_observations(self.reviewer)
        for observation in observations:
            state.record_observation(f"Reviewer: {observation}")
        if not observations:
            state.record_observation(
                "El Reviewer no emitió observaciones parseables sobre el reporte."
            )

    def _render_report(self, state):
        """Devuelve el reporte final: el que redactó el Implementer, más el
        veredicto de la revisión y las observaciones acumuladas en el estado.

        El cuerpo del reporte es responsabilidad del Implementer (y quedó también
        persistido en `REPORT_FILENAME`); acá el orquestador solo le adosa la capa
        de revisión que vive en el estado, para que el resultado impreso muestre
        el ciclo generar→revisar completo.
        """
        report = state.subagent_results.get(
            "implementer", "(el Implementer no produjo reporte)"
        )
        lines = [report]
        if state.sources:
            lines += ["", "## Fuentes", ""]
            lines += [f"- {source}" for source in state.sources]
        if state.observations:
            lines += ["", "## Revisión y observaciones", ""]
            lines += [f"- {obs}" for obs in state.observations]
        tester_result = state.subagent_results.get("tester")
        if tester_result:
            lines += ["", "## Checks (Tester)", "", tester_result]
        if state.missing_evidence:
            lines += ["", "## Falta de evidencia", ""]
            lines += [f"- {gap}" for gap in state.missing_evidence]
        lines += ["", f"_Reporte persistido en `{REPORT_FILENAME}`._"]
        return "\n".join(lines)


def _check_failed(result):
    """Detecta fallos reportados por `execute_command` sin romper el pipeline."""
    lowered = str(result).lower()
    return (
        "command failed" in lowered
        or "error:" in lowered
        or "traceback" in lowered
    )
