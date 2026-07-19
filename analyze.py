"""Caso de uso: analizar un repositorio y producir un mini-reporte.

Corre el sistema multi-agente (orquestador + subagentes) sobre el directorio
actual, o sobre un repo clonado con --clone.

Uso:
    python analyze.py                          # analiza el directorio actual
    python analyze.py --clone URL              # clona un repo y lo analiza
    python analyze.py "foco del análisis"      # pedido específico
"""

import argparse

from agent.factory import build_orchestrator
from repo import clone_repo


def main():
    parser = argparse.ArgumentParser(
        description="Analiza un repositorio con el sistema multi-agente."
    )
    parser.add_argument(
        "--clone",
        metavar="REPO_URL",
        help="URL de un repo GitHub a clonar (y hacer chdir) antes de analizar.",
    )
    parser.add_argument(
        "request",
        nargs="?",
        default="Analizá este repositorio y explicá de qué se trata.",
        help="Pedido/foco del análisis en lenguaje natural.",
    )
    args = parser.parse_args()

    if args.clone:
        clone_repo(args.clone)

    orchestrator = build_orchestrator()
    report, _state = orchestrator.run(args.request)

    print("\n" + "=" * 72)
    print(report)


if __name__ == "__main__":
    main()
