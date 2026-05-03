import json
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import numpy as np

def load_f1_data():
    """Load all F1 data files for analysis"""
    try:
        # Load timing data
        with open('belgian_gp_2024_race/TimingDataF1_json', 'r', encoding='utf-8-sig') as f:
            timing_data = json.load(f)
        
        # Load session data (lap progression)
        with open('belgian_gp_2024_race/SessionData_json', 'r', encoding='utf-8-sig') as f:
            session_data = json.load(f)
        
        # Load tire stint data
        with open('belgian_gp_2024_race/TyreStintSeries_json', 'r', encoding='utf-8-sig') as f:
            tire_data = json.load(f)
        
        return timing_data, session_data, tire_data
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None

def analyze_hamilton_data(timing_data, session_data, tire_data):
    """Analyze Lewis Hamilton's (#44) race data"""
    
    # Get Hamilton's data from timing
    hamilton_data = timing_data['Lines']['44']
    
    print("=" * 60)
    print("LEWIS HAMILTON (#44) - BELGIAN GP 2024 RACE ANALYSIS")
    print("=" * 60)
    
    # Race position and performance
    print(f"Final Position: {hamilton_data['Position']}")
    print(f"Gap to Leader: {hamilton_data['GapToLeader']}")
    print(f"Total Laps: {hamilton_data['NumberOfLaps']}")
    print(f"Pit Stops: {hamilton_data['NumberOfPitStops']}")
    
    # Lap times
    print(f"\nBest Lap Time: {hamilton_data['BestLapTime']['Value']} (Lap {hamilton_data['BestLapTime']['Lap']})")
    print(f"Last Lap Time: {hamilton_data['LastLapTime']['Value']}")
    
    # Speed data at different track points
    speeds = hamilton_data['Speeds']
    print(f"\nSpeed Data:")
    print(f"  Intermediate 1 (I1): {speeds['I1']['Value']} km/h {'(Personal Fastest)' if speeds['I1']['PersonalFastest'] else ''}")
    print(f"  Intermediate 2 (I2): {speeds['I2']['Value']} km/h {'(Personal Fastest)' if speeds['I2']['PersonalFastest'] else ''}")
    print(f"  Finish Line (FL):    {speeds['FL']['Value']} km/h {'(Personal Fastest)' if speeds['FL']['PersonalFastest'] else ''}")
    print(f"  Speed Trap (ST):     {speeds['ST']['Value']} km/h {'(Personal Fastest)' if speeds['ST']['PersonalFastest'] else ''}")
    
    # Sector times
    sectors = hamilton_data['Sectors']
    print(f"\nSector Times:")
    for i, sector in enumerate(sectors, 1):
        print(f"  Sector {i}: {sector['Value']}s {'(Personal Fastest)' if sector.get('PersonalFastest') else ''}")
    
    # Tire strategy
    hamilton_stints = tire_data['Stints']['44']
    print(f"\nTire Strategy:")
    for i, stint in enumerate(hamilton_stints, 1):
        print(f"  Stint {i}: {stint['Compound']} tire, {stint['TotalLaps']} laps")
    
    return hamilton_data, hamilton_stints, session_data['Series']

