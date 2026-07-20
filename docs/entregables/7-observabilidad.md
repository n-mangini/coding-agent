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
Analiza arquitectura, dependencias, riesgos y comandos
```

Esta nueva traza es mas completa para la consigna porque incluye tanto
recuperacion RAG como busqueda web.

## Captura 1: vista resumida de la traza

![Vista resumida de la traza](assets/trace-graph-summary.png)

En esta captura se observa la traza completa como un grafo resumido. El nodo raiz
es `analyze-repo`, que representa la ejecucion completa del caso de uso. Debajo
aparecen las llamadas al modelo y las tools utilizadas.

Elementos visibles:

- `_start_`: inicio de la ejecucion.
- `analyze-repo`: traza raiz del caso de uso.
- `OpenAI-generation`: llamadas al LLM.
- `read_memory`: consulta de memoria persistente.
- `list_files`: exploracion de archivos.
- `read_file`: lectura de archivos relevantes.
- `retrieve`: recuperacion desde la base RAG.
- `OpenAI-embedding`: embedding usado para consultar RAG.
- `web_search`: busqueda web como fallback o complemento.
- `submit_research_result`: registro estructurado del resultado del Researcher.
- `write_file`: escritura del reporte.
- `execute_command`: check tecnico ejecutado por el Tester.
- `submit_review_result`: registro de observaciones del Reviewer.
- `_end_`: fin de la ejecucion.

Esta vista permite comprobar que el flujo no fue una respuesta directa del LLM:
hubo exploracion del repositorio, recuperacion RAG, busqueda web, escritura de
archivo, ejecucion de comandos y revision final.

## Captura 2: grafo completo de ejecucion

![Grafo completo de ejecucion](assets/trace-graph-full.png)

La segunda captura muestra la ejecucion expandida. Ahi se ve el orden real de las
iteraciones entre generaciones del LLM y tools.

Secuencia observada:

1. Inicio de `analyze-repo`.
2. Generacion inicial del LLM.
3. Consulta a memoria con `read_memory`.
4. Listado del repositorio con `list_files`.
5. Lecturas de archivos clave con `read_file`.
6. Recuperacion RAG con `retrieve`.
7. Generacion de embedding con `OpenAI-embedding`.
8. Busqueda web con `web_search`.
9. Registro del resultado de investigacion con `submit_research_result`.
10. Escritura del reporte con `write_file`.
11. Ejecucion del check con `execute_command`.
12. Lecturas y listados adicionales realizados por el Reviewer.
13. Registro del veredicto final con `submit_review_result`.
14. Cierre de la traza.

Esta captura muestra las iteraciones del agente: el LLM decide una accion,
invoca una tool, recibe el resultado y continua con la siguiente decision.

## Captura 3: timeline de la ejecucion

![Timeline de la ejecucion](assets/trace-timeline.png)

La tercera captura muestra la traza en formato timeline. Esta vista permite ver
cuanto tarda cada paso y como se distribuyen las llamadas durante la ejecucion.

La linea de tiempo muestra que las tools locales, como `read_file`, `list_files`,
`write_file` y `execute_command`, son muy rapidas. En cambio, la mayor parte del
tiempo y del costo se concentra en las generaciones `OpenAI-generation`. Tambien
se observa la llamada `OpenAI-embedding` asociada a `retrieve`, que corresponde a
la consulta sobre la base RAG.

