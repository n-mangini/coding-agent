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
        observations: notas transversales (dudas, riesgos).
        missing_evidence: faltas de evidencia reconocidas explícitamente (lo que
            no se pudo verificar y quedó sin respaldo). Se separa de `observations`
            para que el reporte pueda ser honesto sobre lo que no sabe.
    """

    request: str
    progress: list[str] = field(default_factory=list)
    subagent_results: dict[str, str] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)

    def record_progress(self, note):
        """Anota un paso de avance."""
        self.progress.append(note)

    def record_result(self, agent_name, result):
        """Guarda el resultado final de un subagente bajo su nombre."""
        self.subagent_results[agent_name] = result

    def record_source(self, source):
        """Registra una fuente consultada (repo/RAG/web/...); la usa el Researcher."""
        self.sources.append(source)

    def record_modified_file(self, path):
        """Registra un archivo escrito/modificado durante la tarea."""
        self.modified_files.append(path)

    def record_observation(self, note):
        """Anota una observación transversal (dudas, riesgos)."""
        self.observations.append(note)

    def record_missing_evidence(self, note):
        """Reconoce explícitamente una falta de evidencia (algo no verificado)."""
        self.missing_evidence.append(note)
