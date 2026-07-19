"""Cliente LLM, system prompt y esquema de tools en formato OpenAI."""

import os

from openai import OpenAI

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
]


def build_client(api_key):
    """Creates the OpenAI client."""
    return OpenAI(api_key=api_key)


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
