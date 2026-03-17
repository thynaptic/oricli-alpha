import requests
import json

def test_arc_native():
    url = "http://localhost:8089/v1/swarm/run"
    
    # Simple rotation task
    task = {
        "train": [
            {
                "input": [[1, 2], [3, 4]],
                "output": [[3, 1], [4, 2]]
            }
        ],
        "test": [
            {
                "input": [[5, 6], [7, 8]]
            }
        ]
    }
    
    payload = {
        "operation": "solve_arc",
        "params": {
            "task": task
        }
    }
    
    print("[*] Sending ARC task to Go-Native Hive...")
    resp = requests.post(url, json=payload, timeout=300).json()
    
    if resp.get("success"):
        result = resp.get("result", {})
        print(f"[+] ARC Solved! Method: {result.get('method')}")
        print(f"[+] Best Program: {result.get('program')}")
        print(f"[+] Prediction: {result.get('prediction')}")
    else:
        print(f"[!] ARC Failed: {resp}")

if __name__ == "__main__":
    test_arc_native()
