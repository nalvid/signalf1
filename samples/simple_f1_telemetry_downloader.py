#!/usr/bin/env python3
"""
Simple F1 Telemetry Downloader
Downloads telemetry data from F1 LiveTiming API and saves each data type as separate JSON files.
"""

import requests
import json
import gzip
from pathlib import Path
from datetime import datetime
import sys


def decompress_if_needed(content, filename):
    """Decompress .z files if they contain compressed data."""
    if filename.endswith('.z'):
        try:
            # Try to decompress as gzip
            decompressed = gzip.decompress(content)
            return decompressed.decode('utf-8')
        except:
            # If decompression fails, return as text
            return content.decode('utf-8')
    else:
        return content.decode('utf-8')


def parse_f1_data_format(content):
    """Parse F1 live timing data format which may contain special encoding."""
    try:
        # F1 data often comes in a special format with timestamps and delimited data
        lines = content.strip().split('\n')
        data_objects = []
        
        for line in lines:
            if not line.strip():
                continue
                
            # Try to parse as JSON directly first
            try:
                obj = json.loads(line)
                data_objects.append(obj)
                continue
            except:
                pass
            
            # Check if line contains JSON-like data with timestamp prefix
            if '"' in line and '{' in line:
                # Try to extract JSON part
                json_start = line.find('{')
                if json_start > 0:
                    json_part = line[json_start:]
                    try:
                        obj = json.loads(json_part)
                        # Add timestamp if available
                        timestamp_part = line[:json_start].strip()
                        if timestamp_part:
                            obj['_timestamp'] = timestamp_part
                        data_objects.append(obj)
                        continue
                    except:
                        pass
            
            # If we can't parse as JSON, keep as string
            data_objects.append(line.strip())
        
        # Return as single object if only one item, otherwise as array
        if len(data_objects) == 1:
            return data_objects[0]
        elif len(data_objects) > 1:
            return data_objects
        else:
            return content
            
    except Exception:
        return content


def download_session_telemetry(year, meeting_path, session_path, output_dir=None):
    """
    Download F1 telemetry data for a specific session.
    
    Args:
        year: Season year (e.g., 2024, 2025)
        meeting_path: Meeting identifier (e.g., "2024-07-28_Belgian_Grand_Prix")
        session_path: Session identifier (e.g., "2024-07-28_Race", "2024-07-28_Qualifying")
        output_dir: Directory to save files (auto-generated if None)
    
    Returns:
        dict: Dictionary of downloaded data by endpoint
    """
    
    # Auto-generate output directory name if not provided
    if output_dir is None:
        safe_meeting = meeting_path.replace("-", "").replace("_", "").lower()
        safe_session = session_path.split("_")[-1].lower()  # Get just the session type
        output_dir = f"f1_data_{safe_meeting}_{safe_session}"
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Define telemetry endpoints
    endpoints = {
        # Core telemetry data
        "CarData.z": "car_telemetry_data",
        "Position.z": "position_data", 
        "TimingDataF1.json": "timing_data",
        
        # Session information
        "SessionInfo.json": "session_info",
        "SessionData.json": "session_data",
        "SessionStatus.json": "session_status",
        
        # Driver data
        "DriverList.json": "driver_list",
        "DriverRaceInfo.json": "driver_race_info",
        
        # Track and weather
        "TrackStatus.jsonStream": "track_status",
        "WeatherData.json": "weather_data",
        "WeatherDataSeries.json": "weather_series",
        
        # Additional data
        "CurrentTyres.json": "current_tyres",
        "TyreStintSeries.json": "tyre_stints",
        "PitStop.json": "pit_stops",
        "TeamRadio.json": "team_radio",
        "RaceControlMessages.json": "race_control_messages"
    }
    
    base_url = f"https://livetiming.formula1.com/static/{year}/{meeting_path}/{session_path}"
    downloaded_data = {}
    successful_downloads = 0
    
    print(f"🏎️  F1 TELEMETRY DOWNLOADER")
    print(f"📅 Year: {year}")
    print(f"🏁 Meeting: {meeting_path}")
    print(f"🏆 Session: {session_path}")
    print(f"📁 Output: {output_path.absolute()}")
    print(f"🔗 Base URL: {base_url}")
    print("=" * 70)
    
    for endpoint, output_name in endpoints.items():
        url = f"{base_url}/{endpoint}"
        output_file = output_path / f"{output_name}.json"
        
        print(f"📡 Downloading {endpoint:25} → {output_name}.json")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200 and len(response.content) > 10:
                # Decompress if needed
                content = decompress_if_needed(response.content, endpoint)
                
                # Parse F1 data format
                try:
                    parsed_data = parse_f1_data_format(content)
                    
                    # Save as formatted JSON
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(parsed_data, f, indent=2, ensure_ascii=False)
                    
                    file_size = len(content)
                    
                    # Count data points
                    if isinstance(parsed_data, list):
                        data_points = len(parsed_data)
                    elif isinstance(parsed_data, dict):
                        data_points = len(parsed_data)
                    else:
                        data_points = 1
                    
                    print(f"   ✅ Success: {file_size:,} bytes, {data_points:,} data points")
                    
                    downloaded_data[output_name] = parsed_data
                    successful_downloads += 1
                    
                except Exception as e:
                    # If parsing fails, save as text file
                    text_file = output_path / f"{output_name}.txt"
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"   ⚠️  Saved as text: {len(content):,} bytes (parse error: {str(e)[:30]})")
                    
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    print("\n" + "=" * 70)
    print(f"📊 DOWNLOAD SUMMARY")
    print(f"   Successfully downloaded: {successful_downloads}/{len(endpoints)} files")
    print(f"   Output directory: {output_path.absolute()}")
    
    # Create summary file
    summary = {
        "download_info": {
            "timestamp": datetime.now().isoformat(),
            "year": year,
            "meeting_path": meeting_path,
            "session_path": session_path,
            "base_url": base_url,
            "successful_downloads": successful_downloads,
            "total_endpoints": len(endpoints)
        },
        "downloaded_files": list(downloaded_data.keys())
    }
    
    summary_file = output_path / "download_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"   Summary saved: download_summary.json")
    
    if successful_downloads > 0:
        print(f"\n✅ SUCCESS! Downloaded {successful_downloads} telemetry files.")
        print(f"💡 Check the '{output_dir}' folder for all JSON files.")
        
        # Show what was downloaded
        if downloaded_data:
            print(f"\n📋 AVAILABLE DATA:")
            for file_name in sorted(downloaded_data.keys()):
                data = downloaded_data[file_name]
                if isinstance(data, dict):
                    keys = list(data.keys())[:3]
                    print(f"   • {file_name:20} - Keys: {keys}")
                elif isinstance(data, list):
                    print(f"   • {file_name:20} - List with {len(data)} items")
                else:
                    print(f"   • {file_name:20} - Single value")
    else:
        print(f"\n❌ No data downloaded. Session may not be available.")
    
    return downloaded_data


