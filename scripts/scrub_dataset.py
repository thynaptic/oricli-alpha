#!/usr/bin/env python3
"""
Dataset Scrubber - Comprehensive dataset cleaning and normalization tool

Removes duplicates, templates, low-quality samples, and normalizes datasets
for optimal training performance.
"""

import json
import sys
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
import argparse

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

try:
    from difflib import SequenceMatcher
    SIMILARITY_AVAILABLE = True
except ImportError:
    SIMILARITY_AVAILABLE = False


class DatasetScrubber:
    """Comprehensive dataset cleaning and normalization"""
    
    def __init__(self, input_file: Path, output_file: Optional[Path] = None, verbose: bool = True):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file) if output_file else self.input_file.parent / f"{self.input_file.stem}_scrubbed{self.input_file.suffix}"
        self.verbose = verbose
        self.stats = {
            "total_input": 0,
            "duplicates_exact": 0,
            "duplicates_near": 0,
            "templates_removed": 0,
            "too_short": 0,
            "too_long": 0,
            "low_diversity": 0,
            "invalid_fields": 0,
            "formatting_fixed": 0,
            "final_size": 0,
            "token_diversity_before": 0.0,
            "token_diversity_after": 0.0,
        }
        
        if RICH_AVAILABLE:
            self.console = Console(stderr=True)
        else:
            self.console = None
    
    def _print(self, message: str, style: str = ""):
        """Print message with optional Rich styling"""
        if self.console and RICH_AVAILABLE:
            if style:
                self.console.print(message, style=style)
            else:
                self.console.print(message)
        else:
            print(message, file=sys.stderr)
    
    def _get_text_content(self, item: Dict[str, Any]) -> str:
        """Extract text content from various field names"""
        # Try common field names
        for field in ["text", "input", "prompt", "content", "output", "response", "message"]:
            if field in item and item[field]:
                text = item[field]
                if isinstance(text, str):
                    return text
                elif isinstance(text, list):
                    return " ".join(str(t) for t in text)
        
        # Try nested structures
        if "data" in item and isinstance(item["data"], dict):
            return self._get_text_content(item["data"])
        
        # Fallback: concatenate all string values
        text_parts = []
        for value in item.values():
            if isinstance(value, str) and len(value) > 10:  # Skip short metadata
                text_parts.append(value)
        
        return " ".join(text_parts) if text_parts else ""
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization (split on whitespace)"""
        return text.lower().split()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts"""
        if SIMILARITY_AVAILABLE:
            return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        else:
            # Simple word overlap ratio
            tokens1 = set(self._tokenize(text1))
            tokens2 = set(self._tokenize(text2))
            if not tokens1 or not tokens2:
                return 0.0
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            return intersection / union if union > 0 else 0.0
    
    def _hash_text(self, text: str) -> str:
        """Create hash of text for duplicate detection"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _is_template(self, text: str, templates: List[str]) -> bool:
        """Check if text matches a known template pattern"""
        text_lower = text.lower().strip()
        
        # Common template patterns
        template_patterns = [
            r"^this is a (thoughtful|detailed|comprehensive) (response|answer|explanation) (about|regarding|on)",
            r"^let me (elaborate|explain|clarify) (on|about) this (topic|subject|matter)",
            r"^this (recursive|iterative|function|method|algorithm) (calculates|computes|determines)",
            r"^in (this|order|summary|conclusion)",
            r"^to (answer|address|solve|handle) (this|your) (question|problem|issue)",
            r"^here (is|are) (a|some|the) (detailed|comprehensive|thorough)",
            r"^i (would|will|can) (like|be happy) to (help|assist|explain)",
        ]
        
        # Check against patterns
        for pattern in template_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Check against known templates
        for template in templates:
            similarity = self._calculate_similarity(text, template)
            if similarity > 0.85:  # 85% similar to known template
                return True
        
        return False
    
    def _calculate_token_diversity(self, text: str) -> Tuple[float, float, float]:
        """Calculate token diversity metrics"""
        tokens = self._tokenize(text)
        if not tokens:
            return 0.0, 1.0, 0.0
        
        total_tokens = len(tokens)
        unique_tokens = len(set(tokens))
        unique_ratio = unique_tokens / total_tokens if total_tokens > 0 else 0.0
        
        # Repetition rate (most common tokens)
        token_counts = Counter(tokens)
        most_common_count = sum(count for _, count in token_counts.most_common(10))
        repetition_rate = most_common_count / total_tokens if total_tokens > 0 else 0.0
        
        # N-gram diversity (bigrams)
        if len(tokens) >= 2:
            bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
            unique_bigrams = len(set(bigrams))
            bigram_diversity = unique_bigrams / len(bigrams) if bigrams else 0.0
        else:
            bigram_diversity = 0.0
        
        return unique_ratio, repetition_rate, bigram_diversity
    
    def _validate_fields(self, item: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate required fields are present and valid"""
        errors = []
        
        # Check for id
        if "id" not in item or not item["id"]:
            errors.append("missing_id")
        
        # Check for text content
        text = self._get_text_content(item)
        if not text or len(text.strip()) < 1:
            errors.append("missing_text")
        
        # Check for null values
        for key, value in item.items():
            if value is None:
                errors.append(f"null_value_{key}")
        
        # Check for empty strings in important fields
        for field in ["text", "input", "prompt", "output", "response"]:
            if field in item and item[field] == "":
                errors.append(f"empty_{field}")
        
        return len(errors) == 0, errors
    
    def _sanitize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and fix common issues in an item"""
        fixed = 0
        sanitized = {}
        
        for key, value in item.items():
            if isinstance(value, str):
                # Fix newlines
                original = value
                value = value.replace('\r\n', '\n').replace('\r', '\n')
                if value != original:
                    fixed += 1
                
                # Strip whitespace
                value = value.strip()
                
                # Ensure UTF-8
                try:
                    value.encode('utf-8')
                except UnicodeEncodeError:
                    value = value.encode('utf-8', errors='ignore').decode('utf-8')
                    fixed += 1
                
                sanitized[key] = value
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = self._sanitize_item(value)
            elif isinstance(value, list):
                # Sanitize list items
                sanitized[key] = [
                    self._sanitize_item(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                sanitized[key] = value
        
        self.stats["formatting_fixed"] += fixed
        return sanitized
    
    def _normalize_length(self, text: str, min_tokens: int = 4, max_tokens: int = 10000) -> Optional[str]:
        """Normalize text length"""
        tokens = self._tokenize(text)
        token_count = len(tokens)
        
        if token_count < min_tokens:
            self.stats["too_short"] += 1
            return None
        
        if token_count > max_tokens:
            # Truncate to max_tokens
            tokens = tokens[:max_tokens]
            self.stats["too_long"] += 1
            return " ".join(tokens)
        
        return text
    
    def scrub(self) -> Dict[str, Any]:
        """Main scrubbing function"""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        self._print(f"[bold cyan]Dataset Scrubber[/bold cyan]")
        self._print(f"Input: {self.input_file}")
        self._print(f"Output: {self.output_file}\n")
        
        # Load dataset
        self._print("Loading dataset...")
        items = []
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        items.append(item)
                    except json.JSONDecodeError as e:
                        self._print(f"[yellow]Warning:[/yellow] Invalid JSON on line {line_num}: {e}", style="yellow")
                        continue
        except Exception as e:
            raise ValueError(f"Failed to load dataset: {e}")
        
        self.stats["total_input"] = len(items)
        self._print(f"Loaded {len(items):,} items\n")
        
        # Calculate initial token diversity
        if items:
            all_text = " ".join(self._get_text_content(item) for item in items[:1000])  # Sample
            _, _, _ = self._calculate_token_diversity(all_text)
            self.stats["token_diversity_before"] = self._calculate_token_diversity(all_text)[0]
        
        # Progress tracking
        if RICH_AVAILABLE and self.verbose:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            )
            progress.start()
            task = progress.add_task("Scrubbing dataset...", total=len(items))
        else:
            progress = None
            task = None
        
        # Step 1: Sanitize all items
        self._print("\n[bold]Step 1:[/bold] Sanitizing items...")
        sanitized_items = []
        for i, item in enumerate(items):
            sanitized = self._sanitize_item(item)
            sanitized_items.append(sanitized)
            if progress:
                progress.update(task, completed=i + 1)
        
        items = sanitized_items
        
        # Step 2: Deduplication
        self._print("\n[bold]Step 2:[/bold] Removing duplicates...")
        seen_hashes = set()
        seen_texts = []
        deduplicated = []
        
        for i, item in enumerate(items):
            text = self._get_text_content(item)
            text_hash = self._hash_text(text)
            
            # Exact duplicate
            if text_hash in seen_hashes:
                self.stats["duplicates_exact"] += 1
                if progress:
                    progress.update(task, completed=i + 1)
                continue
            
            # Near-duplicate check (>90% similar)
            is_duplicate = False
            for seen_text in seen_texts[-100:]:  # Check last 100 for performance
                similarity = self._calculate_similarity(text, seen_text)
                if similarity > 0.90:
                    self.stats["duplicates_near"] += 1
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_hashes.add(text_hash)
                seen_texts.append(text)
                deduplicated.append(item)
            
            if progress:
                progress.update(task, completed=i + 1)
        
        items = deduplicated
        
        # Step 3: Template detection
        self._print("\n[bold]Step 3:[/bold] Removing template responses...")
        templates = []
        no_templates = []
        
        for i, item in enumerate(items):
            text = self._get_text_content(item)
            if self._is_template(text, templates):
                self.stats["templates_removed"] += 1
            else:
                no_templates.append(item)
                # Add to templates if it's a common pattern
                if len(templates) < 50:  # Keep track of common templates
                    templates.append(text[:200])  # Store prefix for comparison
            
            if progress:
                progress.update(task, completed=i + 1)
        
        items = no_templates
        
        # Step 4: Length normalization
        self._print("\n[bold]Step 4:[/bold] Normalizing lengths...")
        normalized = []
        
        for i, item in enumerate(items):
            text = self._get_text_content(item)
            normalized_text = self._normalize_length(text)
            
            if normalized_text is None:  # Too short, skip
                if progress:
                    progress.update(task, completed=i + 1)
                continue
            
            # Update text in item
            for field in ["text", "input", "prompt", "output", "response"]:
                if field in item:
                    item[field] = normalized_text
                    break
            else:
                # Add to first available text field
                item["text"] = normalized_text
            
            normalized.append(item)
            if progress:
                progress.update(task, completed=i + 1)
        
        items = normalized
        
        # Step 5: Token diversity check
        self._print("\n[bold]Step 5:[/bold] Checking token diversity...")
        diverse_items = []
        
        for i, item in enumerate(items):
            text = self._get_text_content(item)
            unique_ratio, repetition_rate, bigram_diversity = self._calculate_token_diversity(text)
            
            # Low diversity threshold
            if unique_ratio < 0.1 or repetition_rate > 0.8 or bigram_diversity < 0.05:
                self.stats["low_diversity"] += 1
            else:
                diverse_items.append(item)
            
            if progress:
                progress.update(task, completed=i + 1)
        
        items = diverse_items
        
        # Step 6: Field validation
        self._print("\n[bold]Step 6:[/bold] Validating fields...")
        valid_items = []
        
        for i, item in enumerate(items):
            is_valid, errors = self._validate_fields(item)
            if not is_valid:
                self.stats["invalid_fields"] += 1
            else:
                valid_items.append(item)
            
            if progress:
                progress.update(task, completed=i + 1)
        
        items = valid_items
        
        # Step 7: Balance enforcement (topic/type distribution)
        self._print("\n[bold]Step 7:[/bold] Enforcing balance...")
        balanced_items = self._enforce_balance(items)
        
        if progress:
            progress.stop()
        
        items = balanced_items
        
        # Calculate final token diversity
        if items:
            all_text = " ".join(self._get_text_content(item) for item in items[:1000])  # Sample
            self.stats["token_diversity_after"] = self._calculate_token_diversity(all_text)[0]
        
        # Save scrubbed dataset
        self._print(f"\n[bold]Saving scrubbed dataset...[/bold]")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        self.stats["final_size"] = len(items)
        
        return self.stats
    
    def _enforce_balance(self, items: List[Dict[str, Any]], max_per_topic: int = 10000) -> List[Dict[str, Any]]:
        """Enforce balance across topics/types"""
        # Group by topic/type if metadata exists
        topic_groups = defaultdict(list)
        
        for item in items:
            topic = "unknown"
            if "metadata" in item and isinstance(item["metadata"], dict):
                topic = item["metadata"].get("topic", item["metadata"].get("type", "unknown"))
            elif "topic" in item:
                topic = item["topic"]
            elif "type" in item:
                topic = item["type"]
            
            topic_groups[topic].append(item)
        
        # Limit each topic to max_per_topic
        balanced = []
        for topic, topic_items in topic_groups.items():
            if len(topic_items) > max_per_topic:
                # Randomly sample to balance
                import random
                balanced.extend(random.sample(topic_items, max_per_topic))
            else:
                balanced.extend(topic_items)
        
        return balanced
    
    def print_summary(self):
        """Print scrubbing summary"""
        stats = self.stats
        
        if RICH_AVAILABLE:
            table = Table(title="Dataset Scrubbing Summary", show_header=True, header_style="bold cyan")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green", justify="right")
            
            table.add_row("Total input items", f"{stats['total_input']:,}")
            table.add_row("Exact duplicates removed", f"{stats['duplicates_exact']:,}")
            table.add_row("Near-duplicates removed", f"{stats['duplicates_near']:,}")
            table.add_row("Templates removed", f"{stats['templates_removed']:,}")
            table.add_row("Too short removed", f"{stats['too_short']:,}")
            table.add_row("Too long truncated", f"{stats['too_long']:,}")
            table.add_row("Low diversity removed", f"{stats['low_diversity']:,}")
            table.add_row("Invalid fields removed", f"{stats['invalid_fields']:,}")
            table.add_row("Formatting issues fixed", f"{stats['formatting_fixed']:,}")
            table.add_row("", "")  # Separator
            table.add_row("[bold]Final size[/bold]", f"[bold green]{stats['final_size']:,}[/bold green]")
            
            diversity_improvement = stats['token_diversity_after'] - stats['token_diversity_before']
            diversity_pct = (diversity_improvement / stats['token_diversity_before'] * 100) if stats['token_diversity_before'] > 0 else 0
            table.add_row("[bold]Token diversity improved[/bold]", f"[bold green]+{diversity_pct:.1f}%[/bold green]")
            
            self.console.print(table)
        else:
            print("\n" + "="*60, file=sys.stderr)
            print("Dataset Scrubbing Summary", file=sys.stderr)
            print("="*60, file=sys.stderr)
            print(f"Total input items: {stats['total_input']:,}", file=sys.stderr)
            print(f"Exact duplicates removed: {stats['duplicates_exact']:,}", file=sys.stderr)
            print(f"Near-duplicates removed: {stats['duplicates_near']:,}", file=sys.stderr)
            print(f"Templates removed: {stats['templates_removed']:,}", file=sys.stderr)
            print(f"Too short removed: {stats['too_short']:,}", file=sys.stderr)
            print(f"Too long truncated: {stats['too_long']:,}", file=sys.stderr)
            print(f"Low diversity removed: {stats['low_diversity']:,}", file=sys.stderr)
            print(f"Invalid fields removed: {stats['invalid_fields']:,}", file=sys.stderr)
            print(f"Formatting issues fixed: {stats['formatting_fixed']:,}", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"Final size: {stats['final_size']:,} lines", file=sys.stderr)
            
            diversity_improvement = stats['token_diversity_after'] - stats['token_diversity_before']
            diversity_pct = (diversity_improvement / stats['token_diversity_before'] * 100) if stats['token_diversity_before'] > 0 else 0
            print(f"Token diversity improved: +{diversity_pct:.1f}%", file=sys.stderr)
            print("="*60 + "\n", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Scrub and normalize datasets for training",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Input dataset file (JSONL format)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: input_file_scrubbed.jsonl)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="Show verbose output"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode (suppress verbose output)"
    )
    
    args = parser.parse_args()
    
    if args.quiet:
        args.verbose = False
    
    scrubber = DatasetScrubber(
        input_file=Path(args.input_file),
        output_file=Path(args.output) if args.output else None,
        verbose=args.verbose
    )
    
    try:
        stats = scrubber.scrub()
        scrubber.print_summary()
        
        # Print summary in requested format
        print(f"\nFound duplicates: {stats['duplicates_exact'] + stats['duplicates_near']:,}")
        print(f"Fixed formatting issues: {stats['formatting_fixed']:,}")
        print(f"Removed low-quality samples: {stats['templates_removed'] + stats['too_short'] + stats['low_diversity'] + stats['invalid_fields']:,}")
        print(f"Normalized dataset → final size: {stats['final_size']:,} lines")
        
        diversity_improvement = stats['token_diversity_after'] - stats['token_diversity_before']
        diversity_pct = (diversity_improvement / stats['token_diversity_before'] * 100) if stats['token_diversity_before'] > 0 else 0
        print(f"Token diversity improved: +{diversity_pct:.1f}%")
        
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
