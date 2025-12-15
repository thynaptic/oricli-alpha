---
name: Multi-source data pipeline
overview: Add support for multiple data sources (Wikipedia, LibriVox, OpenLibrary) to the neural text generator while maintaining full compatibility with all existing arguments. Implement a flexible source selection system that supports both single and multiple sources.
todos:
  - id: "1"
    content: Create BaseDataSource abstract class and DataSourceRegistry in neural_text_generator_data.py
    status: completed
  - id: "2"
    content: Refactor existing Gutenberg code into GutenbergSource class implementing BaseDataSource
    status: completed
    dependencies:
      - "1"
  - id: "3"
    content: Implement WikipediaSource class with Wikipedia API integration
    status: completed
    dependencies:
      - "1"
  - id: "4"
    content: Implement LibriVoxSource class with LibriVox catalog access
    status: completed
    dependencies:
      - "1"
  - id: "5"
    content: Implement OpenLibrarySource class with OpenLibrary/Internet Archive integration
    status: completed
    dependencies:
      - "1"
  - id: "6"
    content: Update NeuralTextGeneratorData to use DataSourceRegistry and support source parameter
    status: completed
    dependencies:
      - "1"
      - "2"
      - "3"
      - "4"
      - "5"
  - id: "7"
    content: Update neural_text_generator.py to accept and pass source parameter in _train_model()
    status: completed
    dependencies:
      - "6"
  - id: "8"
    content: Add --source and --list-sources arguments to train_neural_text_generator.py script
    status: completed
    dependencies:
      - "7"
  - id: "9"
    content: Test all sources independently with all argument combinations
    status: completed
    dependencies:
      - "8"
  - id: "10"
    content: Test multiple sources combined in single training run
    status: completed
    dependencies:
      - "8"
  - id: "11"
    content: Update documentation and help text for new source options
    status: completed
    dependencies:
      - "8"
---

# Multi-Source Data Pipeline Implementation Plan

## Overview

Enhance the neural text generator to support multiple data sources beyond Project Gutenberg. The implementation will maintain full backward compatibility and ensure all existing arguments work with every data source.

## Architecture Changes

### 1. Data Source Abstraction Layer

Create a base interface for data sources in `mavaia_core/brain/modules/neural_text_generator_data.py`:

- **BaseDataSource** abstract class with methods:
- `load_data(book_ids, categories, max_books, max_text_size) -> str`
- `get_available_categories() -> List[str]`
- `get_source_name() -> str`
- `supports_categories() -> bool`
- `supports_book_ids() -> bool`

### 2. Implement Data Sources

#### 2.1 GutenbergSource (refactor existing)

- Refactor `load_gutenberg_data()` into `GutenbergSource` class
- Maintain all existing functionality
- Keep as default source

#### 2.2 WikipediaSource

- Use Wikipedia API (wikipedia library or direct API calls)
- Support categories via Wikipedia categories/portals
- Support article selection via article titles (similar to book_ids)
- Handle rate limiting and API quotas
- Cache downloaded articles

#### 2.3 LibriVoxSource

- Access LibriVox catalog via API or web scraping
- Support categories via LibriVox collections/genres
- Support book selection via LibriVox book IDs
- Download text transcripts (if available) or extract from audiobook metadata
- Cache downloaded content

#### 2.4 OpenLibrarySource

- Use OpenLibrary API (openlibrary.org)
- Support categories via OpenLibrary subjects/genres
- Support book selection via OpenLibrary work IDs or ISBNs
- Download full text from Internet Archive when available
- Handle different book formats (EPUB, PDF, plain text)

### 3. Data Source Registry

Create a `DataSourceRegistry` class to:

- Register all available sources
- Provide source discovery
- Handle source selection logic
- Support single or multiple sources

### 4. Unified Data Loading Interface

Modify `NeuralTextGeneratorData` class to:

- Accept `source` parameter (single string or list of strings)
- Route to appropriate source(s)
- Combine data from multiple sources when multiple sources specified
- Maintain backward compatibility (default to "gutenberg" if not specified)

### 5. Command-Line Integration

Update `scripts/train_neural_text_generator.py`:

- Add `--source` argument that accepts one or more source names
- Add `--list-sources` argument to show available sources
- Update help text to document source options
- Pass source parameter through to module

### 6. Module Integration

Update `mavaia_core/brain/modules/neural_text_generator.py`:

- Accept `source` parameter in `_train_model()` method
- Pass source to data loading functions
- Update docstrings to document source parameter

## Implementation Details

### File Changes

1. **`mavaia_core/brain/modules/neural_text_generator_data.py`**

- Add `BaseDataSource` abstract class
- Refactor existing Gutenberg code into `GutenbergSource` class
- Add `WikipediaSource` class
- Add `LibriVoxSource` class
- Add `OpenLibrarySource` class
- Add `DataSourceRegistry` class
- Update `NeuralTextGeneratorData` to use registry
- Maintain backward compatibility

2. **`mavaia_core/brain/modules/neural_text_generator.py`**

- Update `_train_model()` to accept and pass `source` parameter
- Update docstrings

3. **`scripts/train_neural_text_generator.py`**

- Add `--source` argument (accepts multiple values)
- Add `--list-sources` argument
- Pass source to training parameters

### Source-Specific Considerations

**Wikipedia:**

- Use `wikipedia` Python library or direct API
- Map categories to Wikipedia categories/portals
- Support article selection via titles
- Handle disambiguation pages
- Cache articles to avoid repeated API calls

**LibriVox:**

- Use LibriVox API or web scraping
- Map categories to LibriVox collections
- Support book selection via LibriVox IDs
- Download text transcripts when available
- Handle cases where only audio is available

**OpenLibrary:**

- Use OpenLibrary API
- Map categories to OpenLibrary subjects
- Support work IDs, ISBNs, or book titles
- Download from Internet Archive when available
- Handle different formats (prefer plain text)

### Argument Compatibility Matrix

All existing arguments must work with all sources:

| Argument | Gutenberg | Wikipedia | LibriVox | OpenLibrary |
|----------|-----------|-----------|----------|-------------|
| `book_ids` | ✅ Book IDs | ✅ Article titles | ✅ LibriVox IDs | ✅ Work IDs/ISBNs |
| `categories` | ✅ Genre categories | ✅ Wikipedia categories | ✅ LibriVox collections | ✅ OpenLibrary subjects |
| `max_books` | ✅ | ✅ (max articles) | ✅ | ✅ |
| `max_text_size` | ✅ | ✅ | ✅ | ✅ |
| `data_percentage` | ✅ | ✅ | ✅ | ✅ |

### Error Handling

- Graceful fallback if a source is unavailable
- Clear error messages for unsupported argument combinations
- Logging for source-specific issues
- Continue with available sources if one fails

### Caching Strategy

- Each source caches to its own subdirectory
- Cache structure: `data/{source_name}/`
- Cache format: plain text files with metadata
- Cache invalidation: configurable (default: never, or by date)

## Testing Strategy

- Test each source independently
- Test multiple sources combined
- Test all argument combinations with each source
- Test error handling and fallbacks
- Test caching behavior
- Verify backward compatibility (no source specified = Gutenberg)

## Documentation Updates

- Update module docstrings
- Update training script help text
- Add source-specific usage examples
- Document source limitations and requirements
- Update README files

## Dependencies

- `wikipedia` library (optional, for Wikipedia source)
- `requests` (already used)
- Consider `internetarchive` library for OpenLibrary

## Migration Path

- Default behavior unchanged (Gutenberg if no source specified)
- Existing scripts continue to work
- New `--source` argument is optional
- Gradual migration as users adopt new sources