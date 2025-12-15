#!/usr/bin/env python3
"""
Training Script for Neural Text Generator
Downloads Project Gutenberg data, preprocesses, and trains character/word models
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mavaia_core.brain.modules.neural_text_generator import NeuralTextGeneratorModule


def main():
    """Main training function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Train neural text generation models"
    )
    parser.add_argument(
        "--model-type",
        choices=["character", "word", "both"],
        default="both",
        help="Type of model to train",
    )
    parser.add_argument(
        "--book-ids",
        type=int,
        nargs="+",
        help="Project Gutenberg book IDs to use for training",
    )
    parser.add_argument(
        "--categories",
        type=str,
        nargs="+",
        choices=["fiction", "non_fiction", "technical", "philosophy", "poetry", 
                 "drama", "adventure", "mystery", "science_fiction", "classic"],
        help="Categories of books to load (e.g., fiction technical)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--train-for-minutes",
        type=float,
        help="Maximum training time in minutes (overrides epochs if set)",
    )
    parser.add_argument(
        "--train-for-hours",
        type=float,
        help="Maximum training time in hours (overrides epochs if set)",
    )
    parser.add_argument(
        "--max-text-size",
        type=int,
        help="Maximum text size in characters",
    )
    parser.add_argument(
        "--max-books",
        type=int,
        help="Maximum number of books to load",
    )
    parser.add_argument(
        "--data-percentage",
        type=float,
        default=1.0,
        help="Percentage of data to use (0.0-1.0, default: 1.0)",
    )
    parser.add_argument(
        "--continue-training",
        action="store_true",
        help="Continue training from existing model",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Neural Text Generator Training")
    print("=" * 80)
    print(f"Model type: {args.model_type}")
    if args.categories:
        print(f"Categories: {', '.join(args.categories)}")
    if args.book_ids:
        print(f"Book IDs: {args.book_ids}")
    if args.train_for_hours:
        print(f"Training time: {args.train_for_hours} hours")
    elif args.train_for_minutes:
        print(f"Training time: {args.train_for_minutes} minutes")
    else:
        print(f"Epochs: {args.epochs}")
    if args.max_text_size:
        print(f"Max text size: {args.max_text_size:,} characters")
    if args.max_books:
        print(f"Max books: {args.max_books}")
    if args.data_percentage < 1.0:
        print(f"Data percentage: {args.data_percentage*100:.1f}%")
    print(f"Continue training: {args.continue_training}")
    print()

    # Initialize module
    generator = NeuralTextGeneratorModule()
    generator.initialize()

    # Train model
    train_params = {
        "model_type": args.model_type,
        "epochs": args.epochs,
        "continue_training": args.continue_training,
        "data_percentage": args.data_percentage,
    }

    if args.book_ids:
        train_params["book_ids"] = args.book_ids
    
    if args.categories:
        train_params["categories"] = args.categories
    
    if args.train_for_hours:
        train_params["train_for_hours"] = args.train_for_hours
    elif args.train_for_minutes:
        train_params["train_for_minutes"] = args.train_for_minutes
    
    if args.max_text_size:
        train_params["max_text_size"] = args.max_text_size
    
    if args.max_books:
        train_params["max_books"] = args.max_books

    print("Starting training...")
    result = generator.execute("train_model", train_params)

    if result.get("success"):
        print("\n✓ Training completed successfully!")
        
        # Save models
        print("\nSaving models...")
        save_result = generator.execute("save_model", {"model_type": args.model_type})
        
        if save_result.get("success"):
            print("✓ Models saved successfully!")
            for model_type, save_info in save_result.get("results", {}).items():
                if save_info.get("success"):
                    print(f"  {model_type} model: {save_info.get('path', 'N/A')}")
        else:
            print("✗ Failed to save models")
            print(f"  Error: {save_result.get('error', 'Unknown error')}")
        
        # Generate sample outputs
        print("\nGenerating sample outputs...")
        sample_prompts = [
            "The quick brown",
            "Once upon a time",
            "In the beginning",
        ]
        
        for prompt in sample_prompts:
            gen_result = generator.execute(
                "generate_text",
                {
                    "prompt": prompt,
                    "model_type": "character" if args.model_type in ["character", "both"] else "word",
                    "max_length": 100,
                    "temperature": 0.7,
                },
            )
            if gen_result.get("success"):
                print(f"\nPrompt: '{prompt}'")
                print(f"Generated: {gen_result.get('text', '')[:200]}...")
    else:
        print("\n✗ Training failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        return 1

    print("\n" + "=" * 80)
    print("Training Complete")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())

