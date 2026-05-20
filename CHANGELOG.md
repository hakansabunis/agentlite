# Changelog

All notable changes to **agentlite** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `agent.stream(message)` — streaming with full tool-loop integration.
  Yields rich events (`text`, `tool_use_start`, `tool_result`, `done`) so
  callers can render token-by-token output and react to tool calls live.
- `agentlite.testing` module — public testing helpers:
  - `MockClient` — scripted mock of the Anthropic client (queues
    responses for `.create()` and streams for `.stream()`).
  - `text_response`, `tool_use_response` — build non-streaming responses.
  - `text_stream`, `tool_use_stream` — build streaming event sequences,
    including realistic chunked `input_json_delta` for tool inputs.
  - Lets users write unit tests against their agent code without hitting
    the real Anthropic API. Coverage of `agentlite.testing` itself: 96%.
- Typed exception hierarchy under `agentlite.errors` (also re-exported from
  the package root):
  - `AgentError` — base class; users can `except AgentError` to catch all
    agentlite-raised errors.
  - `AgentMaxTurnsError` — raised by `Agent.run()` when `max_turns` is
    exceeded (replaces the generic `RuntimeError` from v0.1).
  - `UnexpectedStopReasonError` — raised when the model stops with an
    unhandled `stop_reason` (e.g. `"refusal"`).
  - `ToolNotFoundError`, `ToolExecutionError`, `PermissionDeniedError` —
    available as classes for user code; not raised by default (fail-safe:
    these conditions are reported back to the model via `tool_result`).
- `tool_choice` parameter on `Agent.__init__` and `Agent.run()`: pin a
  specific tool, force any tool, or disable tools entirely.
- `subagent(...)` factory — creates a `Tool` that, when called by a
  parent agent, internally runs a fresh `Agent` with its own system
  prompt, tools, model, and `max_turns`. The parent agent treats it
  as a regular tool; the sub-agent's full loop runs in isolation and
  only its final text returns to the parent.
  Supports cheap-model delegation (default `claude-haiku-4-5`),
  context isolation, and independent client injection for testing.
- `Usage` aggregator: per-turn token / cache / cost data is now collected
  across the entire loop and exposed as `result.usage`.

### Changed
- `Agent.run()` now returns an `AgentResult` object instead of a bare
  string. The final text is at `result.text`; usage is at `result.usage`.
  **Breaking**: callers using `text = agent.run(...)` need `text = agent.run(...).text`.

## [0.1.0] - 2026-05-20

### Added
- Initial release.
- `@tool` decorator that turns Python functions into Claude-compatible
  tools (introspection-based JSON Schema generation).
- `Agent` class with built-in tool-use loop, `max_turns` safety brake,
  and prompt caching enabled by default.
- `Agent.stream_text()` for plain text streaming (no tool integration).
- Permission system: `@tool(read_only=True)` and
  `@tool(requires_confirmation=True)` with pluggable `confirm_fn`.
- 17 unit tests, 80% coverage, GitHub Actions CI on Python 3.10–3.13.

[Unreleased]: https://github.com/hakansabunis/agentlite/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hakansabunis/agentlite/releases/tag/v0.1.0
