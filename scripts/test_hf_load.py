from datasets import load_dataset
import sys
import os

dataset_id = "mlfoundations-dev/oh-dcft-v3.1-gemini-1.5-pro"
print(f"--- HF Dataset Quality Report: {dataset_id} ---")

try:
    # 1. Connectivity & Load Check
    print("[*] Testing reachability and loading metadata...")
    ds = load_dataset(dataset_id, split="train")
    
    # 2. Structure Analysis
    rows = len(ds)
    cols = ds.column_names
    print(f"[✓] SUCCESS: Dataset reachable.")
    print(f"    - Total Rows: {rows}")
    print(f"    - Columns Found: {', '.join(cols)}")
    
    # 3. Content Verification
    print("[*] Analyzing sample content for extraction...")
    first_row = ds[0]
    extractable = False
    for col in cols:
        val = first_row.get(col)
        if val and isinstance(val, (str, list, dict)):
            sample_len = len(str(val))
            if sample_len > 10:
                print(f"    - Found quality data in column '{col}' ({type(val).__name__}, sample len: {sample_len})")
                extractable = True
    
    if not extractable:
        print("[!] WARNING: No obvious text content found in the first row.")
    else:
        print("[✓] Dataset looks valid and ready for training.")

except Exception as e:
    print(f"[✗] FAILED to load dataset: {e}")
    sys.exit(1)

print("-" * 50)
