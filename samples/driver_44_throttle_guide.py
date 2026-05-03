#!/usr/bin/env python3
"""
SUMMARY: How to Extract F1 Throttle Telemetry Data for Driver #44

This is a complete guide showing how to extract throttle and other telemetry data
for any F1 driver from live timing log files.
"""

import json
from pathlib import Path
from signalf1.extractor import parse_log_file, decompress_data


def extract_driver_throttle_data(log_file_path: str, driver_number: str):
  """
  Extract throttle telemetry data for a specific driver.

  Args:
      log_file_path: Path to the F1 log file
      driver_number: Driver number as string (e.g., "44")

  Returns:
      List of telemetry data points with throttle information
  """
  # Step 1: Parse the log file
  entries = parse_log_file(log_file_path)
  print(f"Parsed {len(entries)} log entries")

  # Step 2: Extract compressed telemetry data
  throttle_data = []

  for entry in entries:
    # Check if entry contains SignalR data
    if entry.raw_data and isinstance(entry.raw_data, dict):
      # Look for compressed car data in the 'R' field
      if "R" in entry.raw_data and isinstance(entry.raw_data["R"], dict):
        r_data = entry.raw_data["R"]

        # CarData.z contains compressed telemetry channels
        if "CarData.z" in r_data:
          compressed_data = r_data["CarData.z"]

          # Step 3: Decompress the data
          decompressed = decompress_data(compressed_data)

          if decompressed:
            try:
              car_data = json.loads(decompressed)

              # Step 4: Extract data for the specific driver
              if "Entries" in car_data:
                for data_entry in car_data["Entries"]:
                  cars = data_entry.get("Cars", {})

                  # Check if our target driver has data
                  if driver_number in cars:
                    driver_data = cars[driver_number]
                    channels = driver_data.get("Channels", {})

                    # Step 5: Map telemetry channels to meaningful names
                    telemetry_point = {
                      "timestamp": entry.timestamp,
                      "utc_time": data_entry.get("Utc"),
                      # F1 Telemetry Channel Mapping:
                      "rpm": channels.get("0"),  # Engine RPM
                      "speed_kmh": channels.get("2"),  # Speed in km/h
                      "gear": channels.get("3"),  # Current gear
                      "throttle_percent": channels.get("4"),  # Throttle position (0-100%)
                      "brake_percent": channels.get("5"),  # Brake pressure (0-100%)
                      "drs_status": channels.get("45"),  # DRS system status
                      # Raw channel data for reference
                      "raw_channels": channels,
                    }

                    throttle_data.append(telemetry_point)

            except json.JSONDecodeError:
              # Skip malformed JSON data
              continue

  return throttle_data


def main():
  """Example usage for extracting driver #44 throttle data."""

  print("=" * 60)
  print("F1 DRIVER #44 THROTTLE DATA EXTRACTION GUIDE")
  print("=" * 60)

  # Configuration
  log_file = r"data\raw\hungary2025.log"
  target_driver = "44"  # Lewis Hamilton's car number

  # Check if log file exists
  if not Path(log_file).exists():
    print(f"❌ Log file not found: {log_file}")
    return

  # Extract throttle data
  print(f"\n🔍 Extracting throttle data for driver #{target_driver}...")
  throttle_data = extract_driver_throttle_data(log_file, target_driver)

  # Analyze results
  if throttle_data:
    print(f"✅ Successfully extracted {len(throttle_data)} throttle data points!")

    # Basic analysis
    throttle_values = [point["throttle_percent"] for point in throttle_data if point["throttle_percent"] is not None]

    if throttle_values:
      print(f"\n📊 THROTTLE ANALYSIS:")
      print(f"   • Data points: {len(throttle_values)}")
      print(f"   • Throttle range: {min(throttle_values)}% - {max(throttle_values)}%")
      print(f"   • Average throttle: {sum(throttle_values) / len(throttle_values):.1f}%")

      # Show first few data points
      print(f"\n📋 SAMPLE DATA:")
      for i, point in enumerate(throttle_data[:3]):
        print(f"   Point {i + 1}: {point['timestamp']}")
        print(f"      Throttle: {point['throttle_percent']}%")
        print(f"      Speed: {point['speed_kmh']} km/h")
        print(f"      RPM: {point['rpm']}")
        print()

    # Export data
    output_file = f"driver_{target_driver}_throttle_data.json"
    export_data = []
    for point in throttle_data:
      export_point = point.copy()
      export_point["timestamp"] = point["timestamp"].isoformat()
      export_data.append(export_point)

    with Path(output_file).open("w") as f:
      json.dump(export_data, f, indent=2)

    print(f"💾 Data saved to: {output_file}")

  else:
    print(f"❌ No throttle data found for driver #{target_driver}")
    print("   This could mean:")
    print("   • Driver was not active during this session")
    print("   • Different driver number in the data")
    print("   • Limited telemetry data in this log file")

  # Usage instructions
  print(f"\n📚 HOW TO USE THIS DATA:")
  print(f"   1. Load the JSON file in your analysis tool")
  print(f"   2. Plot throttle_percent over time for visualization")
  print(f"   3. Correlate with speed_kmh and rpm for analysis")
  print(f"   4. Look for patterns in throttle application")

  # F1 Channel Reference
  print(f"\n🏎️  F1 TELEMETRY CHANNEL REFERENCE:")
  print(f"   • Channel 0: Engine RPM")
  print(f"   • Channel 2: Speed (km/h)")
  print(f"   • Channel 3: Gear position")
  print(f"   • Channel 4: Throttle position (0-100%)")
  print(f"   • Channel 5: Brake pressure (0-100%)")
  print(f"   • Channel 45: DRS (Drag Reduction System) status")

  print(f"\n✨ Extraction complete!")


if __name__ == "__main__":
  main()
