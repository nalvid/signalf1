#!/usr/bin/env python3
"""
Download F1 data from specific endpoint
"""

import requests


def download_f1_data(url, output_file):
    """
    Download F1 data from URL and save to file.
    
    Args:
        url: F1 data endpoint URL
        output_file: Filename to save data
    
    Returns:
        True if successful, False otherwise
    """
    print(f"📡 Downloading from: {url}")
    
    try:
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"✅ Data saved to: {output_file}")
            print(f"📊 File size: {len(response.text)} bytes")
            
            # Show preview
            preview = response.text[:300] + "..." if len(response.text) > 300 else response.text
            print(f"📋 Preview: {preview}")
            return True
        else:
            print(f"❌ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Download from the specific endpoint you provided
    url = "https://livetiming.formula1.com/static/2025/2025/2025-06-01_Spanish_Grand_Prix/2025-06-01_Race"
    output_file = "spanish_gp_2025_race.txt"
    
    download_f1_data(url, output_file)
