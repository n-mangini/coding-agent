# Reflexion para el cierre

Este documento junta material para armar la seccion final del trabajo: que
funciono, que fallo, que senales aparecieron durante las pruebas y que mejoras
quedarian para una iteracion posterior.

## Que funciono

### Arquitectura por subagentes

La separacion en Explorer, Researcher, Implementer, Tester y Reviewer termino
siendo una buena forma de controlar responsabilidades. Cada subagente tiene un
`tool_map` chico y un prompt especifico, entonces el orquestador puede componer
el flujo sin darle a todos las mismas capacidades.

Lo mas importante fue que el sistema dejo de ser un unico agente con todas las
tools disponibles y paso a tener roles acotados:

- Explorer: lectura del repo y memoria del proyecto.
- Researcher: evidencia externa con RAG primero y web como fallback.
- Implementer: escritura del reporte final en un unico path permitido.
- Tester: ejecucion de un check real por allowlist.
- Reviewer: lectura y validacion final del reporte.

Esa division hizo mas facil razonar sobre seguridad, errores y trazabilidad.

### Estado compartido

`TaskState` sirvio como punto de coordinacion entre pasos. En lugar de que cada
subagente dependa implicitamente del historial conversacional anterior, el
orquestador guarda resultados, fuentes, archivos modificados, observaciones,
eventos de loop y faltas de evidencia en una estructura explicita.

Esto ayudo especialmente en tres lugares:

- El Researcher registra fuentes estructuradas.
- El Tester deja su resultado para que el Reviewer lo considere.
- El reporte final puede mostrar observaciones y falta de evidencia sin depender
  de que el modelo las recuerde.

### Tools acotadas

Las tools con mayor riesgo quedaron envueltas por permisos mas especificos:

- `write_file` del Implementer solo puede escribir `REPORTE-ANALISIS.md`.
- `execute_command` del Tester existe como tool, pero solo acepta comandos de
  `ALLOWED_TEST_COMMANDS`.
- Las policies globales siguen validando antes de ejecutar tools.

El e2e de la issue #5 valido esta idea: el Tester rechazo un comando no
permitido (`rm -rf .`) y ejecuto solo el check esperado.

### Validacion e2e

Las pruebas end-to-end fueron utiles para descubrir problemas que no aparecian
en lectura estatica. Por ejemplo, la primera version del Tester usaba
`python -m compileall ...`; en este entorno el ejecutable `python` no existia en
el `PATH`, asi que el check fallo. Cambiarlo a `python3 -m compileall ...`
resolvio el problema y dejo una validacion mas compatible con el entorno real.

El e2e final ejecuto el flujo completo:

```text
Explorer -> Researcher -> Implementer -> Tester -> Reviewer
```

y el reporte final incluyo `Checks (Tester)` con resultado exitoso.

## Que fallo o costo mas

### Dependencia de servicios externos

Los e2e dependen de OpenAI y Tavily. Eso hizo que algunas validaciones fallaran
por causas externas al codigo:

- key de OpenAI incorrecta o sin cuota;
- `.env` no disponible en la worktree donde se estaba probando;
- Tavily configurado o no segun el entorno.

La conclusion es que el sistema necesita una capa mas clara de smoke tests
locales/fake para validar wiring sin depender siempre de APIs externas, y dejar
los e2e reales para checkpoints puntuales.

### RAG sin indice

El flujo de Researcher funciono, pero varias pruebas devolvieron:

```text
Sin resultados en el indice RAG
```

Eso no es un error del codigo, sino una falta de preparacion del indice. El
comportamiento correcto fue reconocer la falta de evidencia y usar web como
fallback cuando habia Tavily. Aun asi, para una demo o cierre conviene remarcar
que RAG requiere ingestion previa:

```bash
python -m rag.ingest <path>
```

Sin esa etapa, el sistema debe ser honesto: no puede inventar evidencia local que
no esta indexada.

### Formato de cierre de issues

La PR #17 quedo vinculada con `Refs #5`, pero eso no cierra automaticamente una
issue en GitHub. Para que GitHub cierre la issue al mergear, el body de la PR
debe usar `Closes #5`, `Fixes #5` o `Resolves #5`.

Este fue un fallo de proceso, no de implementacion. La issue se cerro despues de
forma manual.

## Loops detectados

Se agrego deteccion de loops en el harness para identificar tool calls
repetidas. La idea es registrar eventos cuando el agente insiste con la misma
accion sin avanzar, y escalar con intervenciones:

1. primero inyecta una senal para replantear;
2. si persiste, corta el ciclo y deja una observacion.

Durante las pruebas de cierre no aparecio un loop bloqueante en el flujo final,
pero la instrumentacion es relevante porque el patron es esperable en agentes
con tools: el modelo puede quedar atrapado leyendo el mismo archivo, repitiendo
la misma busqueda o intentando el mismo comando despues de un error.

Lo valioso es que esos eventos no quedan invisibles: `Subagent.run` los registra
en `TaskState.observations`, y el reporte puede exponerlos como parte del
resultado.

