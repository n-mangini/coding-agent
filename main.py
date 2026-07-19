"""Chat interactivo con el coding agent.

Uso:
    python main.py                 # solo el workspace local
    python main.py --clone URL     # clona un repo y hace chdir antes del chat

Comandos dentro del chat:
    /plan on|off|status
    /supervise on|off|status
    exit
"""

import argparse

from agent.factory import build_harness
from agent.observability import observed_run
from repo import clone_repo


def main():
    parser = argparse.ArgumentParser(description="Coding Agent — chat interactivo")
    parser.add_argument(
        "--clone",
        metavar="REPO_URL",
        help="URL de un repo GitHub a clonar (y hacer chdir) antes de arrancar.",
    )
    args = parser.parse_args()

    if args.clone:
        clone_repo(args.clone)

    harness = build_harness()

    conversation_history = harness.new_conversation()
    plan_mode_enabled = False
    supervision_enabled = False

    print("\nAgent ready!")
    print("Commands: /plan on|off|status | /supervise on|off|status | exit")

    while True:
        try:
            user_input = input("\nUser: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEnding conversation.")
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("Ending conversation.")
            break

        if user_input.lower() == "/plan on":
            plan_mode_enabled = True
            print("✅ Plan mode ENABLED.")
            continue
        if user_input.lower() == "/plan off":
            plan_mode_enabled = False
            print("✅ Plan mode DISABLED.")
            continue
        if user_input.lower() == "/plan status":
            print(f"Plan mode is {'ENABLED' if plan_mode_enabled else 'DISABLED'}.")
            continue

        if user_input.lower() == "/supervise on":
            supervision_enabled = True
            print(
                "🛡  Supervision ENABLED (write_file & execute_command will "
                "require confirmation)."
            )
            continue
        if user_input.lower() == "/supervise off":
            supervision_enabled = False
            print("🛡  Supervision DISABLED.")
            continue
        if user_input.lower() == "/supervise status":
            print(
                f"Supervision is {'ENABLED' if supervision_enabled else 'DISABLED'}."
            )
            continue

        # Una traza por turno de chat: agrupa TODO el trabajo del turno —la
        # generación del plan (si Plan mode está activo) y la ejecución— para
        # que la generation del planning también anide en la traza del turno.
        with observed_run("chat-turn", user_input):
            # Por defecto ejecutamos el mensaje tal cual. Plan mode solo cambia
            # QUÉ input recibe el agente (le antepone el plan aprobado); por eso
            # run_conversation se llama una sola vez, abajo, en ambos casos.
            agent_input = user_input
            if plan_mode_enabled:
                approved_plan = harness.plan_mode_turn(user_input, conversation_history)
                if approved_plan is None:
                    print("Task cancelled.")
                    continue
                agent_input = (
                    f"{user_input}\n\n"
                    f"Follow this approved plan strictly:\n{approved_plan}"
                )

            final_response, conversation_history = harness.run_conversation(
                agent_input,
                conversation_history,
                supervision_enabled=supervision_enabled,
            )

        print(f"\nAgent: {final_response}")


if __name__ == "__main__":
    main()
