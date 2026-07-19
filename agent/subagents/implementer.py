"""Implementer: subagente que redacta el reporte de análisis y lo persiste.

Toma el material crudo que dejaron los pasos previos en el `TaskState` (lo que
exploró el Explorer y lo que investigó el Researcher) y lo redacta como un
reporte coherente que responde al pedido original. Su `tool_map` está acotado a
ESCRITURA (`write_file`): no lee el repo ni ejecuta comandos, porque su insumo ya
está en el estado. Escribe el reporte en un archivo fijo (`REPORT_FILENAME`) para
que quede como artefacto verificable y para que el Reviewer pueda leerlo.
"""

from .. import tools as tools_module
from ..harness import Harness
from ..llm import schemas_for
from .base import Subagent

IMPLEMENTER_TOOLS = ["write_file"]

# Ruta fija del artefacto. Es la única fuente de verdad del nombre del reporte:
# el Implementer lo escribe acá y el Reviewer lo lee de acá (se lo pasa el
# orquestador en la tarea), así ningún subagente inventa la ruta.
REPORT_FILENAME = "REPORTE-ANALISIS.md"

IMPLEMENTER_SYSTEM_MESSAGE = (
    "Sos el subagente IMPLEMENTER de un sistema de análisis de repositorios. "
    "Tu tarea es REDACTAR el reporte final de análisis del repo a partir del "
    "material que te pasa el orquestador (exploración del repo e investigación "
    "web ya hechas). No explorás el repo ni ejecutás comandos: tu única "
    "herramienta es write_file, con la que persistís el reporte. "
    f"Escribí el reporte completo en el archivo '{REPORT_FILENAME}' con una sola "
    "llamada a write_file. El reporte debe responder al pedido original del "
    "usuario, estar en Markdown y ser claro y conciso, con al menos estas "
    "secciones: 1) Resumen (qué es el repo y cómo responde al pedido), "
    "2) Estructura, 3) Dependencias, 4) Convenciones, y una sección de Fuentes "
    "si las hubiera. Basate solo en el material provisto; si algo no está "
    "verificado, decilo explícitamente en vez de inventarlo. "
    "Una vez escrito el archivo, respondé SIN llamar más tools con el texto "
    "completo del reporte que guardaste (el mismo contenido)."
)


def build_implementer(client, policies=None):
    """Construye el subagente Implementer, acotado a `write_file`.

    Args:
        client: cliente OpenAI compartido.
        policies: set de políticas compartido (invariante de #11: todo Harness de
            producción las recibe; el rol lo da el `tool_map` acotado).
    """
    tool_map = {"write_file": tools_module.write_file}
    harness = Harness(
        client,
        tool_map,
        schemas_for(IMPLEMENTER_TOOLS),
        system_message=IMPLEMENTER_SYSTEM_MESSAGE,
        policies=policies,
    )
    return Subagent(
        name="implementer",
        description="Redacta el reporte de análisis desde el estado y lo persiste (escritura acotada).",
        harness=harness,
    )
