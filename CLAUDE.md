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

The agent is a tool-calling loop over the OpenAI chat completions API. Wiring flows: `factory.build_harness()` reads env config, builds the OpenAI client and tool map, and returns a `Harness`; the entrypoints (`main.py`, `run_tests.py`) drive it. On top of that single-agent base sits a **multi-agent layer** (TP Final): `factory.build_orchestrator()` returns an `Orchestrator` that delegates to subagents; `analyze.py` drives the "analyze a repo → report" use case.

- **`agent/tools.py`** — the 5 tool implementations: `read_file`, `list_files`, `write_file`, `execute_command`, `web_search`. Each returns a string (success text or an `Error: ...` message — tools never raise; errors go back to the LLM as content). `web_search` is built via `make_web_search(tavily_api_key)` so it can degrade to a stub.
- **`agent/llm.py`** — the OpenAI client, `SYSTEM_MESSAGE`, `PLANNING_SYSTEM_MESSAGE`, `MODEL`, and `TOOL_SCHEMAS` (the OpenAI function schema). This schema is the source of truth the LLM sees; it must be kept in sync with the actual function signatures in `tools.py`. `call_llm()` is a single turn returning `(message, error)`; pass `tools=None` for a no-tools call (e.g. Plan Mode). `schemas_for(names)` returns the schema subset for a subagent's allowed tools.
- **`agent/harness.py`** — `Harness.run_conversation()` is the core loop: call LLM → if it returned `tool_calls`, execute each and append `role:"tool"` results, repeat; else return the final text. Each `Harness` carries its own `system_message` (default `SYSTEM_MESSAGE`), so subagents specialize by reusing the same engine. Two extra modes live here: **Plan Mode** (`plan_mode_turn`/`generate_plan` — a separate no-tools LLM call that proposes a numbered plan and iterates on user feedback before execution) and **Supervision** (`_confirm_action` — human-in-the-loop confirmation, gated on the `approval` list from `agent.config.yaml`).
- **`agent/policies.py`** + **`agent.config.yaml`** (raíz) — capa de políticas que valida cada tool call **antes** de ejecutarla. `agent.config.yaml` declara permisos de `read` / `write` / `commands` (cada uno con `allow`/`deny` de patrones glob) y una lista `approval`. `load_policies()` carga y valida la config al iniciar (acá sí lanza: config malformada = error de arranque). `Policies.check(tool, args)` devuelve `(allowed, reason)` sin lanzar; `Harness._execute_tool_call` la consulta y, si deniega, appendea un `role:"tool"` con el motivo como `Error: ...` (mismo patrón que las tools). `deny` tiene prioridad; `allow` vacío = permitir todo salvo `deny`. La lista `approval` define, cuando la Supervisión está activa, qué tools piden confirmación (es la única fuente de verdad; se pasa a todos los `Harness`, incluidos los subagentes). `web_search` no tiene sección: no está gobernada por políticas.
- **`agent/state.py`** — `TaskState`, the state shared across the orchestrator and every subagent (request, progress, per-subagent results, sources, modified files, observations).
- **`agent/subagents/`** — each subagent is a `Harness` with its own system prompt and a restricted `tool_map`, wrapped by `Subagent` (`base.py`) which runs a task in a fresh conversation and records the result into `TaskState`. `explorer.py` (`build_explorer`) is a read-only subagent (`read_file`, `list_files`) that reports structure/deps/conventions.
- **`agent/orchestrator.py`** — `Orchestrator` (the main agent): creates the `TaskState`, delegates to subagents as if they were tools, and renders the report. Skeleton pipeline is a single Explorer step; new subagents plug into `run` without changing the shape.
- **`agent/factory.py`** — the only place tool name → function mapping is defined (`tool_map`); add new tools here plus in `tools.py` and the `TOOL_SCHEMAS` schema in `llm.py`. `build_orchestrator()` wires the multi-agent layer.
- **`repo.py`** (project root, not part of the `agent/` package) — `clone_repo()` shallow-clones a GitHub repo into `AGENT_WORKSPACE` and `chdir`s into it, so all relative tool paths resolve inside the cloned repo. It lives outside `agent/` because it's environment setup the entry points run before the agent exists, not an agent capability.

### Things to know when editing

- Adding a tool requires three coordinated changes: the function in `tools.py`, its entry in `TOOL_SCHEMAS` (schema) in `llm.py`, and its entry in `tool_map` in `factory.py`.
- The harness filters LLM-provided args against the function's real signature via `inspect.signature` before calling, so extra/hallucinated args are dropped silently.
- `conversation_history` mixes raw OpenAI message objects (assistant turns) and plain dicts (system/user/tool turns); `_planning_history` normalizes this when building the planning prompt. Preserve that duality if you touch history handling.
- Plan Mode and Supervision are toggled at runtime via chat commands (`/plan on|off|status`, `/supervise on|off|status`) handled in `main.py`, not via config.
- `execute_command` runs `subprocess.run(..., shell=True)` and `write_file` overwrites without confirmation unless Supervision is on — the loop can modify the filesystem of whatever cwd it runs in.

## Code conventions & design principles

These are the maintainer's standing preferences. Apply them to new code and when
touching existing code; they take precedence over generic defaults. The guiding
goal: **anyone should be able to open a file and read it top-to-bottom without
jumping between files to understand it.**

- **One level of abstraction per function.** A high-level function orchestrates
  the *what*; the concrete *how* is extracted below it. Example: `run_conversation`
  says "for each tool call, execute it" and delegates the parsing/validation/
  supervision mechanics to `_execute_tool_call`. Don't mix `json.loads`,
  `inspect.signature`, dict-building, etc. into an orchestration-level function.
- **Reading locality beats hiding trivia.** Do NOT extract a helper (or push a
  value behind an indirection) when the detail is trivial and stable — it forces
  a jump for no benefit. Extract ONLY when there is real duplication or a genuine
  mix of abstraction levels. When in doubt, keep it inline and readable in place.
- **Prefer a single exit / single append over duplicated tails.** When branches
  differ only in a value, compute the value in the branches and do the shared
  action once (e.g. `_execute_tool_call` builds `content` per case, appends once).
- **Comments explain *why*, not *what*.** Document the design decision, not the
  mechanics the code already shows.
- **Honest, unambiguous names.** Disambiguate overloaded terms: `TOOL_SCHEMAS`
  (what the LLM sees) vs `tools.py` (implementations). Names like `run_tests.py`
  should mean what they say (it's actually a demo battery, not a test suite).
- **Location reflects ownership.** Things that aren't the agent live outside the
  `agent/` package (e.g. `repo.py` is environment setup, so it sits at the root).
- **Consistency; no unexplained asymmetry.** All LLM turns go through `call_llm`
  (single OpenAI boundary) — don't call the API raw. If you must leave an
  asymmetry, justify it in a comment.
- **Atomic, single-purpose commits.** One logical change per commit; split a file
  across commits with `git add -p` when needed. If you notice an unrelated change
  mixed into your diff, surface it before committing rather than bundling it.
- **Keep this file honest.** When a refactor changes a name/flow documented here,
  update the relevant section in the same change (as was done for `TOOL_SCHEMAS`).

## Agent skills

### Issue tracker

Issues are tracked in this repo's GitHub Issues via the `gh` CLI; external PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` + `docs/adr/` at the repo root). See `docs/agents/domain.md`.
