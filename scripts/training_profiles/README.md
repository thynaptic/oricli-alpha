# Training Profiles

This directory contains YAML configuration files for training profiles. Each profile defines a set of training parameters that can be used with the `--profile` option.

## Usage

To use a profile:
```bash
python scripts/train_neural_text_generator.py --profile <profile_name>
```

To list all available profiles:
```bash
python scripts/train_neural_text_generator.py --list-profiles
```

## Profile Format

Each profile is a YAML file with the following structure:

```yaml
# Profile description (shown in --list-profiles)
description: "Description of what this profile does"

# Data source(s) to use (optional, defaults to "gutenberg")
# Can be a single source string or list of sources
source: wikipedia
# Or multiple sources:
source:
  - gutenberg
  - wikipedia

# Book categories to load (list of strings)
categories:
  - fiction
  - classic
  - technical

# Number of training epochs
epochs: 10

# Maximum number of books/items to load per source
max_books: 5

# Maximum text size in characters (use null for no limit)
max_text_size: 150000

# Percentage of data to use (0.0 to 1.0)
data_percentage: 0.7

# Model type: "character", "word", or "both"
model_type: both

# Search term for HuggingFace (optional, HuggingFace source only)
# Used to search HuggingFace Hub for datasets matching the term
search: "chatgpt OR claude OR conversation"
```

## Available Data Sources

- `gutenberg`: Project Gutenberg books (default)
- `wikipedia`: Wikipedia articles
- `librivox`: LibriVox audiobooks
- `openlibrary`: OpenLibrary/Internet Archive books
- `internetarchive`: Internet Archive items (uses `internetarchive` Python library)
- `huggingface`: HuggingFace datasets (uses `datasets` Python library)

You can specify multiple sources in a list to combine data from different sources.

**Note**: Some sources require additional libraries:
- `internetarchive`: `pip install internetarchive` or `pipx install internetarchive`
- `huggingface`: `pip install datasets huggingface_hub`

**API Keys**: For HuggingFace private datasets, set `HF_TOKEN` or `MAVAIA_HUGGINGFACE_TOKEN` environment variable, or add to `mavaia_core/data/api_keys.json` (see `api_keys.json.example` for format).

## Available Categories

- `fiction`
- `non_fiction`
- `technical`
- `philosophy`
- `poetry`
- `drama`
- `adventure`
- `mystery`
- `science_fiction`
- `classic`

## Creating Custom Profiles

1. Create a new YAML file in this directory (e.g., `my_profile.yaml`)
2. Use the format shown above
3. The profile name will be the filename without the `.yaml` extension
4. Run `--list-profiles` to verify your profile is discovered

## Overriding Profile Settings

You can override any profile setting using command-line arguments:

```bash
# Use 'fast' profile but override epochs
python scripts/train_neural_text_generator.py --profile fast --epochs 20

# Use 'tech' profile but override categories
python scripts/train_neural_text_generator.py --profile tech --categories fiction classic

# Use 'wikipedia' profile but override source
python scripts/train_neural_text_generator.py --profile wikipedia --source gutenberg

# Use 'multi_source' profile but add more sources
python scripts/train_neural_text_generator.py --profile multi_source --source gutenberg wikipedia librivox
```

Command-line arguments always take precedence over profile settings.

## Examples with New Data Sources

```bash
# Train with Wikipedia articles
python scripts/train_neural_text_generator.py --profile wikipedia

# Quick Wikipedia training
python scripts/train_neural_text_generator.py --profile wikipedia_fast

# Combine Gutenberg and Wikipedia
python scripts/train_neural_text_generator.py --profile gutenberg_wikipedia

# Use all available sources
python scripts/train_neural_text_generator.py --profile all_sources

# Wikipedia with specific articles
python scripts/train_neural_text_generator.py --profile wikipedia --book-ids "Artificial intelligence" "Machine learning"
```

## Default Profiles

The following profiles are included by default:

### Gutenberg Profiles (Classic)
- **fast**: Quick training with limited data for rapid iteration
- **tech**: Technical content focused training
- **comprehensive**: Comprehensive training with maximum data
- **classic**: Classic literature focused training
- **fiction**: Fiction and narrative focused training
- **balanced**: Balanced mix of content types for general purpose

### Wikipedia Profiles (Modern & Diverse)
- **wikipedia**: Train on Wikipedia articles for diverse, modern content
- **wikipedia_fast**: Quick Wikipedia training for rapid iteration
- **wikipedia_tech**: Technical Wikipedia articles focused training
- **wikipedia_literature**: Wikipedia articles focused on literature and fiction
- **wikipedia_comprehensive**: Comprehensive Wikipedia training with maximum articles

### Multi-Source Profiles
- **multi_source**: Train on multiple data sources (Gutenberg + Wikipedia) for diverse content
- **gutenberg_wikipedia**: Combine classic literature (Gutenberg) with modern content (Wikipedia)
- **all_sources**: Train on all available data sources for maximum diversity

### Internet Archive Profiles (8 profiles)
- **internetarchive**: Train on Internet Archive items for diverse public domain content
- **internetarchive_fast**: Quick Internet Archive training for rapid iteration
- **internetarchive_tech**: Technical Internet Archive items focused training
- **internetarchive_literature**: Internet Archive items focused on literature and fiction
- **internetarchive_classic**: Classic literature and timeless works from Internet Archive
- **internetarchive_philosophy**: Philosophical works and intellectual content from Internet Archive
- **internetarchive_adventure**: Adventure stories, mysteries, and thrilling narratives from Internet Archive
- **internetarchive_poetry**: Poetry collections and verse from Internet Archive
- **internetarchive_science**: Science, technology, and technical content from Internet Archive
- **internetarchive_comprehensive**: Comprehensive Internet Archive training with maximum items across all categories

### HuggingFace Profiles (6 profiles)
- **huggingface**: Train on HuggingFace datasets for diverse content
- **huggingface_fast**: Quick HuggingFace training for rapid iteration
- **huggingface_tech**: Technical datasets from HuggingFace
- **huggingface_literature**: Literature and fiction datasets from HuggingFace
- **huggingface_conversations**: ChatGPT and Claude conversation datasets from HuggingFace
- **huggingface_comprehensive**: Comprehensive HuggingFace training with maximum datasets

### Other Sources
- **openlibrary**: Train on OpenLibrary/Internet Archive books for diverse literature
