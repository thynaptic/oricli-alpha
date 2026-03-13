# API Keys Configuration

This directory can store API keys for various data sources used by the neural text generator.

## Setup

1. Copy the example file:
   ```bash
   cp api_keys.json.example api_keys.json
   ```

2. Edit `api_keys.json` and fill in your API keys:
   ```json
   {
     "huggingface": {
       "token": "your_hf_token_here"
     }
   }
   ```

## Environment Variables (Alternative)

You can also set API keys via environment variables (recommended for production):

```bash
# HuggingFace
export MAVAIA_HUGGINGFACE_TOKEN="your_token_here"
# or use the standard HF variable
export HF_TOKEN="your_token_here"

# Internet Archive (optional)
export MAVAIA_IA_ACCESS_KEY="your_access_key"
export MAVAIA_IA_SECRET_KEY="your_secret_key"
```

## Security

- The `api_keys.json` file is gitignored and will not be committed to version control
- Environment variables are preferred for production deployments
- Never commit API keys to version control

## Getting API Keys

- **HuggingFace**: Get your token from https://huggingface.co/settings/tokens
- **Internet Archive**: Optional, get credentials from https://archive.org/account/s3.php

## Usage

The neural text generator will automatically load API keys from:
1. Environment variables (highest priority)
2. `api_keys.json` file (if exists)
3. Default to public access (for public datasets)

