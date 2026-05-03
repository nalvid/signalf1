#!/usr/bin/env python3
"""
Simple F1 telemetry downloader - single function to get and save telemetry data.
"""

import requests
import json


def download_f1_telemetry(year, round_number, output_file):
    """
    Download F1 telemetry data and save to file.
    
    Args:
        year: F1 season year (e.g., 2024)
        round_number: Race weekend number (e.g., 14 for Spa)
        output_file: Filename to save data
    
    Returns:
        True if successful, False otherwise
    """
    # Try different F1 endpoints
    endpoints = [
        f"https://livetiming.formula1.com/static/{year}/{round_number:02d}/car_data.jsonl",
        f"https://livetiming.formula1.com/static/{year}/{round_number:02d}/lap_times.json",
        f"https://livetiming.formula1.com/static/{year}/{round_number:02d}/session_status.json",
        f"https://api.formula1.com/v1/event-tracker",
        f"https://ergast.com/api/f1/{year}/{round_number}/laps.json",
        f"https://ergast.com/api/f1/{year}/{round_number}/results.json"
    ]
    
    for i, url in enumerate(endpoints):
        print(f"� Trying endpoint {i+1}: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200 and len(response.text) > 100:
                # Save raw data to file
                with open(f"{output_file}_{i+1}.json", 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                print(f"✅ Data saved to: {output_file}_{i+1}.json")
                print(f"📊 File size: {len(response.text)} bytes")
                
                # Show preview of data
                preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
                print(f"📋 Preview: {preview}")
                return True
            else:
                print(f"❌ HTTP {response.status_code} or empty response")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("❌ All endpoints failed")
    return False


# Example usage
if __name__ == "__main__":
    # Try Spa 2025 race telemetry
    success = download_f1_telemetry(2025, 14, "spa_2025_telemetry.jsonl")
    
    if not success:
        # Fallback to 2024 data
        print("\n🔄 Trying 2024 Spa data as backup...")
        download_f1_telemetry(2024, 14, "spa_2024_telemetry.jsonl")
