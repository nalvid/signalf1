
# Example: How to load and analyze the exported throttle data

import json
import matplotlib.pyplot as plt
from datetime import datetime

# Load the exported data
with open("driver_44_throttle_detailed.json", "r") as f:
    throttle_data = json.load(f)

# Convert timestamps
timestamps = [datetime.fromisoformat(point["timestamp"]) for point in throttle_data]
throttle_values = [point["throttle_percent"] for point in throttle_data]
speed_values = [point["speed_kmh"] for point in throttle_data]

# Create visualization
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# Throttle plot
ax1.plot(timestamps, throttle_values, 'g-', linewidth=2, label='Throttle %')
ax1.set_ylabel('Throttle (%)')
ax1.set_title('Driver #44 Throttle Input Over Time')
ax1.grid(True, alpha=0.3)
ax1.legend()

# Speed plot
ax2.plot(timestamps, speed_values, 'b-', linewidth=2, label='Speed (km/h)')
ax2.set_ylabel('Speed (km/h)')
ax2.set_xlabel('Time')
ax2.set_title('Driver #44 Speed Over Time')
ax2.grid(True, alpha=0.3)
ax2.legend()

plt.tight_layout()
plt.show()

# Analysis
print(f"Average throttle: {sum(throttle_values)/len(throttle_values):.1f}%")
print(f"Max speed: {max(speed_values)} km/h")
print(f"Data points: {len(throttle_data)}")
