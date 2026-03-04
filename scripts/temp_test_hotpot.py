from datasets import load_dataset
import sys

dataset_id = "hotpot_qa"
config = "distractor"
print(f"--- HF Dataset Quality Report: {dataset_id}:{config} ---")

try:
    # 1. Connectivity & Load Check
    print("[*] Testing reachability and loading metadata...")
    ds = load_dataset(dataset_id, config, split="train", streaming=True)
    
    # 2. Structure Analysis
    # Since we are streaming, we can't get length easily without iteration, but we can get column names.
    # Actually, load_dataset with split="train" without streaming is better for full info if it's not too big.
    # HotpotQA is quite large, so let's stick to streaming for a quick check.
    
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
