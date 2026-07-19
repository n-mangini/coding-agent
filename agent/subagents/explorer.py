"""Explorer: subagente de solo lectura que entiende el repo.

Su trabajo es explorar el repositorio del directorio actual y describir su
estructura, dependencias y convenciones. Tiene un `tool_map` acotado a
lectura/exploración: no puede escribir archivos ni ejecutar comandos.
"""

from .. import tools as tools_module
from ..harness import Harness
from ..llm import schemas_for
from .base import Subagent

EXPLORER_TOOLS = ["read_file", "list_files"]

EXPLORER_SYSTEM_MESSAGE = (
    "Sos el subagente EXPLORER de un sistema de análisis de repositorios. "
    "Tu tarea es entender el repositorio del directorio actual: su estructura, "
    "sus dependencias y sus convenciones de código. "
    "Solo tenés herramientas de LECTURA y EXPLORACIÓN (list_files, read_file): "
    "no escribís archivos ni ejecutás comandos. "
    "Explorá de lo general a lo particular (primero el árbol, luego los archivos "
    "clave como README, requirements/pyproject, config y algunos módulos). "
    "Cuando tengas evidencia suficiente, respondé SIN llamar más tools con un "
    "mini-reporte claro y conciso con estas tres secciones: "
    "1) Estructura, 2) Dependencias, 3) Convenciones. "
    "Basate solo en lo que efectivamente leíste; si algo no lo pudiste verificar, "
    "decilo explícitamente en vez de inventarlo."
)


def build_explorer(client, policies=None):
    """Construye el subagente Explorer con permisos de solo lectura."""
    tool_map = {
        "read_file": tools_module.read_file,
        "list_files": tools_module.list_files,
    }
    harness = Harness(
        client,
        tool_map,
        schemas_for(EXPLORER_TOOLS),
        system_message=EXPLORER_SYSTEM_MESSAGE,
        policies=policies,
    )
    return Subagent(
        name="explorer",
        description="Analiza estructura, dependencias y convenciones del repo (solo lectura).",
        harness=harness,
    )
