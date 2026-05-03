"""Internal async event primitives for the SignalR client."""

__all__ = ["CloseEvent", "Event", "EventHook", "InvokeEvent"]


class Event:
  """Base event type for transport commands."""


class InvokeEvent(Event):
  def __init__(self, message):
    self.type = "INVOKE"
    self.message = message


class CloseEvent(Event):
  def __init__(self):
    self.type = "CLOSE"


class EventHook:
  def __init__(self):
    self._handlers = []

  def __iadd__(self, handler):
    self._handlers.append(handler)
    return self

  def __isub__(self, handler):
    self._handlers.remove(handler)
    return self

  async def fire(self, *args, **kwargs):
    for handler in self._handlers:
      await handler(*args, **kwargs)