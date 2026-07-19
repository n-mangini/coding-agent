"""Researcher: subagente que cubre la falta de evidencia (RAG primero, web después).

Cuando la exploración del repo no alcanza para responder, este subagente consulta
PRIMERO el índice RAG (`retrieve`, sobre Chroma) y solo cae a `web_search` si el
RAG no trae evidencia suficiente. Devuelve la información con sus fuentes
atribuidas y el origen marcado (repo / memoria / RAG / web / inferencia) mediante
una tool-call estructurada, no un pie de texto libre. Su `tool_map` está acotado
a `retrieve`, `web_search` y `submit_research_result`; si el RAG no está
disponible (sin `chromadb` o índice vacío) o no hay `TAVILY_API_KEY`, las tools
de evidencia degradan a stub y el Researcher sigue sin romper.
"""

from ..harness import Harness
from ..llm import schemas_for
from .base import Subagent

RESEARCHER_TOOLS = ["retrieve", "web_search"]
SOURCE_ORIGINS = ("repo", "memoria", "rag", "web", "inferencia")

SUBMIT_RESEARCH_RESULT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "submit_research_result",
        "description": (
            "Registra el resultado final del Researcher con fuentes estructuradas. "
            "Debe ser la última tool-call antes de responder."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "respuesta": {
                    "type": "string",
                    "description": "Respuesta breve y clara para el reporte.",
                },
                "fuentes": {
                    "type": "array",
                    "description": "Fuentes usadas, con origen explícito.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "origen": {
                                "type": "string",
                                "enum": list(SOURCE_ORIGINS),
                                "description": "Origen de la evidencia.",
                            },
                            "referencia": {
                                "type": "string",
                                "description": "URL, archivo, chunk o descripción corta.",
                            },
                        },
                        "required": ["origen", "referencia"],
                    },
                },
            },
            "required": ["respuesta", "fuentes"],
        },
    },
}

RESEARCHER_SYSTEM_MESSAGE = (
    "Sos el subagente RESEARCHER de un sistema de análisis de repositorios. "
    "Tu tarea es cubrir la FALTA DE EVIDENCIA: cuando lo que se sabe del repo no "
    "alcanza para responder, buscás la evidencia que falta. "
    "Tenés dos herramientas y un ORDEN obligatorio: consultá SIEMPRE PRIMERO "
    "'retrieve' (índice RAG local sobre Chroma). Solo si 'retrieve' no trae "
    "evidencia suficiente (devuelve 'Sin resultados', un error de disponibilidad, "
    "o chunks que no responden al pedido) caés a 'web_search'. No uses web_search "
    "si el RAG ya alcanzó. No leés archivos ni ejecutás comandos. "
    "Si una tool devuelve un error de disponibilidad (RAG sin chromadb/índice, o "
    "web_search sin TAVILY_API_KEY), no reintentes en loop: seguí con la otra o, "
    "si tampoco hay, respondé con lo que puedas inferir y dejalo explícito. "
    "Siempre citás tus fuentes y marcás su ORIGEN, que puede ser: 'repo' (algo que "
    "ya se sabía del repositorio), 'memoria' (contexto previo dado), 'rag' (un "
    "chunk recuperado con retrieve; usá la fuente que aparece tras 'FUENTE_RAG:'), "
    "'web' (un resultado de web_search, incluí la URL) o 'inferencia' (razonamiento "
    "propio sin evidencia externa). "
    "Cuando tengas la respuesta, tu ÚLTIMA tool-call debe ser "
    "submit_research_result con JSON estructurado: 'respuesta' y 'fuentes'. "
    "Después de esa tool, respondé solo con la misma respuesta breve, sin repetir "
    "JSON ni agregar una sección de fuentes en texto libre."
)


class ResearcherSubagent(Subagent):
    """Subagente Researcher con salida estructurada capturada por tool-call."""

    def __init__(self, harness, submitted):
        super().__init__(
            name="researcher",
            description="Busca evidencia RAG-first y devuelve fuentes estructuradas.",
            harness=harness,
        )
        self.submitted = submitted
        self.sources = []

    def run(self, task, state):
        """Ejecuta la investigación y expone respuesta/fuentes estructuradas."""
        state.record_progress(f"Delegando en '{self.name}'.")
        self.submitted.clear()
        self.sources = []
        history = self.harness.new_conversation()
        result, _ = self.harness.run_conversation(task, history)

        if self.submitted:
            result = self.submitted["respuesta"]
            self.sources = self.submitted["fuentes"]

        state.record_result(self.name, result)
        for event in self.harness.loop_events:
            state.record_observation(f"{self.name}: {event}")
        return result


def build_researcher(client, retrieve, web_search, policies=None):
    """Construye el Researcher, acotado a evidencia y salida estructurada.

    Args:
        client: cliente OpenAI compartido.
        retrieve: callable de recuperación RAG (real o el stub de `make_retrieve`).
        web_search: callable de búsqueda (real o el stub de `make_web_search`).
        policies: set de políticas compartido. Todo Harness de producción las
            recibe (invariante de #11): el rol lo da el `tool_map` acotado, las
            policies son invariantes de seguridad globales iguales para todos.
    """
    submitted = {}

    def submit_research_result(respuesta, fuentes):
        submitted["respuesta"] = str(respuesta).strip()
        submitted["fuentes"] = _normalize_sources(fuentes)
        return "Resultado de investigación registrado."

    tool_map = {
        "retrieve": retrieve,
        "web_search": web_search,
        "submit_research_result": submit_research_result,
    }
    harness = Harness(
        client,
        tool_map,
        schemas_for(RESEARCHER_TOOLS) + [SUBMIT_RESEARCH_RESULT_SCHEMA],
        system_message=RESEARCHER_SYSTEM_MESSAGE,
        policies=policies,
    )
    return ResearcherSubagent(harness, submitted)


def extract_sources(result):
    """Devuelve fuentes estructuradas de un `ResearcherSubagent`.

    `result` puede ser el subagente (camino nuevo) o una lista de fuentes ya
    normalizada. Se conserva este helper para que el orquestador no conozca el
    detalle de almacenamiento interno del Researcher.
    """
    if isinstance(result, ResearcherSubagent):
        return [(source["origen"], source["referencia"]) for source in result.sources]
    return [
        (source["origen"], source["referencia"])
        for source in _normalize_sources(result)
    ]


def _normalize_sources(raw_sources):
    """Normaliza fuentes JSON del LLM y descarta entradas mal formadas."""
    if not isinstance(raw_sources, list):
        return []
    normalized = []
    for source in raw_sources:
        if not isinstance(source, dict):
            continue
        origin = str(source.get("origen", "")).strip().lower()
        reference = str(source.get("referencia", "")).strip()
        if origin not in SOURCE_ORIGINS or not reference:
            continue
        normalized.append({"origen": origin, "referencia": reference})
    return normalized
