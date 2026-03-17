import requests
import time
import json

MODELS = ["deepseek-r1:1.5b", "ministral-3:3b", "nemotron-3-nano:4b", "qwen3.5:2b"]
PROMPTS = [
    "Write a python function to reverse a linked list.",
    "Convert this CSV to JSON: name,age\nalice,30\nbob,25. ONLY output JSON.",
    "If I have 3 apples and you give me 2 more, but then I eat 1, how many do I have? Think step by step.",
    "Explain the difference between a mutex and a semaphore.",
    "Write a regex to validate an email address."
]

def run_shootout():
    results = {}
    for model in MODELS:
        print(f"\n--- Testing Model: {model} ---")
        model_results = []
        for prompt in PROMPTS:
            start = time.time()
            try:
                resp = requests.post("http://localhost:11434/api/generate", 
                                   json={"model": model, "prompt": prompt, "stream": False},
                                   timeout=120).json()
                duration = time.time() - start
                text = resp.get("response", "")
                
                # Basic grading
                has_filler = any(x in text.lower() for x in ["here is", "sure", "i can help"])
                is_json = "{" in text and "}" in text if "CSV" in prompt else True
                
                model_results.append({
                    "prompt": prompt[:30] + "...",
                    "latency": round(duration, 2),
                    "has_filler": has_filler,
                    "length": len(text)
                })
                print(f"  Done: {prompt[:30]}... ({round(duration, 2)}s)")
            except Exception as e:
                print(f"  FAILED: {model} - {e}")
        results[model] = model_results
    
    print("\n" + "="*60)
    print("🚀 MODEL SHOOTOUT RESULTS")
    print("="*60)
    for model, data in results.items():
        avg_lat = sum(d["latency"] for d in data) / len(data) if data else 0
        filler_rate = sum(1 for d in data if d["has_filler"]) / len(data) if data else 0
        print(f"{model:<20} | Avg Latency: {avg_lat:>5.2f}s | Filler Rate: {filler_rate:>4.0%}")
    print("="*60)

if __name__ == "__main__":
    run_shootout()
