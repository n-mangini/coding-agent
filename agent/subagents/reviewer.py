"""Reviewer: subagente de solo lectura que valida el reporte vs. el pedido.

Cierra el ciclo generar→revisar: lee el reporte que escribió el Implementer y
verifica que efectivamente responda al pedido original del usuario. Su `tool_map`
está acotado a LECTURA (`read_file`, `list_files`): no escribe ni ejecuta nada,
solo valida. Como el LLM no puede llamar a `record_observation`, registra sus
observaciones con una tool-call estructurada (`submit_review_result`) que el
orquestador extrae con `extract_observations` y registra en el `TaskState`.
"""

from .. import tools as tools_module
from ..harness import Harness
from ..llm import schemas_for
from .base import Subagent

REVIEWER_TOOLS = ["read_file", "list_files"]

SUBMIT_REVIEW_RESULT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "submit_review_result",
        "description": (
            "Registra el resultado final del Reviewer con observaciones "
            "estructuradas. Debe ser la última tool-call antes de responder."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "veredicto": {
                    "type": "string",
                    "description": "Veredicto breve sobre si el reporte responde al pedido.",
                },
                "observaciones": {
                    "type": "array",
                    "description": "Hallazgos relevantes de la revisión.",
                    "items": {"type": "string"},
                },
            },
            "required": ["veredicto", "observaciones"],
        },
    },
}

REVIEWER_SYSTEM_MESSAGE = (
    "Sos el subagente REVIEWER de un sistema de análisis de repositorios. "
    "Tu tarea es VALIDAR el reporte que redactó el Implementer: verificar que "
    "responda al pedido original del usuario, que sea coherente con el repo y "
    "que no invente cosas sin evidencia. "
    "Tenés herramientas de solo LECTURA (read_file, list_files): leé el archivo "
    "del reporte que te indica el orquestador y, si hace falta, contrastá con "
    "archivos del repo usando solo rutas relativas al directorio actual. No uses "
    "rutas absolutas ni salgas del repo. No escribís ni ejecutás nada. "
    "Cuando tengas el veredicto, tu ÚLTIMA tool-call debe ser "
    "submit_review_result con JSON estructurado: 'veredicto' y 'observaciones'. "
    "Incluí una observación por cada hallazgo relevante (faltantes, afirmaciones "
    "sin respaldo, aciertos). Si el reporte responde bien al pedido y no tenés "
    "reparos, registrá igual una observación confirmándolo. Después de esa tool, "
    "respondé solo con el veredicto breve, sin repetir JSON."
)


class ReviewerSubagent(Subagent):
    """Subagente Reviewer con observaciones capturadas por tool-call."""

    def __init__(self, harness, submitted):
        super().__init__(
            name="reviewer",
            description="Valida el reporte y deja observaciones estructuradas.",
            harness=harness,
        )
        self.submitted = submitted
        self.observations = []

    def run(self, task, state):
        """Ejecuta la revisión y expone observaciones estructuradas."""
        state.record_progress(f"Delegando en '{self.name}'.")
        self.submitted.clear()
        self.observations = []
        history = self.harness.new_conversation()
        result, _ = self.harness.run_conversation(task, history)

        if self.submitted:
            result = self.submitted["veredicto"]
            self.observations = self.submitted["observaciones"]

        state.record_result(self.name, result)
        for event in self.harness.loop_events:
            state.record_observation(f"{self.name}: {event}")
        return result


def build_reviewer(client, policies=None):
    """Construye el subagente Reviewer con permisos de solo lectura.

    Args:
        client: cliente OpenAI compartido.
        policies: set de políticas compartido (invariante de #11: todo Harness de
            producción las recibe; el rol lo da el `tool_map` acotado).
    """
    submitted = {}

    def submit_review_result(veredicto, observaciones):
        submitted["veredicto"] = str(veredicto).strip()
        submitted["observaciones"] = _normalize_observations(observaciones)
        return "Resultado de revisión registrado."

    def read_repo_file(file_path):
        if not _is_safe_relative_path(file_path):
            return f"Error: el Reviewer solo puede leer rutas relativas del repo: {file_path}"
        return tools_module.read_file(file_path)

    def list_repo_files(path="."):
        if not _is_safe_relative_path(path):
            return f"Error: el Reviewer solo puede listar rutas relativas del repo: {path}"
        return tools_module.list_files(path)

    tool_map = {
        "read_file": read_repo_file,
        "list_files": list_repo_files,
        "submit_review_result": submit_review_result,
    }
    harness = Harness(
        client,
        tool_map,
        schemas_for(REVIEWER_TOOLS) + [SUBMIT_REVIEW_RESULT_SCHEMA],
        system_message=REVIEWER_SYSTEM_MESSAGE,
        policies=policies,
    )
    return ReviewerSubagent(harness, submitted)


def extract_observations(result):
    """Devuelve observaciones estructuradas de un `ReviewerSubagent`.

    `result` puede ser el subagente (camino nuevo) o una lista de textos ya
    normalizada.
    """
    if isinstance(result, ReviewerSubagent):
        return result.observations
    return _normalize_observations(result)


def _normalize_observations(raw_observations):
    """Normaliza observaciones JSON del LLM y descarta entradas vacías."""
    if not isinstance(raw_observations, list):
        return []
    observations = []
    for observation in raw_observations:
        if observation is None:
            continue
        text = str(observation).strip()
        if text:
            observations.append(text)
    return observations


def _is_safe_relative_path(path):
    """True si `path` se mantiene dentro del repo actual."""
    text = str(path or ".").replace("\\", "/")
    parts = [part for part in text.split("/") if part not in ("", ".")]
    return not text.startswith("/") and ".." not in parts
