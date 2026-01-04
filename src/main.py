from flask import Flask, render_template, request, jsonify
import feedparser
import concurrent.futures
import logging
import pytz
from datetime import datetime
import os
import html2text
import urllib.parse
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from config import Config

# Import summarization modules (optional - only used if GENERATE_DIGEST is enabled)
try:
    from news_categorizer import categorize_articles, deduplicate_by_category
    from news_summarizer import NewsSummarizer
    SUMMARIZATION_AVAILABLE = True
except ImportError:
    SUMMARIZATION_AVAILABLE = False
    app.logger.warning("Summarization modules not available. Install dependencies: pip install litellm tqdm")

# Set template folder to parent directory's templates folder
app = Flask(__name__, template_folder='../templates')

# Configure Flask's logger
app.logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
app.logger.addHandler(handler)


@dataclass
class Article:
    """Represents a news article from RSS feed."""
    title: str
    link: str
    published: str
    summary: str
    published_parsed: Optional[tuple] = None

    @classmethod
    def from_feed_entry(cls, entry: Any) -> 'Article':
        """Create Article from feedparser entry with validation.

        Args:
            entry: Feedparser entry object containing article data

        Returns:
            Article instance with data from feed entry
        """
        return cls(
            title=getattr(entry, 'title', 'Untitled'),
            link=getattr(entry, 'link', ''),
            published=getattr(entry, 'published', ''),
            summary=getattr(entry, 'summary', ''),
            published_parsed=getattr(entry, 'published_parsed', None)
        )


def validate_article(article: Any) -> bool:
    """Check if article has required fields.

    Args:
        article: Article or entry object to validate

    Returns:
        True if article has all required fields, False otherwise
    """
    return (
        hasattr(article, 'title') and article.title and
        hasattr(article, 'link') and article.link and
        hasattr(article, 'published') and
        hasattr(article, 'summary')
    )


def fetch_feed_data(url: str) -> Optional[Dict[str, Any]]:
    """Fetch RSS feed data with error handling.

    Args:
        url: RSS feed URL to fetch

    Returns:
        Dictionary with 'feed_title' and 'articles' keys, or None on failure
    """
    try:
        feed = feedparser.parse(url)
        if not hasattr(feed, 'feed') or not hasattr(feed.feed, 'title'):
            app.logger.warning(f"Invalid feed structure from {url}")
            return None
        return {
            "feed_title": feed.feed.title,
            "articles": feed.entries
        }
    except Exception as e:
        app.logger.error(f"Failed to fetch feed {url}: {str(e)}")
        return None


def convert_to_cdt_time(published_time: str) -> str:
    """Convert published time to configured timezone with error handling.

    Args:
        published_time: Time string from RSS feed

    Returns:
        Formatted time string in configured timezone, or original on error
    """
    try:
        cdt_timezone = pytz.timezone(Config.TIMEZONE)

        # Split the published time string into parts
        parts = published_time.split()

        if len(parts) < 5:
            return published_time  # Return original if can't parse

        # Extract date and time components
        date_str = ' '.join(parts[1:4])
        time_str = parts[4]

        # Parse the date and time components
        parsed_time = datetime.strptime(date_str + ' ' + time_str,
                                        "%d %b %Y %H:%M:%S")

        # Set the timezone to CDT
        cdt_time = cdt_timezone.localize(parsed_time)

        return cdt_time.strftime("%a, %d %b %Y %H:%M:%S %Z")
    except (ValueError, IndexError) as e:
        app.logger.warning(f"Failed to convert time '{published_time}': {str(e)}")
        return published_time  # Fallback to original


def deduplicate_articles(articles: List[Article]) -> List[Article]:
    """Remove duplicate articles based on title (per-request deduplication).

    Args:
        articles: List of Article objects

    Returns:
        List of unique Article objects (duplicates removed)
    """
    original_count = len(articles)
    seen = set()
    unique = []
    for article in articles:
        if hasattr(article, 'title') and article.title not in seen:
            seen.add(article.title)
            unique.append(article)

    duplicates = original_count - len(unique)
    if duplicates > 0:
        app.logger.info(f"Removed {duplicates} duplicate articles ({len(unique)} unique)")

    return unique


