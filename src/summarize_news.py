#!/usr/bin/env python3
"""
NoBS News Summarizer - CLI Tool

Generate AI-powered news digests from the JSON news data.

Usage:
    python src/summarize_news.py --input data/news_source.txt --output data/news_digest.md
    python src/summarize_news.py  # Uses default paths
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from news_categorizer import categorize_articles, deduplicate_by_category, get_duplicate_count
from news_summarizer import NewsSummarizer
from dataclasses import dataclass


@dataclass
class SimpleArticle:
    """Simple article representation for JSON loading."""
    title: str
    link: str
    published: str
    summary: str


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the application.

    Args:
        verbose: Enable debug logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def load_articles_from_json(json_path: str) -> List[SimpleArticle]:
    """
    Load articles from JSON file.

    Args:
        json_path: Path to JSON file

    Returns:
        List of SimpleArticle objects
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = [
        SimpleArticle(
            title=item['title'],
            link=item['link'],
            published=item['published'],
            summary=item['summary']
        )
        for item in data
    ]

    return articles


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate AI-powered news digest from NoBS news data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with defaults
  python src/summarize_news.py

  # Custom input/output paths
  python src/summarize_news.py --input data/news_source.txt --output data/digest.md

  # Use different LLM model
  python src/summarize_news.py --model openrouter/openai/gpt-4o

  # Verbose output for debugging
  python src/summarize_news.py --verbose
        """
    )

    parser.add_argument(
        '--input', '-i',
        default=None,
        help='Input JSON file path (default: data/news_source.txt)'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output Markdown file path (default: data/news_digest_YYYY-MM-DD.md)'
    )
    parser.add_argument(
        '--model', '-m',
        default=None,
        help=f'LLM model to use (default: {Config.LLM_MODEL})'
    )
    parser.add_argument(
        '--max-articles',
        type=int,
        default=None,
        help=f'Max articles per category (default: {Config.MAX_ARTICLES_PER_CATEGORY})'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bars'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Determine paths
    if args.input:
        input_path = Path(args.input)
    else:
        # Use project root relative path
        project_root = Path(__file__).parent.parent
        input_path = project_root / 'data' / 'news_source.txt'

    if args.output:
        output_path = Path(args.output)
    else:
        # Use project root relative path with date
        project_root = Path(__file__).parent.parent
        today = datetime.now().strftime('%Y-%m-%d')
        output_path = project_root / 'data' / f'news_digest_{today}.md'

    # Validate input file
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # Print header
    print("\n🤖 NoBS News Summarizer\n")
    logger.info(f"Input: {input_path}")
    logger.info(f"Output: {output_path}")

    # Check for API key
    api_key = Config.OPENROUTER_API_KEY or Config.OPENAI_API_KEY
    if not api_key:
        logger.error("\n❌ No LLM API key found!")
        logger.error("\nPlease set one of the following environment variables:")
        logger.error("  - OPENROUTER_API_KEY (recommended)")
        logger.error("  - OPENAI_API_KEY")
        logger.error("\nGet an OpenRouter key at: https://openrouter.ai/keys")
        sys.exit(1)

    # Determine model and settings
    model = args.model or Config.LLM_MODEL
    max_articles = args.max_articles or Config.MAX_ARTICLES_PER_CATEGORY

    logger.info(f"Model: {model}")
    logger.info(f"Max articles per category: {max_articles}")

    try:
        # Load articles
        print("\n📥 Loading articles...")
        articles = load_articles_from_json(input_path)
        logger.info(f"Loaded {len(articles)} articles")

        if not articles:
            logger.error("No articles found in input file")
            sys.exit(1)

        # Categorize articles
        print("\n🏷️  Categorizing articles...")
        categorized = categorize_articles(articles)

        # Show categorization stats
        for category, arts in categorized.items():
            if arts:
                logger.info(f"  {category}: {len(arts)} articles")

        # Deduplicate articles
        print("\n🔍 Deduplicating articles...")
        original_total = sum(len(arts) for arts in categorized.values())
        deduped = deduplicate_by_category(categorized)
        deduped_total = sum(len(arts) for arts in deduped.values())
        duplicates_removed = original_total - deduped_total

        logger.info(f"Removed {duplicates_removed} duplicates ({deduped_total} unique articles)")

        # Show dedup stats per category
        for category, arts in deduped.items():
            if arts:
                original = len(categorized[category])
                removed = original - len(arts)
                if removed > 0:
                    logger.debug(f"  {category}: removed {removed} duplicates")

        # Initialize summarizer
        print("\n🤖 Initializing LLM summarizer...")
        summarizer = NewsSummarizer(
            model=model,
            api_key=api_key,
            max_articles_per_category=max_articles
        )

        # Generate digest
        print("\n✨ Generating digest with AI summaries...")
        print("   (This may take 1-3 minutes depending on article count)\n")

        digest = summarizer.generate_digest(
            deduped,
            show_progress=not args.no_progress
        )

        # Format as Markdown
        markdown = summarizer.format_digest_markdown(digest)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save digest
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"\n✅ Digest saved to: {output_path}")

        # Print summary stats
        print(f"\n📊 Summary:")
        print(f"  Total articles: {digest.total_articles}")
        print(f"  Unique articles: {digest.total_unique_articles}")
        print(f"  Categories: {len(digest.categories)}")
        print(f"  Sources: {len(digest.sources)}")

        # Print category breakdown
        print(f"\n📂 Category Breakdown:")
        for cat_summary in digest.categories:
            info = summarizer.CATEGORY_INFO[cat_summary.category]
            print(f"  {info['emoji']} {info['name']}: {cat_summary.article_count} articles")

        print(f"\n✨ Done! Check {output_path} for your news digest.\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
