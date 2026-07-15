"""Batería de casos de prueba automatizados.

Reemplaza las celdas de pruebas automatizadas del notebook (celdas 25-26).
Cada caso corre con un historial nuevo para que sean independientes.

Uso:
    python run_tests.py                 # corre en el workspace/cwd actual
    python run_tests.py --clone URL     # clona un repo y corre los casos ahí
"""

import argparse

from agent.factory import build_harness
from agent.llm import SYSTEM_MESSAGE
from agent.repo import clone_repo

EXPLICIT_TEST_CASES = [
    (
        "Corregir un bug",
        "Examina el archivo 'examples/api_request_parallel_processor.py'. Busca y "
        "corrige cualquier error de sintaxis obvio en las primeras 50 líneas. Por "
        "ejemplo, si encuentras una variable `max_attempts` definida pero no "
        "utilizada, o un `import` redundante, corrígelo. Luego, lee el archivo "
        "'README.md' para ver si hay instrucciones generales sobre cómo ejecutar "
        "tests en este repositorio. Si encuentras un error, corrígelo. Si no, solo "
        "indica que no encontraste errores obvios.",
    ),
    (
        "Escribir código nuevo",
        "Crea un nuevo directorio llamado 'my_new_project'. Dentro de "
        "'my_new_project', crea un archivo llamado 'utils.py' con una función "
        "`def multiply(a, b): return a * b`. Luego, crea un archivo 'test_utils.py' "
        "en el mismo directorio que contenga un test para `multiply`. Finalmente, "
        "ejecuta el test desde 'my_new_project' y muéstrame el resultado. Asegúrate "
        "de crear el directorio antes de escribir los archivos.",
    ),
    (
        "Refactorizar código",
        "Lee el archivo 'examples/api_request_parallel_processor.py'. Refactoriza la "
        "función `process_api_requests_from_file` para que divida su lógica "
        "principal en funciones auxiliares más pequeñas para mejorar la "
        "legibilidad. Luego, muestra el código refactorizado. No necesitas "
        "ejecutarlo ni hacer tests.",
    ),
    (
        "Agregar tests",
        "Crea un archivo 'calculator.py' en el directorio actual con una función "
        "`def divide(a, b): return a / b`. Luego, escribe tests unitarios para esta "
        "función en un archivo 'test_calculator.py' en el mismo directorio. Ejecuta "
        "los tests y muestra el output. Asegúrate de manejar el caso de división "
        "por cero.",
    ),
    (
        "Buscar e implementar",
        "Usando una librería que no conozcas (por ejemplo, 'requests' si no la has "
        "usado), busca en la web cómo hacer una solicitud HTTP GET simple a "
        "'https://api.github.com/zen'. Luego, implementa el código para hacer esta "
        "solicitud y muestra el resultado del cuerpo de la respuesta. Si ya usaste "
        "'requests', elige otra librería de propósito general.",
    ),
    (
        "Leer documentación y configurar un proyecto",
        "Crea un directorio llamado 'temp_project'. Dentro de 'temp_project', crea "
        "un archivo 'README.md' con el contenido: 'Este es un proyecto de prueba. "
        "Para instalar las dependencias, ejecuta `pip install -r requirements.txt`. "
        "Para ejecutar el proyecto, ejecuta `python main.py`.' Crea también un "
        "archivo 'requirements.txt' con el contenido: 'requests==2.28.1'. "
        "Finalmente, crea un archivo 'main.py' con el contenido: 'import requests\\n"
        "print(requests.__version__)'. Después de crear estos archivos, lee el "
        "README, instala las dependencias y ejecuta el `main.py`.",
    ),
    (
        "Explorar un repo desconocido",
        "Darle un proyecto que no conoce y pedirle que explique qué hace. Tiene que "
        "navegar archivos, leer código y armar una respuesta.",
    ),
]


def run(harness, test_cases):
    print("Starting automated test execution with explicit test cases...")
    for i, (title, description) in enumerate(test_cases):
        print(f"\n{'=' * 50}")
        print(f"Running Automated Test Case {i + 1}: {title.strip()}")
        print(f"Description: {description.strip()}")
        print(f"{'=' * 50}")

        conversation_history = [{"role": "system", "content": SYSTEM_MESSAGE}]

        user_input = f"Please perform the following task: {description.strip()}"

        try:
            final_response, conversation_history = harness.run_conversation(
                user_input, conversation_history
            )
            print(
                f"\nAgent's Final Response for Test Case {i + 1} "
                f"({title.strip()}):\n{final_response}"
            )
        except Exception as e:  # noqa: BLE001
            print(f"\nError during Test Case {i + 1} ({title.strip()}): {e}")

    print("\nAutomated test execution complete.")


def main():
    parser = argparse.ArgumentParser(description="Coding Agent — casos automatizados")
    parser.add_argument(
        "--clone",
        metavar="REPO_URL",
        help="URL de un repo GitHub a clonar (y hacer chdir) antes de correr.",
    )
    args = parser.parse_args()

    if args.clone:
        clone_repo(args.clone)

    harness = build_harness()
    run(harness, EXPLICIT_TEST_CASES)


if __name__ == "__main__":
    main()