def clean_html(html_content: str) -> str:
    """Convert HTML content to plain text.

    Args:
        html_content: HTML string to convert

    Returns:
        Plain text version of HTML content
    """
    # Create an instance of the html2text converter
    h = html2text.HTML2Text()
    h.ignore_links = Config.HTML2TEXT_IGNORE_LINKS

    # Convert the HTML content to plain text
    text_content = h.handle(html_content)

    return text_content


def fetch_all_feeds(feed_urls: List[str]) -> List[Dict[str, Any]]:
    """Fetch all RSS feeds in parallel and filter out failures.

    Args:
        feed_urls: List of RSS feed URLs to fetch

    Returns:
        List of successfully fetched feed data dictionaries
    """
    app.logger.info(f"Fetching {len(feed_urls)} RSS feeds...")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        feed_data_list = list(executor.map(fetch_feed_data, feed_urls))

    # Filter out None results from failed feeds
    successful_feeds = [feed for feed in feed_data_list if feed is not None]
    failed_count = len(feed_urls) - len(successful_feeds)

    if failed_count > 0:
        app.logger.warning(f"Failed to fetch {failed_count} of {len(feed_urls)} feeds")

    app.logger.info(f"Successfully fetched {len(successful_feeds)} feeds")
    return successful_feeds


def transform_article_url(url: str) -> str:
    """Transform article URL to archive service URL.

    Args:
        url: Original article URL

    Returns:
        Archive service URL with encoded original URL
    """
    url_without_query = url.split('?')[0]
    encoded_url = urllib.parse.quote_plus(url_without_query)
    return Config.ARCHIVE_SERVICE_URL + encoded_url


def process_articles(feed_data_list: List[Dict[str, Any]]) -> List[Article]:
    """Process articles from feed data: convert to Article objects, transform URLs and clean HTML.

    Args:
        feed_data_list: List of feed data dictionaries

    Returns:
        List of processed Article objects
    """
    all_articles = []
    skipped = 0

    for feed_data in feed_data_list:
        feed_title = feed_data.get("feed_title", "Unknown")
        article_count = len(feed_data["articles"])
        app.logger.debug(f"Processing {article_count} articles from '{feed_title}'")

        for entry in feed_data["articles"]:
            # Validate entry has required fields
            if not validate_article(entry):
                skipped += 1
                continue

            # Create Article from feed entry
            article = Article.from_feed_entry(entry)

            # Transform article URL to archive URL
            article.link = transform_article_url(article.link)

            # Clean the HTML content to remove tags
            article.summary = clean_html(article.summary)

            all_articles.append(article)

    if skipped > 0:
        app.logger.warning(f"Skipped {skipped} invalid articles")

    app.logger.info(f"Processed {len(all_articles)} articles")
    return all_articles


def sort_by_date(articles: List[Article]) -> List[Article]:
    """Sort articles by publication time (newest first).

    Args:
        articles: List of Article objects to sort

    Returns:
        Sorted list of Article objects (in-place sort)
    """
    articles.sort(key=lambda x: x.published_parsed, reverse=True)
    return articles


def convert_article_times(articles: List[Article]) -> List[Article]:
    """Convert all article published times to configured timezone.

    Args:
        articles: List of Article objects

    Returns:
        List of Article objects with converted timestamps
    """
    app.logger.debug(f"Converting {len(articles)} article timestamps to {Config.TIMEZONE}")
    for article in articles:
        article.published = convert_to_cdt_time(article.published)
    return articles


def render_html(articles: List[Article]) -> str:
    """Render the HTML template with articles.

    Args:
        articles: List of Article objects to render

    Returns:
        Rendered HTML string
    """
    return render_template("index.html", all_articles=articles)


@app.route("/")
def index() -> str:
    """Main route: fetch, process, and render news articles.

    Returns:
        Rendered HTML page with aggregated news articles
    """
    app.logger.info("=== Starting news aggregation ===")

    # Fetch feeds
    feed_data_list = fetch_all_feeds(Config.RSS_FEED_URLS)

    # Process articles
    all_articles = process_articles(feed_data_list)

    # Deduplicate
    all_articles = deduplicate_articles(all_articles)

    # Sort by date
    all_articles = sort_by_date(all_articles)

    # Convert times to configured timezone
    all_articles = convert_article_times(all_articles)

    # Save articles to JSON file
    save_articles_to_file(all_articles)

    # Generate AI digest (if enabled)
    digest_path = generate_news_digest(all_articles)
    if digest_path:
        app.logger.info(f"Digest available at: {digest_path}")

    # Render HTML for Flask response
    html = render_html(all_articles)

    app.logger.info(
        f"=== Completed: Displaying {len(all_articles)} articles from {len(feed_data_list)} feeds ==="
    )

    return html


