# Coding Agent

Agente de coding potenciado por un LLM (OpenAI) que puede explorar repositorios,
leer/analizar/modificar archivos y ejecutar tareas de forma autónoma a partir de
instrucciones en lenguaje natural.

Migrado desde el notebook del TP1 (`tp/coding_agent_Fierro_Mangini.ipynb`) a un
proyecto Python ejecutable sin Colab.

## Estructura

```
agent/
  tools.py     # read_file, list_files, write_file, execute_command, web_search
  llm.py       # cliente OpenAI, system prompt y esquema de tools
  harness.py   # loop de orquestación, Plan Mode y Supervisión
  repo.py      # clonado de repos GitHub al workspace
  factory.py   # wiring: arma el Harness desde variables de entorno
main.py        # chat interactivo (reemplaza las pruebas manuales del notebook)
run_tests.py   # batería de casos automatizados (reemplaza las pruebas del notebook)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar OPENAI_API_KEY (y TAVILY_API_KEY para web_search)
```

## Uso

Chat interactivo:

```bash
python main.py
# o clonando un repo primero:
python main.py --clone https://github.com/openai/openai-cookbook
```

Comandos dentro del chat:

- `/plan on|off|status` — Plan Mode: arma un plan y lo aprueba/itera antes de ejecutar.
- `/supervise on|off|status` — Supervisión (human-in-the-loop): pide confirmación
  antes de `write_file` y `execute_command`.
- `exit` — salir.

Casos de prueba automatizados:

```bash
python run_tests.py --clone https://github.com/openai/openai-cookbook
```

## Notas de la migración

- Las claves ya no vienen de `google.colab.userdata` sino de `.env` / entorno
  (con fallback a `input()` para la de OpenAI).
- El workspace pasó de `/content/workspace` (Colab) a `./workspace` (configurable
  con `AGENT_WORKSPACE`).
- La supervisión ahora hace *pretty-print* del `content` en `write_file` para poder
  revisarlo antes de aprobar (mejora sugerida en el análisis del Caso 2 del TP1).
