#!/usr/bin/env python3
"""
Enhanced F1 telemetry extractor with driver discovery and comprehensive throttle analysis.

This script first discovers which drivers have telemetry data, then extracts
detailed throttle and other telemetry data for a specific driver.
"""

import json
from pathlib import Path
from signalf1.extractor import parse_log_file, decompress_data


def discover_drivers_with_telemetry(log_file_path: str):
  """
  Discover which drivers have telemetry data in the log file.

  Args:
      log_file_path: Path to the F1 log file

  Returns:
      Dictionary of driver numbers and their data point counts
  """
  entries = parse_log_file(log_file_path)
  driver_data_counts = {}

  for entry in entries:
    if entry.raw_data and isinstance(entry.raw_data, dict):
      if "R" in entry.raw_data and isinstance(entry.raw_data["R"], dict):
        r_data = entry.raw_data["R"]

        if "CarData.z" in r_data:
          compressed_data = r_data["CarData.z"]
          decompressed = decompress_data(compressed_data)

          if decompressed:
            try:
              car_data = json.loads(decompressed)

              if "Entries" in car_data:
                for data_entry in car_data["Entries"]:
                  cars = data_entry.get("Cars", {})

                  for driver_num in cars.keys():
                    if driver_num not in driver_data_counts:
                      driver_data_counts[driver_num] = 0
                    driver_data_counts[driver_num] += 1

            except json.JSONDecodeError:
              continue

  return driver_data_counts


def extract_driver_telemetry(log_file_path: str, target_driver: str):
  """
  Extract comprehensive telemetry data for a specific driver.

  Args:
      log_file_path: Path to the F1 log file
      target_driver: Driver number as string (e.g., "44")

  Returns:
      List of telemetry data points
  """
  entries = parse_log_file(log_file_path)
  telemetry_data = []

  for entry in entries:
    if entry.raw_data and isinstance(entry.raw_data, dict):
      if "R" in entry.raw_data and isinstance(entry.raw_data["R"], dict):
        r_data = entry.raw_data["R"]

        if "CarData.z" in r_data:
          compressed_data = r_data["CarData.z"]
          decompressed = decompress_data(compressed_data)

          if decompressed:
            try:
              car_data = json.loads(decompressed)

              if "Entries" in car_data:
                for data_entry in car_data["Entries"]:
                  utc_time = data_entry.get("Utc")
                  cars = data_entry.get("Cars", {})

                  if target_driver in cars:
                    driver_data = cars[target_driver]
                    channels = driver_data.get("Channels", {})

                    # Extract all available channels
                    telemetry_point = {
                      "log_timestamp": entry.timestamp,
                      "utc_timestamp": utc_time,
                      "raw_channels": channels,
                      # Standard F1 telemetry channels
                      "rpm": channels.get("0"),
                      "speed_kmh": channels.get("2"),
                      "gear": channels.get("3"),
                      "throttle_percent": channels.get("4"),
                      "brake_percent": channels.get("5"),
                      "drs_status": channels.get("45"),
                    }

                    telemetry_data.append(telemetry_point)

            except json.JSONDecodeError:
              continue

  return telemetry_data


