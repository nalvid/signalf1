"""
Python SignalR Hub client.

This module is based on the excellent work of Stanislav Lazarov.
Since the original module is no longer developed it's been integrated
into Fast-F1. Original source https://github.com/slazarov/python-signalr-client

"""

import asyncio
import concurrent.futures
import datetime
import json
import logging
import sys
import time
from collections.abc import Iterable
from json import dumps, loads
from urllib.parse import urlencode, urlparse, urlunparse

import requests
import websockets
from websockets.exceptions import ConnectionClosed as ConnectionClosed

try:
  import uvloop

  asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ModuleNotFoundError:
  pass


__all__ = ["Hub"]


class Transport:
  def __init__(self, connection):
    self._connection = connection
    self._ws_params = None
    self._conn_handler = None
    self.ws_loop = None
    self.invoke_queue = None
    self.ws = None
    self._set_loop_and_queue()

  # ===================================
  # Public Methods

  def start(self):
    self._ws_params = WebSocketParameters(self._connection)
    self._connect()
    if not self.ws_loop.is_running():
      self.ws_loop.run_forever()

  def send(self, message):
    asyncio.Task(self.invoke_queue.put(InvokeEvent(message)), loop=self.ws_loop)

  def close(self):
    asyncio.Task(self.invoke_queue.put(CloseEvent()), loop=self.ws_loop)

  # -----------------------------------
  # Private Methods

  def _set_loop_and_queue(self):
    try:
      self.ws_loop = asyncio.get_event_loop()
    except RuntimeError:
      self.ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self.ws_loop)
    self.invoke_queue = asyncio.Queue()

  def _connect(self):
    self._conn_handler = asyncio.ensure_future(self._socket(self.ws_loop), loop=self.ws_loop)

  async def _socket(self, loop):
    async with websockets.connect(
      self._ws_params.socket_url, extra_headers=self._ws_params.headers, loop=loop
    ) as self.ws:
      self._connection.started = True
      await self._master_handler(self.ws)

  async def _master_handler(self, ws):
    consumer_task = asyncio.ensure_future(self._consumer_handler(ws), loop=self.ws_loop)
    producer_task = asyncio.ensure_future(self._producer_handler(ws), loop=self.ws_loop)
    done, pending = await asyncio.wait([consumer_task, producer_task], return_when=asyncio.FIRST_EXCEPTION)

    for task in pending:
      task.cancel()

    try:
      consumer_exception = consumer_task.exception()
    except asyncio.CancelledError:
      pass
    else:
      if not isinstance(consumer_exception, websockets.exceptions.ConnectionClosedOK):
        raise consumer_exception

  async def _consumer_handler(self, ws):
    while True:
      message = await ws.recv()
      if len(message) > 0:
        data = loads(message)
        await self._connection.received.fire(**data)

  async def _producer_handler(self, ws):
    while True:
      try:
        event = await self.invoke_queue.get()
        if event is not None:
          if event.type == "INVOKE":
            await ws.send(dumps(event.message))
          elif event.type == "CLOSE":
            await ws.close()
            while ws.open is True:
              await asyncio.sleep(0.1)
            else:
              self._connection.started = False
              break
        else:
          break
        self.invoke_queue.task_done()
      except Exception as e:
        raise e


class WebSocketParameters:
  def __init__(self, connection):
    self.protocol_version = "1.5"
    self.raw_url = self._clean_url(connection.url)
    self.conn_data = self._get_conn_data(connection.hub)
    self.session = connection.session
    self.headers = None
    self.socket_conf = None
    self._negotiate()
    self.socket_url = self._get_socket_url()

  @staticmethod
  def _clean_url(url):
    if url[-1] == "/":
      return url[:-1]
    else:
      return url

  @staticmethod
  def _get_conn_data(hub):
    conn_data = dumps([{"name": hub}])
    return conn_data

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
    return "; ".join(["%s=%s" % (name, value) for name, value in request.items()])

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


class Event:
  """
  Event is base class providing an interface
  for all subsequent(inherited) events.
  """


class InvokeEvent(Event):
  def __init__(self, message):
    self.type = "INVOKE"
    self.message = message


class CloseEvent(Event):
  def __init__(self):
    self.type = "CLOSE"


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
          await self._handlers[method](message)

    connection.received += handle

  def name(self) -> str:
    return self._name

  def on(self, method, handler):
    if method not in self._handlers:
      self._handlers[method] = handler

  def off(self, method, handler):
    if method in self._handlers:
      self._handlers[method] -= handler


