# SignalR Client -- Project Analysis

This document provides a technical analysis of the SignalR client codebase in the `signalf1` project,
focused on identifying issues, architectural concerns, and concrete refactoring opportunities.

---

## 1. File and Module Overview

| File | Lines | Purpose |
|------|-------|---------|
| `_client.py` | ~600 | SignalR transport, connection, hub, event system, and the main `SignalRClient` class |
| `_data.py` | ~470 | `LiveTimingData` for loading/parsing saved log files; time-parsing utilities |
| `extractor.py` | ~430 | Log file parsing and data extraction (dataclasses, decompression) |
| `log_extractor.py` | ~430 | Near-identical duplicate of `extractor.py` |
| `_server.py` | ~1 | Stub: `class SignalF1Server: ...` |
| `__init__.py` | ~7 | Public API re-exports |
| `__main__.py` | ~80 | CLI entry point (partially commented out / contains dead code) |
| `tests/client_test.py` | 0 | Empty -- no tests exist |

---

## 2. Critical Issues

### 2.1 Deprecated and Broken asyncio API Usage

The `Transport` class uses asyncio APIs that have been deprecated since Python 3.8 and removed in Python 3.10+:

- `asyncio.Task(..., loop=self.ws_loop)` -- the `loop` parameter was removed.
- `asyncio.ensure_future(..., loop=self.ws_loop)` -- same issue.
- `asyncio.wait([...], return_when=...)` -- passing coroutines directly is no longer supported.
- `websockets.connect(..., loop=loop)` -- the `loop` parameter was removed in `websockets` 11+.

These will raise `TypeError` on Python 3.12+ which is the project's minimum target (`requires-python = ">=3.12"`).

**Affected locations:**
- `Transport.send()` -- `asyncio.Task(..., loop=...)`
- `Transport.close()` -- `asyncio.Task(..., loop=...)`
- `Transport._connect()` -- `asyncio.ensure_future(..., loop=...)`
- `Transport._socket()` -- `websockets.connect(..., loop=...)`
- `Transport._master_handler()` -- `asyncio.ensure_future(..., loop=...)`

### 2.2 Pinned websockets Version with API Mismatch

`pyproject.toml` pins `websockets==11.0.1`. The code uses `websockets.connect()` with the `loop` parameter which was already removed in websockets 10.x. This means the code likely fails at runtime.

### 2.3 No Tests

`tests/client_test.py` is empty. There are zero tests for any component. No transport, connection, parsing, or extraction logic is validated.

### 2.4 Duplicate Modules

`extractor.py` and `log_extractor.py` are nearly identical files with the same dataclass definitions (`LogEntry`, `SessionInfo`, `DriverInfo`, `TimingData`) and the same extraction functions. The only differences are minor type-hint style (`list[X]` vs `List[X]`, `dict` vs `Dict`). One of these files is redundant and should be removed.

### 2.5 Inconsistent `DriverList` Key Casing

In `extractor.py`, the driver list topic is matched as `"Driverlist"` (lowercase 'l'), while in `log_extractor.py` it is `"DriverList"` (uppercase 'L'). The server sends `"DriverList"` and the subscription topic in `SignalRClient.topics` is also `"DriverList"`. The `extractor.py` variant will therefore never match driver data.

---

## 3. Architectural Issues

### 3.1 God-File: `_client.py`

`_client.py` contains 10+ classes and standalone functions in a single ~600-line file:

- `Transport` -- WebSocket transport layer
- `WebSocketParameters` -- connection negotiation
- `Event`, `InvokeEvent`, `CloseEvent` -- event types
- `HubServer`, `HubClient`, `Hub` -- SignalR hub abstraction
- `EventHook` -- async event dispatcher
- `Connection` -- connection manager
- `messages_from_raw()` -- log parsing utility function
- `ColorFormatter` -- logging formatter
- `SignalRClient` -- the main client

These should be separated into focused modules with clear responsibilities.

### 3.2 Tight Coupling Between Transport and Connection

`Transport` holds a direct reference to `Connection` and accesses `Connection.logger`, `Connection.received`, `Connection.started`, `Connection.url`, `Connection.hub`, and `Connection.session`. `Connection` in turn creates `Transport` in its constructor. This circular dependency makes both classes untestable in isolation.

### 3.3 Mixed Sync/Async Execution Model

The client mixes synchronous and asynchronous patterns in complex, error-prone ways:

