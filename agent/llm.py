"""Cliente LLM, system prompt y esquema de tools en formato OpenAI."""

import os

from .memory import CATEGORIES as MEMORY_CATEGORIES
from .observability import build_openai_client

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

SYSTEM_MESSAGE = (
    "You are an AI coding assistant. You can perform tasks by calling tools. "
    "You should think step-by-step and then call a tool or respond to the user. "
    "You will be provided with a task, a set of available tools, and the history "
    "of the conversation. "
    "When you use a tool, clearly state which tool you are using and its arguments. "
    "After a tool call, you will be given the tool's output. "
    "If you need to search for information, use the 'web_search' tool. "
    "If you believe the task is complete, respond to the user without calling any "
    "tools. "
    "Before writing a file to a new path, ensure that its parent directory exists. "
    "If it doesn't, create it using appropriate tools."
)

PLANNING_SYSTEM_MESSAGE = (
    "You are in PLAN MODE. Do NOT call any tools. "
    "Given the user's request, output a concise, numbered step-by-step plan "
    "describing which tools you would use (read_file, write_file, "
    "list_files, execute_command, web_search) and why. Keep it short and "
    "concrete. Output only the plan text, nothing else."
)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a file given its path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read.",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "Lists files and directories in the specified path. Defaults to "
                "current directory if no path is provided."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to list.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Writes content to a file, overwriting existing content if the "
                "file exists."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file.",
                    },
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Executes a shell command and returns its stdout and stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Performs a web search and returns the results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": (
                "Devuelve la memoria persistente del proyecto (lo aprendido en "
                "corridas anteriores: arquitectura, dependencias, comandos, "
                "convenciones, decisiones, bugs, resúmenes). Consultala al empezar "
                "para no re-descubrir lo ya sabido."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": (
                "Guarda un dato duradero del proyecto en la memoria persistente, "
                "bajo una categoría. Usalo cuando descubras algo estable que "
                "convenga recordar en próximas corridas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "enum": list(MEMORY_CATEGORIES),
                        "description": "Categoría bajo la que archivar la nota.",
                    },
                    "nota": {
                        "type": "string",
                        "description": "El dato a recordar, corto y concreto.",
                    },
                },
                "required": ["categoria", "nota"],
            },
        },
    },
]


def schemas_for(names):
    """Devuelve el subconjunto de TOOL_SCHEMAS cuyos nombres estén en `names`.

    Cada subagente ve solo las tools que tiene permitidas; este helper mantiene
    el esquema (lo que ve el LLM) en sincronía con su `tool_map` acotado.
    """
    wanted = set(names)
    return [s for s in TOOL_SCHEMAS if s["function"]["name"] in wanted]


def build_client(api_key):
    """Creates the OpenAI client (instrumentado con Langfuse si hay credenciales).

    La decisión de instrumentar vive en `observability.build_openai_client`; acá
    seguimos teniendo el único borde con OpenAI, ahora observable sin tocar el loop.
    """
    return build_openai_client(api_key)


def call_llm(client, messages, tools=TOOL_SCHEMAS, model=MODEL):
    """Single LLM turn. Returns (message, error).

    Con `tools=None` se llama al modelo sin herramientas (p. ej. Plan Mode,
    donde el LLM solo debe devolver texto).
    """
    params = {"model": model, "messages": messages}
    if tools is not None:
        params["tools"] = tools
        params["tool_choice"] = "auto"
    try:
        response = client.chat.completions.create(**params)
        return response.choices[0].message, None
    except Exception as e:  # noqa: BLE001
        return None, f"Error calling LLM: {e}"
