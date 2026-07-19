"""Reviewer: subagente de solo lectura que valida el reporte vs. el pedido.

Cierra el ciclo generar→revisar: lee el reporte que escribió el Implementer y
verifica que efectivamente responda al pedido original del usuario. Su `tool_map`
está acotado a LECTURA (`read_file`, `list_files`): no escribe ni ejecuta nada,
solo valida. Como el LLM no puede llamar a `record_observation`, emite sus
observaciones en un pie parseable (`OBSERVACION: <texto>`) que el orquestador
extrae con `extract_observations` y registra en el `TaskState`.
"""

from .. import tools as tools_module
from ..harness import Harness
from ..llm import schemas_for
from .base import Subagent

REVIEWER_TOOLS = ["read_file", "list_files"]

# Prefijo del pie parseable que el orquestador usa para registrar las
# observaciones en el TaskState (mismo patrón que `FUENTE:` del Researcher).
OBSERVATION_PREFIX = "OBSERVACION:"

REVIEWER_SYSTEM_MESSAGE = (
    "Sos el subagente REVIEWER de un sistema de análisis de repositorios. "
    "Tu tarea es VALIDAR el reporte que redactó el Implementer: verificar que "
    "responda al pedido original del usuario, que sea coherente con el repo y "
    "que no invente cosas sin evidencia. "
    "Tenés herramientas de solo LECTURA (read_file, list_files): leé el archivo "
    "del reporte que te indica el orquestador y, si hace falta, contrastá con "
    "archivos del repo. No escribís ni ejecutás nada. "
    "Cuando termines, respondé SIN llamar más tools: primero un veredicto breve "
    "(¿el reporte responde al pedido? ¿qué está bien, qué falta o qué corregir?) "
    "y al final una sección de observaciones donde cada observación va en su "
    f"propia línea con este formato exacto: '{OBSERVATION_PREFIX} <texto>'. "
    "Incluí una observación por cada hallazgo relevante (faltantes, "
    "afirmaciones sin respaldo, aciertos). Si el reporte responde bien al "
    "pedido y no tenés reparos, emití igual una línea de observación "
    "confirmándolo. No inventes líneas de observación vacías."
)


def build_reviewer(client, policies=None):
    """Construye el subagente Reviewer con permisos de solo lectura.

    Args:
        client: cliente OpenAI compartido.
        policies: set de políticas compartido (invariante de #11: todo Harness de
            producción las recibe; el rol lo da el `tool_map` acotado).
    """
    tool_map = {
        "read_file": tools_module.read_file,
        "list_files": tools_module.list_files,
    }
    harness = Harness(
        client,
        tool_map,
        schemas_for(REVIEWER_TOOLS),
        system_message=REVIEWER_SYSTEM_MESSAGE,
        policies=policies,
    )
    return Subagent(
        name="reviewer",
        description="Valida que el reporte responda al pedido y deja observaciones (solo lectura).",
        harness=harness,
    )


def extract_observations(result):
    """Extrae las observaciones del pie parseable que emite el Reviewer.

    Devuelve la lista de textos de las líneas con formato `OBSERVACION: <texto>`.
    Las líneas sin texto se ignoran (el LLM podría emitir una línea vacía;
    preferimos no registrar ruido).
    """
    observations = []
    for line in result.splitlines():
        line = line.strip()
        if not line.startswith(OBSERVATION_PREFIX):
            continue
        text = line[len(OBSERVATION_PREFIX):].strip()
        if text:
            observations.append(text)
    return observations