- `Transport.start()` calls `self.ws_loop.run_forever()` synchronously, blocking the thread.
- `SignalRClient._run()` uses `concurrent.futures.ThreadPoolExecutor` to run `self._connection.start()` in a thread pool, which internally calls `run_forever()`.
- `SignalRClient._on_message()` uses a thread pool executor to offload `_to_file()`, which does synchronous file I/O.
- `SignalRClient.start()` tries to detect if an event loop is running and either uses `asyncio.run()` or raises an error.

This threading model is fragile and hard to reason about.

### 3.4 No Reconnection Logic

When the WebSocket connection drops, the client logs and exits. There is no retry or reconnect mechanism. For a live timing client that may run for hours during a race session, this is a significant reliability gap.

### 3.5 No Graceful Shutdown

There is no proper cleanup on exceptions or system signals. The `_output_file` may not be flushed/closed on unexpected disconnects. The event loop shutdown is not orderly.

---

## 4. Code Quality Issues

### 4.1 Dead Code in `__main__.py`

The file contains a large block of commented-out argparse code from the original `fastf1.livetiming` module, followed by the actual `main()` function. The commented-out code was never adapted and serves no purpose.

### 4.2 Debug Handler Does Timeout Logic

`_on_debug()` contains the exact same timeout/supervision logic as `_supervise()`. When `debug=True`, `_supervise()` is still launched via `_async_start()`, creating duplicate supervision. Additionally, `_on_debug` is registered as both `connection.error` handler and `connection.received` handler, meaning it fires on every message in debug mode.

### 4.3 Hardcoded Self-Timeout Override

The constructor sets `self.timeout = 0` regardless of the `timeout` parameter passed by the user:

```python
def __init__(self, ..., timeout: int = 60, ...):
    ...
    self.timeout = 0  # Never timeout
```

The constructor signature advertises a default of 60 seconds, but the implementation forces it to 0 (disabled). This is misleading.

### 4.4 Inline Import and Print Statements in `_to_file`

`_to_file()` contains `import json` inline (json is already imported at module level) and unconditional `print()` statements with ANSI escape codes. The method mixes file-writing responsibility with console output, violating separation of concerns.

### 4.5 String-Based Event Type Dispatch

`InvokeEvent` and `CloseEvent` use a string `.type` field (`"INVOKE"`, `"CLOSE"`) for dispatch in `_producer_handler`. This is fragile. A proper pattern would use `isinstance` checks or an enum.

### 4.6 No Type Annotations on Core Classes

`Transport`, `WebSocketParameters`, `Connection`, `Hub`, `HubServer`, `EventHook` have no type annotations on attributes or most methods. Only `SignalRClient` has partial annotations.

### 4.7 Raw Dict Key Access for SignalR Protocol

Protocol fields like `"H"`, `"M"`, `"A"`, `"I"`, `"E"` are accessed via string literals scattered throughout the codebase. These magic strings should be constants or modeled as typed structures.

### 4.8 Cookie Handling Uses `%` Formatting

`WebSocketParameters._get_cookie_str()` uses old-style `"%s=%s" %` formatting, inconsistent with the rest of the codebase which uses f-strings.

---

## 5. Dependency and Configuration Issues

### 5.1 Unnecessary Dependencies

- `numpy` and `pandas` are listed as core dependencies but are only used in `_data.py` for the `delta_time()` function, which is itself marked as deprecated and carries a warning that it will be removed.
- `aiohttp` is listed as a dependency but not imported anywhere in the codebase.
- `python-dotenv` is listed but never used.

### 5.2 uvloop Import Side Effect

At module level, `_client.py` unconditionally tries to import `uvloop` and set it as the global event loop policy. This is a global side effect that happens on import, which can interfere with other code or tests.

### 5.3 Build Artifacts in Repository

The `build/` directory contains compiled artifacts with a copy of the source code. This should not be in version control.

---

## 6. Naming and API Issues

### 6.1 Inconsistent Public Names

- The package exports `SignalF1` which is actually `SignalRClient` internally.
- `LiveTimingData` references `fastf1` in its docstrings but is part of `signalf1`.
- `messages_from_raw()` is a standalone function in `_client.py` but logically belongs with data processing.

### 6.2 FastF1 Remnants

The codebase was forked from FastF1 and still contains FastF1-specific references:

- Docstrings reference `:mod:\`fastf1.api\``, `:mod:\`fastf1.core\``, `:class:\`~fastf1.livetiming.client.SignalRClient\``
- `_data.py` type hints reference `"fastf1.core.Lap"` and `"fastf1.core.Telemetry"`
- `__main__.py` references `fastf1.livetiming`
- `_async_start()` logs `"Starting FastF1 live timing client VERSION]"`