## Falta de evidencia detectada

El caso mas claro fue Researcher + RAG:

- Si el indice Chroma esta vacio, `retrieve` devuelve explicitamente que no hay
  resultados.
- Si la web no aporta evidencia especifica del repo analizado, el Researcher
  debe decirlo en vez de completar con suposiciones.
- `TaskState.missing_evidence` separa esas faltas de evidencia de las
  observaciones generales.

Esta separacion es importante para el cierre porque muestra una decision de
diseno: el agente no solo produce respuestas, tambien debe declarar que no pudo
verificar algo cuando corresponde.

## Mejoras posibles

### Tests locales sin LLM

Agregar tests unitarios o smoke tests que no llamen a OpenAI permitiria validar:

- wiring de subagentes;
- allowlists;
- parseo de fuentes y observaciones estructuradas;
- persistencia de memoria JSON;
- degradacion de RAG/Tavily cuando faltan dependencias o keys.

Esto reduciria costo y fragilidad de validacion.

### Comandos de Tester configurables

Hoy el Tester tiene un comando inicial hardcodeado:

```bash
python3 -m compileall .
```

Es seguro y suficiente para el TP, pero podria evolucionar a una lista
configurable en `agent.config.yaml`, manteniendo allowlist estricta y evitando
que el modelo elija comandos libremente.

### Mejor preparacion del RAG

Para que Researcher sea mas util, el flujo podria incluir una etapa explicita de
ingestion o una advertencia mas visible cuando `rag_store` esta vacio. Tambien
podria documentarse una receta de demo:

```bash
python -m rag.ingest docs README.md CLAUDE.md
python analyze.py "Analiza este repo"
```

### Mejor cierre automatico de issues

Estandarizar templates de PR con `Closes #N` evitaria issues abiertas despues de
mergear. Esto puede quedar como convencion en el doc de issue tracker.

### Reportes mas deterministas

El reporte final depende del texto generado por LLM. Para hacerlo mas
determinista, se podria:

- fijar secciones obligatorias;
- pasarle al Implementer un esquema mas estricto;
- exigir que cada afirmacion relevante tenga fuente local, RAG o web;
- hacer que Reviewer marque explicitamente afirmaciones sin evidencia.

## Ejecucion de agentes en paralelo

Para cerrar tres issues a la vez (#7 memoria + contexto, #8 RAG con Chroma, #4
Implementer + Reviewer) se lanzaron tres agentes en paralelo, cada uno en su
propio git worktree aislado sobre `main`, con la consigna de crear su rama,
implementar y abrir la PR. El resultado fueron tres PRs:

- #4 -> PR #14 (`feat/issue-4-implementer-reviewer`)
- #8 -> PR #15 (`feat/issue-8-rag-chroma`)
- #7 -> PR #16 (rama del worktree, ver abajo)

### Que funciono

- El aislamiento por worktree permitio que los tres agentes tocaran archivos
  compartidos (`factory.py`, `orchestrator.py`, `CLAUDE.md`) sin pisarse entre
  si durante el desarrollo.
- Cada agente respeto las convenciones del repo: commits atomicos con trailer
  `Co-Authored-By`, `Closes #N` en el body, y actualizacion de `CLAUDE.md` en el
  mismo cambio.

### Que costo o quedo pendiente

- **Conflictos de merge esperables:** al tocar los tres el mismo trio de
  archivos, el aislamiento resuelve el desarrollo pero no la integracion. Hay que
  mergear de a uno y rebasear los siguientes.
- **Colision de nombre de rama:** el agente de #7 no pudo usar
  `feat/issue-7-memoria-contexto` porque el nombre ya estaba tomado, y la PR #16
  salio desde la rama del worktree. Conviene renombrar antes de mergear si se
  quiere un nombre prolijo.
- **Verificacion limitada:** los worktrees no tenian las dependencias instaladas
  (`openai`, `chromadb`, etc.), asi que la validacion fue de imports/parseo y
  logica pura, no ejecucion end-to-end contra la API real. Esto refuerza la
  mejora ya listada de tener smoke tests locales sin LLM.

## Sintesis para usar en el cierre

El trabajo mostro que una arquitectura multiagente con estado compartido permite
controlar mejor el flujo que un agente unico con todas las tools. Funcionaron
bien la division por roles, las tools acotadas, la memoria persistente, el RAG
con fallback y la validacion con Tester. Lo que mas costo fue la dependencia de
servicios externos para e2e y la necesidad de preparar correctamente el entorno
(`.env`, cuotas, Tavily, indice RAG). Tambien aparecio una mejora de proceso:
usar palabras de cierre automatico en PRs para no dejar issues abiertas.

La decision mas importante fue hacer explicitas las limitaciones: si no hay
evidencia en RAG o web, el sistema debe decirlo; si un check falla, no debe
romper todo el pipeline, sino registrar la observacion para que el Reviewer y el
reporte final la tengan en cuenta.
