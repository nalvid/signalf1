"""
Transport
"""

# Python compatibility for <3.6
try:
    ModuleNotFoundError
except NameError:
    ModuleNotFoundError = ImportError

try:
    from ujson import dumps, loads
except ModuleNotFoundError:
    from json import dumps, loads

import asyncio

import websockets

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ModuleNotFoundError:
    pass


from websockets.exceptions import ConnectionClosed as ConnectionClosed

from json import dumps
from urllib.parse import urlencode, urlparse, urlunparse

import requests


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
        self._conn_handler = asyncio.ensure_future(
            self._socket(self.ws_loop), loop=self.ws_loop
        )

    async def _socket(self, loop):
        async with websockets.connect(
            self._ws_params.socket_url, extra_headers=self._ws_params.headers, loop=loop
        ) as self.ws:
            self._connection.started = True
            await self._master_handler(self.ws)

    async def _master_handler(self, ws):
        consumer_task = asyncio.ensure_future(
            self._consumer_handler(ws), loop=self.ws_loop
        )
        producer_task = asyncio.ensure_future(
            self._producer_handler(ws), loop=self.ws_loop
        )
        done, pending = await asyncio.wait(
            [consumer_task, producer_task], return_when=asyncio.FIRST_EXCEPTION
        )

        for task in pending:
            task.cancel()

        try:
            consumer_exception = consumer_task.exception()
        except asyncio.CancelledError:
            pass
        else:
            if not isinstance(
                consumer_exception, websockets.exceptions.ConnectionClosedOK
            ):
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
        return "{url}/{action}?{query}".format(url=url, action=action, query=query)

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


class Event(object):
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
