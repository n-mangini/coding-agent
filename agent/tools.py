"""Herramientas que el agente puede invocar.

Cinco tools: read_file, list_files, write_file, execute_command, web_search.
Migradas desde el notebook del TP1 (celdas 10-14).
"""

import os
import subprocess

from tavily import TavilyClient


def read_file(file_path):
    """Reads the content of a file given its path.

    Args:
        file_path (str): The path to the file to read.

    Returns:
        str: The content of the file, or an error message if it cannot be read.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:  # noqa: BLE001
        return f"Error reading file {file_path}: {e}"


def list_files(path="."):
    """Lists files and directories in the specified path.

    Args:
        path (str): The directory path to list. Defaults to current directory.

    Returns:
        str: A newline-separated listing, or an error message.
    """
    try:
        entries = os.listdir(path)
        files_and_dirs = []
        for entry in sorted(entries):
            full_path = os.path.join(path, entry)
            if os.path.isfile(full_path):
                files_and_dirs.append(f"📄 {entry}")
            elif os.path.isdir(full_path):
                files_and_dirs.append(f"📁 {entry}")
        return "\n".join(files_and_dirs)
    except FileNotFoundError:
        return f"Error: Directory not found at {path}"
    except Exception as e:  # noqa: BLE001
        return f"Error listing files in {path}: {e}"


def write_file(file_path, content):
    """Writes content to a file, overwriting existing content if it exists.

    Args:
        file_path (str): The path to the file to write.
        content (str): The content to write to the file.

    Returns:
        str: A success message or an error message.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:  # noqa: BLE001
        return f"Error writing to file {file_path}: {e}"


def execute_command(command):
    """Executes a shell command and returns its stdout and stderr.

    Args:
        command (str): The shell command to execute.

    Returns:
        str: The combined stdout and stderr of the command execution.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=True
        )
        return f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        return (
            f"Command failed with error code {e.returncode}:\n"
            f"Stdout:\n{e.stdout}\nStderr:\n{e.stderr}"
        )
    except Exception as e:  # noqa: BLE001
        return f"Error executing command '{command}': {e}"


def make_web_search(tavily_api_key):
    """Builds a web_search tool bound to a Tavily client.

    Returns a callable `web_search(query)`. If no API key is provided, returns a
    stub that reports the tool is unavailable so the harness keeps working.
    """
    if not tavily_api_key:
        def web_search(query):  # noqa: ARG001
            return "Error: web_search unavailable (TAVILY_API_KEY not set)."

        return web_search

    tavily = TavilyClient(api_key=tavily_api_key)

    def web_search(query):
        """Performs a web search using Tavily and returns the results.

        Args:
            query (str): The search query.

        Returns:
            str: A string containing the search results.
        """
        try:
            response = tavily.search(query=query)
            results_str = ""
            for result in response["results"]:
                results_str += f"Title: {result['title']}\n"
                results_str += f"URL: {result['url']}\n"
                results_str += f"Content: {result['content']}\n\n"
            return results_str
        except Exception as e:  # noqa: BLE001
            return f"Error performing web search: {e}"

    return web_search
