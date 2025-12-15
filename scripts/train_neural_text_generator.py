#!/usr/bin/env python3
"""
Training Script for Neural Text Generator
Downloads data from multiple sources (Gutenberg, Wikipedia, LibriVox, OpenLibrary, Internet Archive, HuggingFace),
preprocesses, and trains character/word models

Data Sources:
    --source: Specify data source(s) to use
        - gutenberg: Project Gutenberg books (default)
        - wikipedia: Wikipedia articles
        - librivox: LibriVox audiobooks
        - openlibrary: OpenLibrary/Internet Archive books
        - internetarchive: Internet Archive items (uses internetarchive library)
        - huggingface: HuggingFace datasets (uses datasets library)
    Can specify multiple sources: --source gutenberg wikipedia
    Use --list-sources to see all available sources
    
    For HuggingFace: Set HF_TOKEN or MAVAIA_HUGGINGFACE_TOKEN environment variable
    for private datasets. API keys can also be stored in mavaia_core/data/api_keys.json

Training Profiles:
    Profiles are loaded from YAML files in scripts/training_profiles/
    Users can create custom profiles by adding YAML files to that directory.
    See scripts/training_profiles/README.md for profile format documentation.

Examples:
    # Train with Gutenberg (default)
    python scripts/train_neural_text_generator.py --epochs 10
    
    # Train with Wikipedia
    python scripts/train_neural_text_generator.py --source wikipedia --epochs 10
    
    # Train with multiple sources
    python scripts/train_neural_text_generator.py --source gutenberg wikipedia --epochs 10
    
    # Use specific articles from Wikipedia
    python scripts/train_neural_text_generator.py --source wikipedia --book-ids "Artificial intelligence" "Machine learning"
    
    # Use Internet Archive with specific items
    python scripts/train_neural_text_generator.py --source internetarchive --book-ids "TripDown1905" "goodytwoshoes00newyiala"
    
    # Use Internet Archive with category search
    python scripts/train_neural_text_generator.py --source internetarchive --categories fiction classic
    
    # Use HuggingFace with specific datasets
    python scripts/train_neural_text_generator.py --source huggingface --book-ids "wikitext" "bookcorpus"
    
    # Use HuggingFace with category search
    python scripts/train_neural_text_generator.py --source huggingface --categories technical fiction
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Try to import YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mavaia_core.brain.modules.neural_text_generator import NeuralTextGeneratorModule


# Profile directory (relative to script location)
PROFILES_DIR = Path(__file__).parent / "training_profiles"


def discover_profiles() -> Dict[str, Dict[str, Any]]:
    """
    Discover and load all training profiles from YAML files in the profiles directory.
    
    Returns:
        Dictionary mapping profile names to their configurations
        
    Raises:
        RuntimeError: If YAML support is not available
        ValueError: If profile files are invalid
    """
    if not YAML_AVAILABLE:
        raise RuntimeError(
            "YAML support is required for profile loading. "
            "Please install PyYAML: pip install PyYAML"
        )
    
    profiles = {}
    
    if not PROFILES_DIR.exists():
        # Create directory if it doesn't exist
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        print(
            f"Warning: Profiles directory not found. Created: {PROFILES_DIR}",
            file=sys.stderr
        )
        return profiles
    
    # Discover all YAML files in the profiles directory
    yaml_files = list(PROFILES_DIR.glob("*.yaml")) + list(PROFILES_DIR.glob("*.yml"))
    
    if not yaml_files:
        print(
            f"Warning: No profile files found in {PROFILES_DIR}",
            file=sys.stderr
        )
        return profiles
    
    for yaml_file in sorted(yaml_files):
        profile_name = yaml_file.stem  # Filename without extension
        
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                profile_data = yaml.safe_load(f)
            
            if not isinstance(profile_data, dict):
                print(
                    f"Warning: Invalid profile format in {yaml_file.name}: "
                    f"expected dictionary, got {type(profile_data).__name__}",
                    file=sys.stderr
                )
                continue
            
            # Validate required fields
            if "description" not in profile_data:
                print(
                    f"Warning: Profile {profile_name} missing 'description' field, skipping",
                    file=sys.stderr
                )
                continue
            
            profiles[profile_name] = profile_data
            
        except yaml.YAMLError as e:
            print(
                f"Warning: Failed to parse YAML in {yaml_file.name}: {e}",
                file=sys.stderr
            )
            continue
        except Exception as e:
            print(
                f"Warning: Error loading profile {yaml_file.name}: {e}",
                file=sys.stderr
            )
            continue
    
    return profiles


def load_profile(profile_name: str) -> Dict[str, Any]:
    """
    Load a specific profile by name.
    
    Args:
        profile_name: Name of the profile to load
        
    Returns:
        Dictionary with profile configuration
        
    Raises:
        RuntimeError: If YAML support is not available
        ValueError: If profile is not found or invalid
    """
    if not YAML_AVAILABLE:
        raise RuntimeError(
            "YAML support is required for profile loading. "
            "Please install PyYAML: pip install PyYAML"
        )
    
    # Try .yaml first, then .yml
    profile_file = PROFILES_DIR / f"{profile_name}.yaml"
    if not profile_file.exists():
        profile_file = PROFILES_DIR / f"{profile_name}.yml"
    
    if not profile_file.exists():
        available_profiles = discover_profiles()
        available = ", ".join(available_profiles.keys()) if available_profiles else "none"
        raise ValueError(
            f"Profile '{profile_name}' not found. "
            f"Available profiles: {available}"
        )
    
    try:
        with open(profile_file, "r", encoding="utf-8") as f:
            profile_data = yaml.safe_load(f)
        
        if not isinstance(profile_data, dict):
            raise ValueError(
                f"Invalid profile format: expected dictionary, "
                f"got {type(profile_data).__name__}"
            )
        
        if "description" not in profile_data:
            raise ValueError("Profile missing required 'description' field")
        
        return profile_data.copy()
        
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse profile YAML: {e}") from e
    except Exception as e:
        raise ValueError(f"Error loading profile: {e}") from e


def apply_profile(profile_name: str) -> dict:
    """
    Get configuration for a training profile.
    
    Args:
        profile_name: Name of the profile to apply
        
    Returns:
        Dictionary with profile configuration
        
    Raises:
        RuntimeError: If YAML support is not available
        ValueError: If profile name is not recognized
    """
    return load_profile(profile_name)


def main():
    """Main training function"""
    import argparse

    # Discover available profiles
    try:
        available_profiles = discover_profiles()
    except RuntimeError as e:
        # YAML not available - provide helpful error
        print(f"Error: {e}", file=sys.stderr)
        print(
            "\nTo use training profiles, please install PyYAML:",
            file=sys.stderr
        )
        print("  pip install PyYAML", file=sys.stderr)
        print(
            "\nYou can still use individual training arguments without profiles.",
            file=sys.stderr
        )
        available_profiles = {}
    except Exception as e:
        print(f"Warning: Failed to discover profiles: {e}", file=sys.stderr)
        available_profiles = {}

    parser = argparse.ArgumentParser(
        description="Train neural text generation models"
    )
    
    # Build profile choices list
    profile_choices = list(available_profiles.keys()) if available_profiles else []
    profile_help = (
        f"Training profile to use. Available profiles: {', '.join(profile_choices) if profile_choices else 'none (install PyYAML to enable)'}. "
        f"Profile settings can be overridden by individual arguments."
    )
    
    if profile_choices:
        parser.add_argument(
            "--profile",
            type=str,
            choices=profile_choices,
            help=profile_help,
        )
    else:
        parser.add_argument(
            "--profile",
            type=str,
            help=profile_help + " (Note: No profiles found. Install PyYAML and add profile YAML files to scripts/training_profiles/)",
        )
    parser.add_argument(
        "--model-type",
        choices=["character", "word", "both"],
        default=None,  # Will be set from profile or default
        help="Type of model to train (overrides profile setting)",
    )
    parser.add_argument(
        "--book-ids",
        type=str,
        nargs="+",
        help="Source-specific item IDs to use for training. "
             "For Gutenberg: book IDs (e.g., 84 1342). "
             "For Wikipedia: article titles (e.g., 'Artificial intelligence' 'Machine learning'). "
             "For LibriVox: LibriVox book IDs. "
             "For OpenLibrary: work IDs or ISBNs (e.g., OL82563W). "
             "For Internet Archive: IA item identifiers (e.g., 'TripDown1905'). "
             "For HuggingFace: Dataset names (e.g., 'wikitext', 'bookcorpus', 'openwebtext'). "
             "Works with all data sources.",
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
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Generate sample outputs from trained models (loads models, no training)",
    )
    parser.add_argument(
        "--sample-model-type",
        choices=["character", "word", "both"],
        help="Model type to use for sampling (default: both if available)",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List all available training profiles and exit",
    )
    parser.add_argument(
        "--source",
        type=str,
        nargs="+",
        help="Data source(s) to use: gutenberg, wikipedia, librivox, openlibrary, internetarchive, huggingface. "
             "Can specify multiple sources (e.g., --source gutenberg wikipedia). "
             "Default: gutenberg",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List all available data sources and exit",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Search term for HuggingFace dataset search (only works with --source huggingface). "
             "Searches HuggingFace Hub for datasets matching the term.",
    )

    args = parser.parse_args()
    
    # Handle --list-sources
    if args.list_sources:
        from mavaia_core.brain.modules.neural_text_generator_data import NeuralTextGeneratorData
        
        print("Available Data Sources:")
        print("=" * 80)
        
        sources = NeuralTextGeneratorData.list_available_sources()
        if not sources:
            print("\nNo data sources found.")
            return 0
        
        for source_name in sorted(sources):
            source_info = NeuralTextGeneratorData.get_source_info(source_name)
            if source_info:
                print(f"\n{source_name.upper()}")
                print(f"  Supports categories: {source_info['supports_categories']}")
                print(f"  Supports item IDs: {source_info['supports_book_ids']}")
                if source_info['categories']:
                    print(f"  Available categories: {', '.join(source_info['categories'])}")
        
        print("\n" + "=" * 80)
        print("\nUsage: python scripts/train_neural_text_generator.py --source <source_name>")
        print("You can specify multiple sources: --source gutenberg wikipedia")
        print("\nAll existing arguments (--book-ids, --categories, --max-books, etc.)")
        print("work with all data sources.")
        return 0
    
    # Handle --list-profiles
    if args.list_profiles:
        print("Available Training Profiles:")
        print("=" * 80)
        
        if not available_profiles:
            print("\nNo profiles found.")
            if not YAML_AVAILABLE:
                print("\nYAML support is not available.")
                print("Please install PyYAML: pip install PyYAML")
            else:
                print(f"\nProfile directory: {PROFILES_DIR}")
                print("Add YAML files (*.yaml or *.yml) to this directory to create profiles.")
            print("\n" + "=" * 80)
            return 0
        
        for profile_name in sorted(available_profiles.keys()):
            try:
                profile_data = load_profile(profile_name)
                print(f"\n{profile_name.upper()}")
                print(f"  Description: {profile_data.get('description', 'N/A')}")
                print("  Settings:")
                for key, value in profile_data.items():
                    if key != "description":
                        if value is None:
                            print(f"    {key}: (no limit)")
                        elif isinstance(value, list):
                            print(f"    {key}: {', '.join(str(v) for v in value)}")
                        else:
                            print(f"    {key}: {value}")
            except Exception as e:
                print(f"\n{profile_name.upper()}")
                print(f"  Error loading profile: {e}")
        
        print("\n" + "=" * 80)
        print(f"\nProfile directory: {PROFILES_DIR}")
        print("\nUsage: python scripts/train_neural_text_generator.py --profile <profile_name>")
        print("Individual arguments can override profile settings.")
        print("\nTo create custom profiles, add YAML files to the profile directory.")
        return 0

    # Apply profile settings if specified
    profile_config = {}
    if args.profile:
        try:
            profile_config = apply_profile(args.profile)
            description = profile_config.pop('description', 'N/A')
            print(f"Using profile: {args.profile}")
            print(f"  Description: {description}")
            settings_str = ', '.join(
                f'{k}={v}' for k, v in profile_config.items() 
                if v is not None
            )
            if settings_str:
                print(f"  Settings: {settings_str}")
            print()
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            if available_profiles:
                print(f"Available profiles: {', '.join(available_profiles.keys())}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error loading profile '{args.profile}': {e}", file=sys.stderr)
            return 1

    # Initialize module
    generator = NeuralTextGeneratorModule()
    generator.initialize()

    # If --sample is specified without training, just generate samples
    if args.sample and not any([
        args.epochs != 10,  # Default epochs
        args.train_for_minutes,
        args.train_for_hours,
        args.continue_training,
        args.book_ids,
        args.categories,
    ]):
        # Sample-only mode - load models and generate
        print("=" * 80)
        print("Neural Text Generator - Sample Generation")
        print("=" * 80)
        print("Loading trained models...\n")
        
        # Determine which models to load
        sample_model_type = args.sample_model_type or "both"
        load_result = generator.execute("load_model", {"model_type": sample_model_type})
        
        if not load_result.get("success"):
            print("✗ Failed to load models!")
            print("  Error: Models not found. Train models first with:")
            print("    python scripts/train_neural_text_generator.py --epochs 10")
            return 1
        
        # Show which models loaded
        for model_type, result in load_result.get("results", {}).items():
            if result.get("success"):
                print(f"✓ {model_type} model loaded")
            else:
                print(f"✗ {model_type} model: {result.get('error', 'Not found')}")
        
        print()
        
        # Generate samples (code continues below)
        sample_only = True
    else:
        sample_only = False
        # Training mode
        
        # Build training parameters with profile defaults, overridden by explicit arguments
        train_params = {}
        
        # Apply profile defaults first
        if profile_config:
            train_params.update({
                k: v for k, v in profile_config.items() 
                if k != "description" and v is not None
            })
        
        # Override with explicit arguments (explicit args take precedence over profile)
        # Source: use explicit arg if provided, otherwise profile/default
        if args.source:
            # If multiple sources, use list; if single, use string
            train_params["source"] = args.source if len(args.source) > 1 else args.source[0]
        elif "source" not in train_params:
            train_params["source"] = "gutenberg"  # Default
        
        # Model type: use explicit arg if provided, otherwise profile/default
        if args.model_type is not None:
            train_params["model_type"] = args.model_type
        elif "model_type" not in train_params:
            train_params["model_type"] = "both"
        
        # Epochs: use explicit arg if different from default, otherwise profile/default
        if args.epochs != 10:  # User explicitly set epochs
            train_params["epochs"] = args.epochs
        elif "epochs" not in train_params:
            train_params["epochs"] = 10
        
        # Continue training flag
        train_params["continue_training"] = args.continue_training
        
        # Data percentage: use explicit arg if different from default, otherwise profile/default
        if args.data_percentage != 1.0:  # User explicitly set data_percentage
            train_params["data_percentage"] = args.data_percentage
        elif "data_percentage" not in train_params:
            train_params["data_percentage"] = 1.0
        
        # Book IDs: explicit argument always overrides
        if args.book_ids:
            train_params["book_ids"] = args.book_ids
        
        # Categories: explicit argument always overrides profile
        if args.categories:
            train_params["categories"] = args.categories
        
        # Training time: explicit arguments always override
        if args.train_for_hours:
            train_params["train_for_hours"] = args.train_for_hours
            # Remove epochs if time-based training is specified
            train_params.pop("epochs", None)
        elif args.train_for_minutes:
            train_params["train_for_minutes"] = args.train_for_minutes
            # Remove epochs if time-based training is specified
            train_params.pop("epochs", None)
        
        # Max text size: explicit argument always overrides
        if args.max_text_size:
            train_params["max_text_size"] = args.max_text_size
        
        # Max books: explicit argument always overrides
        if args.max_books:
            train_params["max_books"] = args.max_books
        
        # Search: explicit argument always overrides
        if args.search:
            train_params["search"] = args.search
        
        # Print training configuration
        print("=" * 80)
        print("Neural Text Generator Training")
        print("=" * 80)
        if args.profile:
            print(f"Profile: {args.profile}")
        print(f"Data source(s): {train_params.get('source', 'gutenberg')}")
        print(f"Model type: {train_params.get('model_type', 'both')}")
        if train_params.get("categories"):
            print(f"Categories: {', '.join(train_params['categories'])}")
        if train_params.get("book_ids"):
            print(f"Item IDs: {train_params['book_ids']}")
        if train_params.get("train_for_hours"):
            print(f"Training time: {train_params['train_for_hours']} hours")
        elif train_params.get("train_for_minutes"):
            print(f"Training time: {train_params['train_for_minutes']} minutes")
        elif train_params.get("epochs"):
            print(f"Epochs: {train_params['epochs']}")
        if train_params.get("max_text_size"):
            print(f"Max text size: {train_params['max_text_size']:,} characters")
        if train_params.get("max_books"):
            print(f"Max items per source: {train_params['max_books']}")
        if train_params.get("search"):
            print(f"Search term: {train_params['search']}")
        data_pct = train_params.get("data_percentage", 1.0)
        if data_pct < 1.0:
            print(f"Data percentage: {data_pct*100:.1f}%")
        print(f"Continue training: {train_params.get('continue_training', False)}")
        print()

        print("Starting training...")
        result = generator.execute("train_model", train_params)

        if not result.get("success"):
            print("\n✗ Training failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1

        print("\n✓ Training completed successfully!")
        
        # Save models
        model_type = train_params.get("model_type", "both")
        print("\nSaving models...")
        save_result = generator.execute("save_model", {"model_type": model_type})
        
        if save_result.get("success"):
            print("✓ Models saved successfully!")
            for model_type, save_info in save_result.get("results", {}).items():
                if save_info.get("success"):
                    print(f"  {model_type} model: {save_info.get('path', 'N/A')}")
        else:
            print("✗ Failed to save models")
            print(f"  Error: {save_result.get('error', 'Unknown error')}")
        
        # Load models for sampling if requested
        if args.sample:
            load_result = generator.execute("load_model", {"model_type": model_type})
            if not load_result.get("success"):
                print("\n⚠ Warning: Could not reload models for sampling")
                return 0

    # Generate sample outputs if requested
    if args.sample or sample_only:
        print("\n" + "=" * 80)
        print("Generating Sample Outputs")
        print("=" * 80)
        
        # Determine which models are available
        if sample_only:
            # Check which models actually loaded
            model_types_to_test = []
            for model_type, result in load_result.get("results", {}).items():
                if result.get("success"):
                    model_types_to_test.append(model_type)
            if not model_types_to_test:
                print("✗ No models available for sampling")
                return 1
        else:
            model_types_to_test = []
            resolved_model_type = train_params.get("model_type", "both")
            if resolved_model_type in ["character", "both"]:
                model_types_to_test.append("character")
            if resolved_model_type in ["word", "both"]:
                model_types_to_test.append("word")
            
            if not model_types_to_test:
                model_types_to_test = ["character"]  # Default fallback
        
        for model_type in model_types_to_test:
                print(f"\n--- {model_type.upper()} Model Samples ---\n")
                
                # Sample prompts for different scenarios
                sample_prompts = [
                    {
                        "prompt": "The quick brown",
                        "type": "Short phrase",
                        "max_length": 50,
                        "temperature": 0.7,
                    },
                    {
                        "prompt": "Once upon a time",
                        "type": "Story opening",
                        "max_length": 100,
                        "temperature": 0.8,
                    },
                    {
                        "prompt": "In the beginning",
                        "type": "Philosophical",
                        "max_length": 150,
                        "temperature": 0.7,
                    },
                    {
                        "prompt": "The scientist discovered",
                        "type": "Technical",
                        "max_length": 120,
                        "temperature": 0.6,
                    },
                    {
                        "prompt": "She walked into the room",
                        "type": "Narrative",
                        "max_length": 200,
                        "temperature": 0.75,
                    },
                ]
                
                for sample_config in sample_prompts:
                    prompt = sample_config["prompt"]
                    sample_type = sample_config["type"]
                    max_length = sample_config["max_length"]
                    temperature = sample_config["temperature"]
                    
                    print(f"[{sample_type}] Prompt: '{prompt}'")
                    print(f"  Temperature: {temperature}, Max length: {max_length}")
                    
                    gen_result = generator.execute(
                        "generate_text",
                        {
                            "prompt": prompt,
                            "model_type": model_type,
                            "max_length": max_length,
                            "temperature": temperature,
                        },
                    )
                    
                    if gen_result.get("success"):
                        generated_text = gen_result.get("text", "")
                        # Show full generated text (not truncated)
                        print(f"  Generated ({len(generated_text)} chars):")
                        print(f"  {generated_text}")
                        
                        # Calculate some quality metrics
                        word_count = len(generated_text.split())
                        sentence_count = generated_text.count('.') + generated_text.count('!') + generated_text.count('?')
                        avg_words_per_sentence = word_count / max(sentence_count, 1)
                        
                        print(f"  Stats: {word_count} words, {sentence_count} sentences, "
                              f"{avg_words_per_sentence:.1f} words/sentence")
                    else:
                        print(f"  ✗ Generation failed: {gen_result.get('error', 'Unknown error')}")
                    
                    print()  # Blank line between samples
                
                # Generate sentence samples
                print("\n--- Sentence Samples ---\n")
                sentence_prompts = [
                    "The cat",
                    "She said",
                    "In the morning",
                    "The problem is",
                ]
                
                for prompt in sentence_prompts:
                    sentence_result = generator.execute(
                        "generate_text",
                        {
                            "prompt": prompt,
                            "model_type": model_type,
                            "max_length": 100,
                            "temperature": 0.7,
                        },
                    )
                    
                    if sentence_result.get("success"):
                        generated = sentence_result.get("text", "")
                        # Extract just the sentence (first complete sentence)
                        sentences = []
                        for char in generated:
                            sentences.append(char)
                            if char in ".!?" and len(sentences) > len(prompt):
                                break
                        sentence = "".join(sentences).strip()
                        if not sentence.endswith((".", "!", "?")):
                            sentence += "."
                        
                        print(f"Prompt: '{prompt}'")
                        print(f"  → {sentence}")
                    else:
                        print(f"Prompt: '{prompt}'")
                        print(f"  ✗ Failed: {sentence_result.get('error', 'Unknown error')}")
                
                print()
                
                # Generate a longer paragraph sample
                print("\n--- Paragraph Sample ---\n")
                paragraph_result = generator.execute(
                    "generate_text",
                    {
                        "prompt": "The story begins when",
                        "model_type": model_type,
                        "max_length": 500,
                        "temperature": 0.75,
                    },
                )
                
                if paragraph_result.get("success"):
                    paragraph_text = paragraph_result.get("text", "")
                    print(f"Prompt: 'The story begins when'")
                    print(f"Generated paragraph ({len(paragraph_text)} characters):\n")
                    print(paragraph_text)
                    print()
                else:
                    print(f"✗ Paragraph generation failed: {paragraph_result.get('error', 'Unknown error')}\n")
        
        print("\n" + "=" * 80)
        if sample_only:
            print("Sample Generation Complete")
        else:
            print("Training Complete")
        print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

