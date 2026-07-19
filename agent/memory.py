"""Memoria persistente por proyecto en un JSON del propio repo.

El agente y sus subagentes acumulan acá lo que van aprendiendo de un proyecto
—arquitectura, dependencias, comandos, convenciones, decisiones, bugs y
resúmenes— para no re-descubrirlo en cada corrida. La memoria vive en un archivo
JSON dentro del proyecto (`.agent_memory.json` en el cwd, que tras `clone_repo`
es la raíz del repo clonado), así queda naturalmente indexada por proyecto.

Los subagentes la leen y la escriben a través de dos tools acotadas
(`make_memory_tools`): `read_memory` para traer el contexto acumulado y `remember`
para agregar un dato bajo una de las categorías conocidas. Igual que el resto de
las tools, nunca levantan: los errores vuelven al LLM como un string `Error: ...`.
"""

import json
from dataclasses import dataclass, field

# El archivo vive dentro del proyecto: así la memoria queda por-proyecto sin
# necesidad de un índice global ni de claves externas.
MEMORY_FILENAME = ".agent_memory.json"

# Categorías conocidas de la memoria. Son la fuente de verdad tanto para el
# schema de la tool `remember` (lo que ve el LLM) como para la validación al
# escribir: un `remember` a una categoría desconocida se rechaza sin romper.
CATEGORIES = (
    "arquitectura",
    "dependencias",
    "comandos",
    "convenciones",
    "decisiones",
    "bugs",
    "resumenes",
)


@dataclass
class ProjectMemory:
    """Memoria acumulada de un proyecto, persistida como JSON.

    Cada categoría es una lista de notas cortas. `path` es el archivo JSON donde
    se persiste; `remember` deduplica y guarda en el acto para que la memoria
    sobreviva aunque la corrida se corte a la mitad.
    """

    path: str
    entries: dict[str, list[str]] = field(default_factory=dict)

    def remember(self, categoria, nota):
        """Agrega una nota a una categoría (deduplicando) y persiste.

        Devuelve un string de confirmación o de error; nunca levanta, porque lo
        consume el LLM como salida de tool.
        """
        if categoria not in CATEGORIES:
            return (
                f"Error: categoría desconocida '{categoria}'. "
                f"Usá una de: {', '.join(CATEGORIES)}."
            )
        nota = str(nota).strip()
        if not nota:
            return "Error: la nota está vacía."

        notas = self.entries.setdefault(categoria, [])
        if nota in notas:
            return f"Ya estaba en memoria bajo '{categoria}': {nota}"
        notas.append(nota)
        self.save()
        return f"Guardado en memoria bajo '{categoria}': {nota}"

    def render(self):
        """Devuelve la memoria como texto legible (contexto para el LLM)."""
        secciones = [
            f"- {categoria}:\n"
            + "\n".join(f"    · {nota}" for nota in self.entries[categoria])
            for categoria in CATEGORIES
            if self.entries.get(categoria)
        ]
        if not secciones:
            return "(memoria del proyecto vacía)"
        return "Memoria del proyecto:\n" + "\n".join(secciones)

    def is_empty(self):
        """True si no hay ninguna nota en ninguna categoría."""
        return not any(self.entries.get(c) for c in CATEGORIES)

    def save(self):
        """Persiste la memoria en su archivo JSON."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)


def load_project_memory(project_dir="."):
    """Carga la memoria del proyecto desde su JSON (vacía si no existe).

    Degrada elegante: si el archivo está corrupto o ilegible, arranca con memoria
    vacía en vez de romper la corrida — la memoria es una ayuda, no un invariante.
    """
    path = f"{project_dir.rstrip('/')}/{MEMORY_FILENAME}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        entries = {}
    return ProjectMemory(path=path, entries=entries)


def make_memory_tools(memory):
    """Construye las tools `read_memory` y `remember` ligadas a una memoria.

    Sigue el patrón de `make_web_search`: las tools quedan cerradas sobre la
    instancia de `ProjectMemory`, así el orquestador y los subagentes comparten
    la misma memoria del proyecto. Devuelve un dict nombre -> callable listo para
    sumar al `tool_map`.
    """

    def read_memory():
        return memory.render()

    def remember(categoria, nota):
        return memory.remember(categoria, nota)

    return {"read_memory": read_memory, "remember": remember}
