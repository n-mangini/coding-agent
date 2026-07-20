# 8. Reflexion breve

## Que funciono bien

### Separacion por subagentes

La arquitectura multiagente funciono bien porque permitio separar
responsabilidades. En lugar de tener un unico agente con todas las herramientas,
el sistema divide la tarea entre subagentes especializados:

- `Explorer`: explora el repositorio y detecta estructura, dependencias y
  convenciones.
- `Researcher`: busca evidencia adicional con estrategia RAG-first y fallback
  web.
- `Implementer`: redacta y guarda el reporte final.
- `Tester`: ejecuta una validacion tecnica acotada.
- `Reviewer`: revisa si el reporte responde al pedido original.

Esta division hizo mas facil controlar permisos, razonar sobre errores y revisar
que cada parte del flujo cumpliera un objetivo concreto.

### Estado compartido explicito

`TaskState` fue una pieza central. Permitio que el orquestador y los subagentes
compartan informacion sin depender solamente del historial conversacional del
LLM.

En el estado se registran:

- pedido original;
- progreso de la tarea;
- resultados por subagente;
- fuentes recuperadas;
- archivos modificados;
- observaciones;
- faltas de evidencia.

Esto ayudo a que el reporte final pudiera incluir fuentes, checks, observaciones
del Reviewer y faltas de evidencia de forma explicita.

### Tools acotadas y politicas

Tambien funciono bien limitar las herramientas segun el rol de cada subagente.
Por ejemplo:

- el Implementer solo puede escribir `REPORTE-ANALISIS.md`;
- el Tester solo puede ejecutar comandos incluidos en una allowlist;
- las policies globales validan cada tool call antes de ejecutarla.

Esto redujo el riesgo de acciones no deseadas, especialmente en escritura de
archivos y ejecucion de comandos.

### RAG con fallback

La estrategia RAG-first fue util como criterio de evidencia. El Researcher debe
consultar primero la base local con `retrieve` y solo usar `web_search` si la
evidencia recuperada no alcanza.

Este orden hace que el sistema priorice fuentes propias del proyecto y reduzca
respuestas basadas solamente en inferencia.

### Observabilidad

La integracion con Langfuse tambien fue valiosa. Cuando esta configurada, permite
ver trazas completas de ejecucion, llamadas al LLM, llamadas a tools, entradas,
salidas, errores y latencias. Esto facilita entender que hizo el agente en cada
paso y justificar el comportamiento observado.

## Que fallo o costo mas

### Dependencia de servicios externos

Una dificultad importante fue que las pruebas end-to-end dependen de servicios
externos como OpenAI y Tavily. Eso puede generar fallos que no dependen del
codigo del proyecto, por ejemplo:

- falta de cuota;
- `.env` mal configurado;
- Tavily no disponible;
- diferencias entre entornos de ejecucion. (Windows)

Esto mostro que conviene separar mejor las pruebas locales de las pruebas reales
contra APIs externas.

### RAG requiere ingesta previa

Otro punto importante fue que RAG no funciona magicamente si antes no se poblo el
indice. Cuando el indice Chroma esta vacio, `retrieve` devuelve que no hay
resultados.

Eso no es un error del sistema, pero si es una condicion que debe estar clara en
la instalacion y en la demo:

```bash
python -m rag.ingest docs
```

Sin esa ingesta previa, el sistema debe reconocer que no tiene evidencia local
suficiente.

### Validacion limitada por entorno

El Tester ejecuta un check acotado con `compileall`. Esto sirve para detectar
errores basicos de sintaxis o importacion, pero no reemplaza una suite completa
de tests. Es una validacion util para el TP, aunque limitada.

Ademas, en algunas pruebas aparecieron diferencias de entorno, por ejemplo el
uso de `python` versus `python3`. Eso obligo a ajustar el comando permitido para
que funcionara en el entorno real.

## Falta de evidencia detectada

La falta de evidencia aparecio principalmente en el flujo de RAG:

- si el indice Chroma esta vacio, no hay chunks para recuperar;
- si `TAVILY_API_KEY` no esta configurada, no hay fallback web real;
- si ni RAG ni web aportan datos suficientes, el sistema debe marcarlo como
  falta de evidencia.

Esta decision es importante: el agente no deberia inventar informacion para
completar una respuesta. Si no puede verificar algo, debe decirlo explicitamente.

Para eso existe el campo:

```text
TaskState.missing_evidence
```

Separar la falta de evidencia de las observaciones generales ayuda a que el
reporte final sea mas honesto y auditable.

## Que mejoraria del sistema

### Tests locales sin LLM

Agregaria tests locales que no dependan de OpenAI ni Tavily. Servirian para
validar:

- wiring de subagentes;
- allowlists del Tester;
- restricciones del Implementer;
- parseo de fuentes del Researcher;
- observaciones del Reviewer;
- persistencia de memoria;
- degradacion cuando RAG o web no estan disponibles.

Esto reduciria costo, tiempo y fragilidad en las pruebas.

### Ingesta RAG mas guiada

Mejoraria la experiencia de RAG agregando una advertencia mas visible cuando el
indice esta vacio, o incluso un comando de preparacion de demo que ingeste las
fuentes principales:

```bash
python -m rag.ingest docs
python -m rag.ingest README.md
python -m rag.ingest CLAUDE.md
```

Tambien podria agregarse una etapa opcional en el flujo para sugerir ingesta
cuando no hay evidencia local.

### Tester mas configurable

El Tester hoy usa un comando permitido hardcodeado. Para una version posterior,
se podria mover la allowlist a `agent.config.yaml`, manteniendo el mismo criterio
de seguridad pero permitiendo adaptar el check segun el proyecto.

### Reportes mas deterministas

El reporte final depende de generacion LLM. Para hacerlo mas consistente, se
podria exigir un esquema mas estricto:

- secciones obligatorias;
- fuentes por afirmacion relevante;
- tabla de evidencias;
- veredicto final del Reviewer;
- lista separada de inferencias y faltas de evidencia.

## Sintesis final

El sistema funciono mejor cuando las responsabilidades quedaron explicitas:
orquestador para coordinar, subagentes para ejecutar roles concretos, `TaskState`
para compartir informacion, policies para limitar acciones y RAG para recuperar
evidencia local.

Lo que mas costo fue la dependencia de servicios externos, la preparacion previa
del indice RAG y la necesidad de validar en entornos distintos. La mejora mas
importante seria agregar pruebas locales sin LLM y una preparacion de RAG mas
guiada.

