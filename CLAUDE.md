# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A coding agent powered by an OpenAI LLM that explores repos, reads/writes/analyzes files, and runs tasks autonomously from natural-language instructions. It was migrated from the TP1 notebook (`tp/coding_agent_Fierro_Mangini.ipynb`) into a runnable Python project. Docs, comments, and prompts are in Spanish; keep new code consistent with that.

## Setup & commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY (and TAVILY_API_KEY for web_search)

python main.py                        # interactive chat (local workspace)
python main.py --clone <github-url>   # clone a repo, chdir into it, then chat
python run_tests.py --clone <url>     # run the automated test-case battery
```

There is no unit-test framework, linter, or build step. `run_tests.py` is a scripted battery of 7 natural-language task cases (in `EXPLICIT_TEST_CASES`) that each run the agent end-to-end against a real LLM — running it makes live API calls and can write files/execute commands in the cwd. To run a single case, edit that list or slice it in `run(harness, ...)`.

Env vars (`.env` or environment): `OPENAI_API_KEY` (required), `TAVILY_API_KEY` (optional — without it `web_search` returns an "unavailable" stub), `OPENAI_MODEL` (default `gpt-4o`), `AGENT_WORKSPACE` (default `./workspace`, where repos are cloned).

## Architecture

The agent is a tool-calling loop over the OpenAI chat completions API. Wiring flows: `factory.build_harness()` reads env config, builds the OpenAI client and tool map, and returns a `Harness`; the entrypoints (`main.py`, `run_tests.py`) drive it.

- **`agent/tools.py`** — the 5 tool implementations: `read_file`, `list_files`, `write_file`, `execute_command`, `web_search`. Each returns a string (success text or an `Error: ...` message — tools never raise; errors go back to the LLM as content). `web_search` is built via `make_web_search(tavily_api_key)` so it can degrade to a stub.
- **`agent/llm.py`** — the OpenAI client, `SYSTEM_MESSAGE`, `MODEL`, and `TOOLS` (the OpenAI function schema). This schema is the source of truth the LLM sees; it must be kept in sync with the actual function signatures in `tools.py`. `call_llm()` is a single turn returning `(message, error)`.
- **`agent/harness.py`** — `Harness.run_conversation()` is the core loop: call LLM → if it returned `tool_calls`, execute each and append `role:"tool"` results, repeat; else return the final text. Two extra modes live here: **Plan Mode** (`plan_mode_turn`/`generate_plan` — a separate no-tools LLM call that proposes a numbered plan and iterates on user feedback before execution) and **Supervision** (`_confirm_action` — human-in-the-loop confirmation, gated on `WRITE_TOOLS = {"write_file", "execute_command"}`).
- **`agent/factory.py`** — the only place tool name → function mapping is defined (`tool_map`); add new tools here plus in `tools.py` and the `TOOLS` schema in `llm.py`.
- **`agent/repo.py`** — `clone_repo()` shallow-clones a GitHub repo into `AGENT_WORKSPACE` and `chdir`s into it, so all relative tool paths resolve inside the cloned repo.

### Things to know when editing

- Adding a tool requires three coordinated changes: the function in `tools.py`, its entry in `TOOLS` (schema) in `llm.py`, and its entry in `tool_map` in `factory.py`.
- The harness filters LLM-provided args against the function's real signature via `inspect.signature` before calling, so extra/hallucinated args are dropped silently.
- `conversation_history` mixes raw OpenAI message objects (assistant turns) and plain dicts (system/user/tool turns); `_planning_history` normalizes this when building the planning prompt. Preserve that duality if you touch history handling.
- Plan Mode and Supervision are toggled at runtime via chat commands (`/plan on|off|status`, `/supervise on|off|status`) handled in `main.py`, not via config.
- `execute_command` runs `subprocess.run(..., shell=True)` and `write_file` overwrites without confirmation unless Supervision is on — the loop can modify the filesystem of whatever cwd it runs in.
