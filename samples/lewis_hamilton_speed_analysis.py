#!/usr/bin/env python3
"""
Lewis Hamilton (#44) Speed Analysis - Belgian GP 2024
Plots speed data over the race from F1 telemetry data
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
import requests
import time

def load_local_telemetry_data():
    """Load existing telemetry data from downloaded files"""
    base_path = Path("belgian_gp_2024_race")
    
    # Load timing data
    timing_file = base_path / "TimingDataF1_json"
    session_file = base_path / "SessionData_json"
    
    timing_data = None
    session_data = None
    
    if timing_file.exists():
        try:
            with open(timing_file, 'r', encoding='utf-8-sig') as f:
                content = f.read().strip()
                if content:
                    timing_data = json.loads(content)
                    print(f"✓ Loaded timing data from {timing_file}")
                else:
                    print(f"✗ Empty timing data file: {timing_file}")
        except json.JSONDecodeError as e:
            print(f"✗ JSON decode error in timing data: {e}")
        except Exception as e:
            print(f"✗ Error loading timing data: {e}")
    else:
        print(f"✗ Timing data file not found: {timing_file}")
    
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8-sig') as f:
                content = f.read().strip()
                if content:
                    session_data = json.loads(content)
                    print(f"✓ Loaded session data from {session_file}")
                else:
                    print(f"✗ Empty session data file: {session_file}")
        except json.JSONDecodeError as e:
            print(f"✗ JSON decode error in session data: {e}")
        except Exception as e:
            print(f"✗ Error loading session data: {e}")
    else:
        print(f"✗ Session data file not found: {session_file}")
    
    return timing_data, session_data

def extract_hamilton_data(timing_data):
    """Extract Lewis Hamilton's speed and lap data"""
    if not timing_data or 'Lines' not in timing_data:
        return None
    
    # Find Hamilton's data (car #44)
    hamilton_data = timing_data['Lines'].get('44')
    
    if not hamilton_data:
        print("Lewis Hamilton (#44) data not found")
        return None
    
    print(f"Lewis Hamilton (#44) - Position: {hamilton_data.get('Position', 'N/A')}")
    print(f"Gap to Leader: {hamilton_data.get('GapToLeader', 'N/A')}")
    print(f"Number of Laps: {hamilton_data.get('NumberOfLaps', 'N/A')}")
    print(f"Best Lap Time: {hamilton_data.get('BestLapTime', {}).get('Value', 'N/A')}")
    print(f"Last Lap Time: {hamilton_data.get('LastLapTime', {}).get('Value', 'N/A')}")
    
    # Extract speed data at different track points
    speeds = hamilton_data.get('Speeds', {})
    speed_data = {}
    
    for point, data in speeds.items():
        speed_value = data.get('Value', '')
        if speed_value and speed_value.isdigit():
            speed_data[point] = int(speed_value)
    
    print(f"Current Speed Data:")
    for point, speed in speed_data.items():
        print(f"  {point}: {speed} km/h")
    
    return {
        'position': hamilton_data.get('Position'),
        'gap_to_leader': hamilton_data.get('GapToLeader'),
        'laps': hamilton_data.get('NumberOfLaps'),
        'best_lap': hamilton_data.get('BestLapTime', {}).get('Value'),
        'last_lap': hamilton_data.get('LastLapTime', {}).get('Value'),
        'speeds': speed_data,
        'sectors': hamilton_data.get('Sectors', [])
    }

def download_historical_telemetry():
    """Attempt to download historical telemetry data from F1 API"""
    base_url = "https://livetiming.formula1.com/static/2024/2024-07-28_Belgian_Grand_Prix/2024-07-28_Race"
    
    print("Attempting to download historical telemetry data...")
    
    # Try to get timing app data which might have historical information
    endpoints_to_try = [
        "TimingAppData.jsonStream",
        "Position.z.jsonStream", 
        "CarData.z.jsonStream",
        "TimingData.jsonStream"
    ]
    
    historical_data = {}
    
    for endpoint in endpoints_to_try:
        url = f"{base_url}/{endpoint}"
        try:
            print(f"Trying {endpoint}...")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Successfully downloaded {endpoint}")
                
                # Save the data
                output_file = Path("belgian_gp_2024_race") / f"{endpoint.replace('.', '_')}"
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                historical_data[endpoint] = response.content
            else:
                print(f"✗ Failed to download {endpoint} (Status: {response.status_code})")
                
        except Exception as e:
            print(f"✗ Error downloading {endpoint}: {e}")
        
        time.sleep(0.5)  # Be respectful to the API
    
    return historical_data