class Hub:
  def __init__(self, name, connection) -> None:
    self.name = name
    self.server = HubServer(name, connection, self)
    self.client = HubClient(name, connection)


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


class Connection:
  protocol_version = "1.5"

  def __init__(self, url, session=None):
    self.url = url
    self.__hubs = {}
    self.__send_counter = -1
    self.hub = None
    self.session = session
    self.received = EventHook()
    self.error = EventHook()
    self.__transport = Transport(self)
    self.started = False

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
  """Extract data from the recorded SignalR message received from F1 Live Timing server.

  This function can be used to extract message data from raw SignalR data
  which was saved using :class:`SignalRClient` in debug mode.

  :param stream: Iterable containing raw SignalR responses.
  """
  result = []
  error_count = 0
  for record in records:
    # Fix not compliant JSON data.
    data = record.replace("'", '"').replace("True", "true").replace("False", "false")
    try:
      data = json.loads(data)
    except json.JSONDecodeError:
      error_count += 1
      continue
    messages = data["M"] if "M" in data and len(data["M"]) > 0 else {}
    for inner_data in messages:
      hub = inner_data["H"] if "H" in inner_data else ""
      if hub.lower() == "streaming":
        message = inner_data["A"]
        result.append(message)

  return result, error_count


class ColorFormatter(logging.Formatter):
  COLORS = {
    "HEADER": "\033[95m",
    "OKBLUE": "\033[94m",
    "OKCYAN": "\033[96m",
    "OKGREEN": "\033[92m",
    "WARNING": "\033[93m",
    "FAIL": "\033[91m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
  }

  def format(self, record):
    msg = super().format(record)
    if record.levelno == logging.INFO:
      return f"{self.COLORS['OKGREEN']}{msg}{self.COLORS['ENDC']}"
    elif record.levelno == logging.WARNING:
      return f"{self.COLORS['WARNING']}{msg}{self.COLORS['ENDC']}"
    elif record.levelno == logging.ERROR:
      return f"{self.COLORS['FAIL']}{msg}{self.COLORS['ENDC']}"
    return msg