@app.route('/shutdown', methods=['POST'])
def shutdown():
    # Shutdown the Flask app gracefully
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()
    return jsonify({'message': 'Shutting down...'})


# Function to save articles as JSON to a file
def save_articles_to_file(articles: List[Article]) -> None:
    """Save articles as JSON to file for client-side rendering.

    Args:
        articles: List of Article objects to save
    """
    import json

    articles_data = []
    for article in articles:
        articles_data.append({
            'title': article.title,
            'link': article.link,
            'published': article.published,
            'summary': article.summary
        })

    # Ensure the output directory exists
    output_dir = os.path.dirname(Config.OUTPUT_FILENAME)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        app.logger.info(f"Created output directory: {output_dir}")

    with open(Config.OUTPUT_FILENAME, 'w', encoding='utf-8') as file:
        json.dump(articles_data, file, indent=2, ensure_ascii=False)

    app.logger.info(f"Saved {len(articles_data)} articles to {Config.OUTPUT_FILENAME}")


def generate_news_digest(articles: List[Article]) -> Optional[str]:
    """
    Generate AI-powered news digest from articles.

    Args:
        articles: List of Article objects

    Returns:
        Path to generated digest file, or None if generation fails/disabled
    """
    # Check if digest generation is enabled
    if not Config.GENERATE_DIGEST:
        app.logger.debug("Digest generation disabled (GENERATE_DIGEST=false)")
        return None

    # Check if summarization modules are available
    if not SUMMARIZATION_AVAILABLE:
        app.logger.warning("Digest generation enabled but summarization modules not available")
        return None

    # Check for API key
    api_key = Config.OPENROUTER_API_KEY or Config.OPENAI_API_KEY
    if not api_key:
        app.logger.warning("Digest generation enabled but no LLM API key found")
        app.logger.warning("Set OPENROUTER_API_KEY or OPENAI_API_KEY to enable digest generation")
        return None

    try:
        app.logger.info("=== Starting digest generation ===")

        # Categorize articles
        app.logger.info("Categorizing articles...")
        categorized = categorize_articles(articles)

        # Log categorization stats
        for category, arts in categorized.items():
            if arts:
                app.logger.debug(f"  {category}: {len(arts)} articles")

        # Deduplicate within categories
        app.logger.info("Deduplicating articles...")
        original_total = sum(len(arts) for arts in categorized.values())
        deduped = deduplicate_by_category(categorized)
        deduped_total = sum(len(arts) for arts in deduped.values())
        duplicates_removed = original_total - deduped_total

        app.logger.info(f"Removed {duplicates_removed} duplicates ({deduped_total} unique articles)")

        # Initialize summarizer
        app.logger.info(f"Initializing summarizer with model: {Config.LLM_MODEL}")
        summarizer = NewsSummarizer(
            model=Config.LLM_MODEL,
            api_key=api_key,
            max_articles_per_category=Config.MAX_ARTICLES_PER_CATEGORY
        )

        # Generate digest (without progress bar for Flask)
        app.logger.info("Generating digest summaries...")
        digest = summarizer.generate_digest(deduped, show_progress=False)

        # Format as Markdown
        markdown = summarizer.format_digest_markdown(digest)

        # Save digest (single file, always updated)
        digest_path = os.path.join(
            os.path.dirname(Config.OUTPUT_FILENAME),
            'news_digest.md'
        )

        with open(digest_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        app.logger.info(f"Digest saved to: {digest_path}")
        app.logger.info(f"  Total articles: {digest.total_articles}")
        app.logger.info(f"  Unique articles: {digest.total_unique_articles}")
        app.logger.info(f"  Categories: {len(digest.categories)}")
        app.logger.info("=== Digest generation complete ===")

        return digest_path

    except Exception as e:
        app.logger.error(f"Error generating digest: {e}")
        import traceback
        app.logger.debug(traceback.format_exc())
        return None


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
