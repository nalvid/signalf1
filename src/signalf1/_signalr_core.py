"""Internal hub and connection primitives for the SignalR client."""

import json
from collections.abc import Iterable

from ._signalr_events import EventHook
from ._signalr_transport import Transport

__all__ = ["Connection", "Hub", "HubClient", "HubServer", "messages_from_raw"]


class HubServer:
  def __init__(self, name, connection, hub):
    self.name = name
    self.__connection = connection
    self.__hub = hub

  def invoke(self, method, *data):
    message = {
      "H": self.name,
      "M": method,
      "A": data,
      "I": self.__connection.increment_send_counter(),
    }
    self.__connection.send(message)


class HubClient:
  def __init__(self, name, connection) -> None:
    self._name = name
    self._handlers = {}

    async def handle(**data):
      messages = data["M"] if "M" in data and len(data["M"]) > 0 else {}
      for inner_data in messages:
        hub = inner_data["H"] if "H" in inner_data else ""
        if hub.lower() == self.name().lower():
          method = inner_data["M"]
          message = inner_data["A"]
          handler = self._handlers.get(method)
          if handler is not None:
            await handler(message)

    connection.received += handle

  def name(self) -> str:
    return self._name

  def on(self, method, handler):
    if method not in self._handlers:
      self._handlers[method] = handler

  def off(self, method, handler):
    if self._handlers.get(method) is handler:
      del self._handlers[method]


class Hub:
  def __init__(self, name, connection) -> None:
    self.name = name
    self.server = HubServer(name, connection, self)
    self.client = HubClient(name, connection)


class Connection:
  protocol_version = "1.5"

  def __init__(self, url, session=None, logger=None):
    self.url = url
    self.__hubs = {}
    self.__send_counter = -1
    self.hub = None
    self.session = session
    self.raw_message_handler = None
    self.received = EventHook()
    self.error = EventHook()
    self.__transport = Transport(self)
    self.started = False
    self.logger = logger

    async def handle_error(**data):
      error = data["E"] if "E" in data else None
      if error is not None:
        await self.error.fire(error)

    self.received += handle_error

  def start(self):
    self.hub = list(self.__hubs)[0]
    self.__transport.start()

  def register_hub(self, name):
    if name not in self.__hubs:
      if self.started:
        raise RuntimeError("Cannot create new hub because connection is already started.")
      self.__hubs[name] = Hub(name, self)
      return self.__hubs[name]

  def increment_send_counter(self):
    self.__send_counter += 1
    return self.__send_counter

  def send(self, message):
    self.__transport.send(message)

  def close(self):
    self.__transport.close()


def messages_from_raw(records: Iterable):
  """Extract message payloads from recorded raw SignalR frames."""
  result = []
  error_count = 0
  for record in records:
    try:
      data = json.loads(record)
    except json.JSONDecodeError:
      error_count += 1
      continue
    messages = data["M"] if "M" in data and len(data["M"]) > 0 else {}
    for inner_data in messages:
      hub = inner_data["H"] if "H" in inner_data else ""
      if hub.lower() == "streaming":
        result.append(inner_data["A"])

  return result, error_count