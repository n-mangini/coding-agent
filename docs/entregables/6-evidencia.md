# 6. Evidencia de tareas ejecutadas

Este documento reúne la evidencia de **dos tareas** ejecutadas sobre el
caso de uso (analizar un repo → reporte)

Ambas se ejecutaron sobre el repo de `pypa/sampleproject`. Por cada tarea se incluye el comando, el output relevante
recortado del log, las fuentes/memoria recuperadas y una breve explicación.

> Repositorio analizado: <https://github.com/pypa/sampleproject>

---

## Tarea 1 — RAG + fuentes recuperadas

Capacidades cubiertas: **tarea que requiere usar RAG y mostrar las fuentes
recuperadas** + **ejecución registrada en observabilidad**.

### Comando

```bash
python analyze.py --python https://github.com/pypa/sampleproject \
  "Analizá arquitectura, dependencias, riesgos y comandos"
```

`--python` ingesta primero la base RAG especializada de Python y después clona y
analiza, por lo que el índice RAG **tiene contenido** para consultar.

### Output relevante

Ingesta del índice:

```text
RAG Python cargado: 2 documento(s), 11 chunk(s). Total en el índice: 11.
Cloning https://github.com/pypa/sampleproject ...
✅ Repo cloned to: .../workspace/sampleproject
```

El Researcher consulta el RAG **primero** y obtiene hits reales (con distancia):

```text
🤖 Calling tool: retrieve with args: {'query': 'arquitectura, dependencias, riesgos y comandos del repositorio'}
Tool output: FUENTE_RAG: .../rag/sources/python/python-ecosystem-guide.md (distancia 0.8540)
             FUENTE_RAG: .../rag/sources/python/python-ecosystem-guide.md (distancia 0.8937)
             FUENTE_RAG: .../rag/sources/python/python-ecosystem-guide.md (distancia 0.9108)
             FUENTE_RAG: .../rag/sources/python/python-ecosystem-guide.md (distancia 0.9516)
```

Como la evidencia del RAG es genérica (una guía, no el repo puntual), cae a la
web como fallback y emite el resultado con **fuentes estructuradas (JSON)**,
diferenciando el origen de cada una:

```text
🤖 Calling tool: submit_research_result with args:
   {'respuesta': 'No se encontró evidencia directa sobre la arquitectura detallada...',
    'fuentes': [{'origen': 'rag', 'referencia': '.../python-ecosystem-guide.md'},
                {'origen': 'web', 'referencia': 'https://packaging.python.org/.../pyproject-toml'},
                {'origen': 'web', 'referencia': 'https://realpython.com/python-pyproject-toml'}]}
```

El reporte final materializa esas fuentes en su sección correspondiente:

```text
## Fuentes
- .../rag/sources/python/python-ecosystem-guide.md (origen: rag)
- https://packaging.python.org/en/latest/specifications/pyproject-toml (origen: web)
- https://realpython.com/python-pyproject-toml (origen: web)
```

### Fuentes recuperadas

- **RAG:** `rag/sources/python/python-ecosystem-guide.md` (4 fragmentos, distancias 0.85–0.95)
- **Web (fallback):** `packaging.python.org/.../pyproject-toml`, `realpython.com/python-pyproject-toml`

### Qué se observa

- El Researcher respeta la regla **RAG-first + fallback web** y **diferencia el
  origen** de cada fuente (`rag` / `web`) en salida estructurada JSON.
- Las fuentes recuperadas quedan explícitas en el reporte, cumpliendo el
  requisito de "mostrar las fuentes recuperadas".
- La ejecución completa queda registrada en la herramienta de observabilidad.

---

## Tarea 2 — Memoria del proyecto

Capacidad cubierta: **tarea que requiere usar memoria del proyecto**.

La memoria persistente vive en `.agent_memory.json` en la raíz del repo
analizado. Para demostrar persistencia **entre corridas** se ejecutan dos veces
sobre el mismo directorio ya clonado (sin re-clonar, que borraría la memoria).

### Corrida A — sembrar memoria

```bash
cd workspace/sampleproject
python .../analyze.py "Explorá el repo y guardá en memoria lo estable: arquitectura, dependencias y comandos"
```

El Explorer arranca leyendo memoria (vacía) y, al confirmar hechos estables, los
guarda con `remember`. Al terminar, `.agent_memory.json` contiene:

```json
{
  "arquitectura": [
    "El proyecto sigue una estructura típica con src para el código fuente, tests para pruebas, y uso de pyproject.toml para configuración."
  ],
  "dependencias": [
    "El proyecto depende de peppercorn, con check-manifest y coverage para desarrollo."
  ],
  "comandos": [
    "Presencia de noxfile.py sugiere uso de Nox para automatización de tareas."
  ]
}
```

### Corrida B — reutilizar memoria

```bash
cd workspace/sampleproject
python .../analyze.py "Usando lo que ya sepas del proyecto, resumí arquitectura, dependencias y comandos"
```

Ahora la **primera** tool que corre el Explorer es `read_memory`, y **recupera lo
sembrado en la Corrida A** (ya no está vacía):

```text
🤖 Calling tool: read_memory with args: {}
Tool output: Memoria del proyecto:
- arquitectura:
    · El proyecto sigue una estructura típica con src para el código fuente, tests para pruebas, y uso de pyproject.toml para configuración.
- dependencias:
    · El proyecto depende de peppercorn, con check-manifest y coverage para desarrollo.
- comandos:
    · Presencia de noxfile.py sugiere uso de Nox para automatización de tareas.
```

Comparado con las corridas de la Tarea 1, donde `read_memory` devolvía
`(memoria del proyecto vacía)`, acá arranca con contexto previo.

### Memoria recuperada

- Categorías `arquitectura`, `dependencias`, `comandos` pobladas en la Corrida A
  y leídas al inicio de la Corrida B (`.agent_memory.json`).

### Qué se observa

- La memoria del proyecto **persiste entre ejecuciones**: lo aprendido en una
  corrida está disponible en la siguiente sin volver a descubrirlo.
- El Explorer sigue el contrato de su prompt: `read_memory` al empezar y
  `remember` para lo estable, de modo que la memoria se enriquece con el uso.
- Es la diferencia entre un agente sin estado entre corridas y uno que acumula
  conocimiento del proyecto.

---

## Síntesis

| | Tarea 1 (RAG) | Tarea 2 (memoria) |
|---|---|---|
| Capacidad pedida | RAG + fuentes recuperadas | Memoria del proyecto |
| Evidencia principal | `retrieve` con hits + `submit_research_result` (fuentes JSON `rag`/`web`) | `read_memory` recupera lo que otra corrida guardó con `remember` |
| Artefacto | `REPORTE-ANALISIS.md` | `.agent_memory.json` poblado |

