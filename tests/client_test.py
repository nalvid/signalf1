import asyncio
import io
import json
import logging
import threading

import pytest
import signalf1.__main__ as cli
import signalf1._client as client_module
from signalf1 import SignalF1
from signalf1._client import EventHook, HubClient
from signalf1._data import LiveTimingData


class DummyConnection:
	def __init__(self):
		self.received = EventHook()


def test_client_writes_json_lines(tmp_path):
	output_file = tmp_path / "session.log"
	logger = logging.getLogger("signalf1-test-json")
	logger.handlers.clear()
	logger.propagate = False

	client = SignalF1(file_name=str(output_file), logger=logger)
	client._output_file = output_file.open("w", encoding="utf-8")

	message = ["TimingData", {"Driver": "O'Brien", "Flag": True}, "2026-05-01T00:00:00Z"]
	client._to_file(message)
	client._output_file.close()

	assert output_file.read_text(encoding="utf-8") == json.dumps(message, ensure_ascii=False) + "\n"


def test_client_writes_to_stdout_without_output_file(capsys):
	logger = logging.getLogger("signalf1-test-stdout")
	logger.handlers.clear()
	logger.propagate = False

	client = SignalF1(file_name=None, logger=logger)
	message = ["TimingData", {"Driver": "VER"}, "2026-05-01T00:00:00Z"]

	client._to_file(message)

	assert capsys.readouterr().out == json.dumps(message, ensure_ascii=False) + "\n"


def test_client_writes_to_custom_data_stream():
	logger = logging.getLogger("signalf1-test-stream")
	logger.handlers.clear()
	logger.propagate = False

	stream = io.StringIO()
	client = SignalF1(file_name=None, data_stream=stream, logger=logger)
	message = ["TimingData", {"Driver": "PIA"}, "2026-05-01T00:00:00Z"]

	client._to_file(message)

	assert stream.getvalue() == json.dumps(message, ensure_ascii=False) + "\n"


def test_client_writes_to_custom_data_writer():
	logger = logging.getLogger("signalf1-test-writer")
	logger.handlers.clear()
	logger.propagate = False
	forwarded = []

	client = SignalF1(file_name=None, data_writer=forwarded.append, logger=logger)
	message = ["TimingData", {"Driver": "NOR"}, "2026-05-01T00:00:00Z"]

	client._to_file(message)

	assert forwarded == [json.dumps(message, ensure_ascii=False)]


def test_debug_mode_writes_raw_signalr_frames_to_data_sink():
	logger = logging.getLogger("signalf1-test-debug")
	logger.handlers.clear()
	logger.propagate = False
	forwarded = []
	raw_message = json.dumps({"M": [{"H": "Streaming", "M": "feed", "A": ["TimingData", {"Lines": {}}, "2026-05-01T00:00:00Z"]}]})

	client = SignalF1(file_name=None, debug=True, data_writer=forwarded.append, logger=logger)

	asyncio.run(client._on_raw_message(raw_message))

	assert forwarded == [raw_message]


def test_client_rejects_multiple_data_sinks(tmp_path):
	output_file = tmp_path / "session.log"

	with pytest.raises(ValueError, match="Only one of file_name, data_stream, or data_writer"):
		SignalF1(file_name=str(output_file), data_writer=lambda payload: payload)


def test_live_timing_data_parses_json_and_legacy_lines():
	livedata = LiveTimingData()

	livedata._parse_line('["TimingData", {"Driver": "VER"}, "2026-05-01T00:00:00Z"]')
	livedata._parse_line(
		"2026-05-01 00:00:00+00:00,['TimingData', {'Driver': \"O'Brien\", 'Flag': True}, '2026-05-01T00:00:01Z']"
	)

	assert livedata.errorcount == 0
	assert livedata.data["TimingData"][0][1]["Driver"] == "VER"
	assert livedata.data["TimingData"][1][1]["Driver"] == "O'Brien"
	assert livedata.data["TimingData"][1][1]["Flag"] is True


