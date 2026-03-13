import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import os
import sys
from pathlib import Path

def test_model(model_path, prompt):
    # Convert to Path object for easier manipulation
    path = Path(model_path)
    
    # If absolute path fails, try relative to repo root
    if not path.exists():
        # Try /workspace/oricli prefix (Pod standard)
        pod_path = Path("/workspace/oricli") / path.relative_to(path.anchor if path.is_absolute() else "")
        if pod_path.exists():
            path = pod_path
        else:
            print(f"ERROR: Model path not found: {model_path}")
            print(f"Tried: {path.absolute()}")
            print(f"Tried: {pod_path.absolute()}")
            # List current directory to help debug
            print(f"Current directory: {os.getcwd()}")
            print(f"Contents: {os.listdir('.')}")
            return

    print(f"Loading model from {path}...")
    try:
        tokenizer = GPT2Tokenizer.from_pretrained(str(path))
        model = GPT2LMHeadModel.from_pretrained(str(path))
    except Exception as e:
        print(f"Failed to load model: {e}")
        return
    
    inputs = tokenizer(prompt, return_tensors="pt")
    
    print(f"Generating for prompt: {prompt[:100]}...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs, 
            max_new_tokens=200, 
            do_sample=True, 
            temperature=0.7,
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print("\n--- RAW MODEL RESPONSE ---")
    print(response[len(prompt):])
    print("--------------------------")

if __name__ == "__main__":
    # Allow passing path as arg, otherwise use relative default
    default_rel_path = "models/neural_text_generator_remote/curriculum/knowledge_world_dense_20260303_183107/transformer"
    
    model_path = sys.argv[1] if len(sys.argv) > 1 else default_rel_path
    
    prompt = "please convert the input table from html format to jsonl format please respond only with the table input table: <table border=\"1\" class=\"dataframe\"> <thead> <tr style=\"text-align: right;\"> <th>country</th> <th>inequality hdi</th> </tr> </thead> <tbody> <tr> <td>indonesia</td> <td>2</td> </tr> </tbody> </table> output:."
    
    test_model(model_path, prompt)
