"""Internal websocket transport and negotiation for the SignalR client."""

import asyncio
from json import dumps, loads
from urllib.parse import urlencode, urlparse, urlunparse

import requests
import websockets
from websockets.exceptions import ConnectionClosed

from ._signalr_events import CloseEvent, InvokeEvent

__all__ = ["Transport", "WebSocketParameters"]


class Transport:
  def __init__(self, connection):
    self._connection = connection
    self._ws_params = None
    self._conn_handler = None
    self.ws_loop = None
    self.invoke_queue = None
    self.ws = None
    self._set_loop_and_queue()

  def start(self):
    asyncio.set_event_loop(self.ws_loop)
    self._ws_params = WebSocketParameters(self._connection)
    self._connect()
    if not self.ws_loop.is_running():
      try:
        self.ws_loop.run_forever()
      finally:
        self._shutdown_loop()

  def send(self, message):
    self.ws_loop.call_soon_threadsafe(self.invoke_queue.put_nowait, InvokeEvent(message))

  def close(self):
    if self.ws_loop is None or self.ws_loop.is_closed():
      return
    self.ws_loop.call_soon_threadsafe(self.invoke_queue.put_nowait, CloseEvent())

  def _set_loop_and_queue(self):
    self.ws_loop = asyncio.new_event_loop()
    self.invoke_queue = asyncio.Queue()

  def _connect(self):
    self._conn_handler = self.ws_loop.create_task(self._socket())

  async def _socket(self):
    try:
      async with websockets.connect(
        self._ws_params.socket_url, additional_headers=self._ws_params.headers
      ) as self.ws:
        self._connection.started = True
        await self._master_handler(self.ws)
    finally:
      self._connection.started = False
      self.ws = None
      self._stop_loop()

  async def _master_handler(self, ws):
    consumer_task = asyncio.create_task(self._consumer_handler(ws))
    producer_task = asyncio.create_task(self._producer_handler(ws))
    done, pending = await asyncio.wait([consumer_task, producer_task], return_when=asyncio.FIRST_EXCEPTION)

    for task in pending:
      task.cancel()
    if pending:
      await asyncio.gather(*pending, return_exceptions=True)

    for task in done:
      try:
        task_exception = task.exception()
      except asyncio.CancelledError:
        continue
      if task_exception is not None and not isinstance(task_exception, ConnectionClosed):
        raise task_exception

  async def _consumer_handler(self, ws):
    while True:
      try:
        message = await ws.recv()
        if len(message) > 0:
          self._connection.logger.debug("Received raw message: %s", message)
          if self._connection.raw_message_handler is not None:
            await self._connection.raw_message_handler(message)
          data = loads(message)
          await self._connection.received.fire(**data)
      except ConnectionClosed:
        raise
      except Exception as exc:
        self._connection.logger.error(f"Exception in consumer handler: {exc}", exc_info=True)
        raise

  async def _producer_handler(self, ws):
    while True:
      try:
        event = await self.invoke_queue.get()
        if event is not None:
          if event.type == "INVOKE":
            await ws.send(dumps(event.message))
          elif event.type == "CLOSE":
            await ws.close()
            await ws.wait_closed()
            break
        else:
          break
        self.invoke_queue.task_done()
      except Exception as exc:
        raise exc

  def _stop_loop(self):
    if self.ws_loop is None or self.ws_loop.is_closed() or not self.ws_loop.is_running():
      return

    try:
      running_loop = asyncio.get_running_loop()
    except RuntimeError:
      running_loop = None

    if running_loop is self.ws_loop:
      self.ws_loop.stop()
    else:
      self.ws_loop.call_soon_threadsafe(self.ws_loop.stop)

  def _shutdown_loop(self):
    pending = asyncio.all_tasks(self.ws_loop)
    for task in pending:
      task.cancel()
    if pending:
      self.ws_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    self.ws_loop.run_until_complete(self.ws_loop.shutdown_asyncgens())
    self.ws_loop.close()


class WebSocketParameters:
  def __init__(self, connection):
    self.protocol_version = "1.5"
    self.raw_url = self._clean_url(connection.url)
    self.conn_data = self._get_conn_data(connection.hub)
    self.session = connection.session
    self.headers = None
    self.socket_conf = None
    connection.logger.info(f"Negotiating SignalR connection to {self.raw_url}")
    self._negotiate()
    connection.logger.info(f"Negotiation complete. Socket conf: {self.socket_conf}")
    self.socket_url = self._get_socket_url()
    connection.logger.info(f"WebSocket URL: {self.socket_url}")

  @staticmethod
  def _clean_url(url):
    if url[-1] == "/":
      return url[:-1]
    return url

  @staticmethod
  def _get_conn_data(hub):
    return dumps([{"name": hub}])

  @staticmethod
  def _format_url(url, action, query):
    return f"{url}/{action}?{query}"

  def _negotiate(self):
    if self.session is None:
      self.session = requests.Session()
    query = urlencode(
      {
        "connectionData": self.conn_data,
        "clientProtocol": self.protocol_version,
      }
    )
    url = self._format_url(self.raw_url, "negotiate", query)
    self.headers = dict(self.session.headers)
    request = self.session.get(url)
    self.headers["Cookie"] = self._get_cookie_str(request.cookies)
    self.socket_conf = request.json()

  @staticmethod
  def _get_cookie_str(request):
    return "; ".join(f"{name}={value}" for name, value in request.items())

  def _get_socket_url(self):
    ws_url = self._get_ws_url_from()
    query = urlencode(
      {
        "transport": "webSockets",
        "connectionToken": self.socket_conf["ConnectionToken"],
        "connectionData": self.conn_data,
        "clientProtocol": self.socket_conf["ProtocolVersion"],
      }
    )
    return self._format_url(ws_url, "connect", query)

  def _get_ws_url_from(self):
    parsed = urlparse(self.raw_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    url_data = (
      scheme,
      parsed.netloc,
      parsed.path,
      parsed.params,
      parsed.query,
      parsed.fragment,
    )
    return urlunparse(url_data)