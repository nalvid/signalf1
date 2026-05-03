"""
Python SignalR Hub client.

This module is based on the excellent work of Stanislav Lazarov.
Since the original module is no longer developed it's been integrated
into Fast-F1. Original source https://github.com/slazarov/python-signalr-client

"""

import asyncio
import concurrent.futures
import json
import logging
import sys
import time
from collections.abc import Callable
from typing import TextIO

import requests

from ._signalr_core import Connection, Hub, HubClient, HubServer, messages_from_raw
from ._signalr_events import CloseEvent, Event, EventHook, InvokeEvent
from ._signalr_transport import Transport, WebSocketParameters


__all__ = [
  "CloseEvent",
  "Connection",
  "Event",
  "EventHook",
  "Hub",
  "HubClient",
  "HubServer",
  "InvokeEvent",
  "SignalRClient",
  "Transport",
  "WebSocketParameters",
  "messages_from_raw",
]


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
  data can be processed after the session using the utilities in this
  package, such as :mod:`signalf1.extractor` and :class:`signalf1.LiveTimingData`.


  :param file_name: filename (opt. with path) for the output file
  :param file_mode: one of 'w' or 'a'; append to or overwrite
          file content it the file already exists. Append-mode may be useful
          if the client is restarted during a session.
    :param debug: When set to true, the complete raw SignalR frame is
      written to the configured data sink. By default, only the
      decoded telemetry payload is written.
  :param timeout: Number of seconds after which the client
          will automatically exit when no message data is received.
          Set to zero to disable.
    :param data_stream: Optional text stream for serialized telemetry output.
      If omitted, telemetry is written to stdout unless `file_name`
      or `data_writer` is configured.
    :param data_writer: Optional callback for serialized telemetry output.
      This can be used to forward telemetry elsewhere without coupling
      it to application logging.
  :param logger: By default, errors are logged to the console. If you wish to
          customize logging, you can pass an instance of
          :class:`logging.Logger` (see: :mod:`logging`).
  """

  __URL__ = "https://livetiming.formula1.com/signalr"

  def __init__(
    self,
    file_name: str | None = None,
    file_mode: str = "a",
    debug: bool = False,
    timeout: int = 60,
    data_stream: TextIO | None = None,
    data_writer: Callable[[str], None] | None = None,
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

    configured_data_sinks = sum(option is not None for option in (file_name, data_stream, data_writer))
    if configured_data_sinks > 1:
      raise ValueError("Only one of file_name, data_stream, or data_writer can be configured.")

    self.debug = debug
    self.filename = file_name
    self.filemode = file_mode
    self.timeout = timeout
    self.data_stream = data_stream
    self.data_writer = data_writer
    self._connection = None

    if not logger:
      self.logger = logging.getLogger("SignalR")
      self.logger.setLevel(logging.INFO)
      self.logger.propagate = False
      for handler in list(self.logger.handlers):
        handler.close()
        self.logger.removeHandler(handler)
      console_handler = logging.StreamHandler(sys.stderr)
      console_handler.setFormatter(ColorFormatter("%(asctime)s - %(levelname)s: %(message)s"))
      self.logger.addHandler(console_handler)
    else:
      self.logger = logger

    self._output_file = None
    self._t_last_message = None
    self._last_server_message = None  # Store last server message

  def _emit_data(self, payload: str):
    if self.data_writer is not None:
      self.data_writer(payload)
      return

    if self.filename is None:
      target_stream = self.data_stream or sys.stdout
      target_stream.write(payload + "\n")
      target_stream.flush()
      return

    self._output_file.write(payload + "\n")
    self._output_file.flush()

  def _to_file(self, message):
    payload = json.dumps(message, ensure_ascii=False)
    self._last_server_message = payload
    self._emit_data(payload)

  async def _on_do_nothing(self, msg):
    # just do nothing with the message; intended for debug mode where some
    # callback method still needs to be provided
    pass

  async def _on_raw_message(self, message: str):
    self._t_last_message = time.time()
    try:
      await asyncio.to_thread(self._emit_data, message)
    except Exception:
      self.logger.exception("Exception while writing raw SignalR message")

  async def _on_message(self, msg):
    self._t_last_message = time.time()
    try:
      await asyncio.to_thread(self._to_file, msg)
    except Exception:
      self.logger.exception("Exception while writing message to file")

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
    self.logger.info("Starting SignalF1 live timing client")
    try:
      await asyncio.gather(
        asyncio.create_task(self._supervise()),
        asyncio.create_task(self._run()),
      )
    except asyncio.CancelledError:
      await self._close_connection()
      raise
    finally:
      if self._output_file is not None:
        self._output_file.close()
      self.logger.warning("Exiting...")

  async def _close_connection(self):
    if self._connection is None:
      return

    try:
      self._connection.close()
    except Exception:
      self.logger.exception("Exception while closing SignalR connection")
      return

    while self._connection.started:
      await asyncio.sleep(0.05)

  async def _run(self):
    if self.filename is not None:
      self._output_file = open(self.filename, self.filemode)
    # Create connection
    session = requests.Session()
    session.headers = self.headers
    self._connection = Connection(self.__URL__, session=session, logger=self.logger)

    # Register hub
    hub = self._connection.register_hub("Streaming")

    if self.debug:
      self._connection.raw_message_handler = self._on_raw_message
      hub.client.on("feed", self._on_do_nothing)
    else:
      hub.client.on("feed", self._on_message)

    hub.server.invoke("Subscribe", self.topics)

    # Start the client
    loop = asyncio.get_running_loop()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    connection_future = loop.run_in_executor(pool, self._connection.start)
    try:
      await connection_future
    except asyncio.CancelledError:
      await self._close_connection()
      raise
    except Exception as e:
      self.logger.error(f"Exception in SignalR connection: {e}", exc_info=True)
    finally:
      pool.shutdown(wait=True)
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