def analyze_telemetry(telemetry_data, driver_num):
  """
  Comprehensive analysis of driver telemetry data.

  Args:
      telemetry_data: List of telemetry data points
      driver_num: Driver number
  """
  if not telemetry_data:
    print(f"No telemetry data found for driver #{driver_num}")
    return

  print(f"\n{'=' * 60}")
  print(f"TELEMETRY ANALYSIS FOR DRIVER #{driver_num}")
  print(f"{'=' * 60}")
  print(f"Total telemetry data points: {len(telemetry_data)}")

  # Time range
  first_point = telemetry_data[0]
  last_point = telemetry_data[-1]
  print(f"Time range: {first_point['log_timestamp']} to {last_point['log_timestamp']}")

  # Channel analysis
  all_channels = set()
  for point in telemetry_data:
    all_channels.update(point["raw_channels"].keys())

  print(f"Available telemetry channels: {sorted(all_channels)}")

  # Throttle analysis
  throttle_values = [point["throttle_percent"] for point in telemetry_data if point["throttle_percent"] is not None]

  if throttle_values:
    print(f"\n--- THROTTLE ANALYSIS ---")
    max_throttle = max(throttle_values)
    min_throttle = min(throttle_values)
    avg_throttle = sum(throttle_values) / len(throttle_values)

    print(f"Throttle range: {min_throttle}% to {max_throttle}%")
    print(f"Average throttle: {avg_throttle:.1f}%")

    # Throttle distribution
    throttle_ranges = {
      "0% (Off throttle)": sum(1 for t in throttle_values if t == 0),
      "1-25% (Light throttle)": sum(1 for t in throttle_values if 1 <= t <= 25),
      "26-50% (Medium throttle)": sum(1 for t in throttle_values if 26 <= t <= 50),
      "51-75% (Heavy throttle)": sum(1 for t in throttle_values if 51 <= t <= 75),
      "76-99% (Almost full)": sum(1 for t in throttle_values if 76 <= t <= 99),
      "100%+ (Full throttle)": sum(1 for t in throttle_values if t >= 100),
    }

    print("\nThrottle distribution:")
    for range_name, count in throttle_ranges.items():
      percentage = (count / len(throttle_values)) * 100 if throttle_values else 0
      print(f"  {range_name}: {count} points ({percentage:.1f}%)")

  # Speed analysis
  speed_values = [point["speed_kmh"] for point in telemetry_data if point["speed_kmh"] is not None]

  if speed_values:
    print(f"\n--- SPEED ANALYSIS ---")
    max_speed = max(speed_values)
    min_speed = min(speed_values)
    avg_speed = sum(speed_values) / len(speed_values)

    print(f"Speed range: {min_speed} to {max_speed} km/h")
    print(f"Average speed: {avg_speed:.1f} km/h")

  # RPM analysis
  rpm_values = [point["rpm"] for point in telemetry_data if point["rpm"] is not None]

  if rpm_values:
    print(f"\n--- RPM ANALYSIS ---")
    max_rpm = max(rpm_values)
    min_rpm = min(rpm_values)
    avg_rpm = sum(rpm_values) / len(rpm_values)

    print(f"RPM range: {min_rpm} to {max_rpm}")
    print(f"Average RPM: {avg_rpm:.0f}")

  # Show sample data points
  print(f"\n--- SAMPLE TELEMETRY DATA ---")
  sample_count = min(5, len(telemetry_data))
  for i in range(sample_count):
    point = telemetry_data[i]
    print(f"Point {i + 1} @ {point['log_timestamp']}:")
    print(f"  Throttle: {point['throttle_percent']}% | Brake: {point['brake_percent']}%")
    print(f"  Speed: {point['speed_kmh']} km/h | RPM: {point['rpm']}")
    print(f"  Gear: {point['gear']} | DRS: {point['drs_status']}")
    print(f"  All channels: {point['raw_channels']}")
    print()


def main():
  """Main function to discover drivers and extract telemetry."""
  log_file = r"data\raw\20250802_123439.log.log"

  if not Path(log_file).exists():
    print(f"Log file not found: {log_file}")
    return

  print("DISCOVERING DRIVERS WITH TELEMETRY DATA...")
  driver_counts = discover_drivers_with_telemetry(log_file)

  print(f"\nFound telemetry data for {len(driver_counts)} drivers:")
  for driver_num, count in sorted(driver_counts.items(), key=lambda x: int(x[0])):
    print(f"  Driver #{driver_num}: {count} data points")

  # Extract data for driver #44 (or first available driver if 44 doesn't exist)
  target_driver = "44"
  if target_driver not in driver_counts:
    if driver_counts:
      target_driver = sorted(driver_counts.keys(), key=int)[0]
      print(f"\nDriver #44 not found. Using driver #{target_driver} instead.")
    else:
      print("No drivers with telemetry data found!")
      return

  print(f"\nExtracting telemetry for driver #{target_driver}...")
  telemetry_data = extract_driver_telemetry(log_file, target_driver)

  # Analyze the data
  analyze_telemetry(telemetry_data, target_driver)

  # Save to file
  if telemetry_data:
    output_file = f"driver_{target_driver}_telemetry.json"
    with Path(output_file).open("w") as f:
      json_data = []
      for point in telemetry_data:
        json_point = point.copy()
        json_point["log_timestamp"] = point["log_timestamp"].isoformat()
        json_data.append(json_point)

      json.dump(json_data, f, indent=2)

    print(f"\nTelemetry data saved to: {output_file}")


if __name__ == "__main__":
  main()