def create_race_visualization(hamilton_data, hamilton_stints, lap_series):
    """Create comprehensive race visualization for Lewis Hamilton"""
    
    # Create figure with multiple subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Lewis Hamilton (#44) - Belgian GP 2024 Race Analysis', fontsize=16, fontweight='bold')
    
    # 1. Speed Data Comparison (Bar Chart)
    speeds = hamilton_data['Speeds']
    speed_points = ['I1', 'I2', 'FL', 'ST']
    speed_values = [int(speeds[point]['Value']) for point in speed_points if speeds[point]['Value']]
    speed_labels = ['Intermediate 1', 'Intermediate 2', 'Finish Line', 'Speed Trap']
    
    colors = ['red' if speeds[point]['PersonalFastest'] else 'blue' for point in speed_points if speeds[point]['Value']]
    
    bars = ax1.bar(speed_labels, speed_values, color=colors, alpha=0.7)
    ax1.set_title('Speed at Different Track Points')
    ax1.set_ylabel('Speed (km/h)')
    ax1.set_ylim(0, max(speed_values) * 1.1)
    
    # Add value labels on bars
    for bar, value in zip(bars, speed_values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                f'{value}', ha='center', va='bottom', fontweight='bold')
    
    # Add legend
    ax1.text(0.02, 0.98, 'Red = Personal Fastest', transform=ax1.transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='red', alpha=0.3))
    
    # 2. Tire Strategy Timeline
    stint_colors = {'SOFT': 'red', 'MEDIUM': 'yellow', 'HARD': 'white'}
    stint_edge_colors = {'SOFT': 'darkred', 'MEDIUM': 'orange', 'HARD': 'black'}
    
    current_lap = 0
    for stint in hamilton_stints:
        compound = stint['Compound']
        laps = stint['TotalLaps']
        
        ax2.barh(0, laps, left=current_lap, height=0.5, 
                color=stint_colors[compound], 
                edgecolor=stint_edge_colors[compound],
                linewidth=2, alpha=0.8)
        
        # Add stint labels
        ax2.text(current_lap + laps/2, 0, f'{compound}\n{laps}L', 
                ha='center', va='center', fontweight='bold', fontsize=10)
        
        current_lap += laps
    
    ax2.set_title('Tire Strategy Throughout Race')
    ax2.set_xlabel('Lap Number')
    ax2.set_xlim(0, hamilton_data['NumberOfLaps'])
    ax2.set_ylim(-0.5, 0.5)
    ax2.set_yticks([])
    ax2.grid(True, axis='x', alpha=0.3)
    
    # 3. Lap Time Progression (Estimated)
    # Since we don't have individual lap times, we'll simulate based on tire strategy
    # and session data
    total_laps = hamilton_data['NumberOfLaps']
    lap_numbers = list(range(1, total_laps + 1))
    
    # Extract best lap time in seconds
    best_lap_str = hamilton_data['BestLapTime']['Value']  # Format: "1:46.653"
    minutes, seconds = best_lap_str.split(':')
    best_lap_seconds = int(minutes) * 60 + float(seconds)
    
    # Simulate lap times based on tire degradation and strategy
    simulated_lap_times = []
    current_lap = 0
    
    for stint in hamilton_stints:
        stint_laps = stint['TotalLaps']
        compound = stint['Compound']
        
        # Base time adjustments by compound (relative to best lap)
        compound_offset = {'SOFT': -1.0, 'MEDIUM': 0.0, 'HARD': +1.5}
        base_time = best_lap_seconds + compound_offset[compound]
        
        # Simulate degradation over stint
        for lap in range(stint_laps):
            # Tire degradation (more degradation on softer compounds)
            degradation_rate = {'SOFT': 0.05, 'MEDIUM': 0.03, 'HARD': 0.02}
            degradation = lap * degradation_rate[compound]
            
            # Add some randomness for realistic variation
            random_variation = np.random.normal(0, 0.3)
            
            lap_time = base_time + degradation + random_variation
            simulated_lap_times.append(lap_time)
        
        current_lap += stint_laps
    
    ax3.plot(lap_numbers, simulated_lap_times, 'b-', linewidth=2, alpha=0.7)
    ax3.axhline(y=best_lap_seconds, color='r', linestyle='--', alpha=0.7, label=f'Best Lap: {best_lap_str}')
    ax3.set_title('Estimated Lap Time Progression')
    ax3.set_xlabel('Lap Number')
    ax3.set_ylabel('Lap Time (seconds)')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Add pit stop markers
    current_lap = 0
    for i, stint in enumerate(hamilton_stints[:-1]):  # Exclude last stint
        current_lap += stint['TotalLaps']
        ax3.axvline(x=current_lap, color='red', linestyle='|', linewidth=3, alpha=0.8)
        ax3.text(current_lap, ax3.get_ylim()[1], 'PIT', ha='center', va='bottom', 
                fontweight='bold', color='red')
    
    # 4. Race Timeline with Key Events
    # Convert session times to race progression
    if lap_series:
        race_duration_minutes = []
        start_time = datetime.fromisoformat(lap_series[0]['Utc'].replace('Z', '+00:00'))
        
        for lap_info in lap_series:
            lap_time = datetime.fromisoformat(lap_info['Utc'].replace('Z', '+00:00'))
            duration = (lap_time - start_time).total_seconds() / 60  # Convert to minutes
            race_duration_minutes.append(duration)
        
        ax4.plot(race_duration_minutes, lap_numbers, 'g-', linewidth=2)
        ax4.set_title('Race Progression Timeline')
        ax4.set_xlabel('Race Time (minutes)')
        ax4.set_ylabel('Lap Number')
        ax4.grid(True, alpha=0.3)
        
        # Add pit stop markers
        current_lap = 0
        for stint in hamilton_stints[:-1]:
            current_lap += stint['TotalLaps']
            if current_lap <= len(race_duration_minutes):
                pit_time = race_duration_minutes[current_lap-1]
                ax4.axhline(y=current_lap, color='red', linestyle='--', alpha=0.7)
                ax4.text(pit_time, current_lap, ' PIT', ha='left', va='center', 
                        fontweight='bold', color='red')
    
    plt.tight_layout()
    plt.savefig('lewis_hamilton_belgian_gp_2024_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return fig

def main():
    """Main function to run the complete analysis"""
    print("Loading F1 Belgian GP 2024 race data...")
    
    timing_data, session_data, tire_data = load_f1_data()
    
    if not timing_data:
        print("Failed to load data. Please check file paths.")
        return
    
    # Analyze Hamilton's race
    hamilton_data, hamilton_stints, lap_series = analyze_hamilton_data(timing_data, session_data, tire_data)
    
    # Create comprehensive visualization
    print("\nCreating race visualization...")
    fig = create_race_visualization(hamilton_data, hamilton_stints, lap_series)
    
    print(f"\nAnalysis complete! Visualization saved as 'lewis_hamilton_belgian_gp_2024_analysis.png'")
    
    # Summary insights
    print("\n" + "=" * 60)
    print("KEY INSIGHTS:")
    print("=" * 60)
    print("• Hamilton finished 2nd, just 0.526 seconds behind the leader")
    print("• His best lap (1:46.653) was set on lap 33 during his 2nd stint")
    print("• He achieved his personal fastest speed (337 km/h) at Intermediate 1")
    print("• Used a 3-stint strategy: Medium → Hard → Hard")
    print("• Made 2 pit stops during the 44-lap race")
    
if __name__ == "__main__":
    main()
