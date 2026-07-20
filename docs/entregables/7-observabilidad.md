# 7. Evidencia de observabilidad

## Descripcion general

Para evidenciar la observabilidad del sistema se utilizo una traza completa
exportada desde Langfuse.

La traza corresponde a una ejecucion del caso de uso:

```text
analyze-repo
```

Pedido ejecutado:

```text
Analiza este repositorio Python: arquitectura, dependencias, comandos, riesgos y checks relevantes.
```

Trace ID:

```text
852c9088584005f9a577575f5fa6e02c
```

Archivo exportado:

```text
trace-852c9088584005f9a577575f5fa6e02c.json
```

## Captura 1: vista resumida de la traza

![Vista resumida de la traza](assets/trace-graph-summary.png)

En esta captura se observa la traza completa como un grafo resumido. El nodo raiz
es `analyze-repo`, que representa la ejecucion completa del caso de uso. Debajo
aparecen las llamadas a OpenAI y las tools utilizadas por los subagentes.

Elementos visibles:

- `_start_`: inicio de la ejecucion.
- `analyze-repo`: traza raiz del caso de uso.
- `OpenAI-generation`: llamadas al modelo.
- `list_files`: exploracion de archivos.
- `read_file`: lectura de archivos relevantes.
- `read_memory`: consulta de memoria persistente.
- `retrieve`: recuperacion RAG.
- `OpenAI-embedding`: embedding usado para la consulta RAG.
- `submit_research_result`: registro estructurado del resultado del Researcher.
- `write_file`: escritura del reporte.
- `execute_command`: check tecnico ejecutado por el Tester.
- `submit_review_result`: registro de observaciones del Reviewer.
- `_end_`: fin de la ejecucion.

Esta vista permite comprobar que el flujo no fue una respuesta directa del LLM:
hubo ejecucion real de herramientas, recuperacion RAG, escritura de archivo,
validacion y revision.

## Captura 2: grafo completo de ejecucion

![Grafo completo de ejecucion](assets/trace-graph-full.png)

La segunda captura muestra la ejecucion completa en formato expandido. Ahi se ve
el orden de los pasos:

1. Inicio de `analyze-repo`.
2. Primera generacion del LLM.
3. Consulta a memoria con `read_memory`.
4. Listado del repositorio con `list_files`.
5. Lecturas de archivos con `read_file`.
6. Recuperacion RAG con `retrieve`.
7. Generacion de embeddings con `OpenAI-embedding`.
8. Registro de fuentes con `submit_research_result`.
9. Escritura del reporte con `write_file`.
10. Ejecucion del check con `execute_command`.
11. Lectura del reporte por el Reviewer.
12. Nueva inspeccion del repositorio.
13. Registro del veredicto final con `submit_review_result`.
14. Fin de la traza.

Esta captura sirve para mostrar que la observabilidad permite reconstruir el
camino completo del agente, incluyendo decisiones intermedias y tools usadas.

## Captura 3: timeline de la ejecucion

![Timeline de la ejecucion](assets/trace-timeline.png)

La tercera captura muestra la linea de tiempo de la traza. La ejecucion completa
duro aproximadamente:

```text
37.08 segundos
```

Tambien se observa el costo aproximado informado por Langfuse:

```text
USD 0.082283
```

En el timeline se ve que la mayor parte del tiempo se concentra en generaciones
del modelo OpenAI, mientras que las tools locales (`read_file`, `list_files`,
`write_file`, `execute_command`) son muy rapidas. La llamada `retrieve` incluye
una generacion de embedding asociada, necesaria para consultar la base RAG.

## Metricas principales del trace

Del JSON exportado se obtuvieron las siguientes metricas:

| Metrica | Valor |
|---|---:|
| Observaciones totales | 32 |
| Agentes raiz | 1 |
| Generaciones OpenAI | 16 |
| Tools ejecutadas | 14 |
| Embeddings OpenAI | 1 |
| Duracion total | 37.075 s |
| Tokens totales aproximados | 27.959 |
| Costo total aproximado | USD 0.082283 |

Distribucion por nombre de observacion:

| Observacion | Cantidad |
|---|---:|
| `OpenAI-generation` | 16 |
| `read_file` | 6 |
| `list_files` | 2 |
| `read_memory` | 1 |
| `retrieve` | 1 |
| `OpenAI-embedding` | 1 |
| `submit_research_result` | 1 |
| `write_file` | 1 |
| `execute_command` | 1 |
| `submit_review_result` | 1 |
| `analyze-repo` | 1 |

## Que evidencia aporta la traza

La traza permite demostrar que el sistema ejecuto el flujo multiagente completo.
No solo hubo una llamada al LLM, sino una secuencia observable de generaciones y
tools.

La evidencia mas importante es:

- El Explorer consulto memoria, listo archivos y leyo archivos clave.
- El Researcher ejecuto `retrieve` y genero un embedding para consultar RAG.
- El Researcher registro su resultado con `submit_research_result`.
- El Implementer escribio `REPORTE-ANALISIS.md` usando `write_file`.
- El Tester ejecuto un comando real con `execute_command`.
- El Reviewer leyo el reporte, contrasto archivos y registro observaciones con
  `submit_review_result`.

## Resultado del Reviewer observado en la traza

La traza registra que el Reviewer termino con el veredicto:

```text
El reporte es incompleto.
```

Las observaciones principales fueron:

- El reporte cubria estructura del repositorio, pero no profundizaba en
  arquitectura.
- Las dependencias estaban correctamente alineadas con `pyproject.toml`.
- Faltaban comandos especificos de uso o desarrollo.
- No se mencionaban riesgos potenciales.
- Los checks relevantes como `flake8` y `pytest` estaban implicitos, pero no
  suficientemente analizados en el reporte.

Este punto es valioso porque muestra que la observabilidad no solo permite ver
que el sistema corrio, sino tambien detectar limitaciones del resultado final.

## Conclusion

La traza de Langfuse demuestra una ejecucion completa del caso de uso
`analyze-repo`. La herramienta de observabilidad permite ver el grafo de pasos,
el timeline, las llamadas al LLM, las tools ejecutadas, el uso de embeddings, el
costo aproximado y el resultado de la revision final.

Con esta evidencia se cumple el punto 7 del trabajo: hay capturas de pantalla de
la herramienta de observabilidad y una traza completa de ejecucion que permite
auditar el comportamiento del agente.