def get_available_sessions():
    """Show examples of available F1 sessions."""
    
    sessions = {
        "2024 Belgian GP": {
            "year": 2024,
            "meeting": "2024-07-28_Belgian_Grand_Prix",
            "sessions": [
                "2024-07-26_Practice_1",
                "2024-07-26_Practice_2", 
                "2024-07-27_Practice_3",
                "2024-07-27_Qualifying",
                "2024-07-28_Race"
            ]
        },
        "2024 Hungarian GP": {
            "year": 2024,
            "meeting": "2024-07-21_Hungarian_Grand_Prix",
            "sessions": [
                "2024-07-19_Practice_1",
                "2024-07-19_Practice_2",
                "2024-07-20_Practice_3", 
                "2024-07-20_Qualifying",
                "2024-07-21_Race"
            ]
        },
        "2024 British GP": {
            "year": 2024,
            "meeting": "2024-07-07_British_Grand_Prix",
            "sessions": [
                "2024-07-05_Practice_1",
                "2024-07-05_Practice_2",
                "2024-07-06_Practice_3",
                "2024-07-06_Qualifying", 
                "2024-07-07_Race"
            ]
        }
    }
    
    return sessions


def main():
    """Main function with interactive session selection."""
    
    print("🏎️  SIMPLE F1 TELEMETRY DOWNLOADER")
    print("Downloads official F1 telemetry data and saves as separate JSON files")
    print()
    
    # Show available sessions
    sessions = get_available_sessions()
    print("📅 AVAILABLE SESSIONS:")
    print("=" * 50)
    
    for gp_name, gp_info in sessions.items():
        print(f"🏁 {gp_name}:")
        print(f"   Meeting: {gp_info['meeting']}")
        for session in gp_info['sessions']:
            session_type = session.split('_')[-1]
            print(f"   • {session} ({session_type})")
        print()
    
    # For demo, download Hungarian GP 2024 Qualifying
    print("🔄 DEMO: Downloading Hungarian GP 2024 Qualifying...")
    
    hungarian_gp = sessions["2024 Hungarian GP"]
    qualifying_session = "2024-07-20_Qualifying"
    
    downloaded_data = download_session_telemetry(
        year=hungarian_gp["year"],
        meeting_path=hungarian_gp["meeting"],
        session_path=qualifying_session
    )
    
    if downloaded_data:
        print(f"\n🎉 Demo completed successfully!")
        print(f"💡 To download other sessions, call the function with different parameters:")
        print(f"   download_session_telemetry(2024, '2024-07-28_Belgian_Grand_Prix', '2024-07-28_Race')")


if __name__ == "__main__":
    main()
