# agentlite

[![tests](https://github.com/hakansabunis/agentlite/workflows/tests/badge.svg)](https://github.com/hakansabunis/agentlite/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> A small, focused library for building Claude-powered agents in Python.
> Minimal abstractions, prompt caching done right, permissions as a first-class concept.

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

🚧 **Alpha** (v0.1.0) — under active development. API may change before v1.0.

## Installation

```bash
pip install agentlite
```

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

## Features

- **`@tool` decorator** — type hints become JSON Schema, docstring becomes description.
- **Built-in agent loop** with `max_turns` safety brake.
- **Streaming support** — `agent.stream_text()` for token-by-token output.
- **Prompt caching by default** — system prompt + tools cached automatically;
  typically ~80% input cost reduction on repeated requests.
- **Verifiable caching** — inspect `response.usage.cache_read_input_tokens`
  to confirm hits (no silent failures).
- **Permission system** (planned) — mark tools as `requires_confirmation` or `read_only`.
- **Sub-agent support** (planned) — delegate sub-tasks without polluting context.

## Comparison

| | LangChain | OpenAI Agents | Anthropic SDK (raw) | **agentlite** |
|---|---|---|---|---|
| LoC to read | ~150K | ~5K | — | **~2K** |
| Prompt caching | manual | none | manual | **automatic** |
| Permission model | none | none | none | **first-class** |
| Multi-agent | complex | handoffs | none | **`@subagent`** |
| Learning curve | steep | medium | low | **very low** |

## Documentation

Full docs and design notes at: **https://hakansabunis.github.io/blog/**

## License

MIT © 2026 Hakan Sabunis
