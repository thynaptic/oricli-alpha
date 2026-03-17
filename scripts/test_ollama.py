import requests
import json
import time

def test_generate():
    print("Testing Ollama generate endpoint...")
    start = time.time()
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:1.5b",
                "prompt": "Write a python function to add two numbers. Output only the code.",
                "stream": False
            },
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Time: {time.time() - start:.2f}s")
        if response.status_code == 200:
            print(f"Response: {response.json().get('response')[:100]}...")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_generate()