def test_live_timing_data_uses_suffix_prefix_overlap_instead_of_first_match(tmp_path):
	file_one = tmp_path / "part1.jsonl"
	file_two = tmp_path / "part2.jsonl"

	started = json.dumps(["SessionStatus", {"StatusSeries": [{"SessionStatus": "Started", "Utc": "2026-05-01T00:00:00Z"}]}, "2026-05-01T00:00:00Z"])
	heartbeat = json.dumps(["Heartbeat", {"Utc": "2026-05-01T00:00:01Z"}, "2026-05-01T00:00:01Z"])
	unique_mid = json.dumps(["TimingData", {"Lines": {"1": {"Position": "mid"}}}, "2026-05-01T00:00:02Z"])
	overlap_one = json.dumps(["TimingData", {"Lines": {"1": {"Position": "1"}}}, "2026-05-01T00:00:03Z"])
	overlap_two = json.dumps(["TimingData", {"Lines": {"1": {"Position": "2"}}}, "2026-05-01T00:00:04Z"])
	unique_end = json.dumps(["TimingData", {"Lines": {"1": {"Position": "3"}}}, "2026-05-01T00:00:05Z"])

	file_one.write_text("\n".join([started, heartbeat, unique_mid, heartbeat, overlap_one, overlap_two]) + "\n", encoding="utf-8")
	file_two.write_text("\n".join([heartbeat, overlap_one, overlap_two, unique_end]) + "\n", encoding="utf-8")

	livedata = LiveTimingData(str(file_one), str(file_two))
	timing_data = livedata.get("TimingData")

	positions = [entry[1]["Lines"]["1"]["Position"] for entry in timing_data]

	assert positions == ["mid", "1", "2", "3"]


def test_client_logger_does_not_propagate(tmp_path):
	output_file = tmp_path / "session.log"

	client = SignalF1(file_name=str(output_file))

	assert client.logger.propagate is False
	assert not any(isinstance(handler, logging.FileHandler) for handler in client.logger.handlers)


def test_hub_client_ignores_unknown_methods_and_off_unregisters_handler():
	connection = DummyConnection()
	hub_client = HubClient("Streaming", connection)
	received = []

	async def handler(message):
		received.append(message)

	hub_client.on("feed", handler)

	asyncio.run(
		connection.received.fire(
			M=[
				{"H": "Streaming", "M": "unknown", "A": ["ignored"]},
				{"H": "Streaming", "M": "feed", "A": ["payload"]},
			]
		)
	)
	hub_client.off("feed", handler)
	asyncio.run(connection.received.fire(M=[{"H": "Streaming", "M": "feed", "A": ["payload-2"]}]))

	assert received == [["payload"]]


def test_cli_uses_stdout_by_default(monkeypatch):
	captured = {}

	class FakeClient:
		def __init__(self, **kwargs):
			captured.update(kwargs)

		def start(self):
			captured["started"] = True

	monkeypatch.setattr(cli, "SignalF1", FakeClient)

	cli.main([])

	assert captured["file_name"] is None
	assert captured["started"] is True


def test_run_cancellation_closes_connection_and_finishes(monkeypatch):
	class FakeHubClient:
		def on(self, method, handler):
			self.method = method
			self.handler = handler

	class FakeHubServer:
		def invoke(self, method, topics):
			self.method = method
			self.topics = topics

	class FakeHub:
		def __init__(self):
			self.client = FakeHubClient()
			self.server = FakeHubServer()

	class BlockingConnection:
		instances = []

		def __init__(self, url, session=None, logger=None):
			self.url = url
			self.session = session
			self.logger = logger
			self.started = False
			self.raw_message_handler = None
			self.closed = threading.Event()
			self.started_event = threading.Event()
			self.close_called = False
			BlockingConnection.instances.append(self)

		def register_hub(self, name):
			return FakeHub()

		def start(self):
			self.started = True
			self.started_event.set()
			self.closed.wait(timeout=2)
			self.started = False

		def close(self):
			self.close_called = True
			self.closed.set()

	monkeypatch.setattr(client_module, "Connection", BlockingConnection)

	logger = logging.getLogger("signalf1-test-cancel")
	logger.handlers.clear()
	logger.propagate = False
	client = SignalF1(file_name=None, logger=logger)

	async def run_test():
		task = asyncio.create_task(client._run())
		while not BlockingConnection.instances:
			await asyncio.sleep(0)

		started = await asyncio.to_thread(BlockingConnection.instances[0].started_event.wait, 1)
		assert started is True

		task.cancel()
		with pytest.raises(asyncio.CancelledError):
			await asyncio.wait_for(task, timeout=1)

	asyncio.run(run_test())

	assert BlockingConnection.instances[0].close_called is True