### 6.3 Ambiguous `_server.py`

`_server.py` exports a stub class `SignalF1Server` that has no implementation. It is re-exported from `__init__.py`. This is confusing for users and signals incomplete design.

---

## 7. Suggested Refactoring Plan

Priority is ordered from most impactful to least.

### Phase 1 -- Fix Critical Runtime Issues

1. Remove all deprecated `loop=` parameters from asyncio and websockets calls.
2. Rewrite `Transport` to use modern async patterns (`asyncio.create_task`, structured concurrency).
3. Fix the `self.timeout = 0` override to respect the constructor parameter.
4. Remove or update the pinned `websockets==11.0.1` dependency.

### Phase 2 -- Clean Up Module Structure

1. Delete `log_extractor.py` (duplicate of `extractor.py`).
2. Fix the `"Driverlist"` casing bug in `extractor.py`.
3. Split `_client.py` into focused modules:
   - `transport.py` -- `Transport`, `WebSocketParameters`
   - `hub.py` -- `Hub`, `HubServer`, `HubClient`
   - `events.py` -- `EventHook`, `Event`, `InvokeEvent`, `CloseEvent`
   - `connection.py` -- `Connection`
   - `client.py` -- `SignalRClient`
4. Remove dead code from `__main__.py`.
5. Remove or hide `_server.py` stub.

### Phase 3 -- Improve Reliability

1. Add reconnection logic with exponential backoff.
2. Add proper signal handling and graceful shutdown.
3. Fix debug mode duplicate supervision.
4. Ensure file handles are always properly closed (use context managers).

### Phase 4 -- Clean Up Dependencies and References

1. Remove unused dependencies: `aiohttp`, `python-dotenv`.
2. Move `numpy`/`pandas` to optional dependencies (they are required only for the deprecated `delta_time`).
3. Remove all FastF1-specific docstring references and type hints.
4. Remove `build/` from version control; add to `.gitignore`.

### Phase 5 -- Add Tests and Type Safety

1. Write unit tests for message parsing (`messages_from_raw`, `_parse_line`, `_fix_json`).
2. Write integration tests for `WebSocketParameters._negotiate()` with mocked HTTP.
3. Write tests for `extractor.py` functions.
4. Add type annotations to all core classes.
5. Define constants or an enum for SignalR protocol fields (`"H"`, `"M"`, `"A"`, etc.).

---

## 8. Class Dependency Map

```
SignalRClient
  |-- Connection
  |     |-- Transport
  |     |     |-- WebSocketParameters
  |     |     |     |-- requests.Session (HTTP negotiation)
  |     |     |-- websockets (WebSocket I/O)
  |     |     |-- asyncio (event loop, task queue)
  |     |-- Hub
  |     |     |-- HubServer (outbound invocations)
  |     |     |-- HubClient (inbound message dispatch)
  |     |-- EventHook (received, error events)
  |-- logging (FileHandler, StreamHandler, ColorFormatter)
  |-- file I/O (output file)

LiveTimingData (independent, reads from saved log files)

extractor.py / log_extractor.py (independent, reads from saved log files)
```

---

## 9. SignalR Protocol Flow (Current Implementation)

```
1. SignalRClient.start()
2.   -> Connection.start()
3.      -> Transport.start()
4.         -> WebSocketParameters.__init__()
5.            -> HTTP GET /negotiate (gets ConnectionToken)
6.            -> Build wss:// URL with token
7.         -> websockets.connect(wss_url)
8.         -> _master_handler() spawns:
9.            a) _consumer_handler: recv loop -> fire Connection.received
10.           b) _producer_handler: send loop <- invoke_queue
11. HubClient dispatches received messages to registered handlers
12. SignalRClient._on_message() writes data to file
13. SignalRClient._supervise() monitors for timeout
```

---

## 10. Lines of Code Summary

| Category | Approximate LOC |
|----------|----------------|
| SignalR transport + connection (`_client.py`) | 600 |
| Data parsing (`_data.py`) | 470 |
| Log extraction (`extractor.py`) | 430 |
| Duplicate extraction (`log_extractor.py`) | 430 |
| Entry points (`__init__.py`, `__main__.py`) | 90 |
| Tests | 0 |
| **Total** | **~2020** |
| **Effective (excluding duplicates/dead code)** | **~1400** |
