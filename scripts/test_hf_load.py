import argparse
from datasets import load_dataset
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Test HF dataset accessibility and quality.")
    parser.add_argument("--dataset", default="mlfoundations-dev/oh-dcft-v3.1-gemini-1.5-pro", help="HF Dataset ID")
    parser.add_argument("--config", default=None, help="Dataset configuration")
    parser.add_argument("--split", default="train", help="Dataset split to test")
    
    args = parser.parse_args()
    
    dataset_id = args.dataset
    config = args.config
    
    display_name = f"{dataset_id}:{config}" if config else dataset_id
    print(f"--- HF Dataset Quality Report: {display_name} ---")

    try:
        # 1. Connectivity & Load Check
        print("[*] Testing reachability and loading metadata...")
        if config:
            ds = load_dataset(dataset_id, config, split=args.split, streaming=True)
        else:
            ds = load_dataset(dataset_id, split=args.split, streaming=True)
        
        # 2. Structure Analysis
        it = iter(ds)
        first_row = next(it)
        cols = list(first_row.keys())
        
        print(f"[✓] SUCCESS: Dataset reachable.")
        print(f"    - Columns Found: {', '.join(cols)}")
        
        # 3. Content Verification
        print("[*] Analyzing sample content for extraction...")
        extractable = False
        for col in cols:
            val = first_row.get(col)
            if val and isinstance(val, (str, list, dict)):
                sample_str = str(val)
                sample_len = len(sample_str)
                if sample_len > 10:
                    print(f"    - Found quality data in column '{col}' ({type(val).__name__}, sample len: {sample_len})")
                    if sample_len > 100:
                        print(f"      Sample: {sample_str[:150]}...")
                    extractable = True
        
        if not extractable:
            print("[!] WARNING: No obvious text content found in the first row.")
        else:
            print("[✓] Dataset looks valid and ready for training.")

    except Exception as e:
        print(f"[✗] FAILED to load dataset: {e}")
        sys.exit(1)

    print("-" * 50)

if __name__ == "__main__":
    main()
