"""Wiring: carga config del entorno y arma el Harness con sus tools."""

import os

from dotenv import load_dotenv

from . import tools as tools_module
from .harness import Harness
from .llm import TOOLS, build_client


def build_harness():
    """Construye un Harness listo para usar a partir de variables de entorno.

    Lee OPENAI_API_KEY (obligatoria) y TAVILY_API_KEY (opcional, para web_search)
    desde el entorno o un archivo .env. Si falta la de OpenAI, la pide por stdin.
    """
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("Using OpenAI API key from environment.")
    else:
        api_key = input("Enter your OpenAI API key: ").strip()

    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if tavily_api_key:
        print("Using Tavily API key from environment.")
    else:
        print("TAVILY_API_KEY not set — web_search will be unavailable.")

    client = build_client(api_key)
    web_search = tools_module.make_web_search(tavily_api_key)

    tool_map = {
        "read_file": tools_module.read_file,
        "list_files": tools_module.list_files,
        "write_file": tools_module.write_file,
        "execute_command": tools_module.execute_command,
        "web_search": web_search,
    }

    return Harness(client, tool_map, TOOLS)
