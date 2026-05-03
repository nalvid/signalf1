#!/usr/bin/env python3
"""
Extract telemetry for the most active driver and plot speed data.
"""

import json
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from signalf1.extractor import parse_log_file, decompress_data


def extract_driver_telemetry_with_activity(log_file_path: str, target_driver: str = None):
  """
  Extract telemetry for a specific driver or find the most active one.

  Args:
      log_file_path: Path to the F1 log file
      target_driver: Specific driver number or None to auto-select most active

  Returns:
      Tuple of (driver_number, telemetry_data)
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

  # If no specific driver requested, find the most active one
  if target_driver is None:
    print("\nAnalyzing driver activity...")
    driver_activity = {}

    for driver_num, data_points in all_driver_data.items():
      speeds = [p["speed_kmh"] for p in data_points if p["speed_kmh"] is not None]
      max_speed = max(speeds) if speeds else 0
      speed_variance = len(set(speeds)) if speeds else 0

      driver_activity[driver_num] = {
        "max_speed": max_speed,
        "speed_variance": speed_variance,
        "total_points": len(data_points),
      }

    # Sort by activity (speed variance + max speed)
    most_active = max(driver_activity.items(), key=lambda x: x[1]["speed_variance"] + (x[1]["max_speed"] / 10))

    target_driver = most_active[0]
    print(
      f"Most active driver: #{target_driver} (max speed: {most_active[1]['max_speed']} km/h, "
      f"speed variance: {most_active[1]['speed_variance']}, points: {most_active[1]['total_points']})"
    )

  return target_driver, all_driver_data.get(target_driver, [])


def plot_driver_speed(driver_num, telemetry_data):
  """
  Create a speed plot for the driver's telemetry data.

  Args:
      driver_num: Driver number
      telemetry_data: List of telemetry data points
  """
  if not telemetry_data:
    print(f"No telemetry data available for driver #{driver_num}")
    return

  print(f"\nCreating speed plot for driver #{driver_num}...")

  # Extract time and speed data - use UTC timestamps for proper time series
  utc_times = []
  speeds = []
  throttle_values = []
  rpms = []
  gears = []

  for i, point in enumerate(telemetry_data):
    if point["speed_kmh"] is not None:
      # Try to use UTC timestamp, fall back to sequence number
      if point.get("utc_timestamp"):
        try:
          # Parse UTC timestamp
          utc_time = datetime.fromisoformat(point["utc_timestamp"].replace("Z", "+00:00"))
          utc_times.append(utc_time)
        except:
          # If UTC parsing fails, use sequence number
          utc_times.append(i)
      else:
        # Use sequence number as fallback
        utc_times.append(i)

      speeds.append(point["speed_kmh"])
      throttle_values.append(point.get("throttle_percent", 0))
      rpms.append(point.get("rpm", 0))
      gears.append(point.get("gear", 0))

  if not speeds:
    print("No speed data available for plotting")
    return

  print(f"Plotting {len(speeds)} data points over time...")
  print(f"Time range: {utc_times[0]} to {utc_times[-1]}")

  # Create the plot with more subplots for comprehensive telemetry
  fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

  # Speed plot
  ax1.plot(utc_times, speeds, "b-", linewidth=2, marker="o", markersize=4, label="Speed")
  ax1.set_ylabel("Speed (km/h)", fontsize=12)
  ax1.set_title(f"F1 Driver #{driver_num} - Speed Telemetry", fontsize=14, fontweight="bold")
  ax1.grid(True, alpha=0.3)
  ax1.legend()

  # Add speed statistics as text
  max_speed = max(speeds)
  min_speed = min(speeds)
  avg_speed = sum(speeds) / len(speeds)

  stats_text = f"Max: {max_speed} km/h\nMin: {min_speed} km/h\nAvg: {avg_speed:.1f} km/h"
  ax1.text(
    0.02,
    0.98,
    stats_text,
    transform=ax1.transAxes,
    fontsize=10,
    verticalalignment="top",
    bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.8},
  )

  # Throttle plot
  ax2.plot(utc_times, throttle_values, "g-", linewidth=2, marker="s", markersize=3, label="Throttle")
  ax2.set_ylabel("Throttle (%)", fontsize=12)
  ax2.set_title(f"F1 Driver #{driver_num} - Throttle Input", fontsize=14, fontweight="bold")
  ax2.grid(True, alpha=0.3)
  ax2.legend()

  # RPM plot
  ax3.plot(utc_times, rpms, "r-", linewidth=2, marker="^", markersize=3, label="RPM")
  ax3.set_ylabel("RPM", fontsize=12)
  ax3.set_title(f"F1 Driver #{driver_num} - Engine RPM", fontsize=14, fontweight="bold")
  ax3.grid(True, alpha=0.3)
  ax3.legend()

  # Gear plot
  ax4.plot(utc_times, gears, "purple", linewidth=2, marker="D", markersize=4, label="Gear")
  ax4.set_ylabel("Gear", fontsize=12)
  ax4.set_xlabel("Time/Sequence", fontsize=12)
  ax4.set_title(f"F1 Driver #{driver_num} - Gear Position", fontsize=14, fontweight="bold")
  ax4.grid(True, alpha=0.3)
  ax4.legend()

  # Format x-axis labels based on data type
  if isinstance(utc_times[0], datetime):
    # If we have real timestamps, format them nicely
    for ax in [ax1, ax2, ax3, ax4]:
      plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
      ax.set_xlabel("UTC Time", fontsize=12)
  else:
    # If we're using sequence numbers, label accordingly
    for ax in [ax1, ax2, ax3, ax4]:
      ax.set_xlabel("Data Point Sequence", fontsize=12)

  plt.tight_layout()

  # Save the plot
  plot_filename = f"driver_{driver_num}_telemetry_plot.png"
  plt.savefig(plot_filename, dpi=300, bbox_inches="tight")
  print(f"Telemetry plot saved as: {plot_filename}")

  # Show the plot
  plt.show()

  # Print summary
  print("\n📊 TELEMETRY ANALYSIS SUMMARY:")
  print(f"   Driver: #{driver_num}")
  print(f"   Data points: {len(speeds)}")
  print(f"   Speed range: {min_speed} - {max_speed} km/h")
  print(f"   Average speed: {avg_speed:.1f} km/h")
  print(f"   Time span: {utc_times[0]} to {utc_times[-1]}")

  # Print detailed data points
  print(f"\n📋 DETAILED DATA POINTS:")
  for i, (time, speed, throttle, rpm, gear) in enumerate(
    zip(utc_times[:10], speeds[:10], throttle_values[:10], rpms[:10], gears[:10])
  ):
    print(f"   {i + 1}: Time={time}, Speed={speed}km/h, Throttle={throttle}%, RPM={rpm}, Gear={gear}")

  if len(speeds) > 10:
    print(f"   ... and {len(speeds) - 10} more data points")


def main():
  """Main function to extract telemetry and create speed plot."""
  log_file = r"data\raw\hungary2025.log"

  if not Path(log_file).exists():
    print(f"❌ Log file not found: {log_file}")
    return

  print("🏎️  F1 SPEED TELEMETRY ANALYZER")
  print("=" * 50)

  # Extract telemetry for the most active driver
  driver_num, telemetry_data = extract_driver_telemetry_with_activity(log_file)

  if not telemetry_data:
    print("❌ No telemetry data found")
    return

  # Create speed plot
  plot_driver_speed(driver_num, telemetry_data)

  # Save detailed data
  output_file = f"driver_{driver_num}_full_telemetry.json"
  export_data = []
  for point in telemetry_data:
    export_point = point.copy()
    export_point["log_timestamp"] = point["log_timestamp"].isoformat()
    export_data.append(export_point)

  with Path(output_file).open("w") as f:
    json.dump(export_data, f, indent=2)

  print(f"💾 Full telemetry data saved to: {output_file}")
  print("✅ Analysis complete!")


if __name__ == "__main__":
  main()
