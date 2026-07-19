"""Wiring: carga config del entorno y arma el Harness con sus tools."""

import os

from dotenv import load_dotenv

from . import tools as tools_module
from .harness import Harness
from .llm import TOOL_SCHEMAS, build_client
from .orchestrator import Orchestrator
from .policies import load_policies
from .subagents import build_explorer


def _build_client_from_env():
    """Lee OPENAI_API_KEY del entorno (o la pide por stdin) y arma el cliente."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("Using OpenAI API key from environment.")
    else:
        api_key = input("Enter your OpenAI API key: ").strip()
    return build_client(api_key)


def build_orchestrator():
    """Construye el orquestador multi-agente (agente principal + subagentes).

    Es el punto de entrada del caso de uso "analizar un repo → reporte". En el
    walking skeleton solo cablea el Explorer; los próximos subagentes se suman
    acá y en `Orchestrator`.
    """
    client = _build_client_from_env()
    policies = load_policies()
    explorer = build_explorer(client, policies)
    return Orchestrator(explorer)


def build_harness():
    """Construye un Harness listo para usar a partir de variables de entorno.

    Lee OPENAI_API_KEY (obligatoria) y TAVILY_API_KEY (opcional, para web_search)
    desde el entorno o un archivo .env. Si falta la de OpenAI, la pide por stdin.
    """
    client = _build_client_from_env()

    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if tavily_api_key:
        print("Using Tavily API key from environment.")
    else:
        print("TAVILY_API_KEY not set — web_search will be unavailable.")

    web_search = tools_module.make_web_search(tavily_api_key)

    tool_map = {
        "read_file": tools_module.read_file,
        "list_files": tools_module.list_files,
        "write_file": tools_module.write_file,
        "execute_command": tools_module.execute_command,
        "web_search": web_search,
    }

    return Harness(client, tool_map, TOOL_SCHEMAS, policies=load_policies())
