# Guia de referencia para analizar repositorios Python

Esta guia sirve como base RAG para que el agente razone sobre repositorios del
ecosistema Python. No reemplaza la documentacion oficial ni el analisis directo
del repo: orienta que buscar, que comandos considerar y que riesgos reportar.

## Objetivo del agente especializado

El agente esta orientado a analizar repositorios Python y generar reportes sobre:

- arquitectura y separacion de responsabilidades;
- dependencias y packaging;
- comandos relevantes de instalacion, testing, linting y ejecucion;
- riesgos tecnicos;
- evidencia disponible y faltante;
- checks basicos ejecutables por el Tester.

## Senales de que un repo es Python

Archivos habituales:

- `pyproject.toml`: configuracion moderna de packaging, build backend,
  dependencias, entrypoints y configuracion de herramientas.
- `requirements.txt`: lista historica/simple de dependencias para `pip`.
- `setup.py` o `setup.cfg`: packaging con setuptools en proyectos existentes.
- `tox.ini`, `noxfile.py`: matrices de test o automatizacion.
- `pytest.ini`, `conftest.py`, `tests/`: convenciones de pytest.
- `.pre-commit-config.yaml`: hooks de formato, lint y checks.
- `src/`: layout recomendado para paquetes instalables.
- `<package>/__init__.py`: paquete Python importable.

## Packaging y dependencias

Priorizar `pyproject.toml` cuando exista. Revisar:

- `[build-system]`: backend (`setuptools`, `hatchling`, `poetry-core`, etc.).
- `[project]`: nombre, version, descripcion, requires-python y dependencias.
- `[project.optional-dependencies]`: extras como `dev`, `test`, `docs`.
- `[project.scripts]`: comandos CLI instalables.
- secciones `[tool.*]`: configuracion de pytest, ruff, black, mypy, coverage,
  hatch, poetry u otras herramientas.

Si solo existe `requirements.txt`, identificar:

- dependencias runtime;
- dependencias de desarrollo mezcladas con runtime;
- versiones pinneadas o abiertas;
- ausencia de metadata del paquete.

Riesgos frecuentes:

- falta de `requires-python`;
- dependencias sin version en proyectos productivos;
- lockfiles ausentes cuando el proyecto espera reproducibilidad;
- mezcla de dependencias runtime/dev sin separacion;
- scripts documentados que no coinciden con archivos reales.

## Arquitectura

Al analizar estructura, distinguir:

- entrypoints: `main.py`, `cli.py`, scripts definidos en `pyproject.toml`;
- dominio: paquetes con logica de negocio;
- infraestructura: clientes externos, DB, filesystem, HTTP, colas;
- configuracion: lectura de env vars, archivos YAML/TOML/JSON;
- tests: unitarios, integracion, fixtures y datos de prueba;
- docs: README, ADRs, guias operativas.

Buenas senales:

- imports claros y sin ciclos obvios;
- un unico borde para APIs externas importantes;
- funciones con responsabilidades acotadas;
- configuracion centralizada;
- tests que cubren comportamiento de usuario o contratos publicos;
- documentacion que coincide con comandos existentes.

Alertas:

- entrypoints con mucha logica mezclada;
- `subprocess` o filesystem sin validacion;
- secretos leidos o impresos accidentalmente;
- paths relativos ambiguos;
- codigo que depende de cwd sin documentarlo;
- tests que requieren servicios externos sin fallback.

## Testing y checks

Comandos comunes a buscar antes de proponer ejecucion:

```bash
python3 -m compileall <paths>
python3 -m pytest
python3 -m unittest
python3 -m ruff check .
python3 -m black --check .
python3 -m mypy .
python3 -m coverage run -m pytest
```

El Tester debe ejecutar solamente comandos permitidos por allowlist o por
configuracion explicita. Para un smoke test conservador, `compileall` es util
porque valida sintaxis/importabilidad basica sin correr tests que puedan hacer
I/O, red o cambios de estado.

Si un check falla, el agente no debe inventar una causa. Debe reportar:

- comando ejecutado;
- codigo de salida si esta disponible;
- stdout/stderr relevante;
- hipotesis marcada como inferencia;
- siguiente paso recomendado.

## RAG primero, web despues

El Researcher debe consultar primero el indice RAG. Si el indice no tiene
evidencia suficiente, puede usar web como fallback. En el reporte, diferenciar:

- evidencia del repo analizado;
- memoria persistente del proyecto;
- fragmentos recuperados por RAG;
- resultados web;
- inferencias propias.

Si no hay evidencia, decirlo explicitamente. No completar huecos con
conocimiento general sin marcarlo como inferencia.

## Repositorios de referencia para especializacion

Estos repos no tienen que estar copiados dentro del proyecto. Pueden usarse como
fuentes para clonar snapshots, estudiar convenciones o preparar resumenes
propios para RAG.

### PyPA sampleproject

URL: https://github.com/pypa/sampleproject

Uso recomendado: ejemplo chico para packaging moderno y metadata de proyecto.
Sirve para ver `pyproject.toml`, estructura minima de paquete, extras y scripts.

### pytest

URL: https://github.com/pytest-dev/pytest

Uso recomendado: referencia de testing Python, fixtures, convenciones de tests y
proyecto maduro con tooling. Es grande, asi que conviene ingestar docs o
fragmentos seleccionados antes que todo el repo.

### Flask

URL: https://github.com/pallets/flask

Uso recomendado: framework web liviano. Sirve para reconocer estructura de app
web Python, dependencias WSGI, extensibilidad y documentacion de proyecto.

### Django

URL: https://github.com/django/django

Uso recomendado: framework web grande y maduro. Sirve para estudiar layout de
monorepo Python, tests extensos, documentacion y convenciones de contribucion.
Por tamano, se recomienda ingestar secciones elegidas.

### FastAPI

URL: https://github.com/fastapi/fastapi

Uso recomendado: framework API moderno basado en type hints. Sirve para analizar
repos que usan ASGI, validacion de datos, OpenAPI y tooling moderno.

## Estrategia practica de ingesta

Para una demo simple:

```bash
python -m rag.ingest rag/sources/python
```

Para reforzar con repos de referencia:

```bash
mkdir -p workspace/reference-python
git clone --depth 1 https://github.com/pypa/sampleproject workspace/reference-python/sampleproject
git clone --depth 1 https://github.com/pallets/flask workspace/reference-python/flask
python -m rag.ingest workspace/reference-python/sampleproject
python -m rag.ingest workspace/reference-python/flask/docs
```

No conviene ingestar repos enormes completos sin filtro. Aumenta ruido,
latencia, costo de embeddings y resultados poco especificos.

## Criterio para el reporte final

Un buen reporte de repo Python deberia incluir:

- que tipo de proyecto es;
- entrypoints principales;
- dependencias y comandos;
- estructura de paquetes;
- estrategia de testing;
- riesgos o faltantes;
- fuentes usadas;
- resultado del check del Tester;
- falta de evidencia cuando aplique.
