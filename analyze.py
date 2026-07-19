"""Caso de uso: analizar un repositorio y producir un mini-reporte.

Corre el sistema multi-agente (orquestador + subagentes) sobre el directorio
actual, sobre un repo clonado con --clone, o sobre un repo Python con RAG
especializado cargado automaticamente con --python.

Uso:
    python analyze.py                          # analiza el directorio actual
    python analyze.py --clone URL              # clona un repo y lo analiza
    python analyze.py --python URL             # ingesta RAG Python, clona y analiza
    python analyze.py "foco del análisis"      # pedido específico
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from agent.factory import build_orchestrator
from repo import clone_repo
from rag.ingest import ingest_path
from rag.store import make_rag_store

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_RAG_SOURCES = PROJECT_ROOT / "rag" / "sources" / "python"
DEFAULT_REQUEST = "Analizá este repositorio y explicá de qué se trata."
DEFAULT_PYTHON_REQUEST = (
    "Analizá este repositorio Python: arquitectura, dependencias, comandos, "
    "riesgos y checks relevantes."
)


def main():
    parser = argparse.ArgumentParser(
        description="Analiza un repositorio con el sistema multi-agente."
    )
    clone_group = parser.add_mutually_exclusive_group()
    clone_group.add_argument(
        "--clone",
        metavar="REPO_URL",
        help="URL de un repo GitHub a clonar (y hacer chdir) antes de analizar.",
    )
    clone_group.add_argument(
        "--python",
        metavar="REPO_URL",
        help=(
            "URL de un repo Python: ingesta rag/sources/python en el RAG, "
            "clona el repo y lo analiza."
        ),
    )
    parser.add_argument(
        "request",
        nargs="?",
        default=DEFAULT_REQUEST,
        help="Pedido/foco del análisis en lenguaje natural.",
    )
    args = parser.parse_args()

    if args.python:
        _ingest_python_rag_sources()
        if args.request == DEFAULT_REQUEST:
            args.request = DEFAULT_PYTHON_REQUEST

    repo_url = args.python or args.clone
    if repo_url:
        clone_repo(repo_url)

    orchestrator = build_orchestrator()
    report, _state = orchestrator.run(args.request)

    print("\n" + "=" * 72)
    print(report)


def _ingest_python_rag_sources():
    """Carga las fuentes Python del repo en el índice RAG antes de analizar."""
    if not PYTHON_RAG_SOURCES.exists():
        print(f"Error: no existe la base RAG Python: {PYTHON_RAG_SOURCES}")
        raise SystemExit(1)

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: falta OPENAI_API_KEY para ingestar el RAG Python.")
        raise SystemExit(1)

    os.environ.setdefault("RAG_PERSIST_DIR", str(PROJECT_ROOT / "rag_store"))

    from agent.llm import build_client

    store = make_rag_store(
        build_client(api_key),
        persist_dir=os.environ["RAG_PERSIST_DIR"],
    )
    if store is None:
        print("Error: RAG no disponible (¿falta instalar chromadb?).")
        raise SystemExit(1)

    docs, chunks = ingest_path(store, str(PYTHON_RAG_SOURCES))
    print(
        "RAG Python cargado: "
        f"{docs} documento(s), {chunks} chunk(s). "
        f"Total en el índice: {store.count()}."
    )


if __name__ == "__main__":
    main()
