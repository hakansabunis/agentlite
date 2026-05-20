# agentlite

[![PyPI](https://img.shields.io/pypi/v/agentlite-py.svg)](https://pypi.org/project/agentlite-py/)
[![tests](https://github.com/hakansabunis/agentlite/workflows/tests/badge.svg)](https://github.com/hakansabunis/agentlite/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> A small, focused library for building Claude-powered agents in Python.
> Minimal abstractions, prompt caching done right, permissions as a first-class concept.

## What does this project do?

**agentlite** is a tiny (~2,000 lines) Python library that turns plain Python functions into tools an LLM can call, then runs the full agent loop for you — sending the request to Claude, executing the tools Claude asks for, feeding the results back, and stopping when Claude is done. It bakes in three things most lightweight agent libraries skip: **prompt caching is on by default** (~80% input cost reduction on repeated requests), **permission gating is first-class** (mark a tool as `requires_confirmation=True` and the user is asked before it runs), and **a `max_turns` safety brake** prevents runaway loops. You write the tools, you write the system prompt, the library handles the orchestration — no chains, no graphs, no 150K lines of framework to debug.

```python
from agentlite import Agent, tool

@tool
def get_weather(city: str) -> str:
    """Return current weather for a city."""
    return f"{city}: 22°C, sunny"

agent = Agent(model="claude-opus-4-7", tools=[get_weather])
agent.run("What's the weather in Istanbul?")
```

## Why agentlite?

If you've ever tried to build a Claude agent in Python you've probably faced this choice:

- **Anthropic SDK directly** → fast but you write the agent loop, retry logic, permission handling, and prompt caching yourself.
- **LangChain** → batteries included but ~150K lines of abstractions to navigate, and debugging often means reading the framework's source.

**agentlite** sits in between: ~2,000 lines of focused code that handles the agent loop, tool definitions, prompt caching, and permissions — and gets out of your way for everything else.

## Status

🚧 **Alpha** (v0.2.0) — under active development. API may change before v1.0.
See [CHANGELOG.md](CHANGELOG.md) for the full release history.

## Installation

```bash
pip install agentlite-py
```

> The PyPI distribution name is **`agentlite-py`** (the bare `agentlite` is taken by an unrelated package).
> The Python import is still `agentlite`: `from agentlite import Agent, tool`.

Requires Python 3.10+. Get an Anthropic API key from [console.anthropic.com](https://console.anthropic.com).

## Quick start

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
from agentlite import Agent, tool

@tool
def search_files(pattern: str) -> list[str]:
    """Find files matching a glob pattern."""
    from glob import glob
    return glob(pattern)

@tool
def read_file(path: str) -> str:
    """Read a text file's contents."""
    return open(path, encoding="utf-8").read()

agent = Agent(
    model="claude-opus-4-7",
    system="You help users explore their codebase.",
    tools=[search_files, read_file],
)

agent.run("Find all Python files and summarize the largest one.")
```

## Features (v0.2.0)

- **`@tool` decorator** — type hints become JSON Schema, docstring becomes description.
- **Built-in agent loop** with `max_turns` safety brake.
- **`agent.stream()`** — full streaming with tool-loop integration. Yields
  `TextDeltaEvent`, `ToolUseEvent`, `ToolResultEvent`, `DoneEvent` so you can
  render live token output AND react to tool calls.
- **Prompt caching by default** — system prompt + tools cached automatically.
- **`subagent(...)` factory** — delegate sub-tasks to isolated agents without
  polluting parent context. Sub-agents are exposed as tools.
- **Permission system** — `@tool(requires_confirmation=True)` with pluggable
  `confirm_fn` (terminal default, override for GUI/Slack/web).
- **`tool_choice` control** — `"auto"` / `"any"` / `"none"` / specific tool name.
- **Typed exceptions** — `AgentError` base + 5 subclasses, structured fields
  (`.max_turns`, `.tool_name`, `.original`, `.stop_reason`).
- **`Usage` tracking** — accumulated tokens after each run via `agent.last_usage`,
  with `.estimate_cost_usd(model)` for built-in pricing.
- **`agentlite.testing`** — `MockClient` + factories for testing your agent
  code without hitting the real API.

## Comparison

| | LangChain | OpenAI Agents | Anthropic SDK (raw) | **agentlite** |
|---|---|---|---|---|
| LoC to read | ~150K | ~5K | — | **~2K** |
| Prompt caching | manual | none | manual | **automatic** |
| Permission model | none | none | none | **first-class** |
| Multi-agent | complex | handoffs | none | **`@subagent`** |
| Learning curve | steep | medium | low | **very low** |

## Documentation

Full docs and design notes at: **https://hakansabunis.com**

## License

MIT © 2026 Hakan Sabunis
