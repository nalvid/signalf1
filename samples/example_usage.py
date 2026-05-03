#!/usr/bin/env python3
"""
Example usage of the F1 log extractor with compressed data extraction.

This script demonstrates how to extract and analyze various types of information
from F1 live timing log files, including compressed telemetry data.
"""

import json
from pathlib import Path

from signalf1.extractor import (
  decompress_data,
  extract_car_data,
  generate_log_summary,
  parse_log_file,
  print_log_summary,
)


def extract_compressed_telemetry(log_file_path: str):
  """
  Extract and analyze compressed telemetry data from F1 log.

  Args:
      log_file_path: Path to the F1 log file
  """
  print("=" * 60)
  print("F1 COMPRESSED TELEMETRY EXTRACTION")
  print("=" * 60)

  # Parse the log file
  entries = parse_log_file(log_file_path)
  print(f"Parsed {len(entries)} log entries")

  # Find and extract compressed data
  car_data_entries = []
  position_data_entries = []

  for entry in entries:
    if entry.raw_data and isinstance(entry.raw_data, dict):
      # Look for compressed car data
      if "R" in entry.raw_data and isinstance(entry.raw_data["R"], dict):
        r_data = entry.raw_data["R"]

        # Extract CarData.z
        if "CarData.z" in r_data:
          compressed_data = r_data["CarData.z"]
          decompressed = decompress_data(compressed_data)
          if decompressed:
            try:
              car_data = json.loads(decompressed)
              car_data_entries.append({"timestamp": entry.timestamp, "data": car_data})
            except json.JSONDecodeError:
              pass

        # Extract Position.z
        if "Position.z" in r_data:
          compressed_data = r_data["Position.z"]
          decompressed = decompress_data(compressed_data)
          if decompressed:
            try:
              position_data = json.loads(decompressed)
              position_data_entries.append({"timestamp": entry.timestamp, "data": position_data})
            except json.JSONDecodeError:
              pass

  print(f"Found {len(car_data_entries)} compressed car data entries")
  print(f"Found {len(position_data_entries)} compressed position data entries")

  # Analyze car data
  if car_data_entries:
    print(f"\n--- CAR DATA ANALYSIS ---")
    sample_entry = car_data_entries[0]
    print(f"Sample timestamp: {sample_entry['timestamp']}")

    if "Entries" in sample_entry["data"]:
      entries_data = sample_entry["data"]["Entries"][0]  # First entry
      print(f"UTC timestamp: {entries_data.get('Utc', 'N/A')}")

      if "Cars" in entries_data:
        cars = entries_data["Cars"]
        print(f"Number of cars: {len(cars)}")

        # Show data for first car
        first_car = next(iter(cars.keys()))
        car_channels = cars[first_car].get("Channels", {})
        print(f"Car #{first_car} channels: {car_channels}")

  # Analyze position data
  if position_data_entries:
    print(f"\n--- POSITION DATA ANALYSIS ---")
    sample_entry = position_data_entries[0]
    print(f"Sample timestamp: {sample_entry['timestamp']}")

    if "Position" in sample_entry["data"]:
      positions = sample_entry["data"]["Position"][0]  # First position entry
      print(f"UTC timestamp: {positions.get('Timestamp', 'N/A')}")

      if "Entries" in positions:
        pos_entries = positions["Entries"]
        print(f"Number of cars with position data: {len(pos_entries)}")

        # Show position for cars that are moving
        for car_num, pos_data in pos_entries.items():
          if pos_data.get("X", 0) != 0 or pos_data.get("Y", 0) != 0:
            print(
              f"Car #{car_num}: Status={pos_data.get('Status')}, "
              f"X={pos_data.get('X')}, Y={pos_data.get('Y')}, Z={pos_data.get('Z')}"
            )

  return car_data_entries, position_data_entries


def main():
  """Main function to demonstrate F1 log analysis capabilities."""
  log_file = r"data\raw\20250802_123439.log.log"

  if not Path(log_file).exists():
    print(f"Log file not found: {log_file}")
    return

  # Generate and display basic log summary
  summary = generate_log_summary(log_file)
  print_log_summary(summary)

  print("\n")

  # Extract compressed telemetry data
  car_data, position_data = extract_compressed_telemetry(log_file)

  # Additional analysis examples
  print(f"\n--- ADVANCED ANALYSIS ---")
  if car_data:
    print(f"Car data time range: {car_data[0]['timestamp']} to {car_data[-1]['timestamp']}")

  if position_data:
    print(f"Position data time range: {position_data[0]['timestamp']} to {position_data[-1]['timestamp']}")

  print(f"\nExtraction complete! You now have access to:")
  print(f"  - {len(car_data)} car telemetry data points")
  print(f"  - {len(position_data)} position data points")
  print(f"  - Full session metadata and timing information")


if __name__ == "__main__":
  main()
