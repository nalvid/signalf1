#!/usr/bin/env python3
"""
Debug script to analyze compressed data format
"""

import sys
import os
import base64
import zlib
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from signalf1.extractor import parse_log_file


def debug_compressed_data():
  """Debug the compressed data format."""
  log_file = r"data\raw\20250802_123439.log.log"

  print("Parsing log file...")
  entries = parse_log_file(log_file)

  # Find compressed data examples
  compressed_examples = []
  for entry in entries[:200]:  # Check first 200 entries
    if entry.raw_data and "M" in entry.raw_data:
      messages = entry.raw_data.get("M", [])
      for msg in messages:
        if msg.get("H") == "Streaming" and msg.get("M") == "feed":
          args = msg.get("A", [])
          if len(args) >= 2:
            data_type, data = args[0], args[1]
            if data_type.endswith(".z") and isinstance(data, str):
              compressed_examples.append((data_type, data))
              if len(compressed_examples) >= 3:
                break

  print(f"\nFound {len(compressed_examples)} compressed data examples")

  for i, (data_type, compressed_data) in enumerate(compressed_examples):
    print(f"\n--- Example {i + 1}: {data_type} ---")
    print(f"Length: {len(compressed_data)}")
    print(f"First 100 chars: {compressed_data[:100]}...")
    print(f"Last 100 chars: ...{compressed_data[-100:]}")

    # Try different decompression methods
    print("\nTesting decompression methods:")

    # Method 1: Direct base64 + zlib
    try:
      decoded = base64.b64decode(compressed_data)
      decompressed = zlib.decompress(decoded)
      result = decompressed.decode("utf-8")
      print(f"✓ Method 1 (base64 + zlib): SUCCESS - {len(result)} chars")
      print(f"  Content: {result[:200]}...")
    except Exception as e:
      print(f"✗ Method 1 (base64 + zlib): FAILED - {e}")

    # Method 2: Try with different padding
    try:
      # Add padding if needed
      padding = 4 - (len(compressed_data) % 4)
      if padding != 4:
        padded_data = compressed_data + "=" * padding
      else:
        padded_data = compressed_data

      decoded = base64.b64decode(padded_data)
      decompressed = zlib.decompress(decoded)
      result = decompressed.decode("utf-8")
      print(f"✓ Method 2 (padded base64 + zlib): SUCCESS - {len(result)} chars")
      print(f"  Content: {result[:200]}...")
    except Exception as e:
      print(f"✗ Method 2 (padded base64 + zlib): FAILED - {e}")

    # Method 3: Try gzip instead of zlib
    try:
      import gzip

      decoded = base64.b64decode(compressed_data)
      decompressed = gzip.decompress(decoded)
      result = decompressed.decode("utf-8")
      print(f"✓ Method 3 (base64 + gzip): SUCCESS - {len(result)} chars")
      print(f"  Content: {result[:200]}...")
    except Exception as e:
      print(f"✗ Method 3 (base64 + gzip): FAILED - {e}")

    # Method 4: Try without base64 decoding
    try:
      decompressed = zlib.decompress(compressed_data.encode("utf-8"))
      result = decompressed.decode("utf-8")
      print(f"✓ Method 4 (direct zlib): SUCCESS - {len(result)} chars")
      print(f"  Content: {result[:200]}...")
    except Exception as e:
      print(f"✗ Method 4 (direct zlib): FAILED - {e}")

    # Method 5: Check if it's actually JSON
    try:
      parsed = json.loads(compressed_data)
      print(f"✓ Method 5 (JSON): SUCCESS - it's actually JSON!")
      print(f"  Content: {json.dumps(parsed, indent=2)[:200]}...")
    except Exception as e:
      print(f"✗ Method 5 (JSON): FAILED - {e}")

    print("-" * 60)


if __name__ == "__main__":
  debug_compressed_data()
