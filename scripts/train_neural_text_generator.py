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
    
    Interactive Profile Creator:
    Use --create-profile to launch an interactive wizard that guides you through
    creating a new training profile without leaving the script.

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
    
    # Use HuggingFace with specific datasets (supports full paths like "Anthropic/AnthropicInterviewer")
    python scripts/train_neural_text_generator.py --source huggingface --book-ids "wikitext" "bookcorpus"
    python scripts/train_neural_text_generator.py --source huggingface --book-ids "Anthropic/AnthropicInterviewer"
    
    # Use HuggingFace with category search
    python scripts/train_neural_text_generator.py --source huggingface --categories technical fiction
    
    # Create a new training profile interactively
    python scripts/train_neural_text_generator.py --create-profile
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Try to import YAML support (lightweight, no heavy dependencies)
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Don't import NeuralTextGeneratorModule here - import it only when needed
# This allows --help to work without slow imports
NeuralTextGeneratorModule = None


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


def create_profile_interactive() -> int:
    """
    Interactive profile creator that guides users through creating a training profile.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Try to import rich for colored output
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False
        console = None
    
    if not YAML_AVAILABLE:
        if use_rich:
            console.print("[red]Error:[/red] YAML support is required for profile creation.")
            console.print("Please install PyYAML: [cyan]pip install PyYAML[/cyan]")
        else:
            print("Error: YAML support is required for profile creation.", file=sys.stderr)
            print("Please install PyYAML: pip install PyYAML", file=sys.stderr)
        return 1
    
    # Ensure profiles directory exists
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    
    if use_rich:
        console.print()
        console.print(Panel(
            "[bold]This wizard will guide you through creating a custom training profile.[/bold]\n"
            "You can press Enter to use default values or skip optional fields.",
            title="[bold green]Interactive Training Profile Creator[/bold green]",
            border_style="green"
        ))
        console.print()
    else:
        print("=" * 80)
        print("Interactive Training Profile Creator")
        print("=" * 80)
        print()
        print("This wizard will guide you through creating a custom training profile.")
        print("You can press Enter to use default values or skip optional fields.")
        print()
    
    profile_data = {}
    
    # Get profile name
    while True:
        if use_rich:
            console.print("[bold cyan]Profile name[/bold cyan] (required, will be used as filename):", end=" ")
        else:
            print("Profile name (required, will be used as filename):", end=" ")
        profile_name = input().strip()
        if not profile_name:
            if use_rich:
                console.print("[red]  ✗ Error:[/red] Profile name is required.")
            else:
                print("  Error: Profile name is required.")
            continue
        
        # Validate filename
        if not profile_name.replace("_", "").replace("-", "").isalnum():
            if use_rich:
                console.print("[red]  ✗ Error:[/red] Profile name must contain only letters, numbers, underscores, and hyphens.")
            else:
                print("  Error: Profile name must contain only letters, numbers, underscores, and hyphens.")
            continue
        
        # Check if profile already exists
        profile_file = PROFILES_DIR / f"{profile_name}.yaml"
        if profile_file.exists():
            if use_rich:
                console.print(f"[yellow]  ⚠ Profile '{profile_name}' already exists.[/yellow] Overwrite? (y/N):", end=" ")
            else:
                print(f"  Profile '{profile_name}' already exists. Overwrite? (y/N):", end=" ")
            overwrite = input().strip().lower()
            if overwrite not in ('y', 'yes'):
                if use_rich:
                    console.print("[yellow]  Cancelled. Please choose a different name.[/yellow]")
                else:
                    print("  Cancelled. Please choose a different name.")
                continue
        
        break
    
    # Get description
    if use_rich:
        console.print()
        console.print("[bold cyan]Profile description[/bold cyan] (what this profile is for):")
        console.print("  [dim]Description:[/dim]", end=" ")
    else:
        print()
        print("Profile description (what this profile is for):")
        print("  Description:", end=" ")
    description = input().strip()
    if not description:
        description = f"Custom training profile: {profile_name}"
    profile_data["description"] = description
    
    # Get data source(s)
    if use_rich:
        console.print()
        console.print("[bold cyan]Data source(s)[/bold cyan] to use:")
        console.print("  [dim]Available:[/dim] [green]gutenberg[/green], [green]wikipedia[/green], [green]librivox[/green], [green]openlibrary[/green], [green]internetarchive[/green], [green]huggingface[/green]")
        console.print("  [dim]You can specify multiple sources separated by spaces (e.g., 'gutenberg wikipedia')[/dim]")
        console.print("  [dim]Default:[/dim] [cyan]gutenberg[/cyan]")
        console.print("  [bold]Source(s):[/bold]", end=" ")
    else:
        print()
        print("Data source(s) to use:")
        print("  Available: gutenberg, wikipedia, librivox, openlibrary, internetarchive, huggingface")
        print("  You can specify multiple sources separated by spaces (e.g., 'gutenberg wikipedia')")
        print("  Default: gutenberg")
        print("  Source(s):", end=" ")
    source_input = input().strip()
    if source_input:
        sources = [s.strip() for s in source_input.split() if s.strip()]
        if len(sources) == 1:
            profile_data["source"] = sources[0]
        elif len(sources) > 1:
            profile_data["source"] = sources
        else:
            profile_data["source"] = "gutenberg"
    else:
        profile_data["source"] = "gutenberg"
    
    # Get categories
    if use_rich:
        console.print()
        console.print("[bold cyan]Categories[/bold cyan] (optional, press Enter to skip):")
        console.print("  [dim]Available:[/dim] [green]fiction[/green], [green]non_fiction[/green], [green]technical[/green], [green]philosophy[/green], [green]poetry[/green], [green]drama[/green], [green]adventure[/green], [green]mystery[/green], [green]science_fiction[/green], [green]classic[/green]")
        console.print("  [dim]You can specify multiple categories separated by spaces[/dim]")
        console.print("  [bold]Categories:[/bold]", end=" ")
    else:
        print()
        print("Categories (optional, press Enter to skip):")
        print("  Available: fiction, non_fiction, technical, philosophy, poetry, drama, adventure, mystery, science_fiction, classic")
        print("  You can specify multiple categories separated by spaces")
        print("  Categories:", end=" ")
    categories_input = input().strip()
    if categories_input:
        categories = [c.strip() for c in categories_input.split() if c.strip()]
        if categories:
            profile_data["categories"] = categories
    
    # Get model type
    if use_rich:
        console.print()
        console.print("[bold cyan]Model type:[/bold cyan]")
        console.print("  [dim]Options:[/dim] [green]character[/green], [green]word[/green], [green]transformer[/green], [green]both[/green]")
        console.print("  [dim]Default:[/dim] [cyan]both[/cyan]")
        console.print("  [bold]Model type:[/bold]", end=" ")
    else:
        print()
        print("Model type:")
        print("  Options: character, word, transformer, both")
        print("  Default: both")
        print("  Model type:", end=" ")
    model_type = input().strip().lower()
    if model_type in ["character", "word", "transformer", "both"]:
        profile_data["model_type"] = model_type
    else:
        profile_data["model_type"] = "both"
    
    # Get epochs
    if use_rich:
        console.print()
        console.print("[bold cyan]Number of training epochs:[/bold cyan]")
        console.print("  [dim]Default:[/dim] [cyan]10[/cyan]")
        console.print("  [bold]Epochs:[/bold]", end=" ")
    else:
        print()
        print("Number of training epochs:")
        print("  Default: 10")
        print("  Epochs:", end=" ")
    epochs_input = input().strip()
    if epochs_input:
        try:
            epochs = int(epochs_input)
            if epochs > 0:
                profile_data["epochs"] = epochs
            else:
                if use_rich:
                    console.print("[yellow]  ⚠ Warning:[/yellow] Epochs must be positive, using default: [cyan]10[/cyan]")
                else:
                    print("  Warning: Epochs must be positive, using default: 10")
                profile_data["epochs"] = 10
        except ValueError:
            if use_rich:
                console.print("[yellow]  ⚠ Warning:[/yellow] Invalid number, using default: [cyan]10[/cyan]")
            else:
                print("  Warning: Invalid number, using default: 10")
            profile_data["epochs"] = 10
    else:
        profile_data["epochs"] = 10
    
    # Get max_books (optional)
    if use_rich:
        console.print()
        console.print("[bold cyan]Maximum number of books/items[/bold cyan] to load per source (optional, press Enter to skip):")
        console.print("  [dim]Leave empty for no limit[/dim]")
        console.print("  [bold]Max books:[/bold]", end=" ")
    else:
        print()
        print("Maximum number of books/items to load per source (optional, press Enter to skip):")
        print("  Leave empty for no limit")
        print("  Max books:", end=" ")
    max_books_input = input().strip()
    if max_books_input:
        try:
            max_books = int(max_books_input)
            if max_books > 0:
                profile_data["max_books"] = max_books
        except ValueError:
            if use_rich:
                console.print("[yellow]  ⚠ Warning:[/yellow] Invalid number, skipping max_books")
            else:
                print("  Warning: Invalid number, skipping max_books")
    
    # Get max_text_size (optional)
    if use_rich:
        console.print()
        console.print("[bold cyan]Maximum text size[/bold cyan] in characters (optional, press Enter to skip):")
        console.print("  [dim]Leave empty for no limit[/dim]")
        console.print("  [bold]Max text size:[/bold]", end=" ")
    else:
        print()
        print("Maximum text size in characters (optional, press Enter to skip):")
        print("  Leave empty for no limit")
        print("  Max text size:", end=" ")
    max_text_size_input = input().strip()
    if max_text_size_input:
        try:
            max_text_size = int(max_text_size_input)
            if max_text_size > 0:
                profile_data["max_text_size"] = max_text_size
        except ValueError:
            if use_rich:
                console.print("[yellow]  ⚠ Warning:[/yellow] Invalid number, skipping max_text_size")
            else:
                print("  Warning: Invalid number, skipping max_text_size")
    
    # Get data_percentage (optional)
    if use_rich:
        console.print()
        console.print("[bold cyan]Percentage of data[/bold cyan] to use (optional, press Enter to skip):")
        console.print("  [dim]Range: 0.0 to 1.0 (e.g., 0.5 for 50%)[/dim]")
        console.print("  [dim]Default:[/dim] [cyan]1.0[/cyan] [dim](100%)[/dim]")
        console.print("  [bold]Data percentage:[/bold]", end=" ")
    else:
        print()
        print("Percentage of data to use (optional, press Enter to skip):")
        print("  Range: 0.0 to 1.0 (e.g., 0.5 for 50%)")
        print("  Default: 1.0 (100%)")
        print("  Data percentage:", end=" ")
    data_percentage_input = input().strip()
    if data_percentage_input:
        try:
            data_percentage = float(data_percentage_input)
            if 0.0 < data_percentage <= 1.0:
                profile_data["data_percentage"] = data_percentage
            else:
                if use_rich:
                    console.print("[yellow]  ⚠ Warning:[/yellow] Data percentage must be between 0.0 and 1.0, using default: [cyan]1.0[/cyan]")
                else:
                    print("  Warning: Data percentage must be between 0.0 and 1.0, using default: 1.0")
                profile_data["data_percentage"] = 1.0
        except ValueError:
            if use_rich:
                console.print("[yellow]  ⚠ Warning:[/yellow] Invalid number, using default: [cyan]1.0[/cyan]")
            else:
                print("  Warning: Invalid number, using default: 1.0")
            profile_data["data_percentage"] = 1.0
    else:
        profile_data["data_percentage"] = 1.0
    
    # Get book_ids (optional)
    if use_rich:
        console.print()
        console.print("[bold cyan]Specific item IDs[/bold cyan] to use (optional, press Enter to skip):")
        console.print("  [dim]For Gutenberg:[/dim] book IDs (e.g., '84 1342')")
        console.print("  [dim]For Wikipedia:[/dim] article titles (e.g., 'Artificial intelligence Machine learning')")
        console.print("  [dim]For HuggingFace:[/dim] dataset names (e.g., 'wikitext bookcorpus')")
        console.print("  [dim]You can specify multiple IDs separated by spaces[/dim]")
        console.print("  [bold]Item IDs:[/bold]", end=" ")
    else:
        print()
        print("Specific item IDs to use (optional, press Enter to skip):")
        print("  For Gutenberg: book IDs (e.g., '84 1342')")
        print("  For Wikipedia: article titles (e.g., 'Artificial intelligence Machine learning')")
        print("  For HuggingFace: dataset names (e.g., 'wikitext bookcorpus')")
        print("  You can specify multiple IDs separated by spaces")
        print("  Item IDs:", end=" ")
    book_ids_input = input().strip()
    if book_ids_input:
        book_ids = [bid.strip() for bid in book_ids_input.split() if bid.strip()]
        if book_ids:
            profile_data["book_ids"] = book_ids
    
    # Get search term (optional, mainly for HuggingFace)
    if use_rich:
        console.print()
        console.print("[bold cyan]Search term[/bold cyan] for dataset search (optional, press Enter to skip):")
        console.print("  [dim]Mainly used for HuggingFace source to search the Hub[/dim]")
        console.print("  [dim]Example:[/dim] 'chatgpt OR claude OR conversation'")
        console.print("  [bold]Search term:[/bold]", end=" ")
    else:
        print()
        print("Search term for dataset search (optional, press Enter to skip):")
        print("  Mainly used for HuggingFace source to search the Hub")
        print("  Example: 'chatgpt OR claude OR conversation'")
        print("  Search term:", end=" ")
    search_input = input().strip()
    if search_input:
        profile_data["search"] = search_input
    
    # Get transformer config (if model_type is transformer or both)
    if profile_data.get("model_type") in ["transformer", "both"]:
        if use_rich:
            console.print()
            console.print("[bold cyan]Transformer configuration[/bold cyan] (optional, press Enter to skip):")
            console.print("  [dim]If you want to customize transformer settings, you can configure them here.[/dim]")
            console.print("  [bold]Configure transformer?[/bold] (y/N):", end=" ")
        else:
            print()
            print("Transformer configuration (optional, press Enter to skip):")
            print("  If you want to customize transformer settings, you can configure them here.")
            print("  Configure transformer? (y/N):", end=" ")
        configure_transformer = input().strip().lower()
        
        if configure_transformer in ('y', 'yes'):
            transformer_config = {}
            
            if use_rich:
                console.print()
                console.print("  [bold cyan]Transformer model name:[/bold cyan]")
                console.print("    [dim]Examples:[/dim] [green]gpt2[/green], [green]EleutherAI/gpt-neo-1.3B[/green], [green]microsoft/DialoGPT-medium[/green]")
                console.print("    [dim]Default:[/dim] [cyan]gpt2[/cyan]")
                console.print("    [bold]Model name:[/bold]", end=" ")
            else:
                print()
                print("  Transformer model name:")
                print("    Examples: gpt2, EleutherAI/gpt-neo-1.3B, microsoft/DialoGPT-medium")
                print("    Default: gpt2")
                print("    Model name:", end=" ")
            model_name = input().strip()
            if model_name:
                transformer_config["model_name"] = model_name
            else:
                transformer_config["model_name"] = "gpt2"
            
            if use_rich:
                console.print()
                console.print("  [bold cyan]Max sequence length[/bold cyan] (optional, press Enter for default 1024):")
                console.print("    [bold]Max length:[/bold]", end=" ")
            else:
                print()
                print("  Max sequence length (optional, press Enter for default 1024):")
                print("    Max length:", end=" ")
            max_length_input = input().strip()
            if max_length_input:
                try:
                    max_length = int(max_length_input)
                    if max_length > 0:
                        transformer_config["max_length"] = max_length
                except ValueError:
                    pass
            
            if use_rich:
                console.print()
                console.print("  [bold cyan]Batch size[/bold cyan] (optional, press Enter for default 8):")
                console.print("    [bold]Batch size:[/bold]", end=" ")
            else:
                print()
                print("  Batch size (optional, press Enter for default 8):")
                print("    Batch size:", end=" ")
            batch_size_input = input().strip()
            if batch_size_input:
                try:
                    batch_size = int(batch_size_input)
                    if batch_size > 0:
                        transformer_config["batch_size"] = batch_size
                except ValueError:
                    pass
            
            if use_rich:
                console.print()
                console.print("  [bold cyan]Learning rate[/bold cyan] (optional, press Enter for default 5e-5):")
                console.print("    [bold]Learning rate:[/bold]", end=" ")
            else:
                print()
                print("  Learning rate (optional, press Enter for default 5e-5):")
                print("    Learning rate:", end=" ")
            learning_rate_input = input().strip()
            if learning_rate_input:
                try:
                    learning_rate = float(learning_rate_input)
                    if learning_rate > 0:
                        transformer_config["learning_rate"] = learning_rate
                except ValueError:
                    pass
            
            if transformer_config and len(transformer_config) > 0:
                profile_data["transformer_config"] = transformer_config
    
    # Summary and confirmation
    if use_rich:
        console.print()
        # Create summary table
        table = Table(title="Profile Summary", show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        table.add_row("Profile name", profile_name)
        table.add_row("Description", profile_data.get('description', 'N/A'))
        
        source_val = profile_data.get('source', 'gutenberg')
        if isinstance(source_val, list):
            source_val = ', '.join(source_val)
        table.add_row("Source(s)", source_val)
        
        if 'categories' in profile_data:
            table.add_row("Categories", ', '.join(profile_data['categories']))
        table.add_row("Model type", profile_data.get('model_type', 'both'))
        table.add_row("Epochs", str(profile_data.get('epochs', 10)))
        if 'max_books' in profile_data:
            table.add_row("Max books", str(profile_data['max_books']))
        if 'max_text_size' in profile_data:
            table.add_row("Max text size", f"{profile_data['max_text_size']:,} characters")
        table.add_row("Data percentage", f"{profile_data.get('data_percentage', 1.0) * 100:.1f}%")
        if 'book_ids' in profile_data:
            table.add_row("Item IDs", ', '.join(profile_data['book_ids']))
        if 'search' in profile_data:
            table.add_row("Search term", profile_data['search'])
        if 'transformer_config' in profile_data:
            config_str = ', '.join(f"{k}={v}" for k, v in profile_data['transformer_config'].items())
            table.add_row("Transformer config", config_str)
        
        console.print(table)
        console.print()
        console.print("[bold]Save this profile?[/bold] (Y/n):", end=" ")
    else:
        print()
        print("=" * 80)
        print("Profile Summary")
        print("=" * 80)
        print(f"Profile name: {profile_name}")
        print(f"Description: {profile_data.get('description', 'N/A')}")
        print(f"Source(s): {profile_data.get('source', 'gutenberg')}")
        if 'categories' in profile_data:
            print(f"Categories: {', '.join(profile_data['categories'])}")
        print(f"Model type: {profile_data.get('model_type', 'both')}")
        print(f"Epochs: {profile_data.get('epochs', 10)}")
        if 'max_books' in profile_data:
            print(f"Max books: {profile_data['max_books']}")
        if 'max_text_size' in profile_data:
            print(f"Max text size: {profile_data['max_text_size']:,} characters")
        print(f"Data percentage: {profile_data.get('data_percentage', 1.0) * 100:.1f}%")
        if 'book_ids' in profile_data:
            print(f"Item IDs: {', '.join(profile_data['book_ids'])}")
        if 'search' in profile_data:
            print(f"Search term: {profile_data['search']}")
        if 'transformer_config' in profile_data:
            print(f"Transformer config: {profile_data['transformer_config']}")
        print()
        print("Save this profile? (Y/n):", end=" ")
    
    confirm = input().strip().lower()
    if confirm in ('n', 'no'):
        if use_rich:
            console.print("[yellow]Profile creation cancelled.[/yellow]")
        else:
            print("Profile creation cancelled.")
        return 0
    
    # Save profile
    try:
        # Remove None values and empty dicts/lists before saving
        cleaned_profile = {}
        for key, value in profile_data.items():
            if value is None:
                continue
            if isinstance(value, dict) and not value:
                continue
            if isinstance(value, list) and not value:
                continue
            cleaned_profile[key] = value
        
        profile_file = PROFILES_DIR / f"{profile_name}.yaml"
        with open(profile_file, "w", encoding="utf-8") as f:
            # Write header comment
            f.write(f"# {cleaned_profile.get('description', 'Custom Training Profile')}\n")
            f.write(f"# Created via interactive profile creator\n")
            
            # Write profile data using YAML
            yaml.dump(cleaned_profile, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        if use_rich:
            console.print()
            console.print(Panel(
                f"[bold green]✓ Profile saved successfully![/bold green]\n\n"
                f"[bold]Profile file:[/bold] [cyan]{profile_file}[/cyan]\n\n"
                f"[bold]Usage:[/bold] [cyan]python scripts/train_neural_text_generator.py --profile {profile_name}[/cyan]",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
            console.print()
        else:
            print()
            print(f"✓ Profile saved successfully: {profile_file}")
            print()
            print(f"You can now use this profile with:")
            print(f"  python scripts/train_neural_text_generator.py --profile {profile_name}")
            print()
        return 0
        
    except Exception as e:
        if use_rich:
            console.print()
            console.print(Panel(
                f"[bold red]✗ Error saving profile[/bold red]\n\n"
                f"[red]{str(e)}[/red]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            ))
            console.print()
        else:
            print(f"Error saving profile: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def print_help_rich(parser, available_profiles):
    """Print help using rich formatting"""
    import argparse
    
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False
        console = None
        if parser:
            parser.print_help()
            return
        # If parser is None and rich is not available, we'll still show help below
    
    # If parser is None, we need to build argument info manually
    if parser is None or not use_rich:
        # Build basic argument structure for help display
        # This is used when help is requested before parser is fully built, or when rich is not available
        arg_groups = {
            'profile': [
                {'name': '-h, --help', 'help': 'Show this help message and exit'},
                {'name': '--profile', 'help': 'Training profile to use. Profile settings can be overridden by individual arguments.'},
                {'name': '--create-profile', 'help': 'Launch interactive profile creator to create a new training profile'},
                {'name': '--list-profiles', 'help': 'List all available training profiles and exit'},
            ],
            'data': [
                {'name': '--source', 'help': 'Data source(s) to use: gutenberg, wikipedia, librivox, openlibrary, internetarchive, huggingface. Can specify multiple sources (e.g., --source gutenberg wikipedia). Default: gutenberg'},
                {'name': '--list-sources', 'help': 'List all available data sources and exit'},
                {'name': '--book-ids', 'help': 'Source-specific item IDs to use for training. For Gutenberg: book IDs (e.g., 84 1342). For Wikipedia: article titles. For HuggingFace: dataset names (e.g., wikitext, bookcorpus). Works with all data sources.'},
                {'name': '--categories', 'help': 'Categories of books to load. Choices: fiction, non_fiction, technical, philosophy, poetry, drama, adventure, mystery, science_fiction, classic. Can specify multiple (e.g., fiction technical)'},
                {'name': '--search', 'help': 'Search term for HuggingFace dataset search (only works with --source huggingface). Searches HuggingFace Hub for datasets matching the term.'},
            ],
            'model': [
                {'name': '--model-type', 'help': "Type of model to train (overrides profile setting). Choices: character, word, transformer, both. Use 'transformer' for HuggingFace Transformers models, or 'both' with --model-name to train RNN + Transformer."},
                {'name': '--model-name', 'help': "HuggingFace model name for transformer training (e.g., 'gpt2', 'EleutherAI/gpt-neo-1.3B'). Overrides transformer_config.model_name if provided."},
                {'name': '--transformer-config', 'help': 'Path to JSON file with transformer configuration, or JSON string. Overrides default transformer config from neural_text_generator_config.json.'},
            ],
            'training': [
                {'name': '--epochs', 'help': 'Number of training epochs', 'default': '10'},
                {'name': '--train-for-minutes', 'help': 'Maximum training time in minutes (overrides epochs if set)'},
                {'name': '--train-for-hours', 'help': 'Maximum training time in hours (overrides epochs if set)'},
                {'name': '--max-text-size', 'help': 'Maximum text size in characters'},
                {'name': '--max-books', 'help': 'Maximum number of books to load'},
                {'name': '--data-percentage', 'help': 'Percentage of data to use (0.0-1.0, default: 1.0)', 'default': '1.0'},
                {'name': '--continue-training', 'help': 'Continue training from existing model'},
                {'name': '--run-dir', 'help': 'Output directory for this training run (models, checkpoints, run_config.json)'},
                {'name': '--seed', 'help': 'Random seed for deterministic-ish training (python/numpy/tensorflow)'},
            ],
            'sampling': [
                {'name': '--sample', 'help': 'Generate sample outputs from trained models (loads models, no training)'},
                {'name': '--sample-model-type', 'help': "Model type to use for sampling. Choices: character, word, transformer, both. Default: both if available"},
            ],
        }
        
        # Print header
        if use_rich:
            console.print()
            console.print(Panel(
                "[bold]Train neural text generation models with multiple data sources[/bold]\n"
                "Supports Gutenberg, Wikipedia, LibriVox, OpenLibrary, Internet Archive, and HuggingFace",
                title="[bold green]Neural Text Generator Training Script[/bold green]",
                border_style="green"
            ))
            console.print()
        else:
            print("=" * 80)
            print("Neural Text Generator Training Script")
            print("=" * 80)
            print("Train neural text generation models with multiple data sources")
            print("Supports Gutenberg, Wikipedia, LibriVox, OpenLibrary, Internet Archive, and HuggingFace")
            print("=" * 80)
            print()
        
        # Print each group
        for group_name, args_list in arg_groups.items():
            if group_name == 'profile':
                title = "Profile Options"
                title_rich = "[bold cyan]Profile Options[/bold cyan]"
            elif group_name == 'data':
                title = "Data Source Options"
                title_rich = "[bold cyan]Data Source Options[/bold cyan]"
            elif group_name == 'model':
                title = "Model Options"
                title_rich = "[bold cyan]Model Options[/bold cyan]"
            elif group_name == 'training':
                title = "Training Options"
                title_rich = "[bold cyan]Training Options[/bold cyan]"
            elif group_name == 'sampling':
                title = "Sampling Options"
                title_rich = "[bold cyan]Sampling Options[/bold cyan]"
            else:
                title = "Options"
                title_rich = "[bold cyan]Options[/bold cyan]"
            
            if use_rich:
                table = Table(
                    title=title_rich,
                    show_header=True,
                    header_style="bold magenta",
                    box=None,
                    padding=(0, 2)
                )
                table.add_column("Option", style="cyan", no_wrap=True, width=28)
                table.add_column("Description", style="green", overflow="fold")
            else:
                print(f"{title}:")
                print("-" * 80)
            
            for arg in args_list:
                help_text = arg['help']
                if arg['name'] == '--profile' and available_profiles:
                    profile_list = ', '.join(list(available_profiles.keys())[:5])
                    if len(available_profiles) > 5:
                        profile_list += f" (+{len(available_profiles) - 5} more)"
                    help_text += f"\n  Available profiles: {profile_list}"
                
                if use_rich:
                    help_display = help_text
                    if 'default' in arg:
                        help_display += f"\n[dim]Default: {arg['default']}[/dim]"
                    table.add_row(arg['name'], help_display)
                else:
                    default_text = f" (default: {arg['default']})" if 'default' in arg else ""
                    # Format help text with proper wrapping
                    lines = help_text.split('\n')
                    first_line = lines[0]
                    rest_lines = '\n'.join(lines[1:]) if len(lines) > 1 else ""
                    print(f"  {arg['name']:<30} {first_line}{default_text}")
                    if rest_lines:
                        print(f"  {'':<30} {rest_lines}")
                    print()
            
            if use_rich:
                console.print(table)
                console.print()
            else:
                print()
        
        # Examples
        examples_text = (
            "Examples:\n\n"
            "  python scripts/train_neural_text_generator.py --epochs 10\n"
            "  python scripts/train_neural_text_generator.py --source wikipedia --epochs 10\n"
            "  python scripts/train_neural_text_generator.py --profile fast\n"
            "  python scripts/train_neural_text_generator.py --create-profile\n"
            "  python scripts/train_neural_text_generator.py --list-profiles\n"
            "  python scripts/train_neural_text_generator.py --list-sources"
        )
        
        if use_rich:
            console.print(Panel(
                "[bold]Examples:[/bold]\n\n"
                "[cyan]python scripts/train_neural_text_generator.py --epochs 10[/cyan]\n"
                "[cyan]python scripts/train_neural_text_generator.py --source wikipedia --epochs 10[/cyan]\n"
                "[cyan]python scripts/train_neural_text_generator.py --profile fast[/cyan]\n"
                "[cyan]python scripts/train_neural_text_generator.py --create-profile[/cyan]\n"
                "[cyan]python scripts/train_neural_text_generator.py --list-profiles[/cyan]\n"
                "[cyan]python scripts/train_neural_text_generator.py --list-sources[/cyan]",
                title="[bold green]Usage Examples[/bold green]",
                border_style="green"
            ))
            console.print()
        else:
            print("=" * 80)
            print(examples_text)
            print("=" * 80)
            print()
        
        return
    
    # Get parser actions
    actions = parser._actions
    
    # Group arguments by category
    profile_args = []
    data_args = []
    model_args = []
    training_args = []
    sampling_args = []
    info_args = []
    
    for action in actions:
        if action.dest == 'help' or not action.option_strings:
            continue
        option_strings = ', '.join(action.option_strings)
        help_text = action.help or ''
        
        arg_info = {
            'name': option_strings,
            'help': help_text,
            'default': getattr(action, 'default', None),
            'choices': getattr(action, 'choices', None),
        }
        
        # Categorize arguments
        if any(x in option_strings for x in ['--profile', '--create-profile', '--list-profiles']):
            profile_args.append(arg_info)
        elif any(x in option_strings for x in ['--source', '--book-ids', '--categories', '--search', '--list-sources']):
            data_args.append(arg_info)
        elif any(x in option_strings for x in ['--model-type', '--model-name', '--transformer-config']):
            model_args.append(arg_info)
        elif any(x in option_strings for x in ['--epochs', '--train-for', '--max-', '--data-percentage', '--continue-training']):
            training_args.append(arg_info)
        elif any(x in option_strings for x in ['--sample']):
            sampling_args.append(arg_info)
        else:
            info_args.append(arg_info)
    
    # Print header
    console.print()
    console.print(Panel(
        "[bold]Train neural text generation models with multiple data sources[/bold]\n"
        "Supports Gutenberg, Wikipedia, LibriVox, OpenLibrary, Internet Archive, and HuggingFace",
        title="[bold green]Neural Text Generator Training Script[/bold green]",
        border_style="green"
    ))
    console.print()
    
    # Profile arguments
    if profile_args:
        table = Table(
            title="[bold cyan]Profile Options[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 2)
        )
        table.add_column("Option", style="cyan", no_wrap=True, width=28)
        table.add_column("Description", style="green", overflow="fold")
        
        for arg in profile_args:
            help_text = arg['help']
            if arg.get('choices'):
                choices_str = ', '.join(str(c) for c in arg['choices'][:5])
                if len(arg['choices']) > 5:
                    choices_str += f" (+{len(arg['choices']) - 5} more)"
                help_text += f"\n[dim]Available profiles: {choices_str}[/dim]"
            elif available_profiles:
                # Show available profiles even if not in choices
                profile_list = ', '.join(list(available_profiles.keys())[:5])
                if len(available_profiles) > 5:
                    profile_list += f" (+{len(available_profiles) - 5} more)"
                help_text += f"\n[dim]Available profiles: {profile_list}[/dim]"
            default = arg.get('default')
            if default is not None and default != argparse.SUPPRESS and default != '==SUPPRESS==':
                help_text += f"\n[dim]Default: {default}[/dim]"
            table.add_row(arg['name'], help_text)
        
        console.print(table)
        console.print()
    
    # Data source arguments
    if data_args:
        table = Table(
            title="[bold cyan]Data Source Options[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 2)
        )
        table.add_column("Option", style="cyan", no_wrap=True, width=28)
        table.add_column("Description", style="green", overflow="fold")
        
        for arg in data_args:
            help_text = arg['help']
            if arg.get('choices'):
                choices_str = ', '.join(str(c) for c in arg['choices'][:5])
                if len(arg['choices']) > 5:
                    choices_str += f" (+{len(arg['choices']) - 5} more)"
                help_text += f"\n[dim]Choices: {choices_str}[/dim]"
            default = arg.get('default')
            if default is not None and default != argparse.SUPPRESS and default != '==SUPPRESS==':
                help_text += f"\n[dim]Default: {default}[/dim]"
            table.add_row(arg['name'], help_text)
        
        console.print(table)
        console.print()
    
    # Model arguments
    if model_args:
        table = Table(
            title="[bold cyan]Model Options[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 2)
        )
        table.add_column("Option", style="cyan", no_wrap=True, width=28)
        table.add_column("Description", style="green", overflow="fold")
        
        for arg in model_args:
            help_text = arg['help']
            if arg.get('choices'):
                choices_str = ', '.join(str(c) for c in arg['choices'])
                help_text += f"\n[dim]Choices: {choices_str}[/dim]"
            default = arg.get('default')
            if default is not None and default != argparse.SUPPRESS and default != '==SUPPRESS==':
                help_text += f"\n[dim]Default: {default}[/dim]"
            table.add_row(arg['name'], help_text)
        
        console.print(table)
        console.print()
    
    # Training arguments
    if training_args:
        table = Table(
            title="[bold cyan]Training Options[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 2)
        )
        table.add_column("Option", style="cyan", no_wrap=True, width=28)
        table.add_column("Description", style="green", overflow="fold")
        
        for arg in training_args:
            help_text = arg['help']
            default = arg.get('default')
            if default is not None and default != argparse.SUPPRESS and default != '==SUPPRESS==':
                help_text += f"\n[dim]Default: {default}[/dim]"
            table.add_row(arg['name'], help_text)
        
        console.print(table)
        console.print()
    
    # Sampling arguments
    if sampling_args:
        table = Table(
            title="[bold cyan]Sampling Options[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 2)
        )
        table.add_column("Option", style="cyan", no_wrap=True, width=28)
        table.add_column("Description", style="green", overflow="fold")
        
        for arg in sampling_args:
            help_text = arg['help']
            if arg.get('choices'):
                choices_str = ', '.join(str(c) for c in arg['choices'])
                help_text += f"\n[dim]Choices: {choices_str}[/dim]"
            default = arg.get('default')
            if default is not None and default != argparse.SUPPRESS and default != '==SUPPRESS==':
                help_text += f"\n[dim]Default: {default}[/dim]"
            table.add_row(arg['name'], help_text)
        
        console.print(table)
        console.print()
    
    # Info arguments
    if info_args:
        table = Table(
            title="[bold cyan]Information Options[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 2)
        )
        table.add_column("Option", style="cyan", no_wrap=True, width=28)
        table.add_column("Description", style="green", overflow="fold")
        
        for arg in info_args:
            help_text = arg['help']
            table.add_row(arg['name'], help_text)
        
        console.print(table)
        console.print()
    
    # Examples
    console.print(Panel(
        "[bold]Examples:[/bold]\n\n"
        "[cyan]python scripts/train_neural_text_generator.py --epochs 10[/cyan]\n"
        "[cyan]python scripts/train_neural_text_generator.py --source wikipedia --epochs 10[/cyan]\n"
        "[cyan]python scripts/train_neural_text_generator.py --profile fast[/cyan]\n"
        "[cyan]python scripts/train_neural_text_generator.py --create-profile[/cyan]\n"
        "[cyan]python scripts/train_neural_text_generator.py --list-profiles[/cyan]\n"
        "[cyan]python scripts/train_neural_text_generator.py --list-sources[/cyan]",
        title="[bold green]Usage Examples[/bold green]",
        border_style="green"
    ))
    console.print()


def main():
    """Main training function"""
    import argparse
    
    # Flush output immediately to ensure messages appear
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    # Check for help flag FIRST - before any processing
    # This prevents argparse from printing its default help
    show_help = "--help" in sys.argv or "-h" in sys.argv

    # Discover available profiles (silently if showing help)
    try:
        available_profiles = discover_profiles()
    except RuntimeError as e:
        # YAML not available - provide helpful error (but don't print if just showing help)
        if not show_help:
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
        if not show_help:
            print(f"Warning: Failed to discover profiles: {e}", file=sys.stderr)
        available_profiles = {}
    
    # If showing help, show rich help and exit before building full parser
    if show_help:
        print_help_rich(None, available_profiles)
        return 0

    parser = argparse.ArgumentParser(
        description="Train neural text generation models",
        add_help=False  # We'll handle help ourselves with rich formatting
    )
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="Show this help message and exit",
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
        "--run-dir",
        type=str,
        default=None,
        help="Output directory for this training run (models, checkpoints, run_config.json). Defaults to mavaia_core/models/neural_text_generator/runs/<timestamp>.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic-ish training (python/numpy/tensorflow).",
    )

    parser.add_argument(
        "--model-type",
        choices=["character", "word", "transformer", "both"],
        default=None,  # Will be set from profile or default
        help="Type of model to train (overrides profile setting). "
             "Use 'transformer' for HuggingFace Transformers models, or 'both' with --model-name to train RNN + Transformer.",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        help="HuggingFace model name for transformer training (e.g., 'gpt2', 'EleutherAI/gpt-neo-1.3B'). "
             "Overrides transformer_config.model_name if provided.",
    )
    parser.add_argument(
        "--transformer-config",
        type=str,
        help="Path to JSON file with transformer configuration, or JSON string. "
             "Overrides default transformer config from neural_text_generator_config.json.",
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
             "For HuggingFace: Dataset names or full paths (e.g., 'wikitext', 'bookcorpus', 'Anthropic/AnthropicInterviewer'). "
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
        choices=["character", "word", "transformer", "both"],
        help="Model type to use for sampling (default: both if available)",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List all available training profiles and exit",
    )
    parser.add_argument(
        "--create-profile",
        action="store_true",
        help="Launch interactive profile creator to create a new training profile",
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

    # Parse arguments normally (help was already handled above)
    args = parser.parse_args()
    
    # Handle --list-sources (before any heavy imports)
    if args.list_sources:
        try:
            # Try to import rich for colored output
            try:
                from rich.console import Console
                from rich.table import Table
                from rich.panel import Panel
                from rich.text import Text
                console = Console()
                use_rich = True
            except ImportError:
                use_rich = False
                console = None
            
            # Import data module (may hang if registry initialization is slow)
            print("Loading data sources...", flush=True)
            from mavaia_core.brain.modules.neural_text_generator_data import NeuralTextGeneratorData
            
            sources = NeuralTextGeneratorData.list_available_sources()
            if not sources:
                if use_rich:
                    console.print("[yellow]No data sources found.[/yellow]")
                else:
                    print("No data sources found.")
                return 0
            
            if use_rich:
                # Create formatted table
                table = Table(title="Available Data Sources", show_header=True, header_style="bold magenta")
                table.add_column("Source", style="cyan", no_wrap=True)
                table.add_column("Categories", style="green")
                table.add_column("Item IDs", style="yellow")
                table.add_column("Available Categories", style="blue")
                
                for source_name in sorted(sources):
                    source_info = NeuralTextGeneratorData.get_source_info(source_name)
                    if source_info:
                        categories_support = "✓" if source_info['supports_categories'] else "✗"
                        item_ids_support = "✓" if source_info['supports_book_ids'] else "✗"
                        available_cats = ', '.join(source_info['categories'][:5])
                        if len(source_info['categories']) > 5:
                            available_cats += f" (+{len(source_info['categories']) - 5} more)"
                        if not available_cats:
                            available_cats = "N/A"
                        
                        table.add_row(
                            source_name.upper(),
                            categories_support,
                            item_ids_support,
                            available_cats
                        )
                
                console.print()
                console.print(table)
                console.print()
                console.print(Panel(
                    "[bold]Usage:[/bold] [cyan]python scripts/train_neural_text_generator.py --source <source_name>[/cyan]\n"
                    "You can specify multiple sources: [cyan]--source gutenberg wikipedia[/cyan]\n"
                    "All existing arguments ([cyan]--book-ids[/cyan], [cyan]--categories[/cyan], [cyan]--max-books[/cyan], etc.)\n"
                    "work with all data sources.",
                    title="[bold green]Usage[/bold green]",
                    border_style="green"
                ))
            else:
                # Fallback to plain text
                print("Available Data Sources:")
                print("=" * 80)
                
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
        except Exception as e:
            print(f"Error listing sources: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
    
    # Handle --create-profile (before any heavy imports)
    if args.create_profile:
        return create_profile_interactive()
    
    # Handle --list-profiles (before any heavy imports)
    if args.list_profiles:
        try:
            # Try to import rich for colored output
            try:
                from rich.console import Console
                from rich.table import Table
                from rich.panel import Panel
                from rich.text import Text
                console = Console()
                use_rich = True
            except ImportError:
                use_rich = False
                console = None
            
            if not available_profiles:
                if use_rich:
                    console.print("[yellow]No profiles found.[/yellow]")
                    if not YAML_AVAILABLE:
                        console.print("[red]YAML support is not available.[/red]")
                        console.print("Please install PyYAML: [cyan]pip install PyYAML[/cyan]")
                    else:
                        console.print(f"Profile directory: [cyan]{PROFILES_DIR}[/cyan]")
                        console.print("Add YAML files (*.yaml or *.yml) to this directory to create profiles.")
                else:
                    print("No profiles found.")
                    if not YAML_AVAILABLE:
                        print("\nYAML support is not available.")
                        print("Please install PyYAML: pip install PyYAML")
                    else:
                        print(f"\nProfile directory: {PROFILES_DIR}")
                        print("Add YAML files (*.yaml or *.yml) to this directory to create profiles.")
                return 0
            
            if use_rich:
                # Create formatted table
                table = Table(title="Available Training Profiles", show_header=True, header_style="bold magenta")
                table.add_column("Profile", style="cyan", no_wrap=True)
                table.add_column("Description", style="green")
                table.add_column("Key Settings", style="blue")
                
                for profile_name in sorted(available_profiles.keys()):
                    try:
                        profile_data = load_profile(profile_name)
                        description = profile_data.get('description', 'N/A')
                        if len(description) > 60:
                            description = description[:57] + "..."
                        
                        # Collect key settings
                        key_settings = []
                        for key in ['model_type', 'source', 'epochs', 'max_books']:
                            if key in profile_data and profile_data[key] is not None:
                                value = profile_data[key]
                                if isinstance(value, list):
                                    value = ', '.join(str(v) for v in value[:2])
                                    if len(profile_data[key]) > 2:
                                        value += f" (+{len(profile_data[key]) - 2} more)"
                                key_settings.append(f"{key}: {value}")
                        
                        settings_str = '\n'.join(key_settings[:3])
                        if len(key_settings) > 3:
                            settings_str += f"\n(+{len(key_settings) - 3} more)"
                        
                        table.add_row(
                            profile_name,
                            description,
                            settings_str or "N/A"
                        )
                    except Exception as e:
                        table.add_row(
                            profile_name,
                            f"[red]Error: {e}[/red]",
                            "N/A"
                        )
                
                console.print()
                console.print(table)
                console.print()
                console.print(Panel(
                    f"[bold]Profile Directory:[/bold] [cyan]{PROFILES_DIR}[/cyan]\n\n"
                    "[bold]Usage:[/bold] [cyan]python scripts/train_neural_text_generator.py --profile <profile_name>[/cyan]\n"
                    "Individual arguments can override profile settings.\n\n"
                    "To create custom profiles, add YAML files to the profile directory.",
                    title="[bold green]Usage[/bold green]",
                    border_style="green"
                ))
            else:
                # Fallback to plain text
                print("Available Training Profiles:")
                print("=" * 80)
                
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
        except Exception as e:
            print(f"Error listing profiles: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

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

    # Import and initialize module only when actually needed (not for --help, --list-sources, --list-profiles)
    global NeuralTextGeneratorModule
    if NeuralTextGeneratorModule is None:
        print("Importing NeuralTextGeneratorModule...", flush=True)
        print("  (This may take a moment if transformers/torch are being imported)", flush=True)
        try:
            from mavaia_core.brain.modules.neural_text_generator import NeuralTextGeneratorModule
            print("Module imported successfully", flush=True)
        except Exception as e:
            print(f"ERROR: Failed to import module: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return 1

    # Initialize module
    print("Initializing neural text generator module...", flush=True)
    generator = NeuralTextGeneratorModule()
    print("Module created, calling initialize()...", flush=True)
    generator.initialize()
    print("Module initialized.", flush=True)

    # Check if we should enter sample-only mode
    # Sample-only mode: --sample is set AND no training arguments are provided
    # Note: We check for explicit training arguments, not defaults
    # If --sample is used alone (no other training args), enter sample-only mode
    has_training_args = any([
        args.epochs != 10,  # User explicitly set epochs (different from default)
        args.train_for_minutes is not None,
        args.train_for_hours is not None,
        args.continue_training,
        args.book_ids is not None,
        args.categories is not None,
        args.source is not None and len(args.source) > 0,  # If source is explicitly set, might be training
        args.max_text_size is not None,
        args.max_books is not None,
        args.data_percentage != 1.0,  # User explicitly set data_percentage
        args.model_name is not None,  # Transformer training
        args.transformer_config is not None,  # Transformer training
    ])
    
    # Note: We check profile after this, but if --sample is used alone, we prioritize sample mode
    
    # If --sample is specified without training arguments, just generate samples
    sample_only = False
    load_result = None
    
    if args.sample and not has_training_args:
        print("Entering sample-only mode...", flush=True)
        # Sample-only mode - load models and generate
        print("=" * 80)
        print("Neural Text Generator - Sample Generation")
        print("=" * 80)
        print("Loading trained models...\n")
        
        # Determine which models to load
        sample_model_type = args.sample_model_type or "both"
        
        print("Attempting to load models (this may take a moment)...")
        print("  Note: Transformer models may take longer to load.\n")
        
        try:
            load_result = generator.execute("load_model", {"model_type": sample_model_type})
        except Exception as e:
            print(f"✗ Error during model loading: {e}")
            print("  This might indicate corrupted model files or missing dependencies.")
            return 1
        
        if not load_result.get("success"):
            print("✗ Failed to load models!")
            print("  Error: Models not found. Train models first with:")
            print("    python scripts/train_neural_text_generator.py --epochs 10")
            return 1
        
        # Show which models loaded
        loaded_models = []
        for model_type, result in load_result.get("results", {}).items():
            if result.get("success"):
                print(f"✓ {model_type} model loaded")
                loaded_models.append(model_type)
            else:
                error_msg = result.get('error', 'Not found')
                # Don't show error for transformer if it's just not available
                if model_type == "transformer" and "not found" in error_msg.lower():
                    print(f"○ {model_type} model: Not available (skip if you only have RNN models)")
                else:
                    print(f"✗ {model_type} model: {error_msg}")
        
        if not loaded_models:
            print("\n✗ No models were successfully loaded!")
            print("  Train models first with: python scripts/train_neural_text_generator.py --epochs 10")
            return 1
        
        print()
        
        # Generate samples (code continues below)
        sample_only = True
    else:
        # Training mode (or sample after training)

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
        
        # Transformer config: handle --model-name and --transformer-config
        transformer_config = None
        if args.transformer_config:
            # Try to load from file first, then parse as JSON string
            config_path = Path(args.transformer_config)
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        transformer_config = json.load(f)
                except Exception as e:
                    print(f"Warning: Failed to load transformer config from file: {e}", file=sys.stderr)
                    # Try parsing as JSON string
                    try:
                        transformer_config = json.loads(args.transformer_config)
                    except:
                        print(f"Error: Failed to parse transformer config: {e}", file=sys.stderr)
                        return 1
            else:
                # Try parsing as JSON string
                try:
                    transformer_config = json.loads(args.transformer_config)
                except Exception as e:
                    print(f"Error: Failed to parse transformer config as JSON: {e}", file=sys.stderr)
                    return 1
        elif "transformer_config" in train_params:
            transformer_config = train_params["transformer_config"]
        
        # Override model_name if provided via --model-name
        if args.model_name:
            if transformer_config is None:
                transformer_config = {}
            transformer_config["model_name"] = args.model_name
        
        # Add transformer_config to train_params if set
        if transformer_config:
            train_params["transformer_config"] = transformer_config
        elif args.model_name:
            # If only model_name is provided, create minimal config
            train_params["model_name"] = args.model_name
        
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
        
        # Resolve run directory and write run metadata early (for reproducibility)
        run_dir = None
        if args.run_dir:
            run_dir = Path(args.run_dir).expanduser()
        else:
            # Default: per-run directory under the module's model folder
            ts = __import__("datetime").datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            run_dir = Path(__file__).parent.parent / "mavaia_core" / "models" / "neural_text_generator" / "runs" / ts
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "checkpoints").mkdir(exist_ok=True)

        # Record latest run pointer (useful for deployment tooling)
        try:
            latest_ptr = Path(__file__).parent.parent / "mavaia_core" / "models" / "neural_text_generator" / "latest_run.txt"
            latest_ptr.write_text(str(run_dir) + "\n", encoding="utf-8")
        except Exception:
            pass

        train_params["run_dir"] = str(run_dir)
        if args.seed is not None:
            train_params["seed"] = int(args.seed)

        # Save a minimal run config + data request manifest
        try:
            import subprocess, platform
            try:
                git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent.parent).decode().strip()
            except Exception:
                git_sha = None

            run_config = {
                "profile": args.profile,
                "git_sha": git_sha,
                "python": sys.version,
                "platform": platform.platform(),
                "train_params": train_params,
            }
            (run_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")

            data_request = {
                "source": train_params.get("source"),
                "book_ids": train_params.get("book_ids"),
                "categories": train_params.get("categories"),
                "max_books": train_params.get("max_books"),
                "max_text_size": train_params.get("max_text_size"),
                "data_percentage": train_params.get("data_percentage"),
                "search": train_params.get("search"),
            }
            (run_dir / "data_request.json").write_text(json.dumps(data_request, indent=2), encoding="utf-8")
        except Exception:
            pass

        # Print training configuration
        # Try to import rich for colored output
        try:
            from rich.console import Console
            from rich.panel import Panel
            console = Console()
            use_rich_config = True
        except ImportError:
            use_rich_config = False
            console = None
        
        if use_rich_config:
            # Build configuration text
            config_lines = []
            if args.profile:
                config_lines.append(f"[bold]Profile:[/bold] [cyan]{args.profile}[/cyan]")
            source_val = train_params.get('source', 'gutenberg')
            if isinstance(source_val, list):
                source_val = ', '.join(source_val)
            config_lines.append(f"[bold]Data source(s):[/bold] [green]{source_val}[/green]")
            config_lines.append(f"[bold]Model type:[/bold] [green]{train_params.get('model_type', 'both')}[/green]")
            if train_params.get("categories"):
                config_lines.append(f"[bold]Categories:[/bold] [green]{', '.join(train_params['categories'])}[/green]")
            if train_params.get("book_ids"):
                book_ids_str = ', '.join(str(bid) for bid in train_params['book_ids'][:3])
                if len(train_params['book_ids']) > 3:
                    book_ids_str += f" (+{len(train_params['book_ids']) - 3} more)"
                config_lines.append(f"[bold]Item IDs:[/bold] [yellow]{book_ids_str}[/yellow]")
            if train_params.get("train_for_hours"):
                config_lines.append(f"[bold]Training time:[/bold] [cyan]{train_params['train_for_hours']} hours[/cyan]")
            elif train_params.get("train_for_minutes"):
                config_lines.append(f"[bold]Training time:[/bold] [cyan]{train_params['train_for_minutes']} minutes[/cyan]")
            elif train_params.get("epochs"):
                config_lines.append(f"[bold]Epochs:[/bold] [cyan]{train_params['epochs']}[/cyan]")
            if train_params.get("max_text_size"):
                config_lines.append(f"[bold]Max text size:[/bold] [cyan]{train_params['max_text_size']:,} characters[/cyan]")
            if train_params.get("max_books"):
                config_lines.append(f"[bold]Max items per source:[/bold] [cyan]{train_params['max_books']}[/cyan]")
            if train_params.get("search"):
                config_lines.append(f"[bold]Search term:[/bold] [yellow]{train_params['search']}[/yellow]")
            if train_params.get("model_name"):
                config_lines.append(f"[bold]Transformer model:[/bold] [green]{train_params['model_name']}[/green]")
            if train_params.get("transformer_config"):
                config = train_params["transformer_config"]
                if isinstance(config, dict) and "model_name" in config:
                    config_lines.append(f"[bold]Transformer model:[/bold] [green]{config['model_name']}[/green]")
            data_pct = train_params.get("data_percentage", 1.0)
            if data_pct < 1.0:
                config_lines.append(f"[bold]Data percentage:[/bold] [cyan]{data_pct*100:.1f}%[/cyan]")
            config_lines.append(f"[bold]Continue training:[/bold] [green]{train_params.get('continue_training', False)}[/green]")
            
            console.print()
            console.print(Panel(
                "\n".join(config_lines),
                title="[bold green]Neural Text Generator Training[/bold green]",
                border_style="green"
            ))
            console.print()
        else:
            # Fallback to plain text
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
            if train_params.get("model_name"):
                print(f"Transformer model: {train_params['model_name']}")
            if train_params.get("transformer_config"):
                config = train_params["transformer_config"]
                if isinstance(config, dict) and "model_name" in config:
                    print(f"Transformer model: {config['model_name']}")
            data_pct = train_params.get("data_percentage", 1.0)
            if data_pct < 1.0:
                print(f"Data percentage: {data_pct*100:.1f}%")
            print(f"Continue training: {train_params.get('continue_training', False)}")
            print()

        # Use rich for training status messages if available
        if use_rich_config:
            console.print("[bold cyan]Starting training...[/bold cyan]")
        else:
            print("Starting training...")
        
        result = generator.execute("train_model", train_params)

        if not result.get("success"):
            error_msg = result.get('error', 'Unknown error')
            if use_rich_config:
                console.print()
                # Format multi-line error messages properly
                error_lines = error_msg.split('\n')
                formatted_error = "[bold red]✗ Training failed![/bold red]\n\n"
                for line in error_lines:
                    if line.strip():
                        # Preserve indentation and formatting
                        if line.startswith('   ') or line.startswith('  '):
                            formatted_error += f"[yellow]{line}[/yellow]\n"
                        elif line.startswith('⚠️') or 'detected' in line.lower():
                            formatted_error += f"[yellow]{line}[/yellow]\n"
                        else:
                            formatted_error += f"[red]{line}[/red]\n"
                    else:
                        formatted_error += "\n"
                
                console.print(Panel(
                    formatted_error.strip(),
                    title="[bold red]Training Error[/bold red]",
                    border_style="red"
                ))
            else:
                print("\n✗ Training failed!")
                print(f"Error: {error_msg}")
            return 1

        if use_rich_config:
            console.print()
            console.print("[bold green]✓ Training completed successfully![/bold green]")
        else:
            print("\n✓ Training completed successfully!")

        # Persist training result metrics alongside artifacts
        try:
            (run_dir / "training_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        except Exception:
            pass
        
        # Save models
        model_type = train_params.get("model_type", "both")
        if use_rich_config:
            console.print("\n[bold cyan]Saving models...[/bold cyan]")
        else:
            print("\nSaving models...")
        
        save_result = generator.execute("save_model", {"model_type": model_type})
        
        if save_result.get("success"):
            if use_rich_config:
                console.print("[bold green]✓ Models saved successfully![/bold green]")
                for model_type, save_info in save_result.get("results", {}).items():
                    if save_info.get("success"):
                        console.print(f"  [green]{model_type}[/green] model: [cyan]{save_info.get('path', 'N/A')}[/cyan]")
            else:
                print("✓ Models saved successfully!")
                for model_type, save_info in save_result.get("results", {}).items():
                    if save_info.get("success"):
                        print(f"  {model_type} model: {save_info.get('path', 'N/A')}")
        else:
            if use_rich_config:
                console.print("[bold red]✗ Failed to save models[/bold red]")
                console.print(f"  [red]Error: {save_result.get('error', 'Unknown error')}[/red]")
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
            if load_result and "results" in load_result:
                for model_type, result in load_result.get("results", {}).items():
                    if result.get("success"):
                        model_types_to_test.append(model_type)
            # Also check sample_model_type if specified
            if args.sample_model_type:
                # If specific model type requested, only use that if it loaded successfully
                if args.sample_model_type in model_types_to_test:
                    model_types_to_test = [args.sample_model_type]
                elif args.sample_model_type == "both":
                    # "both" means use all available models
                    pass
                else:
                    # Try to load the specified model type if not already loaded
                    if load_result is None or not any(
                        r.get("success") for r in load_result.get("results", {}).values()
                    ):
                        load_result = generator.execute("load_model", {"model_type": args.sample_model_type})
                        if load_result.get("success"):
                            model_types_to_test = []
                            for model_type, result in load_result.get("results", {}).items():
                                if result.get("success"):
                                    model_types_to_test.append(model_type)
            if not model_types_to_test:
                print("✗ No models available for sampling")
                print("  Train models first with: python scripts/train_neural_text_generator.py --epochs 10")
                return 1
        else:
            model_types_to_test = []
            resolved_model_type = train_params.get("model_type", "both")
            if resolved_model_type in ["character", "both"]:
                model_types_to_test.append("character")
            if resolved_model_type in ["word", "both"]:
                model_types_to_test.append("word")
            if resolved_model_type in ["transformer", "both"]:
                model_types_to_test.append("transformer")
            
            if not model_types_to_test:
                model_types_to_test = ["character"]  # Default fallback
        
        sample_log_lines = []
        for model_type in model_types_to_test:
            header = f"\n--- {model_type.upper()} Model Samples ---\n"
            print(header)
            sample_log_lines.append(header)
            
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
                print("  Generating...", end="", flush=True)
                
                try:
                    gen_result = generator.execute(
                        "generate_text",
                        {
                            "prompt": prompt,
                            "model_type": model_type,
                            "max_length": max_length,
                            "temperature": temperature,
                        },
                    )
                    print(" ✓")  # Success indicator
                except Exception as e:
                    print(f" ✗ Error: {e}")
                    gen_result = {"success": False, "error": str(e)}
                
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

