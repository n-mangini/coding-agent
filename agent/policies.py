"""Capa de políticas: valida cada tool call antes de ejecutarla.

Las políticas se declaran en `agent.config.yaml` y gobiernan qué rutas se pueden
leer/escribir y qué comandos se pueden ejecutar. `Policies.check()` responde
`(allowed, reason)` sin lanzar excepciones, para que el `Harness` devuelva el
motivo del bloqueo como contenido de un mensaje `role:"tool"` (el mismo patrón
que usan las tools, que nunca lanzan).
"""

import fnmatch
from pathlib import Path

import yaml

# Ruta -> sección de política cuyo objetivo (target) se evalúa.
#   read/write: se matchea el path del archivo; commands: el comando en sí.
# Las tools ausentes de este mapa (p. ej. web_search) no tienen política.
_TOOL_SECTION = {
    "read_file": ("read", "file_path"),
    "list_files": ("read", "path"),
    "write_file": ("write", "file_path"),
    "execute_command": ("commands", "command"),
}

# La config vive en la raíz del proyecto, no en el cwd: los entry points hacen
# chdir al repo clonado, así que resolvemos la ruta relativa al paquete.
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "agent.config.yaml"


class Policies:
    """Reglas cargadas de `agent.config.yaml`, consultadas antes de cada tool.

    Args:
        rules (dict): sección `policies` ya validada (read/write/commands/approval).
    """

    def __init__(self, rules):
        self.rules = rules

    def check(self, tool_name, args):
        """Decide si una tool call está permitida.

        Returns:
            (bool, str): `(True, "")` si se permite; `(False, motivo)` si se
            bloquea. Nunca lanza: el motivo vuelve al LLM como contenido.
        """
        section = _TOOL_SECTION.get(tool_name)
        if section is None:
            return True, ""

        name, arg_key = section
        target = args.get(arg_key, "")
        return _evaluate(self.rules.get(name, {}), target)

    def requires_approval(self, tool_name):
        """Indica si la tool exige confirmación humana según la config."""
        return tool_name in self.rules.get("approval", [])


def _evaluate(rule, target):
    """Aplica deny (prioritario) y luego allow (allowlist si no está vacío)."""
    normalized = _normalize(target)

    for pattern in rule.get("deny", []):
        if _matches(normalized, target, pattern):
            return False, f"Error: policy denied — matchea deny '{pattern}'."

    allow = rule.get("allow", [])
    if allow and not any(_matches(normalized, target, p) for p in allow):
        return False, "Error: policy denied — no está en la allowlist."

    return True, ""


def _matches(normalized, raw, pattern):
    """Matchea patrón glob contra la ruta normalizada y el valor crudo.

    Probar ambos cubre tanto rutas (donde importa normalizar separadores) como
    comandos (donde el patrón busca subcadenas del comando tal cual se pidió).
    """
    return fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(raw, pattern)


def _normalize(target):
    """Normaliza separadores y `./` para que los patrones de ruta sean estables."""
    return str(target).replace("\\", "/").lstrip("./")


def load_policies(config_path=_DEFAULT_CONFIG_PATH):
    """Carga y valida `agent.config.yaml` al iniciar.

    A diferencia de las tools, acá sí lanzamos: una config malformada es un error
    de arranque que debe fallar rápido y visible, no un input del LLM.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    rules = data.get("policies")
    if not isinstance(rules, dict):
        raise ValueError(
            f"{config_path}: falta la clave 'policies' o no es un mapa."
        )

    for name in ("read", "write", "commands"):
        _validate_section(config_path, name, rules.get(name, {}))

    approval = rules.get("approval", [])
    if not isinstance(approval, list):
        raise ValueError(f"{config_path}: 'approval' debe ser una lista de tools.")

    return Policies(rules)


def _validate_section(config_path, name, section):
    """Verifica que una sección tenga `allow`/`deny` como listas."""
    if not isinstance(section, dict):
        raise ValueError(f"{config_path}: la sección '{name}' debe ser un mapa.")
    for key in ("allow", "deny"):
        value = section.get(key, [])
        if not isinstance(value, list):
            raise ValueError(
                f"{config_path}: '{name}.{key}' debe ser una lista de patrones."
            )
