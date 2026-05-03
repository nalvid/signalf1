#!/usr/bin/env python3
"""
Extract throttle telemetry data for driver #44 from F1 live timing log.

This example shows how to extract specific telemetry data for a particular driver,
focusing on throttle input data from the compressed CarData streams.
"""

import json
from pathlib import Path
from datetime import datetime
from signalf1.extractor import parse_log_file, decompress_data


def extract_driver_44_throttle_data(log_file_path: str):
  """
  Extract throttle telemetry data specifically for driver #44.

  Args:
      log_file_path: Path to the F1 log file

  Returns:
      List of throttle data points with timestamps
  """
  print("=" * 60)
  print("EXTRACTING THROTTLE DATA FOR DRIVER #44")
  print("=" * 60)

  # Parse the log file
  entries = parse_log_file(log_file_path)
  print(f"Parsed {len(entries)} log entries")

  # Store throttle data for driver 44
  throttle_data = []

  # Process each log entry
  for entry in entries:
    if entry.raw_data and isinstance(entry.raw_data, dict):
      # Look for compressed car data
      if "R" in entry.raw_data and isinstance(entry.raw_data["R"], dict):
        r_data = entry.raw_data["R"]

        # Extract CarData.z which contains telemetry channels
        if "CarData.z" in r_data:
          compressed_data = r_data["CarData.z"]
          decompressed = decompress_data(compressed_data)

          if decompressed:
            try:
              car_data = json.loads(decompressed)

              # Process each entry in the car data
              if "Entries" in car_data:
                for data_entry in car_data["Entries"]:
                  utc_time = data_entry.get("Utc")
                  cars = data_entry.get("Cars", {})

                  # Check if driver 44 has data
                  if "44" in cars:
                    driver_44_data = cars["44"]
                    channels = driver_44_data.get("Channels", {})

                    # Channel mapping for F1 telemetry:
                    # Channel 0: RPM
                    # Channel 2: Speed (km/h)
                    # Channel 3: nGear
                    # Channel 4: Throttle (0-100%)
                    # Channel 5: Brake (0-100%)
                    # Channel 45: DRS status

                    throttle_value = channels.get("4")  # Channel 4 is throttle

                    if throttle_value is not None:
                      throttle_data.append(
                        {
                          "log_timestamp": entry.timestamp,
                          "utc_timestamp": utc_time,
                          "throttle_percent": throttle_value,
                          "rpm": channels.get("0"),
                          "speed_kmh": channels.get("2"),
                          "gear": channels.get("3"),
                          "brake_percent": channels.get("5"),
                          "drs_status": channels.get("45"),
                        }
                      )

            except json.JSONDecodeError:
              continue

  return throttle_data


def analyze_throttle_data(throttle_data):
  """
  Analyze the extracted throttle data and provide insights.

  Args:
      throttle_data: List of throttle data points
  """
  if not throttle_data:
    print("No throttle data found for driver #44")
    return

  print(f"\n--- THROTTLE DATA ANALYSIS FOR DRIVER #44 ---")
  print(f"Total throttle data points: {len(throttle_data)}")

  # Time range
  first_point = throttle_data[0]
  last_point = throttle_data[-1]
  print(f"Time range: {first_point['log_timestamp']} to {last_point['log_timestamp']}")

  # Throttle statistics
  throttle_values = [point["throttle_percent"] for point in throttle_data if point["throttle_percent"] is not None]

  if throttle_values:
    max_throttle = max(throttle_values)
    min_throttle = min(throttle_values)
    avg_throttle = sum(throttle_values) / len(throttle_values)

    print(f"Throttle range: {min_throttle}% to {max_throttle}%")
    print(f"Average throttle: {avg_throttle:.1f}%")

    # Count full throttle instances (assuming 100% is full throttle)
    full_throttle_count = sum(1 for t in throttle_values if t >= 100)
    print(f"Full throttle instances: {full_throttle_count}")

    # Count off-throttle instances (0% throttle)
    off_throttle_count = sum(1 for t in throttle_values if t == 0)
    print(f"Off-throttle instances: {off_throttle_count}")

  # Show first few data points
  print(f"\n--- SAMPLE THROTTLE DATA POINTS ---")
  for i, point in enumerate(throttle_data[:10]):  # Show first 10 points
    print(f"Point {i + 1}:")
    print(f"  Time: {point['log_timestamp']}")
    print(f"  Throttle: {point['throttle_percent']}%")
    print(f"  Speed: {point['speed_kmh']} km/h")
    print(f"  RPM: {point['rpm']}")
    print(f"  Gear: {point['gear']}")
    print(f"  Brake: {point['brake_percent']}%")
    print(f"  DRS: {point['drs_status']}")
    print()


def find_interesting_throttle_moments(throttle_data):
  """
  Find interesting moments in the throttle data (e.g., quick changes, full throttle periods).

  Args:
      throttle_data: List of throttle data points
  """
  if len(throttle_data) < 2:
    return

  print(f"--- INTERESTING THROTTLE MOMENTS ---")

  # Find rapid throttle changes
  rapid_changes = []
  for i in range(1, len(throttle_data)):
    prev_point = throttle_data[i - 1]
    curr_point = throttle_data[i]

    if prev_point["throttle_percent"] is not None and curr_point["throttle_percent"] is not None:
      throttle_change = abs(curr_point["throttle_percent"] - prev_point["throttle_percent"])

      # Look for changes > 50% throttle
      if throttle_change > 50:
        rapid_changes.append(
          {
            "timestamp": curr_point["log_timestamp"],
            "from_throttle": prev_point["throttle_percent"],
            "to_throttle": curr_point["throttle_percent"],
            "change": throttle_change,
          }
        )

  print(f"Found {len(rapid_changes)} rapid throttle changes (>50%):")
  for change in rapid_changes[:5]:  # Show first 5
    print(f"  {change['timestamp']}: {change['from_throttle']}% → {change['to_throttle']}% (Δ{change['change']:.0f}%)")


def main():
  """Main function to extract and analyze driver #44 throttle data."""
  log_file = r"data\raw\20250802_123439.log.log"

  if not Path(log_file).exists():
    print(f"Log file not found: {log_file}")
    return

  # Extract throttle data for driver #44
  throttle_data = extract_driver_44_throttle_data(log_file)

  # Analyze the data
  analyze_throttle_data(throttle_data)

  # Find interesting moments
  find_interesting_throttle_moments(throttle_data)

  # Save data to file for further analysis
  if throttle_data:
    output_file = "driver_44_throttle_data.json"
    with open(output_file, "w") as f:
      # Convert datetime objects to strings for JSON serialization
      json_data = []
      for point in throttle_data:
        json_point = point.copy()
        json_point["log_timestamp"] = point["log_timestamp"].isoformat()
        json_data.append(json_point)

      json.dump(json_data, f, indent=2)

    print(f"\nThrottle data saved to: {output_file}")
    print(f"You can load this data for further analysis or visualization.")


if __name__ == "__main__":
  main()
