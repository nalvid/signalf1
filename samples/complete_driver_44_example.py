#!/usr/bin/env python3
"""
Complete example: Extract and visualize F1 throttle telemetry data for driver #44.

This script demonstrates the complete workflow for extracting throttle telemetry data
from F1 live timing logs, including data validation and export for visualization.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from signalf1.extractor import parse_log_file, decompress_data


def extract_all_driver_telemetry(log_file_path: str) -> Dict[str, List[Dict[str, Any]]]:
  """
  Extract telemetry data for all drivers to find the most active one.

  Args:
      log_file_path: Path to the F1 log file

  Returns:
      Dictionary mapping driver numbers to their telemetry data
  """
  entries = parse_log_file(log_file_path)
  all_driver_data = {}

  print("Extracting telemetry data for all drivers...")

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

                  for driver_num, driver_data in cars.items():
                    if driver_num not in all_driver_data:
                      all_driver_data[driver_num] = []

                    channels = driver_data.get("Channels", {})

                    telemetry_point = {
                      "log_timestamp": entry.timestamp,
                      "utc_timestamp": utc_time,
                      "rpm": channels.get("0"),
                      "speed_kmh": channels.get("2"),
                      "gear": channels.get("3"),
                      "throttle_percent": channels.get("4"),
                      "brake_percent": channels.get("5"),
                      "drs_status": channels.get("45"),
                      "all_channels": channels,
                    }

                    all_driver_data[driver_num].append(telemetry_point)

            except json.JSONDecodeError:
              continue

  return all_driver_data


def analyze_driver_activity(all_driver_data: Dict[str, List[Dict[str, Any]]]) -> None:
  """
  Analyze which drivers have the most telemetry activity.

  Args:
      all_driver_data: Dictionary of driver telemetry data
  """
  print(f"\n{'=' * 60}")
  print("DRIVER ACTIVITY ANALYSIS")
  print(f"{'=' * 60}")

  driver_stats = {}

  for driver_num, data_points in all_driver_data.items():
    if not data_points:
      continue

    # Calculate activity metrics
    speeds = [p["speed_kmh"] for p in data_points if p["speed_kmh"] is not None]
    throttles = [p["throttle_percent"] for p in data_points if p["throttle_percent"] is not None]

    max_speed = max(speeds) if speeds else 0
    unique_throttle_values = len(set(throttles)) if throttles else 0

    # Check for varying data (not just static values)
    speed_variance = len(set(speeds)) if speeds else 0
    throttle_variance = len(set(throttles)) if throttles else 0

    driver_stats[driver_num] = {
      "total_points": len(data_points),
      "max_speed": max_speed,
      "unique_throttle_values": unique_throttle_values,
      "speed_variance": speed_variance,
      "throttle_variance": throttle_variance,
      "activity_score": speed_variance + throttle_variance + (max_speed / 10),
    }

  # Sort by activity score
  sorted_drivers = sorted(driver_stats.items(), key=lambda x: x[1]["activity_score"], reverse=True)

  print("Driver activity ranking (most active first):")
  for i, (driver_num, stats) in enumerate(sorted_drivers[:10]):  # Show top 10
    print(
      f"{i + 1:2d}. Driver #{driver_num:2s}: "
      f"{stats['total_points']:3d} points, "
      f"max speed: {stats['max_speed']:3.0f} km/h, "
      f"throttle variance: {stats['throttle_variance']}, "
      f"activity score: {stats['activity_score']:.1f}"
    )


def extract_driver_44_throttle_detailed(all_driver_data: Dict[str, List[Dict[str, Any]]]) -> None:
  """
  Detailed analysis of driver #44 throttle data.

  Args:
      all_driver_data: Dictionary of all driver telemetry data
  """
  driver_44_data = all_driver_data.get("44", [])

  print(f"\n{'=' * 60}")
  print("DETAILED DRIVER #44 THROTTLE ANALYSIS")
  print(f"{'=' * 60}")

  if not driver_44_data:
    print("No telemetry data found for driver #44")
    return

  print(f"Total data points for driver #44: {len(driver_44_data)}")

  # Time range
  timestamps = [point["log_timestamp"] for point in driver_44_data]
  time_range = max(timestamps) - min(timestamps)
  print(f"Data time span: {time_range}")

  # Channel analysis
  all_channels_used = set()
  for point in driver_44_data:
    all_channels_used.update(point["all_channels"].keys())

  print(f"Telemetry channels available: {sorted(all_channels_used)}")

  # Throttle-specific analysis
  throttle_values = [point["throttle_percent"] for point in driver_44_data if point["throttle_percent"] is not None]

  if throttle_values:
    print(f"\n--- THROTTLE DATA ---")
    print(f"Throttle value range: {min(throttle_values)}% to {max(throttle_values)}%")
    print(f"Unique throttle values: {sorted(set(throttle_values))}")

    # Check if data seems realistic
    if all(t == throttle_values[0] for t in throttle_values):
      print("⚠️  WARNING: All throttle values are identical - this might be placeholder data")

    if any(t > 100 for t in throttle_values):
      print("⚠️  WARNING: Throttle values > 100% detected - this might indicate data scaling issues")

  # Speed correlation
  speed_values = [point["speed_kmh"] for point in driver_44_data if point["speed_kmh"] is not None]

  if speed_values:
    print(f"\n--- SPEED CORRELATION ---")
    print(f"Speed range: {min(speed_values)} to {max(speed_values)} km/h")

    if max(speed_values) == 0:
      print("⚠️  Car appears to be stationary (0 km/h) - limited telemetry expected")

  # Export data for visualization
  export_data = []
  for point in driver_44_data:
    export_point = {
      "timestamp": point["log_timestamp"].isoformat(),
      "utc_timestamp": point["utc_timestamp"],
      "throttle_percent": point["throttle_percent"],
      "speed_kmh": point["speed_kmh"],
      "rpm": point["rpm"],
      "gear": point["gear"],
      "brake_percent": point["brake_percent"],
      "drs_status": point["drs_status"],
    }
    export_data.append(export_point)

  # Save to file
  output_file = "driver_44_throttle_detailed.json"
  with Path(output_file).open("w") as f:
    json.dump(export_data, f, indent=2)

  print(f"\n📁 Detailed throttle data exported to: {output_file}")

  # Show sample data
  print(f"\n--- SAMPLE DATA POINTS ---")
  for i, point in enumerate(driver_44_data[:3]):
    print(f"Point {i + 1}:")
    print(f"  Timestamp: {point['log_timestamp']}")
    print(f"  Throttle: {point['throttle_percent']}%")
    print(f"  Speed: {point['speed_kmh']} km/h")
    print(f"  RPM: {point['rpm']}")
    print(f"  All channels: {point['all_channels']}")
    print()


def create_usage_example() -> str:
  """
  Create a usage example for loading and analyzing the exported data.

  Returns:
      Example code as string
  """
  example_code = """
