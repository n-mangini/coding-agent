"""Harness del agente: loop de orquestación, Plan Mode y Supervisión."""

import inspect
import json

from .llm import PLANNING_SYSTEM_MESSAGE, SYSTEM_MESSAGE, call_llm
from .observability import trace_tool

# --- Manejo de contexto -----------------------------------------------------
# A partir de este tamaño de historial, resumimos los turnos viejos en vez de
# reenviarlos completos al LLM (una ejecución larga no crece sin límite).
HISTORY_LIMIT = 24
# Cuántos mensajes recientes se conservan tal cual al resumir (el resto se
# condensa en una sola nota). El system message del índice 0 siempre se preserva.
HISTORY_TAIL = 8

# --- Detección de loops -----------------------------------------------------
# Cuántas tool calls idénticas consecutivas cuentan como loop. Con 3, el agente
# que repite exactamente la misma llamada tres veces se considera atascado.
LOOP_THRESHOLD = 3

_REPLAN_NUDGE = (
    "⚠️ Detecté que estás repitiendo la misma acción sin avanzar. Pará, "
    "replanteá tu estrategia y probá un enfoque distinto. Si no tenés forma de "
    "avanzar con las tools disponibles, decilo explícitamente y pedí ayuda en "
    "vez de reintentar lo mismo."
)
_LOOP_STOP_MESSAGE = (
    "Me detuve por seguridad: seguí repitiendo la misma acción incluso después "
    "de intentar replantear, así que estoy en un loop del que no puedo salir "
    "solo. Necesito ayuda o más información para continuar."
)


class Harness:
    """Orquesta la conversación con el LLM y la ejecución de tools.

    Args:
        client: cliente OpenAI.
        tool_map (dict): nombre de tool -> función Python.
        tool_schemas (list): esquema de tools en formato OpenAI (lo que ve el LLM).
        system_message (str): prompt de sistema. Cada subagente pasa el suyo para
            especializarse reusando el mismo motor; por defecto, el genérico.
        policies (Policies | None): capa de políticas consultada antes de cada
            tool call. Si es None, no hay gate por config (comportamiento previo).
    """

    def __init__(
        self,
        client,
        tool_map,
        tool_schemas,
        system_message=SYSTEM_MESSAGE,
        policies=None,
    ):
        self.client = client
        self.tool_map = tool_map
        self.tool_schemas = tool_schemas
        self.system_message = system_message
        self.policies = policies
        self.loop_events = []

    def new_conversation(self):
        """Devuelve un historial nuevo, ya sembrado con el mensaje `system`."""
        return [{"role": "system", "content": self.system_message}]

    # ---------------------------------------------------------------- loop
    def run_conversation(
        self, user_message, conversation_history, supervision_enabled=False
    ):
        """Loop interno: llama al LLM y ejecuta tools hasta obtener respuesta final.

        Dos salvaguardas envuelven al loop clásico: el historial se resume cuando
        crece demasiado (`_manage_context`) para no reenviar todo al LLM, y las
        tool calls repetidas se vigilan (`_intervene_on_loop`) para cortar un
        agente atascado en vez de reintentar para siempre.
        """
        conversation_history.append({"role": "user", "content": user_message})
        recent_signatures = []
        already_replanned = False
        self.loop_events = []

        while True:
            conversation_history = self._manage_context(conversation_history)
            llm_response, error = call_llm(
                self.client, conversation_history, tools=self.tool_schemas
            )

            if error:
                print(f"LLM Error: {error}")
                conversation_history.append(
                    {"role": "assistant", "content": f"An error occurred: {error}"}
                )
                return f"An error occurred: {error}", conversation_history

            if not llm_response.tool_calls:
                conversation_history.append(llm_response)
                return llm_response.content, conversation_history

            conversation_history.append(llm_response)
            for tool_call in llm_response.tool_calls:
                self._execute_tool_call(
                    tool_call, conversation_history, supervision_enabled
                )
                recent_signatures.append(_tool_signature(tool_call))

            intervention, already_replanned = self._intervene_on_loop(
                recent_signatures, already_replanned, conversation_history
            )
            if intervention is not None:
                return intervention, conversation_history

    # ------------------------------------------------------- loop detection
    def _intervene_on_loop(self, signatures, already_replanned, conversation_history):
        """Actúa si las últimas tool calls forman un loop; escala replan → parar.

        Primer loop: inyecta un pedido de replanteo y da otra chance (limpia el
        rastro para no re-disparar de inmediato). Si vuelve a atascarse pese al
        replanteo, corta la corrida y pide ayuda con un mensaje explícito.
        Devuelve `(intervencion, already_replanned)`: `intervencion` es None para
        seguir el loop, o el texto final con el que cortar.
        """
        if not detect_loop(signatures, LOOP_THRESHOLD):
            return None, already_replanned

        if not already_replanned:
            print(f"\n🔁 {_REPLAN_NUDGE}")
            self.loop_events.append(
                "Loop detectado: se pidió replantear la estrategia."
            )
            conversation_history.append({"role": "user", "content": _REPLAN_NUDGE})
            signatures.clear()
            return None, True

        print(f"\n🛑 {_LOOP_STOP_MESSAGE}")
        self.loop_events.append(
            "Loop persistente: el agente se detuvo y pidió ayuda para continuar."
        )
        conversation_history.append(
            {"role": "assistant", "content": _LOOP_STOP_MESSAGE}
        )
        return _LOOP_STOP_MESSAGE, already_replanned

    # ----------------------------------------------------- context handling
    def _manage_context(self, conversation_history):
        """Resume los turnos viejos cuando el historial supera `HISTORY_LIMIT`.

        Preserva el system message y los `HISTORY_TAIL` mensajes más recientes, y
        reemplaza el bloque intermedio por un único resumen. Si el LLM no logra
        resumir, deja el historial intacto: el resumen es una optimización, no un
        invariante. Devuelve el historial (posiblemente compactado).
        """
        if len(conversation_history) <= HISTORY_LIMIT:
            return conversation_history

        boundary = _safe_tail_boundary(conversation_history, HISTORY_TAIL)
        head, tail = conversation_history[1:boundary], conversation_history[boundary:]
        if not head:
            return conversation_history

        summary, error = self._summarize(head)
        if error:
            return conversation_history

        print("\n🧠 Historial largo: resumo los turnos viejos para no reenviarlos.")
        return (
            [conversation_history[0]]
            + [{"role": "system", "content": f"Resumen de la conversación previa:\n{summary}"}]
            + tail
        )

    def _summarize(self, messages):
        """Pide al LLM (sin tools) un resumen compacto de los mensajes dados."""
        transcript = "\n".join(
            f"{_message_role(m)}: {_message_text(m)}" for m in messages
        )
        prompt = [
            {
                "role": "system",
                "content": (
                    "Resumí la siguiente conversación de un agente de codificación "
                    "conservando decisiones, hallazgos, archivos tocados y pendientes. "
                    "Sé breve y concreto; devolvé solo el resumen."
                ),
            },
            {"role": "user", "content": transcript},
        ]
        message, error = call_llm(self.client, prompt, tools=None)
        if error:
            return None, error
        return message.content, None

    # ------------------------------------------------------ tool execution
    def _execute_tool_call(self, tool_call, conversation_history, supervision_enabled):
        """Ejecuta una única tool pedida por el LLM y appendea su resultado.

        Concentra el 'cómo': parsear los args, validar que la tool exista,
        filtrar argumentos contra la firma real y (si corresponde) pedir
        supervisión. `content` acumula el texto a devolver y se appendea una
        sola vez al final, como role:"tool".
        """
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        if function_name not in self.tool_map:
            content = f"Error: Tool '{function_name}' not found."
            print(content)
        elif (policy := self._policy_denial(function_name, function_args)) is not None:
            # El gate de políticas corre primero: es un veto por config, previo a
            # la supervisión humana. El motivo vuelve al LLM como contenido.
            content = policy
            print(f"\n🚫 {content}")
        else:
            tool_function = self.tool_map[function_name]
            sig = inspect.signature(tool_function)
            filtered_args = {
                k: v for k, v in function_args.items() if k in sig.parameters
            }

            denied = (
                self._needs_confirmation(function_name, supervision_enabled)
                and not self._confirm_action(function_name, filtered_args)
            )
            if denied:
                content = f"User denied execution of {function_name}."
                print(f"\n❌ {content}")
            else:
                print(f"\n🤖 Calling tool: {function_name} with args: {filtered_args}")
                content = trace_tool(function_name, tool_function, filtered_args)
                print(f"Tool output: {content}")

        conversation_history.append(
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": content,
            }
        )

    # ------------------------------------------------------------ policies
    def _policy_denial(self, tool_name, args):
        """Devuelve el motivo de bloqueo por política, o None si se permite."""
        if self.policies is None:
            return None
        allowed, reason = self.policies.check(tool_name, args)
        return None if allowed else reason

    def _needs_confirmation(self, tool_name, supervision_enabled):
        """Con Supervisión activa, la lista `approval` de la config define qué tools
        piden confirmación humana. Sin policies o sin supervisión, no se pide nada."""
        if not supervision_enabled or self.policies is None:
            return False
        return self.policies.requires_approval(tool_name)

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

    def generate_plan(self, user_message, conversation_history, feedback=None):
        """Pide al LLM un plan paso a paso (sin llamar tools)."""
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
            [{"role": "system", "content": PLANNING_SYSTEM_MESSAGE}]
            + prior
            + [{"role": "user", "content": request}]
        )

        message, error = call_llm(self.client, planning_messages, tools=None)
        if error:
            return None, error
        return message.content, None

