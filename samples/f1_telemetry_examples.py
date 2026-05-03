#!/usr/bin/env python3
"""
Example Usage of Simple F1 Telemetry Downloader
Shows how to download specific F1 sessions and work with the data.
"""

from analytics.simple_f1_telemetry_downloader import download_session_telemetry
import json
from pathlib import Path


def download_belgian_gp_race():
    """Download Belgian GP 2024 Race data."""
    print("🏁 Downloading Belgian GP 2024 Race...")
    
    data = download_session_telemetry(
        year=2024,
        meeting_path="2024-07-28_Belgian_Grand_Prix",
        session_path="2024-07-28_Race",
        output_dir="belgian_gp_2024_race"
    )
    
    return data


def download_hungarian_gp_qualifying():
    """Download Hungarian GP 2024 Qualifying data."""
    print("🏁 Downloading Hungarian GP 2024 Qualifying...")
    
    data = download_session_telemetry(
        year=2024,
        meeting_path="2024-07-21_Hungarian_Grand_Prix", 
        session_path="2024-07-20_Qualifying",
        output_dir="hungarian_gp_2024_qualifying"
    )
    
    return data


def analyze_driver_data(session_folder):
    """Analyze driver data from a downloaded session."""
    driver_file = Path(session_folder) / "driver_list.json"
    
    if not driver_file.exists():
        print(f"❌ Driver list not found in {session_folder}")
        return
    
    with open(driver_file, 'r', encoding='utf-8') as f:
        drivers = json.load(f)
    
    print(f"\n📊 DRIVER ANALYSIS - {session_folder}")
    print("=" * 60)
    
    # Find Hamilton's data (car #44)
    hamilton_data = None
    for car_num, driver_info in drivers.items():
        if driver_info.get('LastName', '').upper() == 'HAMILTON':
            hamilton_data = driver_info
            print(f"🏎️  Found Lewis Hamilton - Car #{car_num}")
            print(f"   Full Name: {driver_info.get('FullName', 'N/A')}")
            print(f"   Team: {driver_info.get('TeamName', 'N/A')}")
            print(f"   Team Color: #{driver_info.get('TeamColour', 'N/A')}")
            break
    
    if not hamilton_data:
        print("❌ Lewis Hamilton not found in driver list")
    
    # Show all drivers
    print(f"\n👥 ALL DRIVERS ({len(drivers)} total):")
    for car_num, driver_info in sorted(drivers.items(), key=lambda x: int(x[0])):
        name = driver_info.get('FullName', 'Unknown')
        team = driver_info.get('TeamName', 'Unknown')
        print(f"   #{car_num:2} - {name:20} ({team})")


def show_session_summary(session_folder):
    """Show summary of downloaded session data."""
    session_path = Path(session_folder)
    
    if not session_path.exists():
        print(f"❌ Session folder not found: {session_folder}")
        return
    
    print(f"\n📋 SESSION SUMMARY - {session_folder}")
    print("=" * 60)
    
    # Read session info
    session_info_file = session_path / "session_info.json"
    if session_info_file.exists():
        with open(session_info_file, 'r', encoding='utf-8') as f:
            session_info = json.load(f)
        
        meeting = session_info.get('Meeting', {})
        print(f"🏁 Grand Prix: {meeting.get('Name', 'Unknown')}")
        print(f"🏟️  Location: {meeting.get('Location', 'Unknown')}")
        print(f"📅 Date: {session_info.get('StartDate', 'Unknown')}")
        print(f"🏆 Session: {session_info.get('Name', 'Unknown')}")
    
    # List all available data files
    json_files = list(session_path.glob("*.json"))
    print(f"\n📁 Available Data Files ({len(json_files)}):")
    
    for json_file in sorted(json_files):
        if json_file.name == "download_summary.json":
            continue
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                keys = list(data.keys())[:3]
                print(f"   • {json_file.name:25} - Dict with keys: {keys}")
            elif isinstance(data, list):
                print(f"   • {json_file.name:25} - List with {len(data)} items")
            else:
                print(f"   • {json_file.name:25} - Single value")
                
        except Exception as e:
            print(f"   • {json_file.name:25} - Error reading: {str(e)[:30]}")


def main():
    """Main function demonstrating different downloads."""
    
    print("🏎️  F1 TELEMETRY DOWNLOADER - USAGE EXAMPLES")
    print("=" * 60)
    
    # Example 1: Download Belgian GP Race
    print("\n1️⃣  EXAMPLE 1: Belgian GP 2024 Race")
    belgian_data = download_belgian_gp_race()
    
    if belgian_data:
        show_session_summary("belgian_gp_2024_race")
        analyze_driver_data("belgian_gp_2024_race")
    
    # Example 2: Download Hungarian GP Qualifying
    print("\n\n2️⃣  EXAMPLE 2: Hungarian GP 2024 Qualifying")
    hungarian_data = download_hungarian_gp_qualifying()
    
    if hungarian_data:
        show_session_summary("hungarian_gp_2024_qualifying") 
        analyze_driver_data("hungarian_gp_2024_qualifying")
    
    print(f"\n✅ Examples completed!")
    print(f"💡 Check the created folders for all JSON files with telemetry data.")
    print(f"🔍 Use the individual JSON files to analyze specific aspects:")
    print(f"   • driver_list.json - All drivers and their details")
    print(f"   • timing_data.json - Lap times and sector information") 
    print(f"   • weather_data.json - Track weather conditions")
    print(f"   • session_info.json - Grand Prix and session details")


if __name__ == "__main__":
    main()
