"""Observabilidad con Langfuse: traza el borde LLM y la ejecución de tools.

La instrumentación es fina y no invade el loop del `Harness`:

- El borde con OpenAI (`call_llm`) se traza envolviendo el cliente con el drop-in
  de Langfuse (`langfuse.openai.OpenAI`). Cada turno del LLM queda registrado como
  una `generation` (prompts, modelo, tokens, costo, latencia y errores) sin agregar
  un segundo call site a OpenAI: `call_llm` sigue siendo el único.
- Cada ejecución de tool se envuelve en un `span` con su nombre, argumentos,
  salida, latencia y errores (ver `trace_tool`).
- El caso de uso completo se abre como una traza raíz (`observed_run`) para que las
  generations y los spans anteriores aniden todos dentro de una única traza.

Degradación elegante (requisito del issue): si faltan las credenciales de Langfuse
—o la librería no está instalada, o la autenticación falla— todo este módulo se
vuelve un no-op y el agente corre exactamente igual que antes. Nunca dejamos que la
instrumentación rompa una ejecución.

Config por entorno: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.
"""

import os
from contextlib import contextmanager

_client = None
_resolved = False


def _get_client():
    """Devuelve el cliente Langfuse si está utilizable, o None (no-op).

    Solo intentamos inicializar cuando están las dos credenciales; así, sin
    credenciales, ni importamos Langfuse y el módulo queda como un no-op
    silencioso. Cualquier fallo (import, red, auth inválida) también degrada a
    None: la observabilidad jamás debe tumbar una corrida. El resultado se cachea.
    """
    global _client, _resolved
    if _resolved:
        return _client
    _resolved = True

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse import get_client

        client = get_client()
        if not client.auth_check():
            return None
        _client = client
    except Exception:  # noqa: BLE001 — cualquier error => no-op, nunca romper.
        _client = None
    return _client


def build_openai_client(api_key):
    """Construye el cliente OpenAI, instrumentado con Langfuse si es posible.

    Es el punto donde se "envuelve `call_llm`": con credenciales, devolvemos el
    drop-in `langfuse.openai.OpenAI`, que traza cada `chat.completions.create`
    (el único borde con OpenAI) como una generation. Sin credenciales, devolvemos
    el cliente estándar de OpenAI y no cambia nada del comportamiento.
    """
    if _get_client() is not None:
        try:
            from langfuse.openai import OpenAI

            return OpenAI(api_key=api_key)
        except Exception:  # noqa: BLE001 — si falla el drop-in, cliente estándar.
            pass

    from openai import OpenAI

    return OpenAI(api_key=api_key)


@contextmanager
def observed_run(name, request):
    """Abre la traza raíz del caso de uso; las generations y spans anidan adentro.

    Sin Langfuse es un context manager vacío. Al cerrar, hace `flush()` para que
    un proceso corto (la CLI) alcance a enviar la traza antes de terminar.
    """
    client = _get_client()
    if client is None:
        yield
        return

    with client.start_as_current_observation(
        name=name, as_type="agent", input=request
    ):
        try:
            yield
        finally:
            client.flush()


def trace_tool(name, tool_function, args):
    """Ejecuta una tool dentro de un `span`, registrando args y salida.

    Preserva el contrato de las tools (nunca levantan: los errores viajan como
    parte de la salida, un string `Error: ...`), así que el `output` del span ya
    captura esos errores; el span solo registraría una excepción si, contra el
    contrato, alguna tool llegara a levantar una inesperada. Sin Langfuse,
    simplemente ejecuta la tool sin overhead observable.
    """
    client = _get_client()
    if client is None:
        return tool_function(**args)

    with client.start_as_current_observation(
        name=name, as_type="tool", input=args
    ) as span:
        output = tool_function(**args)
        span.update(output=output)
        return output
