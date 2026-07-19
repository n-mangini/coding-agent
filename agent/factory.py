"""Wiring: carga config del entorno y arma el Harness con sus tools."""

import os

from dotenv import load_dotenv

from rag import make_rag_store

from . import tools as tools_module
from .harness import Harness
from .llm import TOOL_SCHEMAS, build_client
from .memory import load_project_memory, make_memory_tools
from .orchestrator import Orchestrator
from .policies import load_policies
from .subagents import build_explorer, build_researcher


def _build_client_from_env():
    """Lee OPENAI_API_KEY del entorno (o la pide por stdin) y arma el cliente."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("Using OpenAI API key from environment.")
    else:
        api_key = input("Enter your OpenAI API key: ").strip()
    return build_client(api_key)


def _build_web_search_from_env():
    """Lee TAVILY_API_KEY del entorno y arma la tool web_search (stub si falta)."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if tavily_api_key:
        print("Using Tavily API key from environment.")
    else:
        print("TAVILY_API_KEY not set — web_search will be unavailable (stub).")
    return tools_module.make_web_search(tavily_api_key)


def _build_retrieve(client):
    """Arma la tool `retrieve` sobre el índice RAG (Chroma); stub si no hay store.

    `make_rag_store` devuelve None sin `chromadb`, y `make_retrieve` degrada a un
    stub que avisa que el RAG no está disponible (como `web_search` sin Tavily)."""
    rag_store = make_rag_store(client)
    if rag_store is None:
        print("chromadb no disponible — retrieve (RAG) quedará como stub.")
    return tools_module.make_retrieve(rag_store)


def build_orchestrator():
    """Construye el orquestador multi-agente (agente principal + subagentes).

    Es el punto de entrada del caso de uso "analizar un repo → reporte". Cablea
    el Explorer y el Researcher; los próximos subagentes se suman acá y en
    `Orchestrator`. Todos los subagentes reciben el mismo set de policies: el rol
    lo da el `tool_map` acotado, las policies son invariantes de seguridad
    globales iguales para todos.
    """
    client = _build_client_from_env()
    policies = load_policies()
    web_search = _build_web_search_from_env()
    retrieve = _build_retrieve(client)
    # Memoria por-proyecto compartida: los subagentes la leen y la escriben con
    # las tools `read_memory` / `remember` cerradas sobre esta misma instancia.
    memory_tools = make_memory_tools(load_project_memory())
    explorer = build_explorer(client, policies, memory_tools)
    researcher = build_researcher(client, retrieve, web_search, policies)
    return Orchestrator(explorer, researcher)


def build_harness():
    """Construye un Harness listo para usar a partir de variables de entorno.

    Lee OPENAI_API_KEY (obligatoria) y TAVILY_API_KEY (opcional, para web_search)
    desde el entorno o un archivo .env. Si falta la de OpenAI, la pide por stdin.
    """
    client = _build_client_from_env()
    web_search = _build_web_search_from_env()
    retrieve = _build_retrieve(client)

    tool_map = {
        "read_file": tools_module.read_file,
        "list_files": tools_module.list_files,
        "write_file": tools_module.write_file,
        "execute_command": tools_module.execute_command,
        "retrieve": retrieve,
        "web_search": web_search,
        **make_memory_tools(load_project_memory()),
    }

    return Harness(client, tool_map, TOOL_SCHEMAS, policies=load_policies())
