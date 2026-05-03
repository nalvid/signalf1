#!/usr/bin/env python3
"""
Test script to extract and decompress F1 timing data
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from signalf1.extractor import (
  parse_log_file,
  extract_car_data,
  decompress_data,
  generate_log_summary,
  print_log_summary,
)


def test_compressed_data_extraction():
  """Test extracting and decompressing data from the log file."""
  log_file = r"data\raw\20250802_123439.log.log"

  print("Parsing log file...")
  entries = parse_log_file(log_file)
  print(f"Found {len(entries)} log entries")

  print("\nExtracting compressed car data...")
  car_data = extract_car_data(entries, limit=5)
  print(f"Found {len(car_data)} compressed car data entries")

  for i, (timestamp, decompressed) in enumerate(car_data):
    print(f"\n--- Car Data Entry {i + 1} ---")
    print(f"Timestamp: {timestamp}")
    print(f"Decompressed data (first 200 chars):")
    print(decompressed[:200] + "..." if len(decompressed) > 200 else decompressed)

  # Test direct decompression of a known compressed string
  print("\n" + "=" * 60)
  print("TESTING DIRECT DECOMPRESSION")
  print("=" * 60)

  # Find a compressed data string from the log
  for entry in entries[:100]:  # Check first 100 entries
    if entry.raw_data and "M" in entry.raw_data:
      messages = entry.raw_data.get("M", [])
      for msg in messages:
        if msg.get("H") == "Streaming" and msg.get("M") == "feed":
          args = msg.get("A", [])
          if len(args) >= 2:
            data_type, data = args[0], args[1]
            if data_type.endswith(".z") and isinstance(data, str):
              print(f"\nFound compressed data type: {data_type}")
              print(f"Compressed string length: {len(data)}")
              print(f"First 100 chars: {data[:100]}...")

              decompressed = decompress_data(data)
              if decompressed:
                print(f"Successfully decompressed! Length: {len(decompressed)}")
                print(f"Decompressed content (first 300 chars):")
                print(decompressed[:300] + "..." if len(decompressed) > 300 else decompressed)
              else:
                print("Failed to decompress data")

              return  # Exit after finding one example

  print("No compressed data found in the first 100 entries")


def test_full_summary():
  """Generate and print a full summary of the log."""
  log_file = r"data\raw\20250802_123439.log.log"

  print("\n" + "=" * 60)
  print("GENERATING FULL LOG SUMMARY")
  print("=" * 60)

  summary = generate_log_summary(log_file)
  print_log_summary(summary)


if __name__ == "__main__":
  test_compressed_data_extraction()
  test_full_summary()
