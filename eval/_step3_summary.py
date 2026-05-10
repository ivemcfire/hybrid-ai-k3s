# summary.py

import csv
from typing import List, Dict, Tuple

def parse_sensor_csv(path: str) -> List[Dict[str, float]]:
    result = []
    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                value = float(row['value'])
                result.append({
                    'timestamp': row['timestamp'],
                    'node_id': row['node_id'],
                    'sensor': row['sensor'],
                    'value': value
                })
            except ValueError:
                continue
    return result

def summarize(path: str, window: int) -> Dict[Tuple[str, str], List[float]]:
    data = parse_sensor_csv(path)
    summary = {}
    
    for entry in data:
        key = (entry['node_id'], entry['sensor'])
        if key not in summary:
            summary[key] = []
        
        values = summary[key]
        values.append(entry['value'])
        
        if len(values) < window:
            summary[key].append(None)
        else:
            avg = sum(values[-window:]) / window
            summary[key].append(avg)
    
    return summary
