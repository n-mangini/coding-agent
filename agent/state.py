"""Estado compartido de la tarea entre el orquestador y los subagentes.

Es la pieza que mantiene consistente al sistema multi-agente: el orquestador lo
crea, cada subagente lee lo que necesita y escribe sus resultados/observaciones,
y el reporte final se arma a partir de él.
"""

from dataclasses import dataclass, field


@dataclass
class TaskState:
    """Estado vivo de una tarea que atraviesa a todos los subagentes.

    Attributes:
        request: el pedido original del usuario en lenguaje natural.
        progress: bitácora de avance (qué se fue delegando/haciendo).
        subagent_results: resultado final de cada subagente, por nombre.
        sources: fuentes citadas (repo/RAG/web/...); las llena el Researcher.
        modified_files: archivos escritos/modificados durante la tarea.
        observations: notas transversales (dudas, riesgos, falta de evidencia).
    """

    request: str
    progress: list[str] = field(default_factory=list)
    subagent_results: dict[str, str] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)

    def record_progress(self, note):
        """Anota un paso de avance."""
        self.progress.append(note)

    def record_result(self, agent_name, result):
        """Guarda el resultado final de un subagente bajo su nombre."""
        self.subagent_results[agent_name] = result

    def add_observation(self, note):
        """Anota una observación transversal."""
        self.observations.append(note)
