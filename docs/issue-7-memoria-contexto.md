# Issue #7 — Memoria y manejo de contexto

## Objetivo

Agregar memoria persistente por proyecto, reducir el historial enviado al LLM
en conversaciones largas y detectar loops de tools para cambiar de estrategia o
detenerse con una falta de avance explícita.

## Cambios

- `agent/memory.py` agrega `ProjectMemory`, persistida en `.agent_memory.json`
  dentro del repo analizado, con categorías estables y deduplicación.
- `read_memory` y `remember` se exponen como tools cerradas sobre una misma
  instancia de memoria, compartida por el orquestador y sus subagentes.
- El Explorer consulta la memoria al comenzar y guarda hallazgos estables
  (arquitectura, dependencias, comandos, convenciones).
- `Harness.run_conversation` resume el historial cuando supera `HISTORY_LIMIT`,
  conservando el system prompt y una cola reciente válida para la API.
- `detect_loop` identifica tool calls idénticas consecutivas; el primer loop
  inyecta un replanteo y el segundo detiene la corrida pidiendo ayuda.
- Las intervenciones de loop quedan en `Harness.loop_events`; `Subagent.run` las
  registra en `TaskState.observations` para que sean visibles en el reporte.
- `TaskState` separa `missing_evidence` de observaciones generales y el reporte
  renderiza una sección dedicada de falta de evidencia.

## Verificación sugerida

- Importar `agent.harness.detect_loop` y probar que tres firmas iguales devuelven
  `True`, mientras que firmas distintas o menos de tres devuelven `False`.
- Ejecutar `analyze.py "Analizá este repo"` y verificar que se crea
  `.agent_memory.json`, que el Explorer puede leerlo en una segunda corrida y
  que el reporte conserva observaciones/faltas de evidencia.
- Forzar un subagente a repetir la misma tool call para comprobar que el primer
  evento replantea y el segundo detiene la ejecución.
