# SignalR Client Documentation

## Overview

This SignalR client is a Python implementation for connecting to and recording live timing data from a SignalR server, such as the F1 live timing service. It is designed to save raw or debug-mode data to a file for later analysis, not for real-time processing.

## Main Features

- Connects to a SignalR server using WebSockets.
- Subscribes to a set of topics (e.g., Heartbeat, CarData.z, TimingData, etc.).
- Saves received messages to a file, with optional debug mode for full message logging.
- Supports both command-line and programmatic usage.
- Handles connection, reconnection, and graceful shutdown.
- Logs to both file and stdout, with colored output for real data/events.

## Key Classes and Their Responsibilities

### SignalRClient

- **Purpose:** Main entry point for users. Handles connection, message processing, file output, and logging.
- **Constructor Arguments:**
  - `file_name`: Output file path for saving data.
  - `file_mode`: File mode ('a' for append, 'w' for overwrite).
  - `debug`: If True, saves full SignalR messages; otherwise, saves only the data part.
  - `timeout`: Inactivity timeout in seconds (set to 0 for no timeout).
  - `logger`: Optional custom logger.
- **Methods:**
  - `start()`: Starts the client, handling event loop setup.
  - `async_start()`: Async version for use in existing event loops.
  - `_run()`: Main async method for connection and message handling.
  - `_to_file(message)`: Writes messages to file and prints colored output.
  - `_on_message(msg)`: Handles incoming data messages.
  - `_on_debug(**data)`: Handles debug-mode messages.
  - `_supervise()`: Monitors for inactivity and triggers shutdown if needed.

### Transport

- **Purpose:** Manages the WebSocket connection and event loop for sending/receiving messages.
- **Key Methods:**
  - `start()`: Initiates the WebSocket connection and event loop.
  - `send(message)`: Queues a message to be sent.
  - `close()`: Queues a close event.

### WebSocketParameters

- **Purpose:** Handles negotiation and construction of the WebSocket URL and headers.
- **Key Methods:**
  - `_negotiate()`: Performs the SignalR negotiation step.
  - `_get_socket_url()`: Constructs the WebSocket URL for connection.

### Hub, HubServer, HubClient

- **Purpose:** Implements the SignalR hub pattern for subscribing to and handling messages.
- **HubServer:** Sends method invocations to the server.
- **HubClient:** Registers handlers for incoming messages and dispatches them.

### EventHook

- **Purpose:** Implements an async event system for message and error handling.

### Connection

- **Purpose:** Manages the overall SignalR connection, hub registration, and message dispatch.

## Message Handling

- Messages from the server are received as JSON objects.
- In normal mode, only the data part (`A` field) is saved.
- In debug mode, the full message is saved.
- The last received server message is stored and logged when the connection closes.

## Logging

- Logs are written to both a file and stdout.
- Real data/events are colorized in the console for visibility.
- Connection status, errors, and shutdowns are logged with appropriate levels.

## Usage

### Programmatic Example

```python
from signalf1 import SignalF1

client = SignalF1(file_name="./data/raw/session.log", debug=False)
client.start()
```

### Command-Line Example

```sh
python -m fastf1.livetiming save session.log
python -m fastf1.livetiming save --debug session_debug.log
```

### Debug Mode

- Use `--debug` or `debug=True` to save the full SignalR message for later extraction.
- Use the `extract` command to process debug-mode files into standard data files.

## File Output

- Each message is saved with a UTC timestamp and the message content.
- In debug mode, the file contains the full JSON message; otherwise, only the data payload.

## Error Handling

- Connection errors, timeouts, and server disconnects are logged.
- The client attempts graceful shutdown and logs the last server message before disconnect.

## Extending the Client

- Add new topics to the `self.topics` list in `SignalRClient` to subscribe to additional data.
- Register new handlers in `HubClient` for custom message processing.
- Customize logging by passing a custom logger to the client.

## Limitations

- Not designed for real-time data processing.
- Server-side disconnects (e.g., after 2 hours) are not automatically handled for seamless reconnection.
- Only supports Python 3.8 or 3.9 (as per original warning).

## Troubleshooting

- If you see "SignalR connection closed by server or finished.", the server is likely offline or not broadcasting.
- If you see exceptions in the logs, check the traceback for details and ensure your environment matches the requirements.
- For no timeout, ensure `timeout=0` is set.

## References

- Original SignalR Python client: <https://github.com/slazarov/python-signalr-client>
- Fast-F1 project: <https://theoehrly.github.io/Fast-F1/>
