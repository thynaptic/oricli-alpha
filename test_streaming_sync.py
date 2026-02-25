import json
import requests
import sys
import time
from pathlib import Path

def test_streaming():
    url = "http://localhost:8004/v1/chat/completions"
    payload = {
        "model": "mavaia-cognitive",
        "messages": [
            {"role": "user", "content": "How does Mavaia handle complex reasoning?"}
        ],
        "stream": True
    }
    
    print(f"Connecting to {url}...")
    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error connecting to server: {e}")
        print("Make sure the Mavaia API server is running on localhost:8001")
        return False

    thought_count = 0
    content_received = False
    stages = set()

    print("\nReceiving stream:")
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                data_str = line_str[6:]
                if data_str == "[DONE]":
                    print("\n[DONE]")
                    break
                
                try:
                    data = json.loads(data_str)
                    if "error" in data:
                        print(f"\nServer Error: {data['error']['message']}")
                        continue
                        
                    if "choices" not in data:
                        print(f"\nMissing 'choices' in chunk: {data_str}")
                        continue
                        
                    delta = data["choices"][0]["delta"]
                    
                    if "thought" in delta:
                        thought_count += 1
                        stage = delta.get("stage", "unknown")
                        stages.add(stage)
                        print(f"Thought ({stage}): {delta['thought']}")
                    
                    if "content" in delta:
                        content_received = True
                        print(delta["content"], end="", flush=True)
                except Exception as e:
                    print(f"\nError parsing chunk: {e}")

    print("\n\nTest Summary:")
    print(f"Thoughts received: {thought_count}")
    print(f"Stages encountered: {', '.join(stages)}")
    print(f"Final content received: {content_received}")
    
    success = thought_count > 0 and content_received
    return success

if __name__ == "__main__":
    if not test_streaming():
        sys.exit(1)