def _tool_signature(tool_call):
    """Firma estable de una tool call (nombre + argumentos crudos) para comparar."""
    return f"{tool_call.function.name}({tool_call.function.arguments})"


def detect_loop(signatures, threshold):
    """True si las últimas `threshold` firmas de tool call son idénticas.

    Función pura (sin estado ni I/O): es el criterio verificable de "loop" que
    usa `_intervene_on_loop`. Con `threshold` firmas iguales consecutivas, el
    agente está repitiendo exactamente la misma acción sin avanzar.
    """
    if threshold <= 0 or len(signatures) < threshold:
        return False
    ultimas = signatures[-threshold:]
    return len(set(ultimas)) == 1


def _safe_tail_boundary(conversation_history, tail_size):
    """Índice donde empieza la cola a preservar, sin partir un grupo de tools.

    Un mensaje `role:"tool"` debe ir precedido por el assistant con sus
    `tool_calls`; si la cola arrancara en un `tool` huérfano, la API fallaría.
    Retrocedemos el borde hasta que no arranque en un mensaje `tool`.
    """
    boundary = max(1, len(conversation_history) - tail_size)
    while boundary < len(conversation_history) and (
        _message_role(conversation_history[boundary]) == "tool"
    ):
        boundary -= 1
    return boundary


def _message_role(message):
    """Rol de un mensaje, ya sea dict (system/user/tool) u objeto (assistant)."""
    if isinstance(message, dict):
        return message.get("role")
    return getattr(message, "role", None)


def _message_text(message):
    """Texto de un mensaje para el transcript del resumen (vacío si no tiene)."""
    if isinstance(message, dict):
        return message.get("content") or ""
    return getattr(message, "content", None) or ""


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
