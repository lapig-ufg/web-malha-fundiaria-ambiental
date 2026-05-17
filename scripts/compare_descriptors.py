import requests
import json
import sys

def compare_json(obj1, obj2, path=""):
    """Recursively compare two JSON objects and return differences."""
    diffs = []
    
    if type(obj1) != type(obj2):
        diffs.append(f"Type mismatch at {path}: {type(obj1)} vs {type(obj2)}")
        return diffs

    if isinstance(obj1, dict):
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())
        
        for key in keys1 - keys2:
            diffs.append(f"Key {key} missing in second object at {path}")
        for key in keys2 - keys1:
            diffs.append(f"Key {key} missing in first object at {path}")
            
        for key in keys1 & keys2:
            diffs.extend(compare_json(obj1[key], obj2[key], f"{path}/{key}"))
            
    elif isinstance(obj1, list):
        if len(obj1) != len(obj2):
            diffs.append(f"List length mismatch at {path}: {len(obj1)} vs {len(obj2)}")
            min_len = min(len(obj1), len(obj2))
            for i in range(min_len):
                diffs.extend(compare_json(obj1[i], obj2[i], f"{path}[{i}]"))
        else:
            for i in range(len(obj1)):
                diffs.extend(compare_json(obj1[i], obj2[i], f"{path}[{i}]"))
    else:
        if obj1 != obj2:
            diffs.append(f"Value mismatch at {path}: {obj1} vs {obj2}")
            
    return diffs

def main():
    url_old = "http://localhost:3001/service/map/descriptor?lang=pt"
    url_new = "http://localhost:3000/service/map/descriptor?lang=pt"
    
    print(f"Fetching from Old: {url_old}")
    try:
        resp_old = requests.get(url_old)
        resp_old.raise_for_status()
        data_old = resp_old.json()
    except Exception as e:
        print(f"Error fetching from old server: {e}")
        return

    print(f"Fetching from New: {url_new}")
    try:
        resp_new = requests.get(url_new)
        resp_new.raise_for_status()
        data_new = resp_new.json()
    except Exception as e:
        print(f"Error fetching from new server: {e}")
        return

    print("\nComparing...")
    diffs = compare_json(data_old, data_new)
    
    if not diffs:
        print("SUCCESS: Descriptors are identical!")
    else:
        print(f"FOUND {len(diffs)} DIFFERENCES:")
        for diff in diffs[:20]:
            print(f" - {diff}")
        if len(diffs) > 20:
            print(f" ... and {len(diffs) - 20} more.")

if __name__ == "__main__":
    main()
