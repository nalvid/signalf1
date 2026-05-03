#!/usr/bin/env python3
"""
F1 TELEMETRY DATA DOWNLOADER - Based on Official F1 LiveTiming API

This shows how to get real F1 telemetry data using the official endpoints
documented at https://livef1.goktugocal.com/livetimingf1/data_topics.html
"""

import requests
import json
from pathlib import Path


def download_f1_telemetry(year, meeting_path, session_path, output_dir="f1_data"):
    """
    Download F1 telemetry data from official F1 LiveTiming API.
    
    Args:
        year: Season year (e.g., 2024)
        meeting_path: Meeting identifier (e.g., "2024-07-28_Belgian_Grand_Prix")
        session_path: Session identifier (e.g., "2024-07-28_Race")
        output_dir: Directory to save files
    
    URL Pattern: https://livetiming.formula1.com/static/{year}/{meeting_path}/{session_path}/{topic}
    """
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Key telemetry endpoints from the documentation
    telemetry_endpoints = {
        # CORE TELEMETRY DATA
        "CarData.z": "Car telemetry data (speed, engine, suspension)",
        "Position.z": "Car position data on track",
        "TimingDataF1.json": "Timing data with sector times and speeds",
        
        # SESSION DATA
        "SessionInfo.json": "Session details and metadata",
        "SessionData.json": "Raw session data with lap times",
        "SessionStatus.json": "Live session status",
        
        # DRIVER DATA  
        "DriverList.json": "List of drivers and car numbers",
        "DriverRaceInfo.json": "Individual driver performance metrics",
        
        # TRACK CONDITIONS
        "TrackStatus.jsonStream": "Track conditions and flags", 
        "WeatherData.json": "Current weather conditions",
        "WeatherDataSeries.json": "Historical weather data",
        
        # ADDITIONAL DATA
        "CurrentTyres.json": "Current tyre information",
        "TyreStintSeries.json": "Tyre usage and strategy data",
        "PitStop.json": "Pit stop data",
        "TeamRadio.json": "Team radio communications",
        "RaceControlMessages.json": "Official race control messages"
    }
    
    base_url = f"https://livetiming.formula1.com/static/{year}/{meeting_path}/{session_path}"
    downloaded_files = []
    
    print(f"🏎️  DOWNLOADING F1 TELEMETRY DATA")
    print(f"📅 Year: {year}")
    print(f"🏁 Meeting: {meeting_path}")
    print(f"🔵 Session: {session_path}")
    print(f"🔗 Base URL: {base_url}")
    print("=" * 60)
    
    for endpoint, description in telemetry_endpoints.items():
        url = f"{base_url}/{endpoint}"
        output_file = Path(output_dir) / f"{endpoint.replace('.', '_')}"
        
        print(f"📡 {endpoint:20} - {description}")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200 and len(response.text) > 10:
                # Save the data
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                file_size = len(response.text)
                print(f"   ✅ Downloaded: {file_size:,} bytes")
                downloaded_files.append((endpoint, file_size))
                
                # Show preview for JSON files
                if endpoint.endswith('.json'):
                    try:
                        data = json.loads(response.text)
                        if isinstance(data, dict):
                            keys = list(data.keys())[:3]
                            print(f"   📋 Keys: {keys}")
                    except:
                        pass
                        
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    print("\n" + "=" * 60)
    print(f"📊 DOWNLOAD SUMMARY:")
    print(f"   Successfully downloaded: {len(downloaded_files)} files")
    print(f"   Saved to directory: {output_dir}")
    
    if downloaded_files:
        total_size = sum(size for _, size in downloaded_files)
        print(f"   Total data size: {total_size:,} bytes")
        
        print(f"\n📁 Downloaded files:")
        for filename, size in downloaded_files:
            print(f"   • {filename:25} ({size:,} bytes)")
    
    return downloaded_files


def get_session_examples():
    """Show example session paths for different F1 events."""
    
    examples = {
        "2024 Belgian GP Race": {
            "year": 2024,
            "meeting_path": "2024-07-28_Belgian_Grand_Prix", 
            "session_path": "2024-07-28_Race"
        },
        "2024 Spanish GP Qualifying": {
            "year": 2024,
            "meeting_path": "2024-06-23_Spanish_Grand_Prix",
            "session_path": "2024-06-23_Qualifying"  
        },
        "2024 Monaco GP Practice 3": {
            "year": 2024,
            "meeting_path": "2024-05-26_Monaco_Grand_Prix",
            "session_path": "2024-05-26_Practice_3"
        }
    }
    
    print("🏁 F1 SESSION EXAMPLES:")
    print("=" * 40)
    for name, params in examples.items():
        print(f"📅 {name}:")
        print(f"   Year: {params['year']}")
        print(f"   Meeting: {params['meeting_path']}")
        print(f"   Session: {params['session_path']}")
        print()
    
    return examples


if __name__ == "__main__":
    print("🏎️  F1 OFFICIAL TELEMETRY DOWNLOADER")
    print("Based on: https://livef1.goktugocal.com/livetimingf1/data_topics.html")
    print()
    
    # Show examples
    examples = get_session_examples()
    
    # Try downloading Belgian GP 2024 race data
    print("🔄 Attempting to download Belgian GP 2024 Race data...")
    example = examples["2024 Belgian GP Race"]
    
    downloaded = download_f1_telemetry(
        year=example["year"],
        meeting_path=example["meeting_path"], 
        session_path=example["session_path"],
        output_dir="belgian_gp_2024_race"
    )
    
    if downloaded:
        print(f"\n✅ SUCCESS! Check the 'belgian_gp_2024_race' folder for telemetry data.")
        print(f"💡 TIP: Look for CarData_z and Position_z files - these contain the detailed telemetry!")
    else:
        print(f"\n❌ No data downloaded. The session may not be publicly available.")
        print(f"💡 TIP: Try different session paths or check if the race has happened yet.")
