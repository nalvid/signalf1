#!/usr/bin/env python3
"""
Lewis Hamilton Speed Analysis from F1 Live Timing Data
Extracts and visualizes speed data for Lewis Hamilton (#44) from qualifying session
"""

import re
import json
import base64
import zlib
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import pandas as pd

def extract_message_data(log_file_path):
    """Extract structured data from F1 live timing log file"""
    lewis_data = []
    
    with open(log_file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            try:
                # Extract timestamp
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
                if not timestamp_match:
                    continue
                    
                timestamp_str = timestamp_match.group(1)
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                
                # Look for JSON data in the message
                json_match = re.search(r'"M":\[(.*?)\]', line)
                if json_match:
                    json_data_str = json_match.group(1)
                    try:
                        # Parse the JSON array
                        json_array = json.loads(f'[{json_data_str}]')
                        
                        for message in json_array:
                            if isinstance(message, dict) and 'A' in message:
                                args = message['A']
                                if len(args) >= 2:
                                    message_type = args[0]
                                    data = args[1]
                                    
                                    # Look for Lewis Hamilton data (driver 44)
                                    if isinstance(data, dict) and 'Lines' in data:
                                        lines = data['Lines']
                                        if '44' in lines:
                                            lewis_info = lines['44']
                                            
                                            # Extract speed data
                                            speeds = {}
                                            if 'Speeds' in lewis_info:
                                                speed_data = lewis_info['Speeds']
                                                for speed_point, speed_info in speed_data.items():
                                                    if isinstance(speed_info, dict) and 'Value' in speed_info:
                                                        try:
                                                            speeds[speed_point] = float(speed_info['Value'])
                                                        except (ValueError, TypeError):
                                                            pass
                                            
                                            # Extract sector times
                                            sectors = {}
                                            if 'Sectors' in lewis_info:
                                                sector_data = lewis_info['Sectors']
                                                for sector_idx, sector_info in sector_data.items():
                                                    if isinstance(sector_info, dict) and 'Value' in sector_info:
                                                        try:
                                                            sectors[f'Sector_{sector_idx}'] = float(sector_info['Value'])
                                                        except (ValueError, TypeError):
                                                            pass
                                            
                                            # Extract other relevant data
                                            position = lewis_info.get('Position', '')
                                            lap_time = ''
                                            if 'LastLapTime' in lewis_info and isinstance(lewis_info['LastLapTime'], dict):
                                                lap_time = lewis_info['LastLapTime'].get('Value', '')
                                            elif 'BestLapTime' in lewis_info and isinstance(lewis_info['BestLapTime'], dict):
                                                lap_time = lewis_info['BestLapTime'].get('Value', '')
                                            
                                            number_of_laps = lewis_info.get('NumberOfLaps', '')
                                            
                                            # Only add if we have meaningful data
                                            if speeds or sectors or lap_time:
                                                data_point = {
                                                    'timestamp': timestamp,
                                                    'message_type': message_type,
                                                    'position': position,
                                                    'lap_time': lap_time,
                                                    'number_of_laps': number_of_laps,
                                                    **speeds,
                                                    **sectors
                                                }
                                                lewis_data.append(data_point)
                                    
                    except json.JSONDecodeError:
                        continue
                        
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue
    
    return lewis_data

def create_speed_visualization(lewis_data):
    """Create comprehensive speed visualization for Lewis Hamilton"""
    if not lewis_data:
        print("No data available for visualization")
        return
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(lewis_data)
    
    # Remove duplicate timestamps and sort
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
    
    print(f"Total data points for Lewis Hamilton: {len(df)}")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Speed columns to plot
    speed_columns = ['I1', 'I2', 'FL', 'ST']
    speed_labels = {
        'I1': 'Intermediate 1 (km/h)',
        'I2': 'Intermediate 2 (km/h)', 
        'FL': 'Finish Line (km/h)',
        'ST': 'Speed Trap (km/h)'
    }
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Lewis Hamilton (#44) - Qualifying Speed Analysis\nHungarian GP 2025 - August 2, 2025', 
                 fontsize=16, fontweight='bold')
    
    # Plot individual speed measurements
    for idx, speed_col in enumerate(speed_columns):
        row = idx // 2
        col = idx % 2
        ax = axes[row, col]
        
        # Filter data where this speed measurement exists
        speed_data = df[df[speed_col].notna()]
        
        if not speed_data.empty:
            ax.plot(speed_data['timestamp'], speed_data[speed_col], 
                   marker='o', linewidth=2, markersize=4, label=speed_labels[speed_col])
            ax.set_title(f'{speed_labels[speed_col]}', fontweight='bold')
            ax.set_ylabel('Speed (km/h)')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            # Add speed values as annotations for key points
            if len(speed_data) <= 20:  # Only annotate if not too many points
                for _, point in speed_data.iterrows():
                    ax.annotate(f'{point[speed_col]:.0f}', 
                              (point['timestamp'], point[speed_col]),
                              textcoords="offset points", xytext=(0,10), ha='center',
                              fontsize=8, alpha=0.7)
            
            # Show statistics
            max_speed = speed_data[speed_col].max()
            min_speed = speed_data[speed_col].min()
            avg_speed = speed_data[speed_col].mean()
            
            stats_text = f'Max: {max_speed:.1f}\nMin: {min_speed:.1f}\nAvg: {avg_speed:.1f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                   fontsize=9)
        else:
            ax.text(0.5, 0.5, f'No {speed_labels[speed_col]} data available', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{speed_labels[speed_col]}', fontweight='bold')
    
    plt.tight_layout()
    
    # Save the plot
    output_file = Path("lewis_hamilton_qualifying_speeds.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Speed analysis plot saved as: {output_file.absolute()}")
    
    # Create a summary table
    print("\n" + "="*80)
    print("LEWIS HAMILTON (#44) - QUALIFYING SPEED SUMMARY")
    print("="*80)
    
    # Overall statistics
    for speed_col in speed_columns:
        speed_data = df[df[speed_col].notna()]
        if not speed_data.empty:
            print(f"\n{speed_labels[speed_col]}:")
            print(f"  📊 Data Points: {len(speed_data)}")
            print(f"  🏎️  Maximum Speed: {speed_data[speed_col].max():.1f} km/h")
            print(f"  🐌 Minimum Speed: {speed_data[speed_col].min():.1f} km/h")
            print(f"  📈 Average Speed: {speed_data[speed_col].mean():.1f} km/h")
            
            # Show progression over time
            if len(speed_data) > 1:
                first_speed = speed_data.iloc[0][speed_col]
                last_speed = speed_data.iloc[-1][speed_col]
                change = last_speed - first_speed
                print(f"  📊 Speed Change: {change:+.1f} km/h (first to last measurement)")
    
    # Lap time information
    lap_times = df[df['lap_time'].notna() & (df['lap_time'] != '')]
    if not lap_times.empty:
        print(f"\n🏁 LAP TIMES:")
        for _, lap in lap_times.iterrows():
            print(f"  Lap Time: {lap['lap_time']} (at {lap['timestamp'].strftime('%H:%M:%S')})")
    
    # Position information
    positions = df[df['position'].notna() & (df['position'] != '')]
    if not positions.empty:
        print(f"\n🏆 POSITIONS:")
        for _, pos in positions.iterrows():
            print(f"  Position: {pos['position']} (at {pos['timestamp'].strftime('%H:%M:%S')})")
    
    print("\n" + "="*80)
    
    plt.show()
    
    return df

def main():
    """Main function to run the analysis"""
    log_file = Path("data/raw/20250802_160643.log")
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return
    
    print("🏎️  Extracting Lewis Hamilton telemetry data from qualifying session...")
    print(f"📁 Reading: {log_file}")
    
    # Extract data
    lewis_data = extract_message_data(log_file)
    
    if not lewis_data:
        print("❌ No Lewis Hamilton data found in the log file")
        return
    
    print(f"✅ Extracted {len(lewis_data)} data points for Lewis Hamilton")
    
    # Create visualization
    df = create_speed_visualization(lewis_data)
    
    # Save raw data to CSV for further analysis
    if not df.empty:
        csv_file = Path("lewis_hamilton_qualifying_data.csv")
        df.to_csv(csv_file, index=False)
        print(f"📊 Raw data saved to: {csv_file.absolute()}")

if __name__ == "__main__":
    main()
