import json

from signalf1.extractor import extract_driver_list, extract_session_info, extract_timing_data, parse_log_file


def test_parse_log_file_supports_jsonl_telemetry_output(tmp_path):
  data_file = tmp_path / "session.jsonl"
  data_file.write_text(
    "\n".join(
      [
        json.dumps(["SessionInfo", {"Meeting": {"Name": "Miami GP", "Location": "Miami"}, "Type": "Race"}, "2026-05-01T00:00:00Z"]),
        json.dumps(["DriverList", {"4": {"RacingNumber": "4", "FullName": "Lando Norris", "Tla": "NOR", "TeamName": "McLaren"}}, "2026-05-01T00:00:01Z"]),
        json.dumps(["TimingData", {"Lines": {"4": {"Sectors": {"0": {"Value": "30.123"}}}}}, "2026-05-01T00:00:02Z"]),
      ]
    )
    + "\n",
    encoding="utf-8",
  )

  entries = parse_log_file(str(data_file))
  session_info = extract_session_info(entries)
  drivers = extract_driver_list(entries)
  timing = extract_timing_data(entries)

  assert len(entries) == 3
  assert session_info.meeting_name == "Miami GP"
  assert session_info.location == "Miami"
  assert session_info.session_type == "Race"
  assert drivers["4"].full_name == "Lando Norris"
  assert len(timing) == 1
  assert timing[0].driver_data["4"]["Sectors"]["0"]["Value"] == "30.123"


def test_parse_log_file_supports_debug_raw_message_json(tmp_path):
  data_file = tmp_path / "raw.jsonl"
  raw_message = {
    "M": [
      {
        "H": "Streaming",
        "M": "feed",
        "A": [
          "DriverList",
          {"16": {"RacingNumber": "16", "FullName": "Charles Leclerc", "Tla": "LEC", "TeamName": "Ferrari"}},
          "2026-05-01T00:00:03Z",
        ],
      }
    ]
  }
  data_file.write_text(json.dumps(raw_message) + "\n", encoding="utf-8")

  entries = parse_log_file(str(data_file))
  drivers = extract_driver_list(entries)

  assert len(entries) == 1
  assert drivers["16"].full_name == "Charles Leclerc"