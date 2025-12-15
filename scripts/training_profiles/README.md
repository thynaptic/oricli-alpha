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

# Book categories to load (list of strings)
categories:
  - fiction
  - classic
  - technical

# Number of training epochs
epochs: 10

# Maximum number of books to load
max_books: 5

# Maximum text size in characters (use null for no limit)
max_text_size: 150000

# Percentage of data to use (0.0 to 1.0)
data_percentage: 0.7

# Model type: "character", "word", or "both"
model_type: both
```

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
```

Command-line arguments always take precedence over profile settings.

## Default Profiles

The following profiles are included by default:

- **fast**: Quick training with limited data for rapid iteration
- **tech**: Technical content focused training
- **comprehensive**: Comprehensive training with maximum data
- **classic**: Classic literature focused training
- **fiction**: Fiction and narrative focused training
- **balanced**: Balanced mix of content types for general purpose
