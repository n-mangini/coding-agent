# 2. Instalacion, configuracion y ejecucion

Este documento describe como instalar, configurar y ejecutar el proyecto
`coding-agent`, un agente de coding con una capa multiagente para analizar
repositorios y generar reportes tecnicos.

## Requisitos previos

- Python 3.10 o superior.
- Git, si se quiere clonar repositorios externos con `--clone`.
- Una API key de OpenAI para ejecutar el agente.
- Opcionalmente, una API key de Tavily para habilitar busqueda web.
- Opcionalmente, credenciales de Langfuse para observabilidad.

## Instalacion

Desde la raiz del proyecto:

```bash
python -m venv .venv
```

Activar el entorno virtual.

En Linux/macOS:

```bash
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Las dependencias principales son:

- `openai`: llamadas al modelo LLM y embeddings.
- `tavily-python`: busqueda web opcional.
- `python-dotenv`: carga de variables desde `.env`.
- `PyYAML`: lectura de `agent.config.yaml`.
- `langfuse`: observabilidad opcional.
- `chromadb`: almacenamiento vectorial para RAG.

## Configuracion

Copiar el archivo de ejemplo:

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Editar `.env` y completar las variables necesarias:

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
OPENAI_MODEL=gpt-4o
AGENT_WORKSPACE=./workspace
RAG_PERSIST_DIR=./rag_store
```

`OPENAI_API_KEY` es obligatoria. Si no esta configurada, el programa la pide por
consola al iniciar.

`TAVILY_API_KEY` es opcional. Si falta, la tool `web_search` queda deshabilitada
mediante un stub que informa que no esta disponible.

`OPENAI_MODEL` es opcional. Si no se define, el proyecto usa el modelo por
defecto configurado en `agent/llm.py`.

`AGENT_WORKSPACE` define donde se clonan los repositorios externos. Por defecto
usa `./workspace`.

`RAG_PERSIST_DIR` define donde se guarda el indice persistente de Chroma para
RAG. Por defecto usa `./rag_store`.

Para observabilidad con Langfuse se pueden configurar:

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Si estas variables no estan presentes, la instrumentacion degrada a no-op y el
agente funciona igual, pero sin trazas externas.

## Configuracion de politicas

El archivo `agent.config.yaml` define restricciones para las tools:

- `read`: rutas permitidas o denegadas para lectura.
- `write`: rutas permitidas o denegadas para escritura.
- `commands`: comandos permitidos o denegados.
- `approval`: tools que requieren confirmacion humana cuando la supervision esta
  activa.

Por defecto se bloquean archivos sensibles como `.env`, carpetas `.git` y
comandos peligrosos como `rm -rf`, `sudo`, `shutdown` o `mkfs`.

## Ejecucion del chat interactivo

Para iniciar el agente en modo chat sobre el directorio actual:

```bash
python main.py
```

Comandos disponibles dentro del chat:

```text
/plan on
/plan off
/plan status
/supervise on
/supervise off
/supervise status
exit
```

`/plan on` activa el modo planificacion: antes de ejecutar, el agente propone un
plan y espera aprobacion.

`/supervise on` activa supervision humana para tools sensibles, como escritura
de archivos o ejecucion de comandos.

Tambien se puede clonar un repositorio y empezar el chat dentro de ese proyecto:

```bash
python main.py --clone https://github.com/usuario/repositorio.git
```

## Ejecucion del caso de uso multiagente

El entregable principal del TP se ejecuta con `analyze.py`. Este entry point arma
el orquestador multiagente y ejecuta la secuencia:

```text
Explorer -> Researcher -> Implementer -> Tester -> Reviewer
```

Para analizar el repositorio actual:

```bash
python analyze.py
```

Para indicar un foco especifico:

```bash
python analyze.py "Analiza la arquitectura, dependencias y riesgos principales"
```

Para clonar y analizar un repositorio externo:

```bash
python analyze.py --clone https://github.com/usuario/repositorio.git
```

El resultado se imprime por consola y el reporte generado se persiste en:

```text
REPORTE-ANALISIS.md
```

## Ingesta y uso de RAG

El sistema incluye una base RAG local con Chroma. Antes de esperar resultados de
`retrieve`, hay que poblar el indice.

Ejemplo para ingestar la documentacion del proyecto:

```bash
python -m rag.ingest docs
```

Ejemplo para ingestar un archivo puntual:

```bash
python -m rag.ingest README.md
```

La ingesta:

1. Recorre archivos de texto conocidos.
2. Divide el contenido en chunks de 1000 caracteres con 200 de solapamiento.
3. Genera embeddings con `text-embedding-3-small`.
4. Guarda los vectores en Chroma dentro de `RAG_PERSIST_DIR`.

Durante el analisis, el subagente Researcher consulta primero `retrieve`. Solo si
RAG no alcanza, usa `web_search` como fallback.

## Ejecucion de tareas demo

El proyecto incluye `run_tests.py`, que ejecuta una bateria de tareas de ejemplo
end-to-end contra el agente.

```bash
python run_tests.py
```

Tambien puede ejecutarse sobre un repositorio clonado:

```bash
python run_tests.py --clone https://github.com/usuario/repositorio.git
```

Estas tareas hacen llamadas reales al LLM y pueden escribir archivos o ejecutar
comandos en el directorio de trabajo, por lo que conviene revisar la configuracion
de supervision y politicas antes de correrlas.

## Verificacion rapida

Para validar que los modulos principales compilan:

```bash
python -m compileall agent rag analyze.py main.py run_tests.py repo.py
```

Este es el mismo tipo de check acotado que ejecuta el subagente Tester dentro del
flujo multiagente.

