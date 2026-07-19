# Fuentes RAG: ecosistema Python

Esta carpeta contiene material de referencia para especializar el agente en el
ecosistema Python. La idea es que el RAG tenga una base tecnica propia antes de
analizar repositorios Python, en vez de depender solamente de busqueda web.

## Ingesta recomendada

Desde la raiz del proyecto:

```bash
python -m rag.ingest rag/sources/python
```

Despues se puede correr el analisis normalmente:

```bash
python analyze.py --clone https://github.com/OWNER/REPO.git \
  "Analiza arquitectura, dependencias, comandos y riesgos de este repo Python"
```

O usar el modo automatico, que ingesta esta carpeta antes de clonar:

```bash
python analyze.py --python https://github.com/OWNER/REPO.git \
  "Analiza arquitectura, dependencias, comandos y riesgos de este repo Python"
```

## Que contiene

- `python-ecosystem-guide.md`: criterios para analizar proyectos Python,
  convenciones esperadas, comandos frecuentes y repositorios de referencia.

## Como extenderlo

Para reforzar la especializacion, se pueden agregar mas archivos Markdown con:

- notas sobre packaging moderno (`pyproject.toml`, build backends, metadata);
- convenciones de testing (`pytest`, fixtures, estructura de tests);
- frameworks concretos usados por el caso de uso elegido;
- ejemplos resumidos de repositorios Python de referencia;
- decisiones tomadas durante ejecuciones anteriores.

Evitar copiar documentacion completa de terceros. Es preferible escribir
resumenes propios, citar URLs fuente y, si se necesita mas detalle, ingestar un
snapshot local controlado de documentacion o repositorios de referencia.