# Example: How to load and analyze the exported throttle data

import json
import matplotlib.pyplot as plt
from datetime import datetime

# Load the exported data
with open("driver_44_throttle_detailed.json", "r") as f:
    throttle_data = json.load(f)

# Convert timestamps
timestamps = [datetime.fromisoformat(point["timestamp"]) for point in throttle_data]
throttle_values = [point["throttle_percent"] for point in throttle_data]
speed_values = [point["speed_kmh"] for point in throttle_data]

# Create visualization
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# Throttle plot
ax1.plot(timestamps, throttle_values, 'g-', linewidth=2, label='Throttle %')
ax1.set_ylabel('Throttle (%)')
ax1.set_title('Driver #44 Throttle Input Over Time')
ax1.grid(True, alpha=0.3)
ax1.legend()

# Speed plot
ax2.plot(timestamps, speed_values, 'b-', linewidth=2, label='Speed (km/h)')
ax2.set_ylabel('Speed (km/h)')
ax2.set_xlabel('Time')
ax2.set_title('Driver #44 Speed Over Time')
ax2.grid(True, alpha=0.3)
ax2.legend()

plt.tight_layout()
plt.show()

# Analysis
print(f"Average throttle: {sum(throttle_values)/len(throttle_values):.1f}%")
print(f"Max speed: {max(speed_values)} km/h")
print(f"Data points: {len(throttle_data)}")
"""
  return example_code


def main():
  """Main function demonstrating complete F1 telemetry extraction workflow."""
  log_file = r"data\raw\20250802_123439.log.log"

  if not Path(log_file).exists():
    print(f"❌ Log file not found: {log_file}")
    return

  print("🏎️  F1 TELEMETRY EXTRACTOR - DRIVER #44 THROTTLE ANALYSIS")
  print("=" * 80)

  # Extract data for all drivers
  all_driver_data = extract_all_driver_telemetry(log_file)

  # Analyze driver activity
  analyze_driver_activity(all_driver_data)

  # Focus on driver #44
  extract_driver_44_throttle_detailed(all_driver_data)

  # Create usage example
  example_code = create_usage_example()
  with Path("visualization_example.py").open("w") as f:
    f.write(example_code)

  print(f"\n📊 Visualization example saved to: visualization_example.py")
  print("\n✅ Analysis complete!")
  print("\nTo visualize the data:")
  print("1. Install matplotlib: pip install matplotlib")
  print("2. Run: python visualization_example.py")


if __name__ == "__main__":
  main()
