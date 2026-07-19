"""Researcher: subagente que cubre la falta de evidencia buscando en la web.

Cuando la exploración del repo no alcanza para responder, este subagente busca
en la web (`web_search`) y devuelve la información con sus fuentes atribuidas y
el origen marcado (web / inferencia). Todavía sin RAG (#8): esta rebanada fija el
contrato del Researcher y el manejo de fuentes. Su `tool_map` está acotado a
`web_search`; si no hay `TAVILY_API_KEY`, esa tool es un stub y el Researcher
degrada sin romper (lo deja anotado como falta de evidencia).
"""

from ..harness import Harness
from ..llm import schemas_for
from .base import Subagent

RESEARCHER_TOOLS = ["web_search"]

# Prefijo del pie parseable que el orquestador usa para registrar las fuentes en
# el TaskState. El LLM no puede llamar a record_source, así que emite las fuentes
# en este formato y el orquestador las extrae con `extract_sources`.
SOURCE_PREFIX = "FUENTE:"

RESEARCHER_SYSTEM_MESSAGE = (
    "Sos el subagente RESEARCHER de un sistema de análisis de repositorios. "
    "Tu tarea es cubrir la FALTA DE EVIDENCIA: cuando lo que se sabe del repo no "
    "alcanza para responder, buscás en la web. "
    "Tu única herramienta es web_search: no leés archivos ni ejecutás comandos. "
    "Cuando detectes que falta evidencia para responder con certeza, disparás una "
    "búsqueda con web_search en vez de inventar. "
    "Si web_search devuelve un error de disponibilidad (por ejemplo, sin "
    "TAVILY_API_KEY), no reintentes en loop: respondé con lo que puedas inferir y "
    "dejá explícito que no pudiste traer evidencia web. "
    "Siempre citás tus fuentes y marcás su ORIGEN: 'web' si viene de un resultado "
    "de búsqueda (incluí la URL), 'inferencia' si es razonamiento propio sin "
    "evidencia externa. "
    "Cuando termines, respondé SIN llamar más tools: primero una respuesta breve "
    "y clara, y al final una sección de fuentes donde cada fuente va en su propia "
    f"línea con este formato exacto: '{SOURCE_PREFIX} <origen> | <referencia>', "
    "donde <origen> es 'web' o 'inferencia' y <referencia> es la URL o una "
    "descripción corta. Si no hubo ninguna fuente, no inventes líneas de fuente."
)


def build_researcher(client, web_search, policies=None):
    """Construye el subagente Researcher, acotado a `web_search`.

    Args:
        client: cliente OpenAI compartido.
        web_search: callable de búsqueda (real o el stub de `make_web_search`).
        policies: set de políticas compartido. Todo Harness de producción las
            recibe (invariante de #11): el rol lo da el `tool_map` acotado, las
            policies son invariantes de seguridad globales iguales para todos.
    """
    tool_map = {"web_search": web_search}
    harness = Harness(
        client,
        tool_map,
        schemas_for(RESEARCHER_TOOLS),
        system_message=RESEARCHER_SYSTEM_MESSAGE,
        policies=policies,
    )
    return Subagent(
        name="researcher",
        description="Busca en la web cuando falta evidencia y devuelve fuentes atribuidas.",
        harness=harness,
    )


def extract_sources(result):
    """Extrae las fuentes del pie parseable que emite el Researcher.

    Devuelve una lista de tuplas `(origen, referencia)` a partir de las líneas
    con formato `FUENTE: <origen> | <referencia>`. Las líneas mal formadas se
    ignoran (el LLM podría equivocar el formato; preferimos no romper).
    """
    sources = []
    for line in result.splitlines():
        line = line.strip()
        if not line.startswith(SOURCE_PREFIX):
            continue
        rest = line[len(SOURCE_PREFIX):].strip()
        origin, sep, reference = rest.partition("|")
        if not sep:
            continue
        sources.append((origin.strip(), reference.strip()))
    return sources
