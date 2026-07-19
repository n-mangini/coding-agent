"""Harness del agente: loop de orquestación, Plan Mode y Supervisión.

Migrado desde el notebook del TP1 (celdas 17 y 19).
"""

import inspect
import json

from .llm import MODEL, SYSTEM_MESSAGE, call_llm

WRITE_TOOLS = {"write_file", "execute_command"}


class Harness:
    """Orquesta la conversación con el LLM y la ejecución de tools.

    Args:
        client: cliente OpenAI.
        tool_map (dict): nombre de tool -> función Python.
        tools (list): esquema de tools en formato OpenAI.
    """

    def __init__(self, client, tool_map, tools):
        self.client = client
        self.tool_map = tool_map
        self.tools = tools

    def new_conversation(self):
        """Devuelve un historial nuevo, ya sembrado con el mensaje `system`."""
        return [{"role": "system", "content": SYSTEM_MESSAGE}]

    # ---------------------------------------------------------------- loop
    def run_conversation(
        self, user_message, conversation_history, supervision_enabled=False
    ):
        """Loop interno: llama al LLM y ejecuta tools hasta obtener respuesta final."""
        conversation_history.append({"role": "user", "content": user_message})

        while True:
            llm_response, error = call_llm(
                self.client, conversation_history, tools=self.tools
            )

            if error:
                print(f"LLM Error: {error}")
                conversation_history.append(
                    {"role": "assistant", "content": f"An error occurred: {error}"}
                )
                return f"An error occurred: {error}", conversation_history

            if llm_response.tool_calls:
                conversation_history.append(llm_response)
                for tool_call in llm_response.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if function_name not in self.tool_map:
                        error_message = f"Error: Tool '{function_name}' not found."
                        print(error_message)
                        conversation_history.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": error_message,
                            }
                        )
                        continue

                    tool_function = self.tool_map[function_name]
                    sig = inspect.signature(tool_function)
                    filtered_args = {
                        k: v for k, v in function_args.items() if k in sig.parameters
                    }

                    if supervision_enabled and function_name in WRITE_TOOLS:
                        if not self._confirm_action(function_name, filtered_args):
                            tool_output = f"User denied execution of {function_name}."
                            print(f"\n❌ {tool_output}")
                            conversation_history.append(
                                {
                                    "tool_call_id": tool_call.id,
                                    "role": "tool",
                                    "name": function_name,
                                    "content": tool_output,
                                }
                            )
                            continue

                    print(
                        f"\n🤖 Calling tool: {function_name} with args: {filtered_args}"
                    )
                    tool_output = tool_function(**filtered_args)
                    print(f"Tool output: {tool_output}")
                    conversation_history.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": tool_output,
                        }
                    )
            else:
                conversation_history.append(llm_response)
                return llm_response.content, conversation_history

    # -------------------------------------------------------- supervision
    def _confirm_action(self, tool_name, args):
        """Pide aprobación al usuario para una tool que modifica el sistema."""
        print(f"\n🛡  Supervision: approve this '{tool_name}' call?")
        # Pretty-print del content en write_file para poder revisarlo (mejora
        # sugerida en el análisis del Caso 2 del TP1).
        if tool_name == "write_file" and "content" in args:
            preview = {k: v for k, v in args.items() if k != "content"}
            print(f"   args: {preview}")
            print("   content:\n" + "\n".join(
                "   | " + line for line in str(args["content"]).splitlines()
            ))
        else:
            print(f"   args: {args}")
        decision = input("Approve? (yes/no): ").strip().lower()
        return decision in ("yes", "y")

    # ----------------------------------------------------------- plan mode
    def generate_plan(self, user_message, conversation_history, feedback=None):
        """Pide al LLM un plan paso a paso (sin llamar tools)."""
        planning_system = (
            "You are in PLAN MODE. Do NOT call any tools. "
            "Given the user's request, output a concise, numbered step-by-step plan "
            "describing which tools you would use (read_file, write_file, "
            "list_files, execute_command, web_search) and why. Keep it short and "
            "concrete. Output only the plan text, nothing else."
        )

        prior = _planning_history(conversation_history)
        request = (
            user_message
            if feedback is None
            else (
                f"{user_message}\n\nUser feedback on previous plan "
                f"(revise accordingly): {feedback}"
            )
        )
        planning_messages = (
            [{"role": "system", "content": planning_system}]
            + prior
            + [{"role": "user", "content": request}]
        )

        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=planning_messages,
            )
            return response.choices[0].message.content, None
        except Exception as e:  # noqa: BLE001
            return None, f"Error generating plan: {e}"

    def plan_mode_turn(self, user_message, conversation_history):
        """Genera un plan, lo muestra y lo itera con feedback del usuario."""
        feedback = None
        while True:
            plan, error = self.generate_plan(
                user_message, conversation_history, feedback=feedback
            )
            if error:
                print(error)
                return None
            print("\n📋 Proposed plan:")
            print(plan)
            decision = input(
                "\nApprove? (yes = run / cancel = abort / anything else = "
                "feedback to revise): "
            ).strip()
            if decision.lower() in ("yes", "y", "approve", "ok"):
                return plan
            if decision.lower() == "cancel":
                return None
            feedback = decision


def _planning_history(conversation_history):
    """Deja solo turnos de texto user/assistant; descarta system/tool y
    assistants con tool_calls."""
    out = []
    for m in conversation_history:
        if isinstance(m, dict):
            role = m.get("role")
            content = m.get("content")
            has_tool_calls = bool(m.get("tool_calls"))
        else:
            role = getattr(m, "role", None)
            content = getattr(m, "content", None)
            has_tool_calls = bool(getattr(m, "tool_calls", None))

        if role in (None, "system", "tool"):
            continue
        if role == "assistant" and (has_tool_calls or not content):
            continue
        out.append({"role": role, "content": content})
    return out