class SignalRClient:
  """A client for receiving and saving F1 timing data which is streamed
  live over the SignalR protocol.

  During an F1 session, timing data and telemetry data are streamed live
  using the SignalR protocol. This class can be used to connect to the
  stream and save the received data into a file.

  The data will be saved in a raw text format without any postprocessing.
  It is **not** possible to use this data during a session. Instead, the
  data can be processed after the session using the :mod:`fastf1.api` and
  :mod:`fastf1.core`


  :param file_name: filename (opt. with path) for the output file
  :param file_mode: one of 'w' or 'a'; append to or overwrite
          file content it the file already exists. Append-mode may be useful
          if the client is restarted during a session.
  :param debug: When set to true, the complete SignalR
          message is saved. By default, only the actual data from a
          message is saved.
  :param timeout: Number of seconds after which the client
          will automatically exit when no message data is received.
          Set to zero to disable.
  :param logger: By default, errors are logged to the console. If you wish to
          customize logging, you can pass an instance of
          :class:`logging.Logger` (see: :mod:`logging`).
  """

  __URL__ = "https://livetiming.formula1.com/signalr"

  def __init__(
    self,
    file_name: str,
    file_mode: str = "a",
    debug: bool = False,
    timeout: int = 60,
    logger=None,
  ):
    self.headers = {
      "User-agent": "BestHTTP",
      "Accept-Encoding": "gzip, identity",
      "Connection": "keep-alive, Upgrade",
    }

    self.topics = [
      "Heartbeat",
      "CarData.z",
      "Position.z",
      "ExtrapolatedClock",
      "TopThree",
      "RcmSeries",
      "TimingStats",
      "TimingAppData",
      "WeatherData",
      "TrackStatus",
      "DriverList",
      "RaceControlMessages",
      "SessionInfo",
      "SessionData",
      "LapCount",
      "TimingData",
    ]

    self.debug = debug
    self.filename = file_name
    self.filemode = file_mode
    self.timeout = 0  # Never timeout
    self._connection = None

    if not logger:
      self.logger = logging.getLogger("SignalR")
      self.logger.setLevel(logging.INFO)
      self.logger.handlers.clear()
      # File handler
      file_handler = logging.FileHandler(file_name + ".log")
      file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s"))
      self.logger.addHandler(file_handler)
      # Console handler with color
      console_handler = logging.StreamHandler(sys.stdout)
      console_handler.setFormatter(ColorFormatter("%(asctime)s - %(levelname)s: %(message)s"))
      self.logger.addHandler(console_handler)
    else:
      self.logger = logger

    self._output_file = None
    self._t_last_message = None
    self._last_server_message = None  # Store last server message

  def _to_file(self, message: str):
    self._last_server_message = message  # Store last message
    if self.filename is None:
      print(message)
    else:
      log_line = str(datetime.datetime.now(tz=datetime.UTC)) + "," + message + "\n"
      self._output_file.write(log_line)
      self._output_file.flush()
      # Print colored to stdout (only for real data/events)
      try:
        import json

        data = json.loads(message)
        # Only colorize if it's a real event/data (not a log line)
        print(f"\033[96m[DATA] {message}\033[0m")
      except Exception:
        pass

  async def _on_do_nothing(self, msg):
    # just do nothing with the message; intended for debug mode where some
    # callback method still needs to be provided
    pass

  async def _on_message(self, msg):
    self._t_last_message = time.time()
    loop = asyncio.get_running_loop()
    try:
      with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, self._to_file, str(msg))
    except Exception:
      self.logger.exception("Exception while writing message to file")

  async def _on_debug(self, **data):
    while True:
      if self.timeout != 0 and time.time() - self._t_last_message > self.timeout:
        self.logger.warning(f"Timeout - received no data for more than {self.timeout} seconds!")

        self._connection.close()
        while self._connection.started:
          await asyncio.sleep(0.1)
        return

      await asyncio.sleep(1)

  async def _supervise(self):
    self._t_last_message = time.time()
    while True:
      if self.timeout != 0 and time.time() - self._t_last_message > self.timeout:
        self.logger.warning(f"Timeout - received no data for more than {self.timeout} seconds!")
        self._connection.close()
        while self._connection.started:
          await asyncio.sleep(0.1)
        return
      await asyncio.sleep(1)

  async def _async_start(self):
    self.logger.info("Starting FastF1 live timing client VERSION]")
    await asyncio.gather(
      asyncio.create_task(self._supervise()),
      asyncio.create_task(self._run()),
    )
    self._output_file.close()
    self.logger.warning("Exiting...")

  async def _run(self):
    if self.filename is not None:
      self._output_file = open(self.filename, self.filemode)
    # Create connection
    session = requests.Session()
    session.headers = self.headers
    self._connection = Connection(self.__URL__, session=session)

    # Register hub
    hub = self._connection.register_hub("Streaming")

    if self.debug:
      # Assign error handler
      self._connection.error += self._on_debug
      # Assign debug message handler to save raw responses
      self._connection.received += self._on_debug
      hub.client.on("feed", self._on_do_nothing)
      # need to connect an async method
    else:
      # Assign hub message handler
      hub.client.on("feed", self._on_message)

    hub.server.invoke("Subscribe", self.topics)

    # Start the client
    loop = asyncio.get_event_loop()
    try:
      with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, self._connection.start)
    except Exception as e:
      self.logger.error(f"Exception in SignalR connection: {e}", exc_info=True)
    finally:
      if self._last_server_message:
        self.logger.info(f"Last server message before disconnect: {self._last_server_message}")
      if self._connection and not self._connection.started:
        self.logger.info("SignalR connection closed by server or finished.")
      else:
        self.logger.info("SignalR client _run finished for unknown reason.")

  def start(self):
    """Connect to the data stream and start writing the data to a file."""
    try:
      # try to get an already running loop (e.g. in newer IPython)
      loop = asyncio.get_running_loop()
    except RuntimeError:
      # there is no running loop yet
      self._start_without_existing_loop()
      return

    try:
      # __IPYTHON__  # noqa
      is_ipython = True
    except NameError:
      is_ipython = False

    if loop and is_ipython:
      raise RuntimeError("Running in an asynchronous IPython session. Please use `await SignalRClient().async_start()`")

    else:
      raise RuntimeError(
        "Cannot start because an asynchronous event loop already "
        "exists. You can try to use the "
        "`SignalRClient().async_start()` coroutine."
      )

  async def async_start(self):
    """
    Connect to the data stream and start writing the data to a file
    when running inside an existing event loop.

    In most cases, you want to use :func:`start` instead.
    """
    loop = asyncio.get_running_loop()
    try:
      task = loop.create_task(self._async_start())
      while not task.done():
        await asyncio.sleep(1)
    except asyncio.CancelledError:
      self.logger.warning("Async execution cancelled - exiting...")

  def _start_without_existing_loop(self):
    try:
      asyncio.run(self._async_start())
    except KeyboardInterrupt:
      self.logger.warning("Keyboard interrupt - exiting...")