def plot_current_speed_data(hamilton_data, session_data):
    """Plot available speed data for Hamilton"""
    if not hamilton_data or not hamilton_data.get('speeds'):
        print("No speed data available to plot")
        return
    
    # Create figure with multiple subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Lewis Hamilton (#44) - Belgian GP 2024 Race Analysis', fontsize=16, fontweight='bold')
    
    # Speed data at different track points
    speeds = hamilton_data['speeds']
    track_points = list(speeds.keys())
    speed_values = list(speeds.values())
    
    # Track point descriptions
    point_descriptions = {
        'I1': 'Intermediate 1',
        'I2': 'Intermediate 2', 
        'FL': 'Finish Line',
        'ST': 'Speed Trap'
    }
    
    # Plot 1: Speed at different track points
    bars = ax1.bar(range(len(track_points)), speed_values, 
                   color=['#00D2BE', '#FF6B6B', '#4ECDC4', '#45B7D1'])
    ax1.set_xlabel('Track Points')
    ax1.set_ylabel('Speed (km/h)')
    ax1.set_title('Speed at Different Track Points')
    ax1.set_xticks(range(len(track_points)))
    ax1.set_xticklabels([f"{point}\n({point_descriptions.get(point, point)})" 
                         for point in track_points])
    
    # Add value labels on bars
    for bar, value in zip(bars, speed_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{value} km/h', ha='center', va='bottom', fontweight='bold')
    
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_ylim(0, max(speed_values) * 1.1)
    
    # Plot 2: Race position and timing info
    info_text = f"""Race Position: {hamilton_data.get('position', 'N/A')}
Gap to Leader: {hamilton_data.get('gap_to_leader', 'N/A')}
Total Laps: {hamilton_data.get('laps', 'N/A')}
Best Lap: {hamilton_data.get('best_lap', 'N/A')}
Last Lap: {hamilton_data.get('last_lap', 'N/A')}"""
    
    ax2.text(0.1, 0.5, info_text, transform=ax2.transAxes, fontsize=12,
             verticalalignment='center', bbox=dict(boxstyle="round,pad=0.3", 
             facecolor="lightblue", alpha=0.5))
    ax2.set_title('Race Statistics')
    ax2.axis('off')
    
    # Plot 3: Sector times
    sectors = hamilton_data.get('sectors', [])
    if sectors:
        sector_times = []
        sector_labels = []
        
        for i, sector in enumerate(sectors):
            value = sector.get('Value', '')
            if value:
                sector_times.append(float(value))
                sector_labels.append(f'Sector {i+1}')
        
        if sector_times:
            bars3 = ax3.bar(range(len(sector_times)), sector_times, 
                           color=['#FF9999', '#66B2FF', '#99FF99'])
            ax3.set_xlabel('Sectors')
            ax3.set_ylabel('Time (seconds)')
            ax3.set_title('Current Lap Sector Times')
            ax3.set_xticks(range(len(sector_times)))
            ax3.set_xticklabels(sector_labels)
            
            # Add value labels
            for bar, value in zip(bars3, sector_times):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{value}s', ha='center', va='bottom', fontweight='bold')
            
            ax3.grid(axis='y', alpha=0.3)
        else:
            ax3.text(0.5, 0.5, 'No sector time data available', 
                    transform=ax3.transAxes, ha='center', va='center')
    else:
        ax3.text(0.5, 0.5, 'No sector data available', 
                transform=ax3.transAxes, ha='center', va='center')
    ax3.set_title('Sector Times')
    
    # Plot 4: Speed comparison with fastest points
    if len(speeds) >= 2:
        # Create a simple speed comparison
        max_speed_point = max(speeds.items(), key=lambda x: x[1])
        min_speed_point = min(speeds.items(), key=lambda x: x[1])
        
        comparison_data = [
            ('Fastest Point', max_speed_point[1], f"{max_speed_point[0]} - {point_descriptions.get(max_speed_point[0], max_speed_point[0])}"),
            ('Slowest Point', min_speed_point[1], f"{min_speed_point[0]} - {point_descriptions.get(min_speed_point[0], min_speed_point[0])}")
        ]
        
        bars4 = ax4.bar([item[0] for item in comparison_data], 
                       [item[1] for item in comparison_data],
                       color=['#00FF00', '#FF4444'])
        
        ax4.set_ylabel('Speed (km/h)')
        ax4.set_title('Speed Range Analysis')
        
        # Add annotations
        for i, (label, speed, description) in enumerate(comparison_data):
            ax4.text(i, speed + 5, f'{speed} km/h\n{description}', 
                    ha='center', va='bottom', fontsize=10)
        
        ax4.grid(axis='y', alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'Insufficient speed data for comparison', 
                transform=ax4.transAxes, ha='center', va='center')
    
    plt.tight_layout()
    
    # Save the plot
    output_file = "lewis_hamilton_belgian_gp_2024_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved as: {output_file}")
    
    plt.show()

def main():
    """Main function to analyze Lewis Hamilton's telemetry data"""
    print("Lewis Hamilton (#44) Speed Analysis - Belgian GP 2024")
    print("=" * 60)
    
    # Load local data
    timing_data, session_data = load_local_telemetry_data()
    
    if not timing_data:
        print("No timing data found. Please ensure Belgian GP data is downloaded.")
        return
    
    # Extract Hamilton's data
    hamilton_data = extract_hamilton_data(timing_data)
    
    if not hamilton_data:
        print("Could not extract Hamilton's data")
        return
    
    print("\n" + "=" * 60)
    
    # Try to download historical data
    # historical_data = download_historical_telemetry()
    
    # Plot current available data
    plot_current_speed_data(hamilton_data, session_data)
    
    print("\nAnalysis complete!")
    print(f"Lewis Hamilton finished in P{hamilton_data.get('position')} with a gap of {hamilton_data.get('gap_to_leader')} to the leader")

if __name__ == "__main__":
    main()
